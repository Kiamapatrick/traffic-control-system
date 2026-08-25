use traffic_control_rs::{Network, Junction, Road, JunctionType, solve_rref, solve_simplex, dinic, edmonds_karp, validate_network};

fn four_junction_network() -> Network {
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

#[test]
fn test_rref_solver() {
    let network = four_junction_network();
    let solution = solve_rref(&network);
    assert!(solution.is_feasible);
    assert_eq!(solution.flows.len(), 5);
}

#[test]
fn test_simplex_solver() {
    let network = four_junction_network();
    let solution = solve_simplex(&network, None);
    assert!(solution.is_feasible);
    assert!(solution.objective_value.is_some());
}

#[test]
fn test_dinic_max_flow() {
    let network = four_junction_network();
    let solution = dinic(&network, "A", "C").unwrap();
    assert!(solution.is_feasible);
    assert!(solution.objective_value.unwrap() > 0.0);
}

#[test]
fn test_edmonds_karp_max_flow() {
    let network = four_junction_network();
    let solution = edmonds_karp(&network, "A", "C").unwrap();
    assert!(solution.is_feasible);
    assert!(solution.objective_value.unwrap() > 0.0);
}

#[test]
fn test_validation() {
    let network = four_junction_network();
    let solution = solve_rref(&network);
    assert!(validate_network(&network, &solution.flows).is_ok());
}

#[test]
fn test_validation_fails_on_bad_flow() {
    let network = four_junction_network();
    let mut bad_flows = std::collections::HashMap::new();
    bad_flows.insert("x1".to_string(), 1000.0);
    assert!(validate_network(&network, &bad_flows).is_err());
}