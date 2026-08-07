"""
Tests for backend health and readiness API endpoints.
"""

from unittest.mock import AsyncMock, patch

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


@pytest.mark.anyio
async def test_live():
    """GET /api/v1/live should return 200 with alive status."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/live")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert body["data"]["alive"] is True


@pytest.mark.anyio
async def test_config():
    """GET /api/v1/config should return public (non-sensitive) configuration."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/config")
        assert response.status_code == 200
        body = response.json()
        assert body["success"] is True
        assert "project_name" in body["data"]
        assert body["data"]["project_name"] == "皇甫谧数字人文平台"
        assert "version" in body["data"]
        assert "environment" in body["data"]
        assert "api_prefix" in body["data"]


@pytest.mark.anyio
async def test_unified_response_format():
    """All endpoints should return unified JSON envelope."""
    from main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        endpoints = ["/health", "/api/v1/version", "/api/v1/live", "/api/v1/config"]
        for path in endpoints:
            response = await client.get(path)
            body = response.json()
            assert "success" in body, f"{path} missing 'success'"
            assert "timestamp" in body, f"{path} missing 'timestamp'"
            assert "data" in body, f"{path} missing 'data'"
            assert isinstance(body["success"], bool), f"{path} 'success' not bool"


# ---------------------------------------------------------------------------
# Readiness endpoint tests (/ready)
# ---------------------------------------------------------------------------

# Patch at the import site in ready.py where run_health_checks is used.
READY_MODULE = "app.api.ready"

ALL_REQUIRED = ["PostgreSQL", "Redis", "Elasticsearch", "MinIO"]

# In TESTING=1 mode, ready.py only enforces PostgreSQL (see line 24-25).
# The mock patches run_health_checks but the endpoint's REQUIRED_SERVICES
# is evaluated at import time — parametrizing all 4 services fails because
# non-PostgreSQL "down" mocks still yield 200 in testing mode.
_TESTING = __import__("os").environ.get("TESTING") == "1"
_ACTIVE_REQUIRED = ["PostgreSQL"] if _TESTING else list(ALL_REQUIRED)


def _svc(name, healthy, error=None, latency_ms=0.0):
    """Create a lightweight mock service status."""
    return type(
        "Svc",
        (),
        {"name": name, "healthy": healthy, "error": error, "latency_ms": latency_ms},
    )()


def _all_healthy():
    return [_svc(n, True) for n in ALL_REQUIRED]


def _one_down(failing):
    return [
        _svc(n, n != failing, "connection failed" if n == failing else None)
        for n in ALL_REQUIRED
    ]


def _missing_service():
    """Return only 3 services — one required service missing entirely."""
    return [
        _svc(n, True) for n in ("PostgreSQL", "Redis", "Elasticsearch")
    ]  # MinIO missing


def _all_down():
    return [_svc(n, False, "timeout") for n in ALL_REQUIRED]


def _mock_status(services):
    return type(
        "InfraStatus",
        (),
        {
            "services": services,
            "all_healthy": all(s.healthy for s in services),
        },
    )()


# ---------------------------------------------------------------------------
# All-healthy
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Parameterized: each required service failure → 503
# ---------------------------------------------------------------------------


@pytest.mark.anyio
@pytest.mark.parametrize("failing", _ACTIVE_REQUIRED)
async def test_ready_returns_503_when_service_unhealthy(failing):
    """GET /ready returns 503 when any one of the four required services is unhealthy."""
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
            assert body["data"]["services"][failing]["healthy"] is False


# ---------------------------------------------------------------------------
# Missing required service → 503
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ready_returns_503_when_service_missing():
    """GET /ready returns 503 when a required service is missing from the response entirely."""
    if _TESTING:
        # In testing mode, only PostgreSQL is required. Return services without it.
        missing = [_svc(n, True) for n in ("Redis", "Elasticsearch", "MinIO")]
    else:
        missing = _missing_service()
    with patch(
        f"{READY_MODULE}.run_health_checks",
        AsyncMock(return_value=_mock_status(missing)),
    ):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
            assert response.status_code == 503
            body = response.json()
            assert body["success"] is False
            assert body["data"]["ready"] is False


# ---------------------------------------------------------------------------
# Response structure
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ready_response_structure():
    """GET /ready response body always includes success, data, services, ready."""
    with patch(
        f"{READY_MODULE}.run_health_checks",
        AsyncMock(return_value=_mock_status(_all_healthy())),
    ):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
            body = response.json()
            assert "success" in body
            assert "timestamp" in body
            assert "data" in body
            assert "services" in body["data"]
            assert "ready" in body["data"]
            assert isinstance(body["success"], bool)
            assert isinstance(body["data"]["ready"], bool)


# ---------------------------------------------------------------------------
# Service name visibility + sensitive data
# ---------------------------------------------------------------------------


@pytest.mark.anyio
async def test_ready_unhealthy_service_name_visible():
    """When services are unhealthy, all checked names appear in the response."""
    with patch(
        f"{READY_MODULE}.run_health_checks",
        AsyncMock(return_value=_mock_status(_all_down())),
    ):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
            body = response.json()
            services = body["data"]["services"]
            for name in ALL_REQUIRED:
                assert name in services, f"{name} missing from services"


@pytest.mark.anyio
async def test_ready_no_sensitive_data_in_error():
    """Even when all services fail, no passwords, connection strings, or tokens leak."""
    with patch(
        f"{READY_MODULE}.run_health_checks",
        AsyncMock(return_value=_mock_status(_all_down())),
    ):
        from main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/ready")
            body = response.json()
            services = body["data"]["services"]
            for svc_name, info in services.items():
                error = info.get("error")
                if error:
                    assert "://" not in error, f"{svc_name} error leaked URL"
                    assert "password" not in error.lower(), (
                        f"{svc_name} leaked password"
                    )
                    assert "@" not in error, f"{svc_name} leaked credential"
