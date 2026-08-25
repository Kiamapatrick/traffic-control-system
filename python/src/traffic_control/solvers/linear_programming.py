from __future__ import annotations

import numpy as np
from scipy.optimize import linprog
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, FlowSolution, SolverMethod, OptimizationObjective


class LPSolverError(Exception):
    pass


def build_lp_problem(
    network: "Network",
    objective: "OptimizationObjective" = None
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[float, float]], list[str]]:
    """
    Build linear programming problem for traffic flow optimization.

    Minimize: c^T x
    Subject to:
        A_eq x = b_eq (flow conservation)
        0 <= x <= capacity
    """
    n_junctions = len(network.junctions)
    n_roads = len(network.roads)

    if n_roads == 0:
        raise LPSolverError("Network has no roads")

    A_eq = np.zeros((n_junctions, n_roads))
    b_eq = np.zeros(n_junctions)

    junction_to_idx = {j.id: i for i, j in enumerate(network.junctions)}
    road_to_idx = {r.id: i for i, r in enumerate(network.roads)}

    for road in network.roads:
        j_src = junction_to_idx[road.source]
        j_tgt = junction_to_idx[road.target]
        r_idx = road_to_idx[road.id]
        A_eq[j_src, r_idx] = -1.0
        A_eq[j_tgt, r_idx] = 1.0

    for junction in network.junctions:
        idx = junction_to_idx[junction.id]
        b_eq[idx] = junction.external_flow

    c = np.zeros(n_roads)
    obj_value = objective.value if objective is not None else "min_cost"
    if obj_value == "min_cost":
        for road in network.roads:
            c[road_to_idx[road.id]] = road.cost_per_unit
    elif obj_value == "max_throughput":
        for road in network.roads:
            c[road_to_idx[road.id]] = -1.0
    elif obj_value == "min_travel_time":
        for road in network.roads:
            c[road_to_idx[road.id]] = road.length / road.free_flow_speed
    elif obj_value == "balance_load":
        for road in network.roads:
            c[road_to_idx[road.id]] = (1.0 / road.capacity) ** 2
        for road in network.roads:
            c[road_to_idx[road.id]] = (1.0 / road.capacity) ** 2

    bounds = [(0.0, road.capacity) for road in network.roads]
    road_ids = [r.id for r in network.roads]

    return c, A_eq, b_eq, bounds, road_ids


def solve_lp(network: "Network", objective: "OptimizationObjective | str" = None) -> "FlowSolution":
    from traffic_control.models import FlowSolution, SolverMethod, OptimizationObjective

    # Convert string to enum if needed
    if isinstance(objective, str):
        objective = OptimizationObjective(objective)

    c, A_eq, b_eq, bounds, road_ids = build_lp_problem(network, objective)

    result = linprog(c, A_eq=A_eq, b_eq=b_eq, bounds=bounds, method="highs")

    if not result.success:
        return FlowSolution(
            flows={rid: 0.0 for rid in road_ids},
            method=SolverMethod.LINEAR_PROGRAMMING,
            objective=objective,
            is_feasible=False,
            violations=[f"LP solver failed: {result.message}"],
            metadata={"status": result.status, "message": result.message}
        )

    flows = {rid: float(result.x[i]) for i, rid in enumerate(road_ids)}

    violations = []
    for road in network.roads:
        flow = flows[road.id]
        if flow > road.capacity + 1e-6:
            violations.append(f"Road {road.id}: flow {flow:.2f} exceeds capacity {road.capacity}")

    return FlowSolution(
        flows=flows,
        method=SolverMethod.LINEAR_PROGRAMMING,
        objective=objective,
        objective_value=float(result.fun) if result.fun is not None else None,
        is_feasible=len(violations) == 0,
        violations=violations,
        metadata={
            "status": result.status,
            "iterations": result.nit,
            "message": result.message,
        }
    )


def solve_min_cost_flow(network: "Network") -> "FlowSolution":
    return solve_lp(network, objective=None)


def solve_max_throughput(network: "Network") -> "FlowSolution":
    return solve_lp(network, objective="max_throughput")


def solve_min_travel_time(network: "Network") -> "FlowSolution":
    return solve_lp(network, objective="min_travel_time")


def solve_balance_load(network: "Network") -> "FlowSolution":
    return solve_lp(network, objective="balance_load")