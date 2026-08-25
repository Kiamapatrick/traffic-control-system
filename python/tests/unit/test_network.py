from __future__ import annotations

import pytest
from traffic_control.network import (
    to_networkx, validate_flow_conservation, validate_capacities,
    validate_connectivity, validate_network, find_bottlenecks,
    load_network_json, save_network_json, generate_four_junction_example,
    generate_manhattan_example, generate_roundabout_example,
)
from traffic_control.models import Network, Junction, Road
import tempfile
import os


class TestGraphConversion:
    def test_to_networkx(self):
        network = generate_four_junction_example()
        G = to_networkx(network)
        assert G.number_of_nodes() == 4
        assert G.number_of_edges() == 5

    def test_node_attributes(self):
        network = generate_four_junction_example()
        G = to_networkx(network)
        assert "position" in G.nodes["A"]
        assert "external_flow" in G.nodes["A"]

    def test_edge_attributes(self):
        network = generate_four_junction_example()
        G = to_networkx(network)
        edge_data = G.edges["A", "B"]
        assert "capacity" in edge_data
        assert "id" in edge_data


class TestValidation:
    def test_flow_conservation_valid(self):
        network = generate_four_junction_example()
        from traffic_control.solvers import solve_rref
        solution = solve_rref(network)
        is_valid, violations = validate_flow_conservation(network, solution.flows)
        assert is_valid

    def test_flow_conservation_invalid(self):
        junctions = [
            Junction(id="A", position=(0, 0), external_flow=10),
            Junction(id="B", position=(100, 0), external_flow=-5),
        ]
        roads = [Road(id="r1", source="A", target="B", capacity=100)]
        network = Network(junctions=junctions, roads=roads)
        flows = {"r1": 10.0}
        is_valid, violations = validate_flow_conservation(network, flows)
        assert not is_valid

    def test_capacities_valid(self):
        network = generate_four_junction_example()
        from traffic_control.solvers import solve_rref
        solution = solve_rref(network)
        is_valid, violations = validate_capacities(network, solution.flows)
        assert is_valid

    def test_capacities_invalid(self):
        junctions = [
            Junction(id="A", position=(0, 0), external_flow=100),
            Junction(id="B", position=(100, 0), external_flow=-100),
        ]
        roads = [Road(id="r1", source="A", target="B", capacity=50)]
        network = Network(junctions=junctions, roads=roads)
        flows = {"r1": 100.0}
        is_valid, violations = validate_capacities(network, flows)
        assert not is_valid

    def test_connectivity_valid(self):
        network = generate_four_junction_example()
        is_valid, violations = validate_connectivity(network)
        assert is_valid

    def test_connectivity_no_sources(self):
        junctions = [
            Junction(id="A", position=(0, 0), external_flow=0),
            Junction(id="B", position=(100, 0), external_flow=0),
        ]
        roads = [Road(id="r1", source="A", target="B", capacity=100)]
        network = Network(junctions=junctions, roads=roads)
        is_valid, violations = validate_connectivity(network)
        assert not is_valid
        assert any("source" in v.lower() for v in violations)

    def test_validate_network(self):
        network = generate_four_junction_example()
        from traffic_control.solvers import solve_rref
        solution = solve_rref(network)
        is_valid, violations = validate_network(network, solution.flows)
        assert is_valid


class TestBottlenecks:
    def test_find_bottlenecks(self):
        network = generate_four_junction_example()
        from traffic_control.solvers import solve_lp
        solution = solve_lp(network, objective="max_throughput")
        bottlenecks = find_bottlenecks(network, solution.flows, threshold=0.5)
        assert isinstance(bottlenecks, list)


class TestPersistence:
    def test_save_load_json(self):
        network = generate_four_junction_example()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_network_json(network, temp_path)
            loaded = load_network_json(temp_path)
            assert len(loaded.junctions) == len(network.junctions)
            assert len(loaded.roads) == len(network.roads)
            assert loaded.junctions[0].id == network.junctions[0].id
        finally:
            os.unlink(temp_path)


class TestGenerators:
    def test_four_junction(self):
        network = generate_four_junction_example()
        assert len(network.junctions) == 4
        assert len(network.roads) == 5

    def test_manhattan(self):
        network = generate_manhattan_example()
        assert len(network.junctions) == 20
        assert len(network.roads) > 0

    def test_roundabout(self):
        network = generate_roundabout_example()
        assert len(network.junctions) == 5
        assert len(network.roads) > 0

    def test_grid_network(self):
        from traffic_control.network.generator import generate_grid_network
        network = generate_grid_network(2, 3, seed=42)
        assert len(network.junctions) == 6
        assert len(network.roads) > 0

    def test_random_network(self):
        from traffic_control.network.generator import generate_random_network
        network = generate_random_network(10, 20, seed=42)
        assert len(network.junctions) == 10
        assert len(network.roads) == 20