"""
Search API — unified search, autocomplete, and reindex endpoints.

Per HFB-PS-1706 Unified Search Product Specification.

Endpoints:
  GET  /api/v1/search          — Unified search across entity types
  GET  /api/v1/search/suggest  — Autocomplete suggestions
  POST /api/v1/search/reindex  — Trigger reindex (admin)
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.search import SearchParams
from app.services.search_service import SearchService
from app.utils.response import api_response

router = APIRouter(prefix="/search", tags=["Search"])

guard_read = require_permission("search", "read")
guard_admin = require_permission("search", "reindex")


# ============================================================
# Unified Search
# ============================================================


@router.get(
    "",
    response_model=dict,
    dependencies=[Depends(guard_read)],
)
async def unified_search(
    session: Annotated[AsyncSession, Depends(get_session)],
    q: str = Query(default="", description="Search query"),
    types: str = Query(default="book,version,passage,person,paper", description="Entity types"),
    dynasty: str | None = Query(default=None, description="Filter by dynasty"),
    category: str | None = Query(default=None, description="Filter by category"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Search across entity types with full-text ILIKE matching.

    Example: GET /api/v1/search?q=针灸&types=book,passage,person&dynasty=西晋
    """
    entity_types = [t.strip() for t in types.split(",") if t.strip()]

    params = SearchParams(
        q=q,
        entity_types=entity_types,
        dynasty=dynasty,
        category=category,
        page=page,
        limit=limit,
    )

    svc = SearchService(session)
    result = await svc.search(params)
    return api_response(data=result.model_dump(mode="json"))


# ============================================================
# Autocomplete / Suggest
# ============================================================


@router.get(
    "/suggest",
    response_model=dict,
    dependencies=[Depends(guard_read)],
)
async def suggest(
    q: str = Query(..., min_length=1, description="Partial query string"),
    limit: int = Query(default=5, ge=1, le=20),
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> dict:
    """Return autocomplete suggestions for the search box.

    Matches entity title/name fields by prefix.

    Example: GET /api/v1/search/suggest?q=皇甫
    """
    svc = SearchService(session)
    suggestions = await svc.suggest(q, limit=limit)
    return api_response(data=[s.model_dump(mode="json") for s in suggestions])


# ============================================================
# Reindex (Admin)
# ============================================================


@router.post(
    "/reindex",
    response_model=dict,
    dependencies=[Depends(guard_admin)],
)
async def reindex(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Trigger a reindex of all searchable entities. Admin only."""
    svc = SearchService(session)
    result = await svc.reindex()
    return api_response(data=result)
