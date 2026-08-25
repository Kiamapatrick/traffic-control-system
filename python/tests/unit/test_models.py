from __future__ import annotations

import pytest
from traffic_control.models import Junction, Road, Network, FlowSolution, SolverMethod


class TestJunction:
    def test_valid_junction(self):
        j = Junction(id="A", position=(10, 20), external_flow=50)
        assert j.id == "A"
        assert j.position == (10, 20)
        assert j.external_flow == 50

    def test_invalid_position(self):
        with pytest.raises(ValueError):
            Junction(id="A", position=(10,))

    def test_empty_id(self):
        with pytest.raises(ValueError):
            Junction(id="", position=(0, 0))


class TestRoad:
    def test_valid_road(self):
        r = Road(id="r1", source="A", target="B", capacity=100, length=5.0)
        assert r.id == "r1"
        assert r.capacity == 100
        assert r.length == 5.0

    def test_same_source_target(self):
        with pytest.raises(ValueError):
            Road(id="r1", source="A", target="A")

    def test_defaults(self):
        r = Road(id="r1", source="A", target="B")
        assert r.capacity == 1000.0
        assert r.length == 1.0
        assert r.cost_per_unit == 1.0


class TestNetwork:
    def test_valid_network(self):
        junctions = [Junction(id="A", position=(0, 0)), Junction(id="B", position=(100, 0))]
        roads = [Road(id="r1", source="A", target="B")]
        net = Network(junctions=junctions, roads=roads)
        assert len(net.junctions) == 2
        assert len(net.roads) == 1

    def test_invalid_road_reference(self):
        junctions = [Junction(id="A", position=(0, 0))]
        roads = [Road(id="r1", source="A", target="B")]
        with pytest.raises(ValueError):
            Network(junctions=junctions, roads=roads)


class TestFlowSolution:
    def test_solution_creation(self):
        sol = FlowSolution(
            flows={"r1": 50.0, "r2": 30.0},
            method=SolverMethod.RREF,
        )
        assert sol.total_flow == 80.0
        assert sol.is_feasible is True

    def test_solution_with_violations(self):
        sol = FlowSolution(
            flows={"r1": -10.0},
            method=SolverMethod.RREF,
            is_feasible=False,
            violations=["Negative flow"],
        )
        assert sol.is_feasible is False
        assert len(sol.violations) == 1