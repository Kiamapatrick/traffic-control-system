from __future__ import annotations

import numpy as np
from scipy import linalg
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, FlowSolution, SolverMethod


class RREFError(Exception):
    pass


def build_system_matrix(network: "Network") -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Build the system matrix A*x = b for traffic flow conservation.

    For each junction: sum(inflows) - sum(outflows) = external_flow
    """
    n_junctions = len(network.junctions)
    n_roads = len(network.roads)

    if n_roads == 0:
        raise RREFError("Network has no roads")

    A = np.zeros((n_junctions, n_roads))
    b = np.zeros(n_junctions)

    junction_to_idx = {j.id: i for i, j in enumerate(network.junctions)}
    road_to_idx = {r.id: i for i, r in enumerate(network.roads)}

    for road in network.roads:
        j_src = junction_to_idx[road.source]
        j_tgt = junction_to_idx[road.target]
        r_idx = road_to_idx[road.id]
        A[j_src, r_idx] = -1.0
        A[j_tgt, r_idx] = 1.0

    for junction in network.junctions:
        idx = junction_to_idx[junction.id]
        b[idx] = junction.external_flow

    road_ids = [r.id for r in network.roads]
    return A, b, road_ids


def rref_solve(
    A: np.ndarray,
    b: np.ndarray,
    tol: float = 1e-10
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    """
    Compute RREF of augmented matrix [A | b] using Gaussian elimination.

    Returns:
        - solution vector (particular solution)
        - nullspace basis vectors
        - pivot column indices
    """
    m, n = A.shape
    if m != b.shape[0]:
        raise RREFError(f"Matrix shape mismatch: A={A.shape}, b={b.shape}")

    M = np.column_stack([A.astype(float), b.astype(float)])
    pivot_cols = []
    row = 0

    for col in range(n):
        if row >= m:
            break

        pivot_row = np.argmax(np.abs(M[row:, col])) + row
        if np.abs(M[pivot_row, col]) < tol:
            continue

        if pivot_row != row:
            M[[row, pivot_row]] = M[[pivot_row, row]]

        M[row] = M[row] / M[row, col]

        for r in range(m):
            if r != row and np.abs(M[r, col]) > tol:
                M[r] -= M[r, col] * M[row]

        pivot_cols.append(col)
        row += 1

    rank = len(pivot_cols)
    if rank == 0:
        return np.zeros(n), np.eye(n), []

    particular = np.zeros(n)
    for i, pc in enumerate(pivot_cols):
        particular[pc] = M[i, -1]

    free_cols = [c for c in range(n) if c not in pivot_cols]
    nullspace = []
    for fc in free_cols:
        vec = np.zeros(n)
        vec[fc] = 1.0
        for i, pc in enumerate(pivot_cols):
            vec[pc] = -M[i, fc]
        nullspace.append(vec)

    return particular, np.array(nullspace).T if nullspace else np.zeros((n, 0)), pivot_cols


def find_feasible_solution(
    particular: np.ndarray,
    nullspace: np.ndarray,
    network: "Network",
    road_ids: list[str],
    tol: float = 1e-10
) -> np.ndarray | None:
    """
    Find a feasible solution satisfying non-negativity and capacity constraints.

    Uses linear programming to find a valid solution in the affine space.
    """
    from scipy.optimize import linprog

    n = len(particular)
    if nullspace.shape[1] == 0:
        if np.all(particular >= -tol) and np.all(particular <= np.array([get_capacity(network, rid) for rid in road_ids]) + tol):
            return np.maximum(particular, 0)
        return None

    c = np.zeros(nullspace.shape[1])

    A_ub = np.vstack([-nullspace.T, nullspace.T])
    b_ub = np.hstack([particular, np.array([get_capacity(network, rid) for rid in road_ids]) - particular])

    bounds = [(None, None)] * nullspace.shape[1]

    result = linprog(c, A_ub=A_ub, b_ub=b_ub, bounds=bounds, method="highs")
    if result.success:
        return particular + nullspace @ result.x
    return None


def get_capacity(network: "Network", road_id: str) -> float:
    for road in network.roads:
        if road.id == road_id:
            return road.capacity
    return float("inf")


def solve_rref(network: "Network") -> "FlowSolution":
    from traffic_control.models import FlowSolution, SolverMethod

    A, b, road_ids = build_system_matrix(network)
    particular, nullspace, pivot_cols = rref_solve(A, b)

    feasible = find_feasible_solution(particular, nullspace, network, road_ids)

    if feasible is None:
        feasible = np.maximum(particular, 0)
        violations = ["No feasible solution found, returning non-negative projection"]
    else:
        violations = []
        for i, rid in enumerate(road_ids):
            cap = get_capacity(network, rid)
            if feasible[i] > cap + 1e-6:
                violations.append(f"Road {rid}: flow {feasible[i]:.2f} exceeds capacity {cap}")

    flows = {rid: max(0.0, float(feasible[i])) for i, rid in enumerate(road_ids)}

    return FlowSolution(
        flows=flows,
        method=SolverMethod.RREF,
        is_feasible=len(violations) == 0,
        violations=violations,
        metadata={
            "rank": len(pivot_cols),
            "nullity": nullspace.shape[1],
            "pivot_columns": pivot_cols,
            "particular_solution": particular.tolist(),
        }
    )


def validate_solution(network: "Network", solution: "FlowSolution") -> tuple[bool, list[str]]:
    violations = []

    flow_dict = solution.flows
    junction_to_idx = {j.id: i for i, j in enumerate(network.junctions)}

    for junction in network.junctions:
        inflow = sum(flow_dict.get(r.id, 0) for r in network.roads if r.target == junction.id)
        outflow = sum(flow_dict.get(r.id, 0) for r in network.roads if r.source == junction.id)
        net_flow = inflow - outflow
        expected = junction.external_flow
        if abs(net_flow - expected) > 1e-6:
            violations.append(
                f"Junction {junction.id}: inflow - outflow = {net_flow:.2f}, expected {expected}"
            )

    for road in network.roads:
        flow = flow_dict.get(road.id, 0)
        if flow < -1e-6:
            violations.append(f"Road {road.id}: negative flow {flow:.2f}")
        if flow > road.capacity + 1e-6:
            violations.append(f"Road {road.id}: flow {flow:.2f} exceeds capacity {road.capacity}")

    return len(violations) == 0, violations