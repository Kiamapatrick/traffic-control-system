from __future__ import annotations

import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, Junction, Road


def generate_grid_network(
    rows: int,
    cols: int,
    spacing: float = 100.0,
    capacity_range: tuple[float, float] = (500, 2000),
    seed: int | None = None,
) -> "Network":
    from traffic_control.models import Network, Junction, Road

    if seed is not None:
        random.seed(seed)

    junctions = []
    roads = []

    for r in range(rows):
        for c in range(cols):
            jid = f"J_{r}_{c}"
            x = c * spacing
            y = r * spacing
            junctions.append(Junction(id=jid, position=(x, y)))

    for r in range(rows):
        for c in range(cols):
            jid = f"J_{r}_{c}"
            if c + 1 < cols:
                target = f"J_{r}_{c+1}"
                cap = random.uniform(*capacity_range)
                roads.append(Road(id=f"R_{jid}_E", source=jid, target=target, capacity=cap))
                roads.append(Road(id=f"R_{target}_W", source=target, target=jid, capacity=cap))
            if r + 1 < rows:
                target = f"J_{r+1}_{c}"
                cap = random.uniform(*capacity_range)
                roads.append(Road(id=f"R_{jid}_S", source=jid, target=target, capacity=cap))
                roads.append(Road(id=f"R_{target}_N", source=target, target=jid, capacity=cap))

    sources = random.sample(junctions, max(1, len(junctions) // 10))
    sinks = random.sample([j for j in junctions if j not in sources], max(1, len(junctions) // 10))

    for j in sources:
        j.external_flow = random.uniform(100, 500)
    for j in sinks:
        j.external_flow = -random.uniform(100, 500)

    return Network(junctions=junctions, roads=roads)


def generate_random_network(
    num_junctions: int,
    num_roads: int,
    area_size: float = 1000.0,
    capacity_range: tuple[float, float] = (500, 2000),
    seed: int | None = None,
) -> "Network":
    from traffic_control.models import Network, Junction, Road

    if seed is not None:
        random.seed(seed)

    junctions = []
    for i in range(num_junctions):
        x = random.uniform(0, area_size)
        y = random.uniform(0, area_size)
        junctions.append(Junction(id=f"J_{i}", position=(x, y)))

    roads = []
    road_id = 0
    attempts = 0
    max_attempts = num_roads * 10

    while len(roads) < num_roads and attempts < max_attempts:
        src = random.choice(junctions)
        tgt = random.choice(junctions)
        if src.id == tgt.id:
            attempts += 1
            continue
        if any(r.source == src.id and r.target == tgt.id for r in roads):
            attempts += 1
            continue

        cap = random.uniform(*capacity_range)
        roads.append(Road(id=f"R_{road_id}", source=src.id, target=tgt.id, capacity=cap))
        road_id += 1

    sources = random.sample(junctions, max(1, num_junctions // 10))
    sinks = random.sample([j for j in junctions if j not in sources], max(1, num_junctions // 10))

    for j in sources:
        j.external_flow = random.uniform(100, 500)
    for j in sinks:
        j.external_flow = -random.uniform(100, 500)

    return Network(junctions=junctions, roads=roads)


def generate_four_junction_example() -> "Network":
    from traffic_control.models import Network, Junction, Road

    junctions = [
        Junction(id="A", position=(200, 600), external_flow=80),
        Junction(id="B", position=(800, 600), external_flow=-30),
        Junction(id="C", position=(800, 200), external_flow=50),
        Junction(id="D", position=(200, 200), external_flow=-100),
    ]

    roads = [
        Road(id="x1", source="A", target="B", capacity=100, length=6.0),
        Road(id="x2", source="B", target="C", capacity=100, length=4.0),
        Road(id="x3", source="C", target="D", capacity=100, length=6.0),
        Road(id="x4", source="D", target="A", capacity=100, length=4.0),
        Road(id="x5", source="B", target="D", capacity=100, length=6.3),
    ]

    return Network(junctions=junctions, roads=roads)


def generate_manhattan_example() -> "Network":
    return generate_grid_network(4, 5, spacing=200.0, seed=42)


def generate_roundabout_example() -> "Network":
    from traffic_control.models import Network, Junction, Road

    center = Junction(id="center", position=(500, 500), external_flow=0)

    num_entries = 4
    junctions = [center]
    roads = []

    for i in range(num_entries):
        angle = 2 * 3.14159 * i / num_entries
        x = 500 + 300 * (angle.__cos__() if hasattr(angle, '__cos__') else __import__('math').cos(angle))
        y = 500 + 300 * (angle.__sin__() if hasattr(angle, '__sin__') else __import__('math').sin(angle))

        entry = Junction(id=f"entry_{i}", position=(x, y), external_flow=100 if i % 2 == 0 else -100)
        junctions.append(entry)

        roads.append(Road(id=f"in_{i}", source=entry.id, target="center", capacity=500, length=300))
        roads.append(Road(id=f"out_{i}", source="center", target=entry.id, capacity=500, length=300))

    for i in range(num_entries):
        next_i = (i + 1) % num_entries
        roads.append(Road(
            id=f"ring_{i}",
            source=f"entry_{i}",
            target=f"entry_{next_i}",
            capacity=300,
            length=400
        ))

    return Network(junctions=junctions, roads=roads)