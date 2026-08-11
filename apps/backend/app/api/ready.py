"""
Readiness and Admin Infrastructure Health endpoints.

- Anonymous /ready & /api/v1/ready: returns summary readiness status without leaking infra details (connection strings, logs, latency).
- Admin /api/v1/admin/health-details: requires admin auth, returns full infrastructure diagnostic details.
"""

import os
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response

from app.middleware.auth import get_current_admin_user
from app.startup.check_infrastructure import run_health_checks
from app.utils.response import api_response

router = APIRouter()

# Required services whose health determines platform readiness.
if os.environ.get("TESTING") == "1":
    REQUIRED_SERVICES: set[str] = {"PostgreSQL"}
else:
    REQUIRED_SERVICES = {"PostgreSQL", "Redis", "Elasticsearch", "MinIO"}


@router.get("/ready")
@router.get("/api/v1/ready")
async def readiness_check(response: Response) -> dict[str, Any]:
    """Readiness probe — checks platform readiness without leaking infrastructure details.

    HTTP 200: all required services healthy.
    HTTP 503: any required service unhealthy.
    Returns ONLY summary {"status": "healthy", "ready": true} to anonymous callers.
    """
    status = await run_health_checks()
    services_map = {svc.name: svc for svc in status.services}

    required_healthy = all(
        getattr(services_map.get(name), "healthy", False) for name in REQUIRED_SERVICES
    )

    response.status_code = 200 if required_healthy else 503

    return api_response(
        data={
            "status": "healthy" if required_healthy else "unhealthy",
            "ready": required_healthy,
        },
        success=required_healthy,
        message="All services healthy"
        if required_healthy
        else "Some services are unhealthy",
    )


@router.get("/api/v1/admin/health-details")
@router.get("/admin/health-details")
async def get_admin_health_details(
    response: Response,
    admin_user_id: Annotated[str, Depends(get_current_admin_user)],
) -> dict[str, Any]:
    """Admin infrastructure health diagnostic details.

    Requires admin authentication.
    Returns full connectivity status, latencies, and error logs for DB, Redis, ES, MinIO, etc.
    """
    status = await run_health_checks()
    services: dict[str, dict[str, Any]] = {}
    for svc in status.services:
        services[svc.name] = {
            "name": svc.name,
            "healthy": svc.healthy,
            "latency_ms": svc.latency_ms if svc.healthy else None,
            "error": svc.error if not svc.healthy else None,
        }

    required_healthy = all(
        services.get(name, {}).get("healthy", False) for name in REQUIRED_SERVICES
    )

    response.status_code = 200 if required_healthy else 503

    return api_response(
        data={
            "status": "healthy" if required_healthy else "unhealthy",
            "ready": required_healthy,
            "services": services,
            "timestamp": datetime.now(UTC).isoformat(),
        },
        success=required_healthy,
        message="Full infrastructure diagnostics retrieved successfully",
    )
