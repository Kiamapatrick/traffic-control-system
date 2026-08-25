# Contributing to Traffic Control System

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Code of Conduct

This project follows the [Contributor Covenant Code of Conduct](https://www.contributor-covenant.org/version/2/1/code_of_conduct/). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.11+
- Rust 1.75+
- Node.js 20+
- Docker & Docker Compose
- MongoDB (local or Atlas)
- SUMO (for ML pipeline)

### Development Setup

```bash
# Clone repository
git clone https://github.com/yourusername/traffic-control-system.git
cd traffic-control-system

# Python
cd python && uv sync --all-extras

# Rust
cd rust && cargo build

# TypeScript
cd typescript && npm install

# Frontend
cd frontend && npm install

# Start services
docker-compose -f docker/docker-compose.yml up -d
```

## Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code following project conventions
- Add tests for new functionality
- Update documentation if needed

### 3. Run Checks

```bash
# Python
cd python && uv run ruff check src tests
cd python && uv run ruff format --check src tests
cd python && uv run mypy src
cd python && uv run pytest

# Rust
cd rust && cargo clippy -- -D warnings
cd rust && cargo test

# TypeScript
cd typescript && npm run lint
cd typescript && npm test

# Frontend
cd frontend && npm run lint
cd frontend && npm test
```

### 4. Commit Changes

```bash
git add .
git commit -m "feat: add your feature description"
```

Follow [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` new feature
- `fix:` bug fix
- `docs:` documentation changes
- `refactor:` code restructuring
- `test:` adding tests
- `chore:` maintenance tasks

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
```

Open a Pull Request against `main` branch.

## Code Style

### Python

- Follow PEP 8 (enforced by ruff)
- Type hints required for all public functions
- Docstrings for public APIs (Google style)
- Maximum line length: 100 characters

### Rust

- Follow standard Rust style (rustfmt)
- Clippy warnings treated as errors
- Document public APIs with `///`

### TypeScript

- Strict mode enabled
- ESLint with TypeScript recommended rules
- Prefer interfaces over types for public APIs

### Frontend

- React functional components with hooks
- Tailwind CSS for styling
- Component names in PascalCase
- Custom hooks prefixed with `use`

## Testing

### Python

- Unit tests in `tests/unit/`
- Integration tests in `tests/integration/`
- Property-based tests in `tests/property/` (Hypothesis)
- Target: >80% coverage

### Rust

- Unit tests in `src/` modules (`#[cfg(test)]`)
- Integration tests in `tests/`
- Benchmarks in `benches/`

### TypeScript

- Tests in `tests/` with Vitest
- Target: >70% coverage

### Frontend

- Component tests with React Testing Library
- E2E tests with Playwright (optional)

## Pull Request Checklist

- [ ] All CI checks pass
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or marked as such)
- [ ] Conventional commit messages
- [ ] Branch up to date with main

## Release Process

1. Update version in `pyproject.toml`, `Cargo.toml`, `package.json`
2. Update `CHANGELOG.md`
3. Create release tag: `git tag v0.2.0`
4. Push tag: `git push origin v0.2.0`
5. GitHub Actions builds and publishes Docker images
6. Create GitHub Release with changelog

## Reporting Issues

- Use GitHub Issues
- Include reproduction steps
- Specify environment (OS, versions)
- Add relevant labels

## Security Issues

Report security vulnerabilities privately to security@example.com. Do not open public issues.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.