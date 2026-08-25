use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::EdgeRef;
use std::collections::{HashMap, VecDeque};
use crate::models::{Network, FlowSolution, SolverMethod};
use crate::network::to_petgraph;

#[derive(Debug, thiserror::Error)]
pub enum MaxFlowError {
    #[error("Source or sink not found")]
    NotFound,
    #[error("No path from source to sink")]
    NoPath,
}

pub fn dinic(network: &Network, source: &str, sink: &str) -> Result<FlowSolution, MaxFlowError> {
    let graph = to_petgraph(network);
    let node_map: HashMap<_, _> = graph.node_indices()
        .map(|n| (graph[n].id.clone(), n))
        .collect();

    let src = node_map.get(source).ok_or(MaxFlowError::NotFound)?;
    let sink = node_map.get(sink).ok_or(MaxFlowError::NotFound)?;

    let mut cap = HashMap::new();
    let mut flow = HashMap::new();
    let mut adj = HashMap::new();

    for edge in graph.edge_references() {
        let u = edge.source();
        let v = edge.target();
        let road = edge.weight();
        cap.insert((u, v), road.capacity);
        cap.insert((v, u), 0.0);
        flow.insert((u, v), 0.0);
        flow.insert((v, u), 0.0);

        adj.entry(u).or_insert_with(Vec::new).push(v);
        adj.entry(v).or_insert_with(Vec::new).push(u);
    }

    let mut max_flow = 0.0;

    while bfs_level(&graph, &cap, &flow, src, sink, &mut HashMap::new()) {
        let mut level = HashMap::new();
        bfs_level(&graph, &cap, &flow, src, sink, &mut level);
        let mut it = HashMap::new();

        while let Some(pushed) = dfs_blocking(&graph, &cap, &mut flow, &adj, &level, &mut it, *src, *sink, f64::INFINITY) {
            max_flow += pushed;
        }
    }

    let mut flows = HashMap::new();
    for edge in graph.edge_references() {
        let u = edge.source();
        let v = edge.target();
        let road = edge.weight();
        let f = flow.get(&(u, v)).copied().unwrap_or(0.0);
        if f > 1e-9 {
            flows.insert(road.id.clone(), f);
        }
    }

    for road in &network.roads {
        flows.entry(road.id.clone()).or_insert(0.0);
    }

    Ok(FlowSolution {
        flows,
        method: SolverMethod::Dinic,
        objective: None,
        objective_value: Some(max_flow),
        is_feasible: true,
        violations: Vec::new(),
        metadata: {
            let mut m = HashMap::new();
            m.insert("maxFlow".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(max_flow).unwrap()));
            m.insert("source".to_string(), serde_json::Value::String(source.to_string()));
            m.insert("sink".to_string(), serde_json::Value::String(sink.to_string()));
            m
        },
    })
}

fn bfs_level(
    graph: &DiGraph<crate::models::Junction, crate::models::Road>,
    cap: &HashMap<(NodeIndex, NodeIndex), f64>,
    flow: &HashMap<(NodeIndex, NodeIndex), f64>,
    src: &NodeIndex,
    sink: &NodeIndex,
    level: &mut HashMap<NodeIndex, i32>,
) -> bool {
    level.clear();
    let mut q = VecDeque::new();
    level.insert(*src, 0);
    q.push_back(*src);

    while let Some(u) = q.pop_front() {
        for edge in graph.edges(u) {
            let v = edge.target();
            let residual = cap.get(&(u, v)).copied().unwrap_or(0.0) - flow.get(&(u, v)).copied().unwrap_or(0.0);
            if residual > 1e-9 && !level.contains_key(&v) {
                level.insert(v, level[&u] + 1);
                q.push_back(v);
            }
        }
    }

    level.contains_key(sink)
}

fn dfs_blocking(
    graph: &DiGraph<crate::models::Junction, crate::models::Road>,
    cap: &HashMap<(NodeIndex, NodeIndex), f64>,
    flow: &mut HashMap<(NodeIndex, NodeIndex), f64>,
    adj: &HashMap<NodeIndex, Vec<NodeIndex>>,
    level: &HashMap<NodeIndex, i32>,
    it: &mut HashMap<NodeIndex, usize>,
    u: NodeIndex,
    sink: NodeIndex,
    f: f64,
) -> Option<f64> {
    if u == sink {
        return Some(f);
    }

    let neighbors = adj.get(&u)?;
    let start = *it.get(&u).unwrap_or(&0);

    for i in start..neighbors.len() {
        let v = neighbors[i];
        it.insert(u, i + 1);

        let residual = cap.get(&(u, v)).copied().unwrap_or(0.0) - flow.get(&(u, v)).copied().unwrap_or(0.0);
        if residual > 1e-9 && level.get(&v) == Some(level[&u] + 1) {
            if let Some(pushed) = dfs_blocking(graph, cap, flow, adj, level, it, v, sink, f.min(residual)) {
                *flow.get_mut(&(u, v)).unwrap() += pushed;
                *flow.get_mut(&(v, u)).unwrap() -= pushed;
                return Some(pushed);
            }
        }
    }

    None
}

pub fn edmonds_karp(network: &Network, source: &str, sink: &str) -> Result<FlowSolution, MaxFlowError> {
    let graph = to_petgraph(network);
    let node_map: HashMap<_, _> = graph.node_indices()
        .map(|n| (graph[n].id.clone(), n))
        .collect();

    let src = node_map.get(source).ok_or(MaxFlowError::NotFound)?;
    let sink = node_map.get(sink).ok_or(MaxFlowError::NotFound)?;

    let mut cap = HashMap::new();
    let mut flow = HashMap::new();
    let mut adj = HashMap::new();

    for edge in graph.edge_references() {
        let u = edge.source();
        let v = edge.target();
        let road = edge.weight();
        cap.insert((u, v), road.capacity);
        cap.insert((v, u), 0.0);
        flow.insert((u, v), 0.0);
        flow.insert((v, u), 0.0);
        adj.entry(u).or_insert_with(Vec::new).push(v);
        adj.entry(v).or_insert_with(Vec::new).push(u);
    }

    let mut max_flow = 0.0;

    while let Some((path_flow, parent)) = bfs_augmenting_path(&graph, &cap, &flow, &adj, *src, *sink) {
        let mut v = *sink;
        while v != *src {
            let u = parent[&v];
            *flow.get_mut(&(u, v)).unwrap() += path_flow;
            *flow.get_mut(&(v, u)).unwrap() -= path_flow;
            v = u;
        }
        max_flow += path_flow;
    }

    let mut flows = HashMap::new();
    for edge in graph.edge_references() {
        let u = edge.source();
        let v = edge.target();
        let road = edge.weight();
        let f = flow.get(&(u, v)).copied().unwrap_or(0.0);
        if f > 1e-9 {
            flows.insert(road.id.clone(), f);
        }
    }

    for road in &network.roads {
        flows.entry(road.id.clone()).or_insert(0.0);
    }

    Ok(FlowSolution {
        flows,
        method: SolverMethod::MaxFlow,
        objective: None,
        objective_value: Some(max_flow),
        is_feasible: true,
        violations: Vec::new(),
        metadata: {
            let mut m = HashMap::new();
            m.insert("maxFlow".to_string(), serde_json::Value::Number(serde_json::Number::from_f64(max_flow).unwrap()));
            m.insert("algorithm".to_string(), serde_json::Value::String("edmonds_karp".to_string()));
            m.insert("source".to_string(), serde_json::Value::String(source.to_string()));
            m.insert("sink".to_string(), serde_json::Value::String(sink.to_string()));
            m
        },
    })
}

fn bfs_augmenting_path(
    graph: &DiGraph<crate::models::Junction, crate::models::Road>,
    cap: &HashMap<(NodeIndex, NodeIndex), f64>,
    flow: &HashMap<(NodeIndex, NodeIndex), f64>,
    adj: &HashMap<NodeIndex, Vec<NodeIndex>>,
    src: NodeIndex,
    sink: NodeIndex,
) -> Option<(f64, HashMap<NodeIndex, NodeIndex>)> {
    let mut parent = HashMap::new();
    let mut path_cap = HashMap::new();
    let mut q = VecDeque::new();

    q.push_back(src);
    path_cap.insert(src, f64::INFINITY);

    while let Some(u) = q.pop_front() {
        for v in adj.get(&u)? {
            let residual = cap.get(&(u, *v)).copied().unwrap_or(0.0) - flow.get(&(u, *v)).copied().unwrap_or(0.0);
            if residual > 1e-9 && !path_cap.contains_key(v) {
                parent.insert(*v, u);
                path_cap.insert(*v, path_cap[&u].min(residual));
                if *v == sink {
                    return Some((path_cap[v], parent));
                }
                q.push_back(*v);
            }
        }
    }

    None
}