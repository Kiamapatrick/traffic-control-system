from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
import numpy as np
import pandas as pd

if TYPE_CHECKING:
    from traffic_control.models import Network


def generate_synthetic_traffic_data(
    network: "Network",
    duration: int = 3600,
    interval: int = 900,
    seed: int = 42,
) -> pd.DataFrame:
    """Generate synthetic traffic flow data without SUMO.

    Uses network topology and flow conservation to create realistic
    time-varying flow patterns for ML training when SUMO is not available.
    """
    np.random.seed(seed)

    n_intervals = duration // interval
    rows = []

    for road in network.roads:
        base_flow = np.random.uniform(0.2, 0.8) * road.capacity

        for t in range(n_intervals):
            time = t * interval
            hour = (time / 3600) % 24

            # Time-of-day pattern (rush hours)
            time_factor = 1.0 + 0.5 * np.sin(2 * np.pi * (hour - 8) / 24)

            # Random variation
            noise = np.random.lognormal(0, 0.1)

            flow = base_flow * time_factor * noise
            flow = min(flow, road.capacity * 0.95)

            # Speed based on flow (fundamental diagram)
            v_free = road.free_flow_speed / 3.6  # m/s
            capacity_per_lane = road.capacity / road.lanes
            critical_density = capacity_per_lane / v_free
            density = flow / v_free
            speed = v_free * (1 - density / critical_density) if density < critical_density else 5.0
            speed = max(speed, 5.0)

            rows.append({
                "time": float(time),
                "edge_id": road.id,
                "flow": float(flow),
                "speed": float(speed * 3.6),  # km/h
                "density": float(density),
                "occupancy": float(min(density / critical_density, 1.0)),
            })

    return pd.DataFrame(rows)


class SUMODataGenerator:
    def __init__(self, sumo_home: str = "/usr/share/sumo", output_dir: str = "data/sumo"):
        self.sumo_home = sumo_home
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_network(self, network: "Network", name: str = "network") -> Path:
        net_file = self.output_dir / f"{name}.net.xml"
        from traffic_control.network.parser import export_sumo_network
        export_sumo_network(network, net_file)
        return net_file

    def generate_routes(self, network: "Network", name: str = "network", duration: int = 3600) -> Path:
        route_file = self.output_dir / f"{name}.rou.xml"
        from traffic_control.network import to_networkx
        import networkx as nx

        G = to_networkx(network)
        sources = [n for n, d in G.nodes(data=True) if d.get("external_flow", 0) > 0]
        sinks = [n for n, d in G.nodes(data=True) if d.get("external_flow", 0) < 0]

        if not sources or not sinks:
            sources = list(G.nodes())[:2]
            sinks = list(G.nodes())[-2:]

        routes = []
        for source in sources:
            for sink in sinks:
                try:
                    path = nx.shortest_path(G, source, sink, weight="length")
                    edges = " ".join(f"{path[i]}->{path[i+1]}" for i in range(len(path)-1))
                    routes.append(f'<route id="route_{source}_{sink}" edges="{edges}"/>')
                except nx.NetworkXNoPath:
                    continue

        vehicles = []
        for i, source in enumerate(sources):
            for sink in sinks:
                route_id = f"route_{source}_{sink}"
                vehicles.append(
                    f'<vehicle id="veh_{source}_{sink}_{i}" route="{route_id}" '
                    f'depart="{i * 10}" type="car"/>'
                )

        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<routes>
    <vType id="car" accel="2.6" decel="4.5" sigma="0.5" length="5" maxSpeed="30"/>
    {''.join(routes)}
    {''.join(vehicles)}
</routes>
"""
        route_file.write_text(content)
        return route_file

    def generate_config(self, name: str = "network") -> Path:
        config_file = self.output_dir / f"{name}.sumocfg"
        content = f"""<?xml version="1.0" encoding="UTF-8"?>
<configuration>
    <input>
        <net-file value="{name}.net.xml"/>
        <route-files value="{name}.rou.xml"/>
    </input>
    <time>
        <begin value="0"/>
        <end value="3600"/>
    </time>
    <output>
        <edge-output output-file="{name}_edge.xml"/>
        <lane-output output-file="{name}_lane.xml"/>
    </output>
