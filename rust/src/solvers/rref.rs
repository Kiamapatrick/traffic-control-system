use nalgebra::{DMatrix, DVector};
use crate::models::{Network, FlowSolution, SolverMethod};
use crate::network::validate_network;
use std::collections::HashMap;

#[derive(Debug, thiserror::Error)]
pub enum RrefError {
    #[error("Matrix shape mismatch: {0}")]
    ShapeMismatch(String),
    #[error("Singular matrix")]
    Singular,
    #[error("No feasible solution")]
    NoFeasibleSolution,
}

pub fn build_system_matrix(network: &Network) -> (DMatrix<f64>, DVector<f64>, Vec<String>) {
    let n_junctions = network.junctions.len();
    let n_roads = network.roads.len();

    let mut a = DMatrix::zeros(n_junctions, n_roads);
    let mut b = DVector::zeros(n_junctions);

    let junction_to_idx: HashMap<_, _> = network.junctions.iter()
        .enumerate()
        .map(|(i, j)| (j.id.clone(), i))
        .collect();

    let road_to_idx: HashMap<_, _> = network.roads.iter()
        .enumerate()
        .map(|(i, r)| (r.id.clone(), i))
        .collect();

    for road in &network.roads {
        let j_src = junction_to_idx[&road.source];
        let j_tgt = junction_to_idx[&road.target];
        let r_idx = road_to_idx[&road.id];
        a[(j_src, r_idx)] = -1.0;
        a[(j_tgt, r_idx)] = 1.0;
    }

    for junction in &network.junctions {
        let idx = junction_to_idx[&junction.id];
        b[idx] = junction.external_flow;
    }

    let road_ids: Vec<String> = network.roads.iter().map(|r| r.id.clone()).collect();

    (a, b, road_ids)
}

pub fn rref_solve(a: &DMatrix<f64>, b: &DVector<f64>, tol: f64) -> Result<(DVector<f64>, DMatrix<f64>, Vec<usize>), RrefError> {
    let (m, n) = a.shape();
    if m != b.len() {
        return Err(RrefError::ShapeMismatch(format!("A={}x{}, b={}", m, n, b.len())));
    }

    let mut m_aug = DMatrix::zeros(m, n + 1);
    m_aug.view_mut((0, 0), (m, n)).copy_from(a);
    m_aug.column_mut(n).copy_from(b);

    let mut pivot_cols = Vec::new();
    let mut row = 0;

    for col in 0..n {
        if row >= m {
            break;
        }

        let mut max_row = row;
        let mut max_val = m_aug[(row, col)].abs();
        for r in (row + 1)..m {
            let val = m_aug[(r, col)].abs();
            if val > max_val {
                max_val = val;
                max_row = r;
            }
        }

        if max_val < tol {
            continue;
        }

        if max_row != row {
            m_aug.swap_rows(row, max_row);
        }

        let pivot = m_aug[(row, col)];
        for c in col..=n {
            m_aug[(row, c)] /= pivot;
        }

        for r in 0..m {
            if r != row {
                let factor = m_aug[(r, col)];
                if factor.abs() > tol {
                    for c in col..=n {
                        m_aug[(r, c)] -= factor * m_aug[(row, c)];
                    }
                }
            }
        }

        pivot_cols.push(col);
        row += 1;
    }

    let rank = pivot_cols.len();
    if rank == 0 {
        return Ok((DVector::zeros(n), DMatrix::zeros(n, 0), pivot_cols));
    }

    let mut particular = DVector::zeros(n);
    for (i, &pc) in pivot_cols.iter().enumerate() {
        particular[pc] = m_aug[(i, n)];
    }

    let free_cols: Vec<usize> = (0..n).filter(|c| !pivot_cols.contains(c)).collect();
    let nullity = free_cols.len();

    let mut nullspace = DMatrix::zeros(n, nullity);
    for (j, &fc) in free_cols.iter().enumerate() {
        nullspace[(fc, j)] = 1.0;
        for (i, &pc) in pivot_cols.iter().enumerate() {
            nullspace[(pc, j)] = -m_aug[(i, fc)];
        }
    }

    Ok((particular, nullspace, pivot_cols))
}

fn get_capacity(network: &Network, road_id: &str) -> f64 {
    network.roads.iter()
        .find(|r| r.id == road_id)
        .map(|r| r.capacity)
        .unwrap_or(f64::INFINITY)
}

pub fn solve_rref(network: &Network) -> FlowSolution {
    let (a, b, road_ids) = build_system_matrix(network);
    let (particular, nullspace, pivot_cols) = rref_solve(&a, &b, 1e-10).unwrap_or_else(|e| {
        eprintln!("RREF error: {}", e);
        (DVector::zeros(a.ncols()), DMatrix::zeros(a.ncols(), 0), vec![])
    });

    let n = road_ids.len();
    let mut feasible = particular;

    if nullspace.ncols() > 0 {
        for i in 0..n {
            if feasible[i] < 0.0 {
                for j in 0..nullspace.ncols() {
                    if nullspace[(i, j)] < 0.0 {
                        feasible[i] = 0.0;
                        break;
                    }
                }
            }
            let cap = get_capacity(network, &road_ids[i]);
            if feasible[i] > cap {
                for j in 0..nullspace.ncols() {
                    if nullspace[(i, j)] > 0.0 {
                        feasible[i] = cap;
                        break;
                    }
                }
            }
        }
    } else {
        for i in 0..n {
            feasible[i] = feasible[i].max(0.0).min(get_capacity(network, &road_ids[i]));
        }
    }

    let mut flows = HashMap::new();
    for (i, road_id) in road_ids.iter().enumerate() {
        flows.insert(road_id.clone(), feasible[i].max(0.0));
    }

    let mut violations = Vec::new();
    if let Err(v) = validate_network(network, &flows) {
        violations = v;
    }

    FlowSolution {
        flows,
        method: SolverMethod::Rref,
        objective: None,
        objective_value: None,
        is_feasible: violations.is_empty(),
        violations,
        metadata: {
            let mut m = HashMap::new();
            m.insert("rank".to_string(), serde_json::Value::Number(serde_json::Number::from(pivot_cols.len())));
            m.insert("nullity".to_string(), serde_json::Value::Number(serde_json::Number::from(nullspace.ncols())));
            m.insert("pivotColumns".to_string(), serde_json::to_value(pivot_cols).unwrap());
            m
        },
    }
}