from fastapi import APIRouter

from app.api.v2.academic import router as academic_router
from app.api.v2.graph import router as graph_router  # Phase 2a
from app.api.v2.paper import router as paper_router  # Phase 2c
from app.api.v2.tei import router as tei_router  # Phase 2b

router = APIRouter()
router.include_router(academic_router)
router.include_router(graph_router)  # Phase 2a
router.include_router(tei_router)  # Phase 2b
router.include_router(paper_router)  # Phase 2c

__all__ = ["router"]
