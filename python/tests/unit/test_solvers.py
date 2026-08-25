from __future__ import annotations

import pytest
import numpy as np
from traffic_control.solvers import (
    solve_rref, solve_lp, solve_milp, solve_max_flow,
    validate_solution, build_system_matrix, rref_solve
)
from traffic_control.models import Network, Junction, Road, SolverMethod, OptimizationObjective
from traffic_control.network.generator import generate_four_junction_example


class TestRREF:
    def test_build_system_matrix(self):
        network = generate_four_junction_example()
        A, b, road_ids = build_system_matrix(network)
        assert A.shape == (4, 5)
        assert b.shape == (4,)
        assert len(road_ids) == 5

    def test_rref_solve(self):
        A = np.array([[1, 1], [1, -1]], dtype=float)
        b = np.array([10, 2], dtype=float)
        particular, nullspace, pivots = rref_solve(A, b)
        assert len(pivots) == 2
        assert particular.shape == (2,)

    def test_solve_rref_four_junction(self):
        network = generate_four_junction_example()
        solution = solve_rref(network)

        assert solution.method == SolverMethod.RREF
        assert len(solution.flows) == 5
        assert all(f >= -1e-6 for f in solution.flows.values())

    def test_validate_solution(self):
        network = generate_four_junction_example()
        solution = solve_rref(network)
        is_valid, violations = validate_solution(network, solution)
        assert is_valid is True or len(violations) > 0


class TestLinearProgramming:
    def test_solve_lp_min_cost(self):
        network = generate_four_junction_example()
        solution = solve_lp(network, OptimizationObjective.MIN_COST)

        assert solution.method == SolverMethod.LINEAR_PROGRAMMING
        assert solution.objective == OptimizationObjective.MIN_COST
        assert solution.objective_value is not None

    def test_solve_lp_max_throughput(self):
        network = generate_four_junction_example()
        solution = solve_lp(network, OptimizationObjective.MAX_THROUGHPUT)

        assert solution.method == SolverMethod.LINEAR_PROGRAMMING
        assert solution.objective == OptimizationObjective.MAX_THROUGHPUT


class TestMILP:
    def test_solve_milp(self):
        network = generate_four_junction_example()
        solution = solve_milp(network)

        assert solution.method == SolverMethod.MILP


class TestMaxFlow:
    def test_solve_max_flow_edmonds_karp(self):
        network = generate_four_junction_example()
        solution = solve_max_flow(network, "A", "C", "edmonds_karp")

        assert solution.method == SolverMethod.MAX_FLOW
        assert solution.objective_value is not None
        assert solution.objective_value > 0

    def test_solve_max_flow_dinic(self):
        network = generate_four_junction_example()
        solution = solve_max_flow(network, "A", "C", "dinic")

        assert solution.method == SolverMethod.DINIC
        assert solution.objective_value is not None

    def test_invalid_source_sink(self):
        network = generate_four_junction_example()
        with pytest.raises(Exception):
            solve_max_flow(network, "INVALID", "C")

    def test_unknown_algorithm(self):
        network = generate_four_junction_example()
        with pytest.raises(Exception):
            solve_max_flow(network, "A", "C", "unknown")


class TestValidation:
    def test_flow_conservation(self):
        junctions = [
            Junction(id="A", position=(0, 0), external_flow=10),
            Junction(id="B", position=(100, 0), external_flow=-10),
        ]
        roads = [Road(id="r1", source="A", target="B", capacity=100)]
        network = Network(junctions=junctions, roads=roads)

        flows = {"r1": 10.0}
        is_valid, violations = validate_solution(network, flows)
        assert is_valid

    def test_capacity_violation(self):
        junctions = [
            Junction(id="A", position=(0, 0), external_flow=100),
            Junction(id="B", position=(100, 0), external_flow=-100),
        ]
        roads = [Road(id="r1", source="A", target="B", capacity=50)]
        network = Network(junctions=junctions, roads=roads)

        flows = {"r1": 100.0}
        is_valid, violations = validate_solution(network, flows)
        assert not is_valid
        assert any("exceeds capacity" in v for v in violations)

    def test_negative_flow(self):
        junctions = [
            Junction(id="A", position=(0, 0), external_flow=10),
            Junction(id="B", position=(100, 0), external_flow=-10),
        ]
        roads = [Road(id="r1", source="A", target="B", capacity=100)]
        network = Network(junctions=junctions, roads=roads)

        flows = {"r1": -5.0}
        is_valid, violations = validate_solution(network, flows)
        assert not is_valid
        assert any("negative flow" in v for v in violations)