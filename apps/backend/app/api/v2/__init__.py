"""API v2 — Academic product layer (Sprint 2)."""

from app.api.v2.academic import router as academic_router
from app.api.v2.graph import router as graph_router  # Phase 2a
from app.api.v2.tei import router as tei_router  # Phase 2b

from fastapi import APIRouter

router = APIRouter()
router.include_router(academic_router)
router.include_router(graph_router)  # Phase 2a
router.include_router(tei_router)  # Phase 2b

__all__ = ["router"]
