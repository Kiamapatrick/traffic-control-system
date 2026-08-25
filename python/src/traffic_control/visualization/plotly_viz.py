from __future__ import annotations

import plotly.graph_objects as go
import plotly.express as px
import numpy as np
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from traffic_control.models import Network, FlowSolution


def create_network_figure(
    network: "Network",
    solution: "FlowSolution | None" = None,
    title: str = "Traffic Network",
) -> go.Figure:
    positions = {j.id: j.position for j in network.junctions}
    flows = solution.flows if solution else {r.id: r.flow for r in network.roads}
    max_flow = max(flows.values()) if flows else 1

    fig = go.Figure()

    for road in network.roads:
        src_pos = positions.get(road.source)
        tgt_pos = positions.get(road.target)
        if src_pos is None or tgt_pos is None:
            continue

        sx, sy = src_pos
        tx, ty = tgt_pos
        flow = flows.get(road.id, 0)

        width = 2 + 8 * (flow / max_flow if max_flow > 0 else 0)
        color_intensity = flow / max_flow if max_flow > 0 else 0
        color = px.colors.sample_colorscale("Viridis", color_intensity)[0]

        dx, dy = tx - sx, ty - sy
        length = np.hypot(dx, dy)
        if length == 0:
            continue

        ux, uy = dx / length, dy / length
        offset = 15
        start_x = sx + offset * ux
        start_y = sy + offset * uy
        end_x = tx - offset * ux
        end_y = ty - offset * uy

        fig.add_annotation(
            x=end_x, y=end_y,
            ax=start_x, ay=start_y,
            xref="x", yref="y",
            axref="x", ayref="y",
            showarrow=True,
            arrowhead=2,
            arrowsize=1 + width / 4,
            arrowwidth=width,
            arrowcolor=color,
            opacity=0.8,
        )

        mid_x = (sx + tx) / 2
        mid_y = (sy + ty) / 2
        fig.add_annotation(
            x=mid_x, y=mid_y,
            text=f"{road.id}: {flow:.0f}",
            showarrow=False,
            font=dict(size=10, color="black"),
            bgcolor="white",
            bordercolor=color,
            borderwidth=1,
            opacity=0.9,
        )

    for junction in network.junctions:
        pos = positions[junction.id]
        fig.add_trace(go.Scatter(
            x=[pos[0]], y=[pos[1]],
            mode="markers+text",
            marker=dict(size=30, color="black", symbol="circle"),
            text=[junction.id],
            textfont=dict(size=14, color="white", family="Arial Black"),
            textposition="middle center",
            showlegend=False,
            hoverinfo="text",
            hovertext=f"Junction {junction.id}<br>External flow: {junction.external_flow:+.0f}",
        ))

        if junction.external_flow != 0:
            color = "green" if junction.external_flow > 0 else "red"
            fig.add_annotation(
                x=pos[0], y=pos[1] - 30,
                text=f"{junction.external_flow:+.0f}",
                showarrow=False,
                font=dict(size=12, color=color, family="Arial Black"),
            )

    x_coords = [p[0] for p in positions.values()]
    y_coords = [p[1] for p in positions.values()]
    x_margin = (max(x_coords) - min(x_coords)) * 0.15 + 20
    y_margin = (max(y_coords) - min(y_coords)) * 0.15 + 20

    fig.update_layout(
        title=title,
        xaxis=dict(range=[min(x_coords) - x_margin, max(x_coords) + x_margin], visible=False),
        yaxis=dict(range=[min(y_coords) - y_margin, max(y_coords) + y_margin], visible=False, scaleanchor="x", scaleratio=1),
        showlegend=False,
        plot_bgcolor="white",
        height=600,
        margin=dict(l=20, r=20, t=50, b=20),
    )

    return fig


def create_flow_bar_chart(solution: "FlowSolution", title: str = "Flow by Road") -> go.Figure:
    roads = list(solution.flows.keys())
    flows = list(solution.flows.values())

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=roads,
        y=flows,
        marker_color=px.colors.sample_colorscale("Viridis", np.linspace(0, 1, len(roads))),
        text=[f"{f:.0f}" for f in flows],
        textposition="outside",
        hovertemplate="%{x}: %{y:.1f} veh/h<extra></extra>",
    ))

    fig.update_layout(
        title=title,
        xaxis_title="Road",
        yaxis_title="Flow (veh/h)",
        showlegend=False,
        plot_bgcolor="white",
        height=400,
    )
    return fig


