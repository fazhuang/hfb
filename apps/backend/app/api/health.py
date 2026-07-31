"""Health check endpoint."""

from typing import Any

from fastapi import APIRouter

from app.utils.response import api_response

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, Any]:
    """Basic health check — returns ok if the service is running."""
    return api_response(data={"status": "healthy"}, message="Service is running")
