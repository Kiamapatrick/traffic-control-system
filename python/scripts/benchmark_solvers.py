#!/usr/bin/env python
"""Benchmark script for comparing solver performance."""

import time
import statistics
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from traffic_control import (
    generate_grid_network,
    generate_four_junction_example,
    solve_rref,
    solve_lp,
    solve_milp,
    solve_max_flow,
)


def benchmark_solver(solver_func, network, runs=10, **kwargs):
    times = []
    for _ in range(runs):
        start = time.perf_counter()
        try:
            solver_func(network, **kwargs)
        except Exception:
            pass
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)
    return times


def run_benchmarks():
    print("=" * 60)
    print("Traffic Control Solver Benchmarks")
    print("=" * 60)

    networks = {
        "four_junction": generate_four_junction_example(),
        "grid_3x3": generate_grid_network(3, 3, seed=42),
        "grid_4x4": generate_grid_network(4, 4, seed=42),
        "grid_5x5": generate_grid_network(5, 5, seed=42),
    }

    solvers = [
        ("RREF", solve_rref, {}),
        ("LP (min_cost)", solve_lp, {"objective": "min_cost"}),
        ("LP (max_throughput)", solve_lp, {"objective": "max_throughput"}),
        ("MILP", solve_milp, {}),
    ]

    results = {}

    for net_name, network in networks.items():
        print(f"\nNetwork: {net_name} ({len(network.junctions)} junctions, {len(network.roads)} roads)")
        print("-" * 60)

        results[net_name] = {}

        for solver_name, solver_func, kwargs in solvers:
            if solver_name == "MILP" and len(network.roads) > 20:
                print(f"  {solver_name}: SKIPPED (too large for MILP)")
                continue

            times = benchmark_solver(solver_func, network, runs=10, **kwargs)
            mean = statistics.mean(times)
            stdev = statistics.stdev(times) if len(times) > 1 else 0
            min_t = min(times)
            max_t = max(times)

            results[net_name][solver_name] = {
                "mean_ms": mean,
                "stdev_ms": stdev,
                "min_ms": min_t,
                "max_ms": max_t,
                "times_ms": times,
            }

            print(f"  {solver_name:25s} {mean:8.2f}±{stdev:6.2f}ms  (min={min_t:.2f}, max={max_t:.2f})")

    # Max flow benchmarks
    print("\n" + "=" * 60)
    print("Max Flow Benchmarks (A -> C)")
    print("=" * 60)

    for net_name, network in networks.items():
        if len(network.junctions) < 4:
            continue

        print(f"\nNetwork: {net_name}")
        print("-" * 60)

        for algo_name, algo_kwargs in [("Edmonds-Karp", {"algorithm": "edmonds_karp"}), ("Dinic", {"algorithm": "dinic"})]:
            times = benchmark_solver(solve_max_flow, network, runs=10, source="A", sink="C", **algo_kwargs)
            mean = statistics.mean(times)
            stdev = statistics.stdev(times) if len(times) > 1 else 0

            print(f"  {algo_name:20s} {mean:8.2f}±{stdev:6.2f}ms")

    # Save results
    output_path = Path(__file__).parent.parent / "benchmark_results.json"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    return results


if __name__ == "__main__":
    run_benchmarks()