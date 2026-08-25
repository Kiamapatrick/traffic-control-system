from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from traffic_control.models import Network, Junction, Road
from traffic_control.network.generator import generate_four_junction_example
from traffic_control.api.main import app


@pytest.fixture
def four_junction_network() -> Network:
    return generate_four_junction_example()


@pytest.fixture
def simple_network() -> Network:
    junctions = [
        Junction(id="A", position=(0, 0), external_flow=100),
        Junction(id="B", position=(100, 0), external_flow=-50),
        Junction(id="C", position=(200, 0), external_flow=-50),
    ]
    roads = [
        Road(id="r1", source="A", target="B", capacity=100),
        Road(id="r2", source="A", target="C", capacity=100),
        Road(id="r3", source="B", target="C", capacity=50),
    ]
    return Network(junctions=junctions, roads=roads)


@pytest.fixture
def grid_network() -> Network:
    from traffic_control.network.generator import generate_grid_network
    return generate_grid_network(3, 3, seed=42)


@pytest_asyncio.fixture
async def authenticated_client():
    """Create an authenticated test client with a valid JWT token."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Register a test user
        await ac.post("/api/v1/auth/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword"
        })
        # Login to get token
        response = await ac.post("/api/v1/auth/login", data={
            "username": "testuser",
            "password": "testpassword"
        })
        token = response.json()["access_token"]
        ac.headers["Authorization"] = f"Bearer {token}"
        yield ac