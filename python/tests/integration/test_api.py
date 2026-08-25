from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from traffic_control.api.main import app
from traffic_control.models import Network, Junction, Road, SolverMethod


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_network():
    return Network(
        junctions=[
            Junction(id="A", position=(0, 0), external_flow=80),
            Junction(id="B", position=(100, 0), external_flow=-30),
            Junction(id="C", position=(100, 100), external_flow=50),
            Junction(id="D", position=(0, 100), external_flow=-100),
        ],
        roads=[
            Road(id="x1", source="A", target="B", capacity=100),
            Road(id="x2", source="B", target="C", capacity=100),
            Road(id="x3", source="C", target="D", capacity=100),
            Road(id="x4", source="D", target="A", capacity=100),
            Road(id="x5", source="B", target="D", capacity=100),
        ]
    )


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestSolveEndpoint:
    @pytest.mark.asyncio
    async def test_solve_rref(self, authenticated_client, sample_network):
        request = {
            "network": sample_network.model_dump(),
            "method": "rref"
        }
        response = await authenticated_client.post("/api/v1/solve", json=request)
        assert response.status_code == 200
        data = response.json()
        assert "solution" in data
        assert data["solution"]["method"] == "rref"
        assert len(data["solution"]["flows"]) == 5

    @pytest.mark.asyncio
    async def test_solve_lp(self, authenticated_client, sample_network):
        request = {
            "network": sample_network.model_dump(),
            "method": "lp",
            "objective": "min_cost"
        }
        response = await authenticated_client.post("/api/v1/solve", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["solution"]["method"] == "lp"
        assert data["solution"]["objective"] == "min_cost"

    @pytest.mark.asyncio
    async def test_solve_max_flow(self, authenticated_client, sample_network):
        request = {
            "network": sample_network.model_dump(),
            "method": "max_flow",
            "parameters": {"source": "A", "sink": "C"}
        }
        response = await authenticated_client.post("/api/v1/solve", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["solution"]["method"] == "max_flow"
        assert data["solution"]["objective_value"] is not None

    @pytest.mark.asyncio
    async def test_solve_invalid_method(self, authenticated_client, sample_network):
        request = {
            "network": sample_network.model_dump(),
            "method": "invalid_method"
        }
        response = await authenticated_client.post("/api/v1/solve", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["solution"]["is_feasible"] is False

    @pytest.mark.asyncio
    async def test_solve_missing_params_max_flow(self, authenticated_client, sample_network):
        request = {
            "network": sample_network.model_dump(),
            "method": "max_flow",
            "parameters": {}
        }
        response = await authenticated_client.post("/api/v1/solve", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["solution"]["is_feasible"] is False


class TestNetworkCRUD:
    @pytest.mark.asyncio
    async def test_create_network(self, authenticated_client, sample_network):
        request = {
            "name": "Test Network",
            "network": sample_network.model_dump(),
            "description": "A test network"
        }
        response = await authenticated_client.post("/api/v1/networks", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Network"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_list_networks(self, authenticated_client):
        response = await authenticated_client.get("/api/v1/networks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_network(self, authenticated_client, sample_network):
        create_request = {
            "name": "Test Network",
            "network": sample_network.model_dump(),
        }
        create_response = await authenticated_client.post("/api/v1/networks", json=create_request)
        network_id = create_response.json()["id"]

        response = await authenticated_client.get(f"/api/v1/networks/{network_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == network_id
        assert data["name"] == "Test Network"

    @pytest.mark.asyncio
    async def test_delete_network(self, authenticated_client, sample_network):
        create_request = {
            "name": "Test Network",
            "network": sample_network.model_dump(),
        }
        create_response = await authenticated_client.post("/api/v1/networks", json=create_request)
        network_id = create_response.json()["id"]

        response = await authenticated_client.delete(f"/api/v1/networks/{network_id}")
        assert response.status_code == 200

        get_response = await authenticated_client.get(f"/api/v1/networks/{network_id}")
        assert get_response.status_code == 404