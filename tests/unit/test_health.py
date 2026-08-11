"""
Tests for backend health and readiness API endpoints — updated for Stage 4 health check closure.
"""

from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.middleware.auth import get_current_admin_user

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
async def test_api_v1_health():
    """GET /api/v1/health should return 200 with healthy status."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["status"] == "healthy"


@pytest.mark.anyio
async def test_version():
    """GET /api/v1/version should return version info."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/version")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "version" in body["data"]
        assert "environment" in body["data"]
        assert body["data"]["project"] == "皇甫谧数字人文平台"


# ---------------------------------------------------------------------------
# Readiness endpoint tests (/ready and /api/v1/ready)
# ---------------------------------------------------------------------------

READY_MODULE = "app.api.ready"
ALL_REQUIRED = ["PostgreSQL", "Redis", "Elasticsearch", "MinIO"]
_TESTING = __import__("os").environ.get("TESTING") == "1"
_ACTIVE_REQUIRED = ["PostgreSQL"] if _TESTING else list(ALL_REQUIRED)


def _svc(name, healthy, error=None, latency_ms=0.0):
    return type(
        "Svc",
        (),
        {"name": name, "healthy": healthy, "error": error, "latency_ms": latency_ms},
    )()


def _all_healthy():
    return [_svc(n, True, latency_ms=1.5) for n in ALL_REQUIRED]


def _one_down(failing):
    return [
        _svc(n, n != failing, "connection failed" if n == failing else None)
        for n in ALL_REQUIRED
    ]


def _mock_status(services):
    return type(
        "InfraStatus",
        (),
        {
            "services": services,
            "all_healthy": all(s.healthy for s in services),
        },
    )()


@pytest.mark.anyio
async def test_ready_all_healthy_returns_200():
    """GET /ready returns 200 + success=true + ready=true when all required services healthy."""
    with patch(
        f"{READY_MODULE}.run_health_checks",
        AsyncMock(return_value=_mock_status(_all_healthy())),
    ):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
            assert response.status_code == 200
            body = response.json()
            assert body["success"] is True
            assert body["data"]["ready"] is True
            assert body["data"]["status"] == "healthy"
            # Omit internal infrastructure details from anonymous readiness probe
            assert "services" not in body["data"] or body["data"].get("services") is None


@pytest.mark.anyio
@pytest.mark.parametrize("failing", _ACTIVE_REQUIRED)
async def test_ready_returns_503_when_service_unhealthy(failing):
    """GET /ready returns 503 when any required service is unhealthy."""
    with patch(
        f"{READY_MODULE}.run_health_checks",
        AsyncMock(return_value=_mock_status(_one_down(failing))),
    ):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
            assert response.status_code == 503
            body = response.json()
            assert body["success"] is False
            assert body["data"]["ready"] is False
            assert body["data"]["status"] == "unhealthy"


@pytest.mark.anyio
async def test_admin_health_details_requires_auth():
    """GET /api/v1/admin/health-details without auth returns 401."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/admin/health-details")
        assert response.status_code in (401, 403)


@pytest.mark.anyio
async def test_admin_health_details_returns_full_diagnostics():
    """GET /api/v1/admin/health-details with admin auth returns full diagnostic details."""
    with patch(
        f"{READY_MODULE}.run_health_checks",
        AsyncMock(return_value=_mock_status(_all_healthy())),
    ):
        from main import app

        # Override admin auth dependency for test
        app.dependency_overrides[get_current_admin_user] = lambda: "test-admin-user"

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/admin/health-details")
                assert response.status_code == 200
                body = response.json()
                assert body["success"] is True
                assert body["data"]["ready"] is True
                assert "services" in body["data"]
                services = body["data"]["services"]
                assert "PostgreSQL" in services
                assert services["PostgreSQL"]["healthy"] is True
        finally:
            app.dependency_overrides.pop(get_current_admin_user, None)
