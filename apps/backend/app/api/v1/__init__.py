"""
API v1 router — all versioned API routes.

Phase 2: Auth + User/Role management.
Phase 3: Entity CRUD (books, versions, chapters, passages, papers, images, persons, documents).
Phase 4: Version Center (lineage, comparison, diff, passage mapping).
Phase 6: Knowledge Graph (entity relations, neighborhood, path finding).
Phase 7: Unified Search (full-text ILIKE, autocomplete, reindex).
Phase 8: AI Research Workspace (chat, summarize, translate, compare; sessions & notes).
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.academic_rag import router as academic_rag_router
from app.api.v1.ai import ai_router, workspace_router
from app.api.v1.auth import router as auth_router
from app.api.v1.dashboard import router as dashboard_router
from app.api.v1.day2_search import router as day2_search_router
from app.api.v1.entities import router as entities_router
from app.api.v1.evidences import router as evidences_router
from app.api.v1.graph import router as graph_router
from app.api.v1.passages import router as passages_router
from app.api.v1.relations import router as relations_router
from app.api.v1.research import router as research_router
from app.api.v1.search import router as search_router
from app.api.v1.users import router as users_router
from app.api.v1.version_center import router as version_center_router

router = APIRouter(prefix="/api/v1")

router.include_router(auth_router)
router.include_router(entities_router)
router.include_router(day2_search_router)
router.include_router(users_router)
router.include_router(version_center_router)
router.include_router(graph_router)
router.include_router(research_router)
router.include_router(search_router)
router.include_router(academic_rag_router)
router.include_router(ai_router)
router.include_router(workspace_router)
router.include_router(dashboard_router)
router.include_router(evidences_router)
router.include_router(passages_router)
router.include_router(relations_router)
