# Architecture Decision Records

## ADR-001: Python Package Management with uv

**Status**: Accepted

**Context**: Need fast, reliable dependency management for Python 3.11+ project.

**Decision**: Use `uv` (Astral) instead of poetry, pipenv, or hatch.

**Rationale**:
- 10-100x faster than pip/poetry
- Built-in virtual environment management
- Lock file support with `uv.lock`
- Compatible with existing `pyproject.toml` standards
- Single binary, no Python runtime needed for install

**Consequences**:
- Team needs to install uv (single binary)
- CI needs `astral-sh/setup-uv` action
- Migration from existing poetry/pipenv projects straightforward

---

## ADR-002: FastAPI for REST API

**Status**: Accepted

**Context**: Need high-performance async API with automatic OpenAPI docs.

**Decision**: Use FastAPI over Flask, Django REST Framework, or aiohttp.

**Rationale**:
- Native async/await support with Starlette
- Automatic OpenAPI/Swagger UI generation
- Pydantic v2 integration for validation
- Excellent performance (on par with Node.js/Go)
- Type hints throughout for IDE support
- Dependency injection system

**Consequences**:
- Requires ASGI server (uvicorn)
- Async-only endpoints for best performance
- Learning curve for developers new to async Python

---

## ADR-003: JWT Authentication

**Status**: Accepted

**Context**: Need stateless authentication for API endpoints.

**Decision**: Use JWT (JSON Web Tokens) with HS256 algorithm.

**Rationale**:
- Stateless - no server-side session storage needed
- Works well with microservices and horizontal scaling
- Standard RFC 7519, wide library support
- Can include custom claims (roles, permissions)
- Short expiry (30 min) with refresh token pattern

**Consequences**:
- Token revocation requires blocklist or short expiry
- Secret key must be rotated periodically
- Payload size limited (browser header limits)
- HS256 symmetric - consider RS256 for multi-service

---

## ADR-004: MongoDB with Beanie ODM

**Status**: Accepted

**Context**: Need document database for flexible network storage.

**Decision**: Use MongoDB (Atlas) with Beanie ODM (async, Pydantic-based).

**Rationale**:
- Document model fits network/graph data naturally
- Flexible schema for evolving network structures
- Beanie provides async motor integration + Pydantic models
- Atlas provides managed cloud with free tier
- Geospatial queries for future location-based features

**Consequences**:
- Not relational - joins require application-level logic
- Eventual consistency by default
- Migration strategy needed for schema changes
- Atlas free tier has 512MB limit

---

## ADR-005: SUMO for Controllable Traffic Simulation

**Status**: Accepted

**Context**: Need realistic traffic data for ML training without real-world data complexity.

**Decision**: Use SUMO (Simulation of Urban MObility) for synthetic data generation.

**Rationale**:
- Open source, mature (20+ years), widely used in research
- Full control over network topology, demand, signals
- Outputs standard formats (edge/lane data XML)
- Can simulate thousands of vehicles efficiently
- Integrates with network generation code
- No privacy/licensing concerns vs real taxi data

**Consequences**:
- Requires SUMO installation (system dependency)
- Synthetic data may not capture all real-world patterns
- Calibration needed for realistic results
- XML parsing overhead for large simulations

---

## ADR-006: React Flow for Network Editor

**Status**: Accepted

**Context**: Need interactive graph editor for network construction.

**Decision**: Use React Flow (xyflow) over Cytoscape.js, D3.js, or custom canvas.

**Rationale**:
- React-native, hooks-based API
- Built-in nodes/edges/handles/panels
- Extensible with custom node/edge types
- Good TypeScript support
- Active maintenance, MIT license
- Handles large graphs (1000+ nodes) well

**Consequences**:
- Learning curve for custom node types
- Bundle size impact (~150KB gzipped)
- Some advanced layout algorithms require Pro version
- Accessibility requires extra work

---

## ADR-007: TypeScript for Browser Solver

**Status**: Accepted

**Context**: Need solver running in browser for interactive demo.

**Decision**: Implement solvers in TypeScript (not WASM from Rust).

**Rationale**:
- Zero-install demo in browser
- Easier debugging with source maps
- TypeScript types match Python Pydantic models
- No WASM compilation complexity
- Can share types via npm package
- Sufficient performance for demo-sized networks (<100 nodes)

**Consequences**:
- Slower than Rust/WASM for large networks
- Numerical precision differences (JS numbers vs f64)
- Maintenance burden of duplicate implementations
- No SIMD/parallelization in browser JS

