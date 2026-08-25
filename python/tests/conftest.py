from __future__ import annotations

import pytest
from traffic_control.models import Network, Junction, Road
from traffic_control.network.generator import generate_four_junction_example


@pytest.fixture
def four_junction_network() -> Network:
    return generate_four_junction_example()


@pytest.fixture
def simple_network() -> Network:
    junctions = [
        Junction(id="A", position=(0, 0), external_flow=100),
        Junction(id="B", position=(100, 0), external_flow=-50),
        Junction(id="C", position=(200, 0), external_flow=-50),
    ]
    roads = [
        Road(id="r1", source="A", target="B", capacity=100),
        Road(id="r2", source="A", target="C", capacity=100),
        Road(id="r3", source="B", target="C", capacity=50),
    ]
    return Network(junctions=junctions, roads=roads)


@pytest.fixture
def grid_network() -> Network:
    from traffic_control.network.generator import generate_grid_network
    return generate_grid_network(3, 3, seed=42)