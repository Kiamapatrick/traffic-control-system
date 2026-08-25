from __future__ import annotations

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, FlowSolution


def draw_network(
    network: "Network",
    solution: "FlowSolution | None" = None,
    ax=None,
    figsize: tuple[int, int] = (10, 8),
    show_labels: bool = True,
    show_capacities: bool = False,
    edge_width_scale: float = 0.01,
    min_width: float = 1.0,
    max_width: float = 6.0,
    cmap: str = "viridis",
) -> tuple[plt.Figure, plt.Axes]:
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    positions = {j.id: j.position for j in network.junctions}

    if not positions:
        return fig, ax

    x_coords = [p[0] for p in positions.values()]
    y_coords = [p[1] for p in positions.values()]
    x_margin = (max(x_coords) - min(x_coords)) * 0.1 + 10
    y_margin = (max(y_coords) - min(y_coords)) * 0.1 + 10
    ax.set_xlim(min(x_coords) - x_margin, max(x_coords) + x_margin)
    ax.set_ylim(min(y_coords) - y_margin, max(y_coords) + y_margin)
    ax.set_aspect("equal")
    ax.axis("off")

    flows = solution.flows if solution else {r.id: r.flow for r in network.roads}
    max_flow = max(flows.values()) if flows else 1

    for road in network.roads:
        src_pos = positions.get(road.source)
        tgt_pos = positions.get(road.target)
        if src_pos is None or tgt_pos is None:
            continue

        sx, sy = src_pos
        tx, ty = tgt_pos

        flow = flows.get(road.id, 0)
        width = min_width + (max_width - min_width) * (flow / max_flow if max_flow > 0 else 0)

        dx, dy = tx - sx, ty - sy
        length = np.hypot(dx, dy)
        if length == 0:
            continue

        ux, uy = dx / length, dy / length
        offset = 15
        start_pt = (sx + offset * ux, sy + offset * uy)
        end_pt = (tx - offset * ux, ty - offset * uy)

        color_intensity = flow / max_flow if max_flow > 0 else 0
        cmap_obj = plt.get_cmap(cmap)
        color = cmap_obj(color_intensity)

        arrow = FancyArrowPatch(
            start_pt, end_pt,
            arrowstyle="->",
            mutation_scale=15 + width * 2,
            color=color,
            linewidth=width,
            alpha=0.8,
        )
        ax.add_patch(arrow)

        if show_labels or show_capacities:
            mx = (sx + tx) / 2
            my = (sy + ty) / 2
            labels = []
            if show_labels:
                labels.append(f"{road.id}: {flow:.0f}")
            if show_capacities:
                labels.append(f"cap: {road.capacity:.0f}")
            if labels:
                ax.text(mx, my, "\n".join(labels), ha="center", va="center",
                        fontsize=8, bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=color, alpha=0.9))

    for junction in network.junctions:
        pos = positions[junction.id]
        circle = plt.Circle(pos, 12, color="black", fill=False, linewidth=2)
        ax.add_patch(circle)
        ax.text(pos[0], pos[1], junction.id, ha="center", va="center", fontsize=12, fontweight="bold")

        if junction.external_flow != 0:
            label = f"{junction.external_flow:+.0f}"
            color = "green" if junction.external_flow > 0 else "red"
            ax.text(pos[0], pos[1] - 25, label, ha="center", va="center",
                    fontsize=10, color=color, fontweight="bold")

    ax.set_title("Traffic Network Flow", fontsize=14, pad=20)
    plt.tight_layout()
    return fig, ax


def plot_flow_distribution(solution: "FlowSolution", ax=None, figsize: tuple[int, int] = (8, 5)) -> tuple[plt.Figure, plt.Axes]:
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    flows = list(solution.flows.values())
    roads = list(solution.flows.keys())

    bars = ax.bar(range(len(flows)), flows, color=plt.cm.viridis(np.linspace(0, 1, len(flows))), edgecolor="white")
    ax.set_xticks(range(len(roads)))
    ax.set_xticklabels(roads, rotation=45, ha="right")
    ax.set_ylabel("Flow (veh/h)")
    ax.set_title("Flow Distribution by Road")

    for bar, val in zip(bars, flows):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(flows) * 0.01,
                f"{val:.0f}", ha="center", va="bottom", fontsize=9)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig, ax


def plot_solver_comparison(results: dict[str, "FlowSolution"], ax=None, figsize: tuple[int, int] = (10, 6)) -> tuple[plt.Figure, plt.Axes]:
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    methods = list(results.keys())
    road_ids = set()
    for sol in results.values():
        road_ids.update(sol.flows.keys())
    road_ids = sorted(road_ids)

    x = np.arange(len(road_ids))
    width = 0.8 / len(methods)

    for i, method in enumerate(methods):
        flows = [results[method].flows.get(rid, 0) for rid in road_ids]
        ax.bar(x + i * width - 0.4 + width/2, flows, width, label=method, alpha=0.8)

    ax.set_xticks(x)
    ax.set_xticklabels(road_ids, rotation=45, ha="right")
    ax.set_ylabel("Flow (veh/h)")
    ax.set_title("Solver Comparison")
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig, ax


def plot_ml_metrics(comparison_df, ax=None, figsize: tuple[int, int] = (8, 5)) -> tuple[plt.Figure, plt.Axes]:
    import pandas as pd
    if ax is None:
        fig, ax = plt.subplots(figsize=figsize)
    else:
        fig = ax.figure

    df = comparison_df if isinstance(comparison_df, pd.DataFrame) else pd.DataFrame(comparison_df)
    x = np.arange(len(df))
    width = 0.25

    ax.bar(x - width, df["mae"], width, label="MAE", color="#3498db")
    ax.bar(x, df["rmse"], width, label="RMSE", color="#e74c3c")
    ax.bar(x + width, df["mape"] * 100, width, label="MAPE (%)", color="#2ecc71")

    ax.set_xticks(x)
    ax.set_xticklabels(df["model"], rotation=45, ha="right")
    ax.set_ylabel("Error")
    ax.set_title("Model Comparison")
    ax.legend()
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    plt.tight_layout()
    return fig, ax