def create_solver_comparison_chart(results: dict[str, "FlowSolution"], title: str = "Solver Comparison") -> go.Figure:
    road_ids = set()
    for sol in results.values():
        road_ids.update(sol.flows.keys())
    road_ids = sorted(road_ids)

    fig = go.Figure()
    methods = list(results.keys())
    colors = px.colors.qualitative.Set1

    for i, method in enumerate(methods):
        flows = [results[method].flows.get(rid, 0) for rid in road_ids]
        fig.add_trace(go.Bar(
            name=method,
            x=road_ids,
            y=flows,
            marker_color=colors[i % len(colors)],
            hovertemplate=f"{method}: %{{y:.1f}} veh/h<extra></extra>",
        ))

    fig.update_layout(
        title=title,
        xaxis_title="Road",
        yaxis_title="Flow (veh/h)",
        barmode="group",
        plot_bgcolor="white",
        height=500,
    )
    return fig


def create_ml_metrics_chart(comparison_data: list[dict], title: str = "Model Comparison") -> go.Figure:
    df_data = comparison_data if isinstance(comparison_data, list) else [comparison_data]
    models = [d["model"] for d in df_data]

    fig = go.Figure()
    fig.add_trace(go.Bar(name="MAE", x=models, y=[d["mae"] for d in df_data], marker_color="#3498db"))
    fig.add_trace(go.Bar(name="RMSE", x=models, y=[d["rmse"] for d in df_data], marker_color="#e74c3c"))
    fig.add_trace(go.Bar(name="MAPE (%)", x=models, y=[d["mape"] * 100 for d in df_data], marker_color="#2ecc71"))

    fig.update_layout(
        title=title,
        xaxis_title="Model",
        yaxis_title="Error",
        barmode="group",
        plot_bgcolor="white",
        height=400,
    )
    return fig


def create_time_series_chart(df, x: str = "time", y: str = "flow", color: str = "edge_id", title: str = "Flow Time Series") -> go.Figure:
    import pandas as pd
    if isinstance(df, pd.DataFrame):
        fig = px.line(df, x=x, y=y, color=color, title=title)
    else:
        fig = go.Figure()
        for trace in df:
            fig.add_trace(go.Scatter(x=trace[x], y=trace[y], mode="lines", name=trace.get("name", "")))

    fig.update_layout(
        plot_bgcolor="white",
        height=400,
    )
    return fig


def create_3d_network(network: "Network", solution: "FlowSolution | None" = None) -> go.Figure:
    positions = {j.id: j.position for j in network.junctions}
    flows = solution.flows if solution else {r.id: r.flow for r in network.roads}
    max_flow = max(flows.values()) if flows else 1

    fig = go.Figure()

    for road in network.roads:
        src_pos = positions.get(road.source)
        tgt_pos = positions.get(road.target)
        if src_pos is None or tgt_pos is None:
            continue

        sx, sy = src_pos
        tx, ty = tgt_pos
        flow = flows.get(road.id, 0)
        width = 2 + 8 * (flow / max_flow if max_flow > 0 else 0)
        color_intensity = flow / max_flow if max_flow > 0 else 0
        color = px.colors.sample_colorscale("Viridis", color_intensity)[0]

        fig.add_trace(go.Scatter3d(
            x=[sx, tx, None],
            y=[sy, ty, None],
            z=[0, 0, None],
            mode="lines",
            line=dict(color=color, width=width),
            showlegend=False,
            hoverinfo="none",
        ))

    for junction in network.junctions:
        pos = positions[junction.id]
        fig.add_trace(go.Scatter3d(
            x=[pos[0]], y=[pos[1]], z=[0],
            mode="markers+text",
            marker=dict(size=10, color="black"),
            text=[junction.id],
            textfont=dict(size=12, color="white"),
            showlegend=False,
        ))

    fig.update_layout(
        title="3D Network View",
        scene=dict(
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            zaxis=dict(visible=False),
        ),
        height=600,
    )
    return fig