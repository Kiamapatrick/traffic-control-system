from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from datetime import datetime, timedelta, timezone
from typing import Annotated
import motor.motor_asyncio
from beanie import init_beanie

from traffic_control.models import (
    Network, FlowSolution, SolveRequest, SolveResponse,
    NetworkCreate, NetworkResponse, Token, TokenData, User,
    PredictionRequest, PredictionResponse, MLModelInfo,
    SolverMethod, OptimizationObjective
)
from traffic_control.solvers import (
    solve_rref, solve_lp, solve_milp, solve_max_flow,
    validate_solution
)
from traffic_control.utils.config import settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


class UserInDB(User):
    hashed_password: str


class Settings(BaseModel):
    mongodb_uri: str
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30


async def get_database():
    client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongodb_uri)
    return client.traffic_control


async def init_db():
    db = await get_database()
    await init_beanie(database=db, document_models=[UserInDB])


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception

    db = await get_database()
    user = await db.users.find_one({"username": token_data.username})
    if user is None:
        raise credentials_exception
    return User(**user)


async def get_current_active_user(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(
    title="Traffic Control API",
    description="Traffic flow optimization API with multiple solvers",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/v1/auth/register", response_model=User)
async def register(user_data: UserInDB):
    db = await get_database()
    existing = await db.users.find_one({"username": user_data.username})
    if existing:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed = get_password_hash(user_data.hashed_password)
    user_doc = user_data.model_dump()
    user_doc["hashed_password"] = hashed
    await db.users.insert_one(user_doc)
    return User(**user_data.model_dump(exclude={"hashed_password"}))


@app.post("/api/v1/auth/login", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]):
    db = await get_database()
    user = await db.users.find_one({"username": form_data.username})
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token(data={"sub": user["username"]})
    return Token(access_token=access_token, expires_in=settings.jwt_expire_minutes * 60)


@app.post("/api/v1/solve", response_model=SolveResponse)
async def solve_network(
    request: SolveRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    import time

    start = time.perf_counter()

    try:
        if request.method == SolverMethod.RREF:
            solution = solve_rref(request.network)
        elif request.method == SolverMethod.LINEAR_PROGRAMMING:
            solution = solve_lp(request.network, request.objective)
        elif request.method == SolverMethod.MILP:
            solution = solve_milp(request.network)
        elif request.method == SolverMethod.MAX_FLOW:
            source = request.parameters.get("source")
            sink = request.parameters.get("sink")
            algorithm = request.parameters.get("algorithm", "dinic")
            if not source or not sink:
                raise ValueError("MAX_FLOW requires 'source' and 'sink' parameters")
            solution = solve_max_flow(request.network, source, sink, algorithm)
        elif request.method == SolverMethod.DINIC:
            source = request.parameters.get("source")
            sink = request.parameters.get("sink")
            if not source or not sink:
                raise ValueError("DINIC requires 'source' and 'sink' parameters")
            solution = solve_max_flow(request.network, source, sink, "dinic")
        else:
            raise ValueError(f"Unknown method: {request.method}")

        solve_time = (time.perf_counter() - start) * 1000

        is_valid, violations = validate_solution(request.network, solution)
        if not is_valid:
            solution.is_feasible = False
            solution.violations.extend(violations)

        return SolveResponse(solution=solution, solve_time_ms=solve_time)

    except Exception as e:
        solve_time = (time.perf_counter() - start) * 1000
        return SolveResponse(
            solution=FlowSolution(
                flows={},
                method=request.method,
                is_feasible=False,
                violations=[str(e)],
            ),
            solve_time_ms=solve_time,
        )


@app.post("/api/v1/networks", response_model=NetworkResponse)
async def create_network(
    network_data: NetworkCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    db = await get_database()
    network_doc = network_data.model_dump()
    network_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    network_doc["updated_at"] = network_doc["created_at"]
    result = await db.networks.insert_one(network_doc)
    network_doc["id"] = str(result.inserted_id)
    return NetworkResponse(**network_doc)


@app.get("/api/v1/networks/{network_id}", response_model=NetworkResponse)
async def get_network(
    network_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    db = await get_database()
    from bson import ObjectId
    network = await db.networks.find_one({"_id": ObjectId(network_id)})
    if not network:
        raise HTTPException(status_code=404, detail="Network not found")
    network["id"] = str(network["_id"])
    return NetworkResponse(**network)


@app.get("/api/v1/networks", response_model=list[NetworkResponse])
async def list_networks(
    current_user: Annotated[User, Depends(get_current_active_user)],
    limit: int = 100,
    offset: int = 0,
):
    db = await get_database()
    cursor = db.networks.find().skip(offset).limit(limit)
    networks = []
    async for doc in cursor:
        doc["id"] = str(doc["_id"])
        networks.append(NetworkResponse(**doc))
    return networks


@app.delete("/api/v1/networks/{network_id}")
async def delete_network(
    network_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    db = await get_database()
    from bson import ObjectId
    result = await db.networks.delete_one({"_id": ObjectId(network_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Network not found")
    return {"message": "Network deleted"}


@app.post("/api/v1/predict", response_model=PredictionResponse)
async def predict_flow(
    request: PredictionRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    import joblib
    from pathlib import Path

    model_path = Path("models") / f"{request.model_id}.joblib"
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model {request.model_id} not found")

    model_data = joblib.load(model_path)
    model = model_data["model"]
    features = model_data["features"]

    X = [[request.features.get(f, 0) for f in features]]
    predictions = model.predict(X)

    return PredictionResponse(
        predictions={f"flow_{i}": float(p) for i, p in enumerate(predictions[0])},
        model_id=request.model_id,
        model_version=model_data.get("version", "1.0"),
    )


@app.get("/api/v1/models", response_model=list[MLModelInfo])
async def list_models(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    from pathlib import Path
    import joblib

    models = []
    for model_file in Path("models").glob("*.joblib"):
        try:
            data = joblib.load(model_file)
            models.append(MLModelInfo(
                model_id=model_file.stem,
                model_type=data.get("model_type", "unknown"),
                features=data.get("features", []),
                target=data.get("target", "flow"),
                metrics=data.get("metrics", {}),
                created_at=data.get("created_at", ""),
                version=data.get("version", "1.0"),
            ))
        except Exception:
            continue
    return models


@app.websocket("/api/v1/simulate/{network_id}")
async def websocket_simulate(websocket, network_id: str):
    await websocket.accept()
    try:
        from traffic_control.network.generator import generate_four_junction_example
        from traffic_control.solvers import solve_rref

        network = generate_four_junction_example()

        for t in range(0, 51, 5):
            network.roads[4].flow = t
            solution = solve_rref(network)
            await websocket.send_json({
                "t": t,
                "flows": solution.flows,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            import asyncio
            await asyncio.sleep(1)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
    finally:
        await websocket.close()


@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)