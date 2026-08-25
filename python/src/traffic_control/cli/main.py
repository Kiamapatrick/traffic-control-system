from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from traffic_control.models import (
    Network, FlowSolution, SolverMethod, OptimizationObjective
)
from traffic_control.solvers import (
    solve_rref, solve_lp, solve_milp, solve_max_flow, validate_solution
)
from traffic_control.network import (
    load_network_json, save_network_json,
    generate_four_junction_example, generate_manhattan_example,
    generate_roundabout_example, generate_grid_network, generate_random_network
)

app = typer.Typer(
    name="traffic-control",
    help="Traffic flow optimization CLI",
    add_completion=False,
    rich_markup_mode="rich",
)

console = Console()


def print_solution(solution: FlowSolution, network: Network | None = None) -> None:
    table = Table(title="Flow Solution")
    table.add_column("Road ID", style="cyan")
    table.add_column("Flow (veh/h)", justify="right", style="green")
    table.add_column("Capacity", justify="right", style="yellow")
    table.add_column("Utilization", justify="right", style="magenta")

    total_flow = 0.0
    for road_id, flow in solution.flows.items():
        total_flow += flow
        cap = "N/A"
        util = "N/A"
        if network:
            for r in network.roads:
                if r.id == road_id:
                    cap = f"{r.capacity:.0f}"
                    util = f"{flow / r.capacity * 100:.1f}%" if r.capacity > 0 else "N/A"
                    break
        table.add_row(road_id, f"{flow:.2f}", cap, util)

    console.print(table)
    console.print(f"\nTotal flow: {total_flow:.2f} veh/h")
    console.print(f"Method: {solution.method.value}")
    if solution.objective_value is not None:
        console.print(f"Objective value: {solution.objective_value:.2f}")
    console.print(f"Feasible: {'✓' if solution.is_feasible else '✗'}")
    if solution.violations:
        console.print("[red]Violations:[/red]")
        for v in solution.violations:
            console.print(f"  - {v}")


@app.command()
def solve(
    network_file: Annotated[Path, typer.Argument(help="Path to network JSON file")],
    method: Annotated[SolverMethod, typer.Option("--method", "-m", help="Solver method")] = SolverMethod.RREF,
    objective: Annotated[OptimizationObjective | None, typer.Option("--objective", "-o", help="Optimization objective")] = None,
    source: Annotated[str | None, typer.Option("--source", "-s", help="Source junction (for max flow)")] = None,
    sink: Annotated[str | None, typer.Option("--sink", "-t", help="Sink junction (for max flow)")] = None,
    algorithm: Annotated[str, typer.Option("--algorithm", "-a", help="Max flow algorithm")] = "dinic",
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Output solution to file")] = None,
):
    """Solve traffic flow for a network."""
    if not network_file.exists():
        console.print(f"[red]Error:[/red] File not found: {network_file}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading network...", total=None)
        network = load_network_json(network_file)
        progress.update(task, description="Solving...")

        params = {}
        if source:
            params["source"] = source
        if sink:
            params["sink"] = sink
        if algorithm:
            params["algorithm"] = algorithm

        if method == SolverMethod.RREF:
            solution = solve_rref(network)
        elif method == SolverMethod.LINEAR_PROGRAMMING:
            solution = solve_lp(network, objective)
        elif method == SolverMethod.MILP:
            solution = solve_milp(network)
        elif method in (SolverMethod.MAX_FLOW, SolverMethod.DINIC):
            if not source or not sink:
                console.print("[red]Error:[/red] MAX_FLOW/DINIC requires --source and --sink")
                raise typer.Exit(1)
            solution = solve_max_flow(network, source, sink, algorithm)
        else:
            console.print(f"[red]Error:[/red] Unknown method: {method}")
            raise typer.Exit(1)

    print_solution(solution, network)

    if output:
        save_network_json(network, output)
        console.print(f"\n[green]Solution saved to {output}[/green]")


@app.command()
def validate(
    network_file: Annotated[Path, typer.Argument(help="Path to network JSON file")],
    solution_file: Annotated[Path | None, typer.Option("--solution", "-s", help="Path to solution JSON file")] = None,
):
    """Validate network constraints."""
    if not network_file.exists():
        console.print(f"[red]Error:[/red] File not found: {network_file}")
        raise typer.Exit(1)

    network = load_network_json(network_file)

    flows = None
    if solution_file and solution_file.exists():
        with open(solution_file) as f:
            data = json.load(f)
            flows = data.get("flows", {})

    is_valid, violations = validate_solution(network, flows or {})

    if is_valid:
        console.print("[green]✓ Network is valid[/green]")
    else:
        console.print("[red]✗ Network has violations:[/red]")
        for v in violations:
            console.print(f"  - {v}")

    if not is_valid:
        raise typer.Exit(1)


@app.command()
def generate(
    type: Annotated[str, typer.Argument(help="Network type: four-junction, manhattan, roundabout, grid, random")],
    output: Annotated[Path, typer.Option("--output", "-o", help="Output file path")],
    rows: Annotated[int, typer.Option("--rows", help="Rows for grid")] = 4,
    cols: Annotated[int, typer.Option("--cols", help="Cols for grid")] = 5,
    junctions: Annotated[int, typer.Option("--junctions", help="Junctions for random")] = 20,
    roads: Annotated[int, typer.Option("--roads", help="Roads for random")] = 50,
    seed: Annotated[int | None, typer.Option("--seed", help="Random seed")] = None,
):
    """Generate example networks."""
    generators = {
        "four-junction": generate_four_junction_example,
        "manhattan": generate_manhattan_example,
        "roundabout": generate_roundabout_example,
        "grid": lambda: generate_grid_network(rows, cols, seed=seed),
        "random": lambda: generate_random_network(junctions, roads, seed=seed),
    }

    if type not in generators:
        console.print(f"[red]Error:[/red] Unknown type: {type}. Options: {', '.join(generators.keys())}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task(f"Generating {type} network...", total=None)
        network = generators[type]()
        progress.update(task, description="Saving...")
        save_network_json(network, output)

    console.print(f"[green]✓ Generated {type} network with {len(network.junctions)} junctions and {len(network.roads)} roads[/green]")
    console.print(f"Saved to: {output}")


@app.command()
def benchmark(
    network_file: Annotated[Path, typer.Argument(help="Path to network JSON file")],
    methods: Annotated[list[SolverMethod], typer.Option("--method", "-m", help="Methods to benchmark")] = [
        SolverMethod.RREF,
        SolverMethod.LINEAR_PROGRAMMING,
    ],
    runs: Annotated[int, typer.Option("--runs", "-r", help="Number of runs per method")] = 10,
):
    """Benchmark solver performance."""
    import time
    import statistics

    if not network_file.exists():
        console.print(f"[red]Error:[/red] File not found: {network_file}")
        raise typer.Exit(1)

    network = load_network_json(network_file)

    table = Table(title="Benchmark Results")
    table.add_column("Method", style="cyan")
    table.add_column("Mean (ms)", justify="right", style="green")
    table.add_column("Stdev (ms)", justify="right", style="yellow")
    table.add_column("Min (ms)", justify="right", style="blue")
    table.add_column("Max (ms)", justify="right", style="red")
    table.add_column("Feasible", justify="center")

    for method in methods:
        times = []
        feasible_count = 0

        for _ in range(runs):
            start = time.perf_counter()
            try:
                if method == SolverMethod.RREF:
                    solution = solve_rref(network)
                elif method == SolverMethod.LINEAR_PROGRAMMING:
                    solution = solve_lp(network)
                elif method == SolverMethod.MILP:
                    solution = solve_milp(network)
                else:
                    continue
                elapsed = (time.perf_counter() - start) * 1000
                times.append(elapsed)
                if solution.is_feasible:
                    feasible_count += 1
            except Exception as e:
                console.print(f"[red]Error with {method.value}: {e}[/red]")

        if times:
            table.add_row(
                method.value,
                f"{statistics.mean(times):.2f}",
                f"{statistics.stdev(times):.2f}" if len(times) > 1 else "N/A",
                f"{min(times):.2f}",
                f"{max(times):.2f}",
                f"{feasible_count}/{runs}",
            )

    console.print(table)


@app.command()
def serve(
    host: Annotated[str, typer.Option("--host", help="Host to bind")] = "0.0.0.0",
    port: Annotated[int, typer.Option("--port", help="Port to bind")] = 8000,
    reload: Annotated[bool, typer.Option("--reload", help="Enable auto-reload")] = False,
):
    """Start the API server."""
    import uvicorn
    uvicorn.run(
        "traffic_control.api.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    app()