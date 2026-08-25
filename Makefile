.PHONY: help install test lint typecheck build clean docker-build docker-up docker-down benchmark

# Default target
help:
	@echo "Traffic Control System - Build Commands"
	@echo ""
	@echo "Python:"
	@echo "  install        Install Python dependencies with uv"
	@echo "  test           Run Python tests with pytest"
	@echo "  lint           Run ruff linter"
	@echo "  typecheck      Run mypy type checker"
	@echo "  format         Format code with ruff"
	@echo "  benchmark      Run Python benchmarks"
	@echo ""
	@echo "Rust:"
	@echo "  rust-test      Run Rust tests"
	@echo "  rust-bench     Run Rust benchmarks"
	@echo "  rust-lint      Run cargo clippy"
	@echo ""
	@echo "TypeScript:"
	@echo "  ts-install     Install TypeScript dependencies"
	@echo "  ts-test        Run TypeScript tests"
	@echo "  ts-build       Build TypeScript"
	@echo "  ts-lint        Run ESLint"
	@echo ""
	@echo "Frontend:"
	@echo "  frontend-install  Install frontend dependencies"
	@echo "  frontend-dev      Start frontend dev server"
	@echo "  frontend-build    Build frontend for production"
	@echo "  frontend-test     Run frontend tests"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build   Build all Docker images"
	@echo "  docker-up      Start all services with docker-compose"
	@echo "  docker-down    Stop all services"
	@echo "  docker-logs    View logs"
	@echo ""
	@echo "All:"
	@echo "  check          Run all lints, type checks, and tests"
	@echo "  clean          Clean build artifacts"

# Python commands
install:
	cd python && uv sync --all-extras

test:
	cd python && uv run pytest -v

lint:
	cd python && uv run ruff check src tests

format:
	cd python && uv run ruff format src tests

typecheck:
	cd python && uv run mypy src

benchmark:
	cd python && uv run python scripts/benchmark_solvers.py

# Rust commands
rust-test:
	cd rust && cargo test

rust-bench:
	cd rust && cargo bench

rust-lint:
	cd rust && cargo clippy -- -D warnings

# TypeScript commands
ts-install:
	cd typescript && npm install

ts-test:
	cd typescript && npm test

ts-build:
	cd typescript && npm run build

ts-lint:
	cd typescript && npm run lint

# Frontend commands
frontend-install:
	cd frontend && npm install

frontend-dev:
	cd frontend && npm run dev

frontend-build:
	cd frontend && npm run build

frontend-test:
	cd frontend && npm test

# Docker commands
docker-build:
	docker-compose -f docker/docker-compose.yml build

docker-up:
	docker-compose -f docker/docker-compose.yml up -d

docker-down:
	docker-compose -f docker/docker-compose.yml down

docker-logs:
	docker-compose -f docker/docker-compose.yml logs -f

# Combined checks
check: lint typecheck test rust-lint rust-test ts-lint ts-test frontend-test
	@echo "All checks passed!"

# Clean
clean:
	cd python && rm -rf .venv __pycache__ .mypy_cache .ruff_cache .pytest_cache htmlcov .coverage
	cd rust && cargo clean
	cd typescript && rm -rf dist node_modules
	cd frontend && rm -rf .next node_modules out
	docker-compose -f docker/docker-compose.yml down -v

# Development
dev: docker-up
	@echo "Services started. API: http://localhost:8000, Frontend: http://localhost:3000"
	@echo "Run 'make docker-logs' to see logs"