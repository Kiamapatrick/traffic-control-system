from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, FlowSolution, SolverMethod


class MaxFlowError(Exception):
    pass


def edmonds_karp(network: "Network", source: str, sink: str) -> "FlowSolution":
    from traffic_control.models import FlowSolution, SolverMethod

    road_to_idx = {r.id: i for i, r in enumerate(network.roads)}
    n = len(network.junctions)
    junction_to_idx = {j.id: i for i, j in enumerate(network.junctions)}

    cap = [[0] * n for _ in range(n)]
    road_map = [[None] * n for _ in range(n)]

    for road in network.roads:
        u = junction_to_idx[road.source]
        v = junction_to_idx[road.target]
        cap[u][v] += road.capacity
        road_map[u][v] = road.id

    s = junction_to_idx.get(source)
    t = junction_to_idx.get(sink)

    if s is None or t is None:
        raise MaxFlowError(f"Source '{source}' or sink '{sink}' not found")

    flow = [[0] * n for _ in range(n)]
    max_flow = 0

    while True:
        parent = [-1] * n
        parent[s] = s
        q = deque([s])
        path_cap = [0] * n
        path_cap[s] = float("inf")

        while q and parent[t] == -1:
            u = q.popleft()
            for v in range(n):
                if parent[v] == -1 and cap[u][v] - flow[u][v] > 1e-9:
                    parent[v] = u
                    path_cap[v] = min(path_cap[u], cap[u][v] - flow[u][v])
                    q.append(v)

        if parent[t] == -1:
            break

        path_flow = path_cap[t]
        v = t
        while v != s:
            u = parent[v]
            flow[u][v] += path_flow
            flow[v][u] -= path_flow
            v = u

        max_flow += path_flow

    flows = {r.id: 0.0 for r in network.roads}
    for u in range(n):
        for v in range(n):
            if flow[u][v] > 1e-9 and road_map[u][v]:
                flows[road_map[u][v]] = flow[u][v]

    return FlowSolution(
        flows=flows,
        method=SolverMethod.MAX_FLOW,
        objective_value=max_flow,
        is_feasible=True,
        metadata={
            "algorithm": "edmonds_karp",
            "source": source,
            "sink": sink,
            "max_flow": max_flow,
        }
    )


def dinic(network: "Network", source: str, sink: str) -> "FlowSolution":
    from traffic_control.models import FlowSolution, SolverMethod

    n = len(network.junctions)
    junction_to_idx = {j.id: i for i, j in enumerate(network.junctions)}
    road_to_idx = {r.id: i for i, r in enumerate(network.roads)}

    s = junction_to_idx.get(source)
    t = junction_to_idx.get(sink)

    if s is None or t is None:
        raise MaxFlowError(f"Source '{source}' or sink '{sink}' not found")

    adj = [[] for _ in range(n)]
    road_ids = {}

    for road in network.roads:
        u = junction_to_idx[road.source]
        v = junction_to_idx[road.target]
        adj[u].append([v, len(adj[v]), road.capacity, road.id])
        adj[v].append([u, len(adj[u]) - 1, 0.0, None])
        road_ids[(u, len(adj[u]) - 1)] = road.id

    def bfs() -> list[int]:
        level = [-1] * n
        level[s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for v, rev, cap, _ in adj[u]:
                if cap > 1e-9 and level[v] == -1:
                    level[v] = level[u] + 1
                    q.append(v)
        return level

    def dfs(u: int, flow: float, level: list[int], it: list[int]) -> float:
        if u == t:
            return flow
        for i in range(it[u], len(adj[u])):
            it[u] = i
            v, rev, cap, rid = adj[u][i]
            if cap > 1e-9 and level[v] == level[u] + 1:
                pushed = dfs(v, min(flow, cap), level, it)
                if pushed > 1e-9:
                    adj[u][i][2] -= pushed
                    adj[v][rev][2] += pushed
                    return pushed
        return 0.0

    max_flow = 0.0
    while True:
        level = bfs()
        if level[t] == -1:
            break
        it = [0] * n
        while True:
            pushed = dfs(s, float("inf"), level, it)
            if pushed < 1e-9:
                break
            max_flow += pushed

    flows = {r.id: 0.0 for r in network.roads}
    for u in range(n):
        for idx, (v, rev, cap, rid) in enumerate(adj[u]):
            if rid is not None:
                original_cap = sum(r.capacity for r in network.roads if r.id == rid)
                flow_val = original_cap - cap
                if flow_val > 1e-9:
                    flows[rid] = flow_val

    return FlowSolution(
        flows=flows,
        method=SolverMethod.DINIC,
        objective_value=max_flow,
        is_feasible=True,
        metadata={
            "algorithm": "dinic",
            "source": source,
            "sink": sink,
            "max_flow": max_flow,
        }
    )


def solve_max_flow(
    network: "Network",
    source: str,
    sink: str,
    algorithm: str = "dinic"
) -> "FlowSolution":
    if algorithm == "edmonds_karp":
        return edmonds_karp(network, source, sink)
    elif algorithm == "dinic":
        return dinic(network, source, sink)
    else:
        raise MaxFlowError(f"Unknown algorithm: {algorithm}")