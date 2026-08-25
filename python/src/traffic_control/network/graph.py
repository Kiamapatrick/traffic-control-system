from __future__ import annotations

import networkx as nx
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, Junction, Road


def to_networkx(network: "Network") -> nx.DiGraph:
    G = nx.DiGraph()
    for junction in network.junctions:
        G.add_node(junction.id, position=junction.position, external_flow=junction.external_flow)
    for road in network.roads:
        G.add_edge(
            road.source,
            road.target,
            id=road.id,
            capacity=road.capacity,
            length=road.length,
            cost=road.cost_per_unit,
            flow=road.flow,
        )
    return G


def validate_flow_conservation(network: "Network", flows: dict[str, float] | None = None) -> tuple[bool, list[str]]:
    violations = []
    if flows is None:
        flows = {r.id: r.flow for r in network.roads}

    for junction in network.junctions:
        inflow = sum(flows.get(r.id, 0) for r in network.roads if r.target == junction.id)
        outflow = sum(flows.get(r.id, 0) for r in network.roads if r.source == junction.id)
        net = inflow - outflow
        if abs(net - junction.external_flow) > 1e-6:
            violations.append(f"Junction {junction.id}: net flow {net:.2f} != external {junction.external_flow}")

    return len(violations) == 0, violations


def validate_capacities(network: "Network", flows: dict[str, float] | None = None) -> tuple[bool, list[str]]:
    violations = []
    if flows is None:
        flows = {r.id: r.flow for r in network.roads}

    for road in network.roads:
        flow = flows.get(road.id, 0)
        if flow < -1e-6:
            violations.append(f"Road {road.id}: negative flow {flow:.2f}")
        if flow > road.capacity + 1e-6:
            violations.append(f"Road {road.id}: flow {flow:.2f} exceeds capacity {road.capacity}")

    return len(violations) == 0, violations


def validate_connectivity(network: "Network") -> tuple[bool, list[str]]:
    violations = []
    G = to_networkx(network)

    if not nx.is_weakly_connected(G):
        violations.append("Network is not weakly connected")

    sources = [j.id for j in network.junctions if j.external_flow > 0]
    sinks = [j.id for j in network.junctions if j.external_flow < 0]

    if not sources:
        violations.append("No source junctions (external_flow > 0)")
    if not sinks:
        violations.append("No sink junctions (external_flow < 0)")

    for source in sources:
        for sink in sinks:
            if not nx.has_path(G, source, sink):
                violations.append(f"No path from source {source} to sink {sink}")

    return len(violations) == 0, violations


def validate_network(network: "Network", flows: dict[str, float] | None = None) -> tuple[bool, list[str]]:
    all_violations = []

    ok, v = validate_flow_conservation(network, flows)
    all_violations.extend(v)

    ok, v = validate_capacities(network, flows)
    all_violations.extend(v)

    ok, v = validate_connectivity(network)
    all_violations.extend(v)

    return len(all_violations) == 0, all_violations


def find_bottlenecks(network: "Network", flows: dict[str, float] | None = None, threshold: float = 0.8) -> list[tuple[str, float]]:
    if flows is None:
        flows = {r.id: r.flow for r in network.roads}

    bottlenecks = []
    for road in network.roads:
        flow = flows.get(road.id, 0)
        utilization = flow / road.capacity if road.capacity > 0 else 0
        if utilization >= threshold:
            bottlenecks.append((road.id, utilization))

    return sorted(bottlenecks, key=lambda x: x[1], reverse=True)


def compute_shortest_paths(network: "Network", weight: str = "length") -> dict[str, dict[str, float]]:
    G = to_networkx(network)
    return dict(nx.all_pairs_dijkstra_path_length(G, weight=weight))


def compute_betweenness_centrality(network: "Network") -> dict[str, float]:
    G = to_networkx(network)
    return nx.betweenness_centrality(G, weight="length")