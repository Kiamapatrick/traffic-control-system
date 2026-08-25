from __future__ import annotations

from enum import Enum
from typing import Annotated, Any, Literal
from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.types import NonNegativeFloat, PositiveFloat, PositiveInt


class SolverMethod(str, Enum):
    RREF = "rref"
    LINEAR_PROGRAMMING = "lp"
    MILP = "milp"
    MAX_FLOW = "max_flow"
    DINIC = "dinic"


class OptimizationObjective(str, Enum):
    MIN_COST = "min_cost"
    MAX_THROUGHPUT = "max_throughput"
    MIN_TRAVEL_TIME = "min_travel_time"
    BALANCE_LOAD = "balance_load"


class JunctionType(str, Enum):
    NORMAL = "normal"
    SOURCE = "source"
    SINK = "sink"


class Junction(BaseModel):
    id: Annotated[str, Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")]
    position: Annotated[tuple[float, float], Field(description="(x, y) coordinates")]
    junction_type: JunctionType = JunctionType.NORMAL
    external_flow: float = Field(default=0.0, description="Positive for source, negative for sink")

    @field_validator("position")
    @classmethod
    def validate_position(cls, v: tuple[float, float]) -> tuple[float, float]:
        if len(v) != 2:
            raise ValueError("Position must be a tuple of (x, y)")
        return v


class Road(BaseModel):
    id: Annotated[str, Field(min_length=1, pattern=r"^[a-zA-Z0-9_-]+$")]
    source: Annotated[str, Field(min_length=1)]
    target: Annotated[str, Field(min_length=1)]
    capacity: PositiveFloat = Field(default=1000.0, description="Max vehicles per hour")
    length: PositiveFloat = Field(default=1.0, description="Length in km")
    flow: float = Field(default=0.0, description="Current flow (vehicles/hour)")
    cost_per_unit: NonNegativeFloat = Field(default=1.0, description="Cost per vehicle")
    free_flow_speed: PositiveFloat = Field(default=50.0, description="km/h")
    lanes: PositiveInt = Field(default=1)

    @field_validator("source", "target")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Junction ID cannot be empty")
        return v

    @model_validator(mode="after")
    def validate_source_target(self) -> Road:
        if self.source == self.target:
            raise ValueError("source and target cannot be the same")
        return self


class Network(BaseModel):
    junctions: list[Junction] = Field(min_length=1)
    roads: list[Road] = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_network(self) -> Network:
        junction_ids = {j.id for j in self.junctions}
        for road in self.roads:
            if road.source not in junction_ids:
                raise ValueError(f"Road {road.id}: source junction '{road.source}' not found")
            if road.target not in junction_ids:
                raise ValueError(f"Road {road.id}: target junction '{road.target}' not found")
            if road.source == road.target:
                raise ValueError(f"Road {road.id}: source and target cannot be the same")
        return self

    def get_adjacency_matrix(self) -> tuple[list[list[int]], list[str]]:
        junction_ids = [j.id for j in self.junctions]
        n = len(junction_ids)
        id_to_idx = {jid: i for i, jid in enumerate(junction_ids)}
        matrix = [[0] * n for _ in range(n)]
        for road in self.roads:
            matrix[id_to_idx[road.source]][id_to_idx[road.target]] = 1
        return matrix, junction_ids

    def get_incidence_matrix(self) -> tuple[list[list[float]], list[str], list[str]]:
        junction_ids = [j.id for j in self.junctions]
        road_ids = [r.id for r in self.roads]
        n_junc = len(junction_ids)
        n_road = len(road_ids)
        junc_to_idx = {jid: i for i, jid in enumerate(junction_ids)}
        road_to_idx = {rid: i for i, rid in enumerate(road_ids)}
        matrix = [[0.0] * n_road for _ in range(n_junc)]
        for road in self.roads:
            j = junc_to_idx[road.source]
            i = junc_to_idx[road.target]
            r = road_to_idx[road.id]
            matrix[j][r] = 1.0
            matrix[i][r] = -1.0
        return matrix, junction_ids, road_ids


class FlowSolution(BaseModel):
    flows: dict[str, float] = Field(description="Road ID -> flow value")
    method: SolverMethod
    objective: OptimizationObjective | None = None
    objective_value: float | None = None
    is_feasible: bool = True
    violations: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def total_flow(self) -> float:
        return sum(self.flows.values())


class SolveRequest(BaseModel):
    network: Network
    method: SolverMethod = SolverMethod.RREF
    objective: OptimizationObjective | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class SolveResponse(BaseModel):
    solution: FlowSolution
    solve_time_ms: float
    iterations: int | None = None


class NetworkCreate(BaseModel):
    name: Annotated[str, Field(min_length=1, max_length=100)]
    network: Network
    description: str | None = None
    tags: list[str] = Field(default_factory=list)


class NetworkResponse(BaseModel):
    id: str
    name: str
    network: Network
    description: str | None
    tags: list[str]
    created_at: str
    updated_at: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    username: str | None = None
    scopes: list[str] = Field(default_factory=list)


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool = False
    scopes: list[str] = Field(default_factory=list)


class MLModelInfo(BaseModel):
    model_id: str
    model_type: str
    features: list[str]
    target: str
    metrics: dict[str, float]
    created_at: str
    version: str


class PredictionRequest(BaseModel):
    model_id: str
    features: dict[str, float]


class PredictionResponse(BaseModel):
    predictions: dict[str, float]
    model_id: str
    model_version: str