---

## ADR-008: nalgebra + petgraph for Rust

**Status**: Accepted

**Context**: Need high-performance linear algebra and graph algorithms in Rust.

**Decision**: Use `nalgebra` for matrices and `petgraph` for graph algorithms.

**Rationale**:
- nalgebra: mature, feature-rich, good performance
- petgraph: standard graph library, multiple algorithms built-in
- Both well-maintained with good documentation
- No GPU compute needed for current problem sizes
- Serde integration for serialization

**Consequences**:
- nalgebra uses column-major (like Fortran/Matlab)
- petgraph Graph type parameterization can be verbose
- Learning curve for linear algebra in Rust

---

## ADR-009: Multi-Stage Docker Builds

**Status**: Accepted

**Context**: Need small, secure production images.

**Decision**: Use multi-stage builds for all services.

**Rationale**:
- Separates build dependencies from runtime
- Reduces attack surface (no compiler in prod)
- Leverages Docker layer caching
- Consistent pattern across Python/Rust/Node
- Enables distroless/scratch base images

**Consequences**:
- More complex Dockerfiles
- Build time slightly longer (but cached)
- Need to copy only necessary artifacts

---

## ADR-010: GitHub Actions for CI/CD

**Status**: Accepted

**Context**: Need automated testing, building, and deployment.

**Decision**: Use GitHub Actions with matrix strategies.

**Rationale**:
- Native GitHub integration
- Free for public repos, generous for private
- Matrix builds for multiple Python/Rust/Node versions
- Reusable workflows and composite actions
- OIDC for cloud deployments
- Pages deployment built-in

**Consequences**:
- Vendor lock-in to GitHub
- Self-hosted runners needed for specialized hardware
- YAML complexity for advanced workflows

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Traffic Control System                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐         │
│  │   Frontend  │    │   Python    │    │    Rust     │         │
│  │  (Next.js)  │◄──►│   API       │◄──►│   Solver    │         │
│  │  Port 3000  │    │  Port 8000  │    │   (CLI)     │         │
│  └─────────────┘    └──────┬──────┘    └─────────────┘         │
│                            │                                     │
│                    ┌───────▼───────┐    ┌─────────────┐         │
│                    │    MongoDB    │    │    SUMO     │         │
│                    │   (Atlas)     │    │  Simulator  │         │
│                    └───────────────┘    └─────────────┘         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **Frontend** → User creates network in React Flow editor
2. **Frontend** → POST `/api/v1/solve` with network + solver params
3. **Python API** → Validates JWT, dispatches to solver
4. **Solver** (Python/Rust/TS) → Computes flow solution
5. **Python API** → Returns solution, stores in MongoDB
6. **Frontend** → Updates React Flow edges with flow values
7. **ML Pipeline** → SUMO generates data → trains models → serves predictions

### Network Representation

```json
{
  "junctions": [
    {"id": "A", "position": [200, 600], "junctionType": "source", "externalFlow": 80}
  ],
  "roads": [
    {"id": "x1", "source": "A", "target": "B", "capacity": 100, "length": 6.0, "costPerUnit": 1}
  ]
}
```

### Solver Interface (All Languages)

```python
def solve(network: Network, method: SolverMethod, **params) -> FlowSolution:
    # method: rref | lp | milp | max_flow | dinic
    # returns: flows, objective_value, is_feasible, violations
```

---

## Performance Targets

| Solver | Network Size | Target Time | Language |
|--------|-------------|-------------|----------|
| RREF | 100x100 | <50ms | Python |
| RREF | 100x100 | <5ms | Rust |
| Simplex | 50 vars | <100ms | Python |
| Simplex | 50 vars | <10ms | Rust |
| Dinic | 1000 nodes | <50ms | Rust |
| Dinic | 1000 nodes | <5ms | Rust |

---

## Security Considerations

- JWT tokens expire in 30 minutes
- Passwords hashed with bcrypt (cost factor 12)
- CORS restricted to known origins
- Input validation via Pydantic on all endpoints
- Rate limiting on auth endpoints
- MongoDB Atlas IP whitelist
- Secrets in environment variables, never in code

---

## Monitoring & Observability

- Health endpoint: `GET /health`
- Structured logging with `structlog`
- Prometheus metrics on `/metrics`
- Request tracing with correlation IDs
- Error tracking via Sentry (optional)