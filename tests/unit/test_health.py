"""
Tests for backend health API endpoints.
"""
import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.anyio
async def test_health():
    """GET /health should return 200 with healthy status."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "healthy"
        assert body["message"] == "Service is running"
        assert "timestamp" in body


@pytest.mark.anyio
async def test_version():
    """GET /version should return version info."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/version")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "version" in body["data"]
        assert "environment" in body["data"]
        assert body["data"]["project"] == "皇甫谧数字人文平台"


@pytest.mark.anyio
async def test_live():
    """GET /live should return 200 with alive status."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/live")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["alive"] is True


@pytest.mark.anyio
async def test_config():
    """GET /config should return public config."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/config")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "project_name" in body["data"]
        assert "services" in body["data"]
        assert "postgres" in body["data"]["services"]
        assert "redis" in body["data"]["services"]
        assert "minio" in body["data"]["services"]


@pytest.mark.anyio
async def test_unified_response_format():
    """All endpoints should return unified JSON envelope."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        endpoints = ["/health", "/version", "/live", "/config"]
        for path in endpoints:
            response = await client.get(path)
            body = response.json()
            assert "success" in body, f"{path} missing 'success'"
            assert "timestamp" in body, f"{path} missing 'timestamp'"
            assert "data" in body, f"{path} missing 'data'"
            assert isinstance(body["success"], bool), f"{path} 'success' not bool"
