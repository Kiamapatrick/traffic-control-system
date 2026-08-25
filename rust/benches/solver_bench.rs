use criterion::{black_box, criterion_group, criterion_main, Criterion, BenchmarkId};
use traffic_control_rs::{Network, solve_rref, solve_simplex, dinic, edmonds_karp, Junction, Road, JunctionType, OptimizationObjective};

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

fn grid_network(n: usize) -> Network {
    let mut junctions = Vec::new();
    let mut roads = Vec::new();

    for r in 0..n {
        for c in 0..n {
            let id = format!("J_{}_{}", r, c);
            junctions.push(Junction {
                id: id.clone(),
                position: [(c * 100) as f64, (r * 100) as f64],
                junction_type: JunctionType::Normal,
                external_flow: 0.0,
            });
        }
    }

    for r in 0..n {
        for c in 0..n {
            let id = format!("J_{}_{}", r, c);
            if c + 1 < n {
                let target = format!("J_{}_{}", r, c + 1);
                roads.push(Road { id: format!("R_{}_E", id), source: id.clone(), target: target.clone(), capacity: 1000.0, length: 100.0, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 2 });
                roads.push(Road { id: format!("R_{}_W", target), source: target, target: id, capacity: 1000.0, length: 100.0, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 2 });
            }
            if r + 1 < n {
                let target = format!("J_{}_{}", r + 1, c);
                roads.push(Road { id: format!("R_{}_S", id), source: id.clone(), target: target.clone(), capacity: 1000.0, length: 100.0, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 2 });
                roads.push(Road { id: format!("R_{}_N", target), source: target, target: id, capacity: 1000.0, length: 100.0, flow: 0.0, cost_per_unit: 1.0, free_flow_speed: 50.0, lanes: 2 });
            }
        }
    }

    let sources = [0, n*n-1];
    for &idx in &sources {
        if idx < junctions.len() {
            junctions[idx].external_flow = if idx == 0 { 500.0 } else { -500.0 };
            junctions[idx].junction_type = if idx == 0 { JunctionType::Source } else { JunctionType::Sink };
        }
    }

    Network { junctions, roads, metadata: std::collections::HashMap::new() }
}

fn bench_rref(c: &mut Criterion) {
    let mut group = c.benchmark_group("rref");
    for n in [2, 3, 4] {
        let net = grid_network(n);
        group.bench_with_input(BenchmarkId::from_parameter(format!("grid_{}x{}", n, n)), &net, |b, net| {
            b.iter(|| solve_rref(black_box(net)));
        });
    }
    group.finish();
}

fn bench_simplex(c: &mut Criterion) {
    let mut group = c.benchmark_group("simplex");
    for n in [2, 3, 4] {
        let net = grid_network(n);
        group.bench_with_input(BenchmarkId::from_parameter(format!("grid_{}x{}", n, n)), &net, |b, net| {
            b.iter(|| solve_simplex(black_box(net), Some(OptimizationObjective::MinCost)));
        });
    }
    group.finish();
}

fn bench_max_flow(c: &mut Criterion) {
    let mut group = c.benchmark_group("max_flow");
    let net = four_junction_network();

    group.bench_function("dinic", |b| {
        b.iter(|| dinic(black_box(&net), "A", "C"));
    });

    group.bench_function("edmonds_karp", |b| {
        b.iter(|| edmonds_karp(black_box(&net), "A", "C"));
    });

    group.finish();
}

criterion_group!(benches, bench_rref, bench_simplex, bench_max_flow);
criterion_main!(benches);