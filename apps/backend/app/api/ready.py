"""
Readiness endpoint — checks all infrastructure dependencies.

Returns HTTP 200 when all required services are healthy.
Returns HTTP 503 when any required service is unhealthy.
"""
from fastapi import APIRouter, Response

from app.startup.check_infrastructure import run_health_checks
from app.utils.response import api_response

router = APIRouter()

# Required services whose health determines platform readiness.
# Non-required services (e.g. Post-MVP) are checked but don't block readiness.
REQUIRED_SERVICES = {"PostgreSQL", "Redis", "Elasticsearch", "MinIO"}


@router.get("/ready")
async def readiness_check(response: Response) -> dict:
    """Readiness probe — checks database, Redis, ES, MinIO connectivity.

    HTTP 200: all required services healthy.
    HTTP 503: any required service unhealthy or missing.
    """
    status = await run_health_checks()
    services = {}
    for svc in status.services:
        # Sanitize error messages: never leak connection strings, passwords, or paths
        safe_error = None
        if not svc.healthy and svc.error:
            safe_error = "connection failed"
        services[svc.name] = {
            "healthy": svc.healthy,
            "latency_ms": svc.latency_ms if svc.healthy else None,
            "error": safe_error,
        }

    required_healthy = all(
        services.get(name, {}).get("healthy", False)
        for name in REQUIRED_SERVICES
    )

    response.status_code = 200 if required_healthy else 503

    return api_response(
        data={
            "ready": required_healthy,
            "services": services,
        },
        success=required_healthy,
        message="All services healthy" if required_healthy else "Some services are unhealthy",
    )
