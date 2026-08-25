use clap::{Parser, Subcommand};
use traffic_control_rs::{Network, solve_rref, solve_simplex, dinic, edmonds_karp, validate_network, FlowSolution};
use std::fs;
use std::time::Instant;

#[derive(Parser)]
#[command(name = "traffic-control-rs")]
#[command(about = "High-performance traffic flow solver in Rust")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    Solve {
        #[arg(short, long)]
        network: String,
        #[arg(short, long, default_value = "rref")]
        method: String,
        #[arg(short, long, default_value = "min_cost")]
        objective: String,
        #[arg(long)]
        source: Option<String>,
        #[arg(long)]
        sink: Option<String>,
        #[arg(short, long)]
        output: Option<String>,
    },
    Validate {
        #[arg(short, long)]
        network: String,
        #[arg(short, long)]
        solution: Option<String>,
    },
    Benchmark {
        #[arg(short, long)]
        network: String,
        #[arg(short, long, default_value = "10")]
        runs: usize,
    },
    Generate {
        #[arg(long, default_value = "four-junction")]
        type: String,
        #[arg(short, long)]
        output: String,
    },
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Solve { network, method, objective, source, sink, output } => {
            let json = fs::read_to_string(&network)?;
            let net: Network = serde_json::from_str(&json)?;

            let start = Instant::now();
            let solution = match method.as_str() {
                "rref" => solve_rref(&net),
                "simplex" => solve_simplex(&net, Some(parse_objective(&objective)?)),
                "max-flow" => {
                    let src = source.ok_or("MAX_FLOW requires --source")?;
                    let snk = sink.ok_or("MAX_FLOW requires --sink")?;
                    edmonds_karp(&net, &src, &snk)?
                }
                "dinic" => {
                    let src = source.ok_or("DINIC requires --source")?;
                    let snk = sink.ok_or("DINIC requires --sink")?;
                    dinic(&net, &src, &snk)?
                }
                _ => return Err(format!("Unknown method: {}", method).into()),
            };
            let elapsed = start.elapsed().as_millis();

            print_solution(&solution, &net);
            println!("\nSolve time: {}ms", elapsed);

            if let Some(out_path) = output {
                let json = serde_json::to_string_pretty(&solution)?;
                fs::write(out_path, json)?;
                println!("Solution saved to {}", out_path);
            }
        }
        Commands::Validate { network, solution } => {
            let json = fs::read_to_string(&network)?;
            let net: Network = serde_json::from_str(&json)?;

            let flows = if let Some(sol_path) = solution {
                let sol_json = fs::read_to_string(sol_path)?;
                let sol: FlowSolution = serde_json::from_str(&sol_json)?;
                sol.flows
            } else {
                net.roads.iter().map(|r| (r.id.clone(), r.flow)).collect()
            };

            match validate_network(&net, &flows) {
                Ok(_) => println!("✓ Network is valid"),
                Err(violations) => {
                    println!("✗ Network has violations:");
                    for v in violations {
                        println!("  - {}", v);
                    }
                    std::process::exit(1);
                }
            }
        }
        Commands::Benchmark { network, runs } => {
            let json = fs::read_to_string(&network)?;
            let net: Network = serde_json::from_str(&json)?;

            let methods = [
                ("rref", || solve_rref(&net)),
                ("simplex", || solve_simplex(&net, None)),
            ];

            for (name, solver) in methods {
                let mut times = Vec::new();
                for _ in 0..runs {
                    let start = Instant::now();
                    let _ = solver();
                    times.push(start.elapsed().as_millis());
                }
                let mean = times.iter().sum::<u128>() as f64 / runs as f64;
                let std = (times.iter().map(|t| (*t as f64 - mean).powi(2)).sum::<f64>() / runs as f64).sqrt();
                println!("{}: {:.2}±{:.2}ms (min={}, max={})", name, mean, std, times.iter().min().unwrap(), times.iter().max().unwrap());
            }
        }
        Commands::Generate { type, output } => {
            let net = match type.as_str() {
                "four-junction" => generate_four_junction(),
                _ => return Err(format!("Unknown type: {}", type).into()),
            };
            let json = serde_json::to_string_pretty(&net)?;
            fs::write(output, json)?;
            println!("Generated {} network saved to {}", type, output);
        }
    }

    Ok(())
}

fn parse_objective(s: &str) -> Result<traffic_control_rs::OptimizationObjective, String> {
    match s {
        "min_cost" => Ok(traffic_control_rs::OptimizationObjective::MinCost),
        "max_throughput" => Ok(traffic_control_rs::OptimizationObjective::MaxThroughput),
        "min_travel_time" => Ok(traffic_control_rs::OptimizationObjective::MinTravelTime),
        "balance_load" => Ok(traffic_control_rs::OptimizationObjective::BalanceLoad),
        _ => Err(format!("Unknown objective: {}", s)),
    }
}

fn print_solution(solution: &FlowSolution, network: &Network) {
    println!("Method: {:?}", solution.method);
    println!("Feasible: {}", solution.is_feasible);
    if let Some(obj) = solution.objective_value {
        println!("Objective value: {:.2}", obj);
    }
    println!("\nFlows:");
    for (road_id, flow) in &solution.flows {
        let cap = network.roads.iter().find(|r| r.id == *road_id).map(|r| r.capacity).unwrap_or(0.0);
        println!("  {}: {:.2} / {:.0} ({:.1}%)", road_id, flow, cap, if cap > 0.0 { flow / cap * 100.0 } else { 0.0 });
    }
    if !solution.violations.is_empty() {
        println!("\nViolations:");
        for v in &solution.violations {
            println!("  - {}", v);
        }
    }
}

fn generate_four_junction() -> Network {
    use traffic_control_rs::{Junction, Road, JunctionType};
    Network {
        junctions: vec![
            Junction { id: "A".into(), position: [200.0, 600.0], junction_type: JunctionType::Source, external_flow: 80.0 },
            Junction { id: "B".into(), position: [800.0, 600.0], junction_type: JunctionType::Sink, external_flow: -30.0 },
            Junction { id: "C".into(), position: [800.0, 200.0], junction_type: JunctionType::Source, external_flow: 50.0 },
            Junction { id: "D".into(), position: [200.0, 200.0], junction_type: JunctionType::Sink, external_flow: -60.0 },
        ],
        roads: vec![
            Road { id: "x1".into(), source: "A".into(), target: "B".into(), capacity: 100.0, length: 6.0, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 1 },
            Road { id: "x2".into(), source: "B".into(), target: "C".into(), capacity: 100.0, length: 4.0, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 1 },
            Road { id: "x3".into(), source: "C".into(), target: "D".into(), capacity: 100.0, length: 6.0, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 1 },
            Road { id: "x4".into(), source: "D".into(), target: "A".into(), capacity: 100.0, length: 4.0, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 1 },
            Road { id: "x5".into(), source: "B".into(), target: "D".into(), capacity: 100.0, length: 6.3, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 1 },
        ],
        metadata: std::collections::HashMap::new(),
    }
}