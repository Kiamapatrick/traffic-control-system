# Traffic Control - Python Package

Core Python implementation of the traffic flow optimization system.

## Features

- **Solvers**: RREF (Gaussian elimination), Linear Programming (SciPy), MILP (OR-Tools), Max Flow (Dinic, Edmonds-Karp)
- **Network Operations**: Graph algorithms, validation, parsing (JSON, GraphML, SUMO)
- **ML Pipeline**: SUMO data generation, feature engineering, regression models (Linear, Ridge, RF, XGBoost), ONNX export
- **API**: FastAPI with JWT auth, MongoDB persistence (Beanie ODM)
- **CLI**: Typer-based commands for solving, validating, generating networks

## Installation

```bash
cd python
uv sync --all-extras
```

## Quickstart

```python
from traffic_control import (
    generate_four_junction_example,
    solve_rref,
    solve_lp,
    validate_solution,
)

network = generate_four_junction_example()
solution = solve_rref(network)
is_valid, violations = validate_solution(network, solution)
```

## Running Tests

```bash
# Unit tests
uv run pytest tests/unit -v

# Integration tests
uv run pytest tests/integration -v

# Property-based tests
uv run pytest tests/property -v

# All tests with coverage
uv run pytest --cov=traffic_control
```

## Code Quality

```bash
# Lint
uv run ruff check src tests

# Format
uv run ruff format src tests

# Type check
uv run mypy src
```

## CLI

```bash
# Solve network
traffic-control solve network.json --method rref
traffic-control solve network.json --method lp --objective min_cost

# Validate
traffic-control validate network.json

# Generate examples
traffic-control generate --type four-junction --output network.json

# Benchmark
traffic-control benchmark network.json --runs 10
```

## Documentation

See the root [README.md](../README.md) for full project documentation, architecture decisions, and deployment guides.