use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::EdgeRef;
use std::collections::HashMap;
use crate::models::{Junction, Network, Road};

pub fn to_petgraph(network: &Network) -> DiGraph<Junction, Road> {
    let mut graph = DiGraph::new();
    let mut node_map = HashMap::new();

    for junction in &network.junctions {
        let idx = graph.add_node(junction.clone());
        node_map.insert(junction.id.clone(), idx);
    }

    for road in &network.roads {
        if let (Some(&src), Some(&tgt)) = (node_map.get(&road.source), node_map.get(&road.target)) {
            graph.add_edge(src, tgt, road.clone());
        }
    }

    graph
}

pub fn validate_flow_conservation(network: &Network, flows: &HashMap<String, f64>) -> Result<(), Vec<String>> {
    let mut violations = Vec::new();

    for junction in &network.junctions {
        let inflow: f64 = network.roads.iter()
            .filter(|r| r.target == junction.id)
            .map(|r| flows.get(&r.id).copied().unwrap_or(0.0))
            .sum();

        let outflow: f64 = network.roads.iter()
            .filter(|r| r.source == junction.id)
            .map(|r| flows.get(&r.id).copied().unwrap_or(0.0))
            .sum();

        let net_flow = inflow - outflow;
        if (net_flow - junction.external_flow).abs() > 1e-6 {
            violations.push(format!(
                "Junction {}: inflow - outflow = {:.2f}, expected {:.2f}",
                junction.id, net_flow, junction.external_flow
            ));
        }
    }

    if violations.is_empty() {
        Ok(())
    } else {
        Err(violations)
    }
}

pub fn validate_capacities(network: &Network, flows: &HashMap<String, f64>) -> Result<(), Vec<String>> {
    let mut violations = Vec::new();

    for road in &network.roads {
        let flow = flows.get(&road.id).copied().unwrap_or(0.0);
        if flow < -1e-6 {
            violations.push(format!("Road {}: negative flow {:.2f}", road.id, flow));
        }
        if flow > road.capacity + 1e-6 {
            violations.push(format!(
                "Road {}: flow {:.2f} exceeds capacity {:.2f}",
                road.id, flow, road.capacity
            ));
        }
    }

    if violations.is_empty() {
        Ok(())
    } else {
        Err(violations)
    }
}

pub fn validate_connectivity(network: &Network) -> Result<(), Vec<String>> {
    let graph = to_petgraph(network);
    let mut violations = Vec::new();

    if !petgraph::algo::is_connected(graph.as_undirected()) {
        violations.push("Network is not weakly connected".to_string());
    }

    let sources: Vec<_> = network.junctions.iter()
        .filter(|j| j.external_flow > 0.0)
        .collect();
    let sinks: Vec<_> = network.junctions.iter()
        .filter(|j| j.external_flow < 0.0)
        .collect();

    if sources.is_empty() {
        violations.push("No source junctions (external_flow > 0)".to_string());
    }
    if sinks.is_empty() {
        violations.push("No sink junctions (external_flow < 0)".to_string());
    }

    for source in sources {
        for sink in sinks {
            let src_idx = graph.node_indices().find(|n| graph[*n].id == source.id);
            let tgt_idx = graph.node_indices().find(|n| graph[*n].id == sink.id);

            if let (Some(src), Some(tgt)) = (src_idx, tgt_idx) {
                if !petgraph::algo::has_path_connecting(&graph, src, tgt, None) {
                    violations.push(format!(
                        "No path from source {} to sink {}",
                        source.id, sink.id
                    ));
                }
            }
        }
    }

    if violations.is_empty() {
        Ok(())
    } else {
        Err(violations)
    }
}

pub fn validate_network(network: &Network, flows: &HashMap<String, f64>) -> Result<(), Vec<String>> {
    let mut all_violations = Vec::new();

    if let Err(v) = validate_flow_conservation(network, flows) {
        all_violations.extend(v);
    }
    if let Err(v) = validate_capacities(network, flows) {
        all_violations.extend(v);
    }
    if let Err(v) = validate_connectivity(network) {
        all_violations.extend(v);
    }

    if all_violations.is_empty() {
        Ok(())
    } else {
        Err(all_violations)
    }
}