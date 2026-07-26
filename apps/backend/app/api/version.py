"""
Version and system info endpoint.
"""
from fastapi import APIRouter

from app.core.config import settings
from app.utils.response import api_response

router = APIRouter()


@router.get("/version")
async def get_version() -> dict:
    """Return application version and environment info."""
    return api_response(
        data={
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "project": settings.PROJECT_NAME,
        }
    )


@router.get("/live")
async def liveness_check() -> dict:
    """Liveness probe — minimal check that the process is alive."""
    return api_response(data={"alive": True}, message="Process is alive")


@router.get("/config")
async def public_config() -> dict:
    """Return public (non-sensitive) configuration."""
    return api_response(
        data={
            "project_name": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "api_prefix": settings.API_V1_PREFIX,
        }
    )