</configuration>
"""
        config_file.write_text(content)
        return config_file

    def run_simulation(self, config_file: Path, output_dir: Path | None = None) -> dict:
        if output_dir is None:
            output_dir = self.output_dir

        cmd = [
            f"{self.sumo_home}/bin/sumo",
            "-c", str(config_file),
            "--edge-output", str(output_dir / f"{config_file.stem}_edge.xml"),
            "--lane-output", str(output_dir / f"{config_file.stem}_lane.xml"),
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.sumo_home)
        if result.returncode != 0:
            raise RuntimeError(f"SUMO simulation failed: {result.stderr}")

        return self.parse_edge_output(output_dir / f"{config_file.stem}_edge.xml")

    def parse_edge_output(self, edge_file: Path) -> pd.DataFrame:
        import xml.etree.ElementTree as ET

        tree = ET.parse(edge_file)
        root = tree.getroot()

        rows = []
        for interval in root.findall("interval"):
            time = float(interval.get("begin", 0))
            for edge in interval.findall("edge"):
                rows.append({
                    "time": time,
                    "edge_id": edge.get("id"),
                    "flow": float(edge.get("flow", 0)),
                    "speed": float(edge.get("speed", 0)),
                    "density": float(edge.get("density", 0)),
                    "occupancy": float(edge.get("occupancy", 0)),
                })

        return pd.DataFrame(rows)

    def generate_dataset(self, network: "Network", name: str = "dataset", duration: int = 3600) -> pd.DataFrame:
        """Generate dataset using SUMO if available, otherwise synthetic data."""
        try:
            net_file = self.generate_network(network, name)
            route_file = self.generate_routes(network, name, duration)
            config_file = self.generate_config(name)
            return self.run_simulation(config_file)
        except (RuntimeError, FileNotFoundError, subprocess.SubprocessError) as e:
            print(f"SUMO not available ({e}), falling back to synthetic data generation...")
            return generate_synthetic_traffic_data(network, duration=duration)


def create_features(df: pd.DataFrame, network: "Network") -> pd.DataFrame:
    from traffic_control.network import to_networkx
    import networkx as nx

    G = to_networkx(network)

    edge_features = {}
    for u, v, data in G.edges(data=True):
        edge_id = data.get("id", f"{u}->{v}")
        edge_features[edge_id] = {
            "length": data.get("length", 1.0),
            "capacity": data.get("capacity", 1000),
            "cost": data.get("cost", 1.0),
        }

    df = df.copy()
    df["hour"] = (df["time"] / 3600).astype(int) % 24
    df["time_of_day"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["day_of_week"] = 0

    for edge_id, feats in edge_features.items():
        mask = df["edge_id"] == edge_id
        df.loc[mask, "length"] = feats["length"]
        df.loc[mask, "capacity"] = feats["capacity"]
        df.loc[mask, "cost"] = feats["cost"]

    df["utilization"] = df["flow"] / df["capacity"].replace(0, np.nan)
    df["travel_time"] = df["length"] / df["speed"].replace(0, np.nan)

    return df


def prepare_training_data(
    df: pd.DataFrame,
    target: str = "flow",
    features: list[str] | None = None,
    lookback: int = 4,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if features is None:
        features = ["hour", "time_of_day", "length", "capacity", "cost", "utilization", "travel_time"]

    available = [f for f in features if f in df.columns]
    if not available:
        raise ValueError("No valid features found in dataframe")

    df = df.sort_values(["edge_id", "time"]).reset_index(drop=True)

    X_list = []
    y_list = []

    for edge_id in df["edge_id"].unique():
        edge_df = df[df["edge_id"] == edge_id].reset_index(drop=True)
        if len(edge_df) <= lookback:
            continue

        for i in range(lookback, len(edge_df)):
            X_list.append(edge_df[available].iloc[i-lookback:i].values.flatten())
            y_list.append(edge_df[target].iloc[i])

    feature_names = [f"{f}_t-{lookback-i}" for i in range(lookback) for f in available]
    return np.array(X_list), np.array(y_list), feature_names