"""
Readiness endpoint — checks all infrastructure dependencies.
"""
from fastapi import APIRouter

from app.startup.check_infrastructure import run_health_checks
from app.utils.response import api_response

router = APIRouter()


@router.get("/ready")
async def readiness_check() -> dict:
    """Readiness probe — checks database, Redis, ES, MinIO connectivity."""
    status = await run_health_checks()
    services = {}
    for svc in status.services:
        services[svc.name] = {
            "healthy": svc.healthy,
            "latency_ms": svc.latency_ms if svc.healthy else None,
            "error": svc.error,
        }

    return api_response(
        data={
            "ready": status.all_healthy,
            "services": services,
        },
        success=status.all_healthy,
        message="All services healthy" if status.all_healthy else "Some services are unhealthy",
    )
