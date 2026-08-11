"""Health check endpoint."""

from typing import Any

from fastapi import APIRouter

from app.utils.response import api_response

router = APIRouter()


@router.get("/health")
@router.get("/api/v1/health")
async def health_check() -> dict[str, Any]:
    """Basic health check — returns summary status without infrastructure details."""
    return api_response(data={"status": "healthy"}, message="Service is running")

