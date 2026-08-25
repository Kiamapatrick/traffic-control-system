use crate::models::{Network, FlowSolution, SolverMethod, OptimizationObjective};
use crate::network::validate_network;
use std::collections::HashMap;

#[derive(Debug, thiserror::Error)]
pub enum SimplexError {
    #[error("No feasible solution")]
    NoFeasibleSolution,
    #[error("Unbounded")]
    Unbounded,
    #[error("Iteration limit exceeded")]
    IterationLimit,
}

pub fn solve_simplex(network: &Network, objective: Option<OptimizationObjective>) -> FlowSolution {
    let n_junctions = network.junctions.len();
    let n_roads = network.roads.len();

    if n_roads == 0 {
        return FlowSolution {
            flows: HashMap::new(),
            method: SolverMethod::Simplex,
            objective,
            objective_value: None,
            is_feasible: false,
            violations: vec!["Network has no roads".to_string()],
            metadata: HashMap::new(),
        };
    }

    let mut tableau = build_tableau(network, objective);
    let mut basis = (0..n_junctions).collect::<Vec<_>>();

    let mut iterations = 0;
    let max_iterations = 1000;

    while iterations < max_iterations {
        if let Some(entering) = find_entering_variable(&tableau) {
            if let Some(leaving) = find_leaving_variable(&tableau, entering) {
                pivot(&mut tableau, leaving, entering);
                basis[leaving] = entering;
                iterations += 1;
            } else {
                return FlowSolution {
                    flows: extract_flows(&tableau, network, &basis),
                    method: SolverMethod::Simplex,
                    objective,
                    objective_value: Some(tableau[(n_junctions, n_junctions + n_roads)]),
                    is_feasible: false,
                    violations: vec!["Problem is unbounded".to_string()],
                    metadata: HashMap::new(),
                };
            }
        } else {
            break;
        }
    }

    let flows = extract_flows(&tableau, network, &basis);
    let mut violations = Vec::new();
    if let Err(v) = validate_network(network, &flows) {
        violations = v;
    }

    FlowSolution {
        flows,
        method: SolverMethod::Simplex,
        objective,
        objective_value: Some(-tableau[(n_junctions, n_junctions + n_roads)]),
        is_feasible: violations.is_empty(),
        violations,
        metadata: {
            let mut m = HashMap::new();
            m.insert("iterations".to_string(), serde_json::Value::Number(serde_json::Number::from(iterations)));
            m
        },
    }
}

fn build_tableau(network: &Network, objective: Option<OptimizationObjective>) -> Vec<Vec<f64>> {
    let n_junctions = network.junctions.len();
    let n_roads = network.roads.len();

    let junction_to_idx: HashMap<_, _> = network.junctions.iter()
        .enumerate()
        .map(|(i, j)| (j.id.clone(), i))
        .collect();

    let road_to_idx: HashMap<_, _> = network.roads.iter()
        .enumerate()
        .map(|(i, r)| (r.id.clone(), i))
        .collect();

    let mut tableau = vec![vec![0.0; n_junctions + n_roads + 1]; n_junctions + 1];

    for road in &network.roads {
        let j_src = junction_to_idx[&road.source];
        let j_tgt = junction_to_idx[&road.target];
        let r_idx = road_to_idx[&road.id];

        tableau[j_src][n_junctions + r_idx] = -1.0;
        tableau[j_tgt][n_junctions + r_idx] = 1.0;
    }

    for (i, junction) in network.junctions.iter().enumerate() {
        tableau[i][n_junctions + n_roads] = junction.external_flow;
    }

    match objective.unwrap_or(OptimizationObjective::MinCost) {
        OptimizationObjective::MinCost => {
            for road in &network.roads {
                let r_idx = road_to_idx[&road.id];
                tableau[n_junctions][n_junctions + r_idx] = road.cost_per_unit;
            }
        }
        OptimizationObjective::MaxThroughput => {
            for r_idx in 0..n_roads {
                tableau[n_junctions][n_junctions + r_idx] = -1.0;
            }
        }
        OptimizationObjective::MinTravelTime => {
            for road in &network.roads {
                let r_idx = road_to_idx[&road.id];
                tableau[n_junctions][n_junctions + r_idx] = road.length / road.free_flow_speed;
            }
        }
        OptimizationObjective::BalanceLoad => {
            for road in &network.roads {
                let r_idx = road_to_idx[&road.id];
                tableau[n_junctions][n_junctions + r_idx] = (1.0 / road.capacity).powi(2);
            }
        }
    }

    for i in 0..n_junctions {
        tableau[n_junctions][i] = -tableau[i].iter().sum::<f64>();
    }
    tableau[n_junctions][n_junctions + n_roads] = -tableau.iter().take(n_junctions)
        .map(|row| row[n_junctions + n_roads]).sum::<f64>();

    tableau
}

fn find_entering_variable(tableau: &[Vec<f64>]) -> Option<usize> {
    let n = tableau[0].len() - 1;
    let last_row = tableau.len() - 1;

    tableau[last_row].iter()
        .take(n)
        .enumerate()
        .filter(|(_, &v)| v > 1e-9)
        .max_by(|a, b| a.1.partial_cmp(b.1).unwrap())
        .map(|(i, _)| i)
}

fn find_leaving_variable(tableau: &[Vec<f64>], entering: usize) -> Option<usize> {
    let n_rows = tableau.len() - 1;
    let rhs_col = tableau[0].len() - 1;

    let mut min_ratio = f64::INFINITY;
    let mut leaving = None;

    for i in 0..n_rows {
        let coeff = tableau[i][entering];
        if coeff > 1e-9 {
            let ratio = tableau[i][rhs_col] / coeff;
            if ratio < min_ratio {
                min_ratio = ratio;
                leaving = Some(i);
            }
        }
    }

    leaving
}

fn pivot(tableau: &mut [Vec<f64>], leaving: usize, entering: usize) {
    let pivot_val = tableau[leaving][entering];
    let n_cols = tableau[0].len();

    for j in 0..n_cols {
        tableau[leaving][j] /= pivot_val;
    }

    for i in 0..tableau.len() {
        if i != leaving {
            let factor = tableau[i][entering];
            if factor.abs() > 1e-9 {
                for j in 0..n_cols {
                    tableau[i][j] -= factor * tableau[leaving][j];
                }
            }
        }
    }
}

fn extract_flows(tableau: &[Vec<f64>], network: &Network, basis: &[usize]) -> HashMap<String, f64> {
    let n_junctions = network.junctions.len();
    let mut flows = HashMap::new();

    let road_to_idx: HashMap<_, _> = network.roads.iter()
        .enumerate()
        .map(|(i, r)| (r.id.clone(), i))
        .collect();

    for (i, &basic_var) in basis.iter().enumerate() {
        if basic_var >= n_junctions {
            let road_idx = basic_var - n_junctions;
            for (road_id, &idx) in &road_to_idx {
                if idx == road_idx {
                    flows.insert(road_id.clone(), tableau[i][n_junctions + n_roads].max(0.0));
                    break;
                }
            }
        }
    }

    for road in &network.roads {
        flows.entry(road.id.clone()).or_insert(0.0);
    }

    flows
}