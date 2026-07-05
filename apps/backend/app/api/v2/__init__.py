"""API v2 — Academic product layer (Sprint 2)."""

from app.api.v2.academic import router as academic_router
from app.api.v2.graph import router as graph_router  # Phase 2a

from fastapi import APIRouter

router = APIRouter()
router.include_router(academic_router)
router.include_router(graph_router)  # Phase 2a

__all__ = ["router"]
