from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, Junction, Road


class ParseError(Exception):
    pass


def load_network_json(path: str | Path) -> "Network":
    from traffic_control.models import Network

    with open(path, "r") as f:
        data = json.load(f)
    return Network.model_validate(data)


def save_network_json(network: "Network", path: str | Path, indent: int = 2) -> None:
    with open(path, "w") as f:
        json.dump(network.model_dump(mode="json"), f, indent=indent)


def load_network_graphml(path: str | Path) -> "Network":
    try:
        import networkx as nx
    except ImportError:
        raise ParseError("networkx required for GraphML parsing")

    G = nx.read_graphml(path)

    junctions = []
    for node_id, data in G.nodes(data=True):
        pos = data.get("position", "(0, 0)")
        if isinstance(pos, str):
            pos = tuple(map(float, pos.strip("()").split(",")))
        junctions.append({
            "id": node_id,
            "position": pos,
            "external_flow": float(data.get("external_flow", 0)),
        })

    roads = []
    for u, v, data in G.edges(data=True):
        roads.append({
            "id": data.get("id", f"{u}->{v}"),
            "source": u,
            "target": v,
            "capacity": float(data.get("capacity", 1000)),
            "length": float(data.get("length", 1.0)),
            "cost_per_unit": float(data.get("cost", 1.0)),
        })

    from traffic_control.models import Network
    return Network(junctions=junctions, roads=roads)


def save_network_graphml(network: "Network", path: str | Path) -> None:
    try:
        import networkx as nx
    except ImportError:
        raise ParseError("networkx required for GraphML export")

    G = nx.DiGraph()
    for j in network.junctions:
        G.add_node(j.id, position=str(j.position), external_flow=j.external_flow)
    for r in network.roads:
        G.add_edge(r.source, r.target, id=r.id, capacity=r.capacity, length=r.length, cost=r.cost_per_unit)

    nx.write_graphml(G, path)


def parse_sumo_network(net_file: str | Path) -> "Network":
    """
    Parse SUMO .net.xml file into Network.

    Requires sumolib. Install with: pip install sumolib
    """
    try:
        import sumolib
    except ImportError:
        raise ParseError("sumolib required for SUMO parsing. Install with: pip install sumolib")

    net = sumolib.net.readNet(str(net_file))

    junctions = []
    for node in net.getNodes():
        x, y = node.getCoord()
        junctions.append({
            "id": node.getID(),
            "position": (float(x), float(y)),
            "external_flow": 0.0,
        })

    roads = []
    for edge in net.getEdges():
        if edge.getFunction() == "internal":
            continue
        from_node = edge.getFromNode().getID()
        to_node = edge.getToNode().getID()
        length = edge.getLength()
        speed = edge.getSpeed()
        lanes = len(edge.getLanes())
        capacity = lanes * speed * 3.6

        for i, lane in enumerate(edge.getLanes()):
            roads.append({
                "id": f"{edge.getID()}_{i}",
                "source": from_node,
                "target": to_node,
                "capacity": capacity,
                "length": length,
                "cost_per_unit": 1.0,
                "lanes": 1,
            })

    from traffic_control.models import Network
    return Network(junctions=junctions, roads=roads)


def export_sumo_network(network: "Network", output_file: str | Path) -> None:
    """
    Export Network to SUMO .net.xml format.

    This creates a basic network file. For production use, use netconvert.
    """
    from traffic_control.models import Network

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<net version="1.9" junctionCornerDetail="5" limitTurnSpeed="5.50">',
    ]

    for junction in network.junctions:
        x, y = junction.position
        lines.append(f'    <junction id="{junction.id}" x="{x:.2f}" y="{y:.2f}" type="priority"/>')

    for road in network.roads:
        lanes = max(1, int(road.capacity / 1800))
        lines.append(
            f'    <edge id="{road.id}" from="{road.source}" to="{road.target}" '
            f'priority="1" numLanes="{lanes}" speed="{road.free_flow_speed / 3.6:.2f}"/>'
        )

    lines.append("</net>")

    with open(output_file, "w") as f:
        f.write("\n".join(lines))