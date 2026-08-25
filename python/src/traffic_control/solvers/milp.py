from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, FlowSolution, SolverMethod


class MILPSolverError(Exception):
    pass


def solve_milp(network: "Network") -> "FlowSolution":
    """
    Solve Mixed Integer Linear Programming for discrete flow values.

    Requires OR-Tools. Falls back to LP relaxation if not available.
    """
    from traffic_control.models import FlowSolution, SolverMethod

    try:
        from ortools.linear_solver import pywraplp
    except ImportError:
        return FlowSolution(
            flows={r.id: 0.0 for r in network.roads},
            method=SolverMethod.MILP,
            is_feasible=False,
            violations=["OR-Tools not installed. Install with: pip install ortools"],
            metadata={"error": "ortools_not_installed"}
        )

    solver = pywraplp.Solver.CreateSolver("SCIP")
    if not solver:
        solver = pywraplp.Solver.CreateSolver("CBC")
    if not solver:
        return FlowSolution(
            flows={r.id: 0.0 for r in network.roads},
            method=SolverMethod.MILP,
            is_feasible=False,
            violations=["No MILP solver available (need SCIP or CBC)"],
            metadata={"error": "no_solver"}
        )

    n_roads = len(network.roads)
    junction_to_idx = {j.id: i for i, j in enumerate(network.junctions)}
    road_to_idx = {r.id: i for i, r in enumerate(network.roads)}

    x = {}
    for road in network.roads:
        x[road.id] = solver.IntVar(0, int(road.capacity), road.id)

    for junction in network.junctions:
        constraint = solver.RowConstraint(junction.external_flow, junction.external_flow)
        for road in network.roads:
            if road.source == junction.id:
                constraint.SetCoefficient(x[road.id], -1)
            elif road.target == junction.id:
                constraint.SetCoefficient(x[road.id], 1)

    objective = solver.Objective()
    for road in network.roads:
        objective.SetCoefficient(x[road.id], road.cost_per_unit)
    objective.SetMinimization()

    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        flows = {rid: x[rid].solution_value() for rid in x}
        return FlowSolution(
            flows=flows,
            method=SolverMethod.MILP,
            objective_value=objective.Value(),
            is_feasible=True,
            metadata={"status": "OPTIMAL", "wall_time": solver.WallTime()}
        )
    else:
        return FlowSolution(
            flows={rid: 0.0 for rid in x},
            method=SolverMethod.MILP,
            is_feasible=False,
            violations=[f"MILP solver status: {status}"],
            metadata={"status": status}
        )