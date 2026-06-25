"""
Dashboard API — system overview, stats, and admin endpoints.

Per MVP Chapter 8 — Dashboard and Admin Panel.

Endpoints:
  GET /api/v1/dashboard/overview  — Dashboard overview (entity counts, recent activity, system info)
  GET /api/v1/dashboard/stats     — Detailed stats with distributions
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.services.dashboard_service import DashboardService
from app.utils.response import api_response

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

guard_read = require_permission("dashboard", "read")


@router.get("/overview", response_model=dict, dependencies=[Depends(guard_read)])
async def dashboard_overview(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Return dashboard overview: entity counts, recent activity, system info."""
    svc = DashboardService(session)
    result = await svc.get_overview()
    return api_response(data=result)


@router.get("/stats", response_model=dict, dependencies=[Depends(guard_read)])
async def dashboard_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Return detailed statistics with dynasty/category distributions."""
    svc = DashboardService(session)
    result = await svc.get_stats()
    return api_response(data=result)
