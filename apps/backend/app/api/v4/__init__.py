"""API V4 — Digital Humanities Research Platform product layer."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v4.education import router as education_router
from app.api.v4.research import router as research_router
from app.api.v4.visualization import router as visualization_router

v4_router = APIRouter(prefix="/api/v4")
v4_router.include_router(research_router)
v4_router.include_router(visualization_router)
v4_router.include_router(education_router)
