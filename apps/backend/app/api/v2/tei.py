"""TEI V2 API routes — Phase 2b commentary, version_tree, variants."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.commentary import (
    CommentaryChainResponse,
    CommentaryCreate,
    CommentaryEnvelope,
    CommentaryGraphResponse,
)
from app.services.version_center import (
    create_commentary,
    get_commentaries_for_passage,
    get_commentary_chain,
    get_commentary_graph,
)

router = APIRouter(prefix="/tei", tags=["TEI V2"])

guard_tei_read = require_permission("ai", "read")
guard_tei_write = require_permission("graph", "review")


@router.get(
    "/passage/{passage_id}/commentaries",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def passage_commentaries(
    passage_id: str,
    layer: Annotated[str | None, Query(description="年代层过滤")] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> CommentaryEnvelope:
    """Get all commentaries for a passage, optionally by layer."""
    result = await get_commentaries_for_passage(session, passage_id, layer=layer)
    return CommentaryEnvelope(success=True, data=result, message="ok")


@router.get(
    "/commentary/{commentary_id}/chain",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def commentary_chain(
    commentary_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Trace full commentary chain from root to this commentary."""
    chain = await get_commentary_chain(session, commentary_id)
    return CommentaryEnvelope(
        success=True,
        data=CommentaryChainResponse(chain=chain, depth=len(chain)),
        message="ok",
    )


@router.post(
    "/commentary",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_write)],
)
async def create_commentary_endpoint(
    body: CommentaryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Create a new commentary annotation."""
    result = await create_commentary(session, body)
    return CommentaryEnvelope(success=True, data=result, message="ok")


@router.get(
    "/commentary-graph",
    response_model=CommentaryEnvelope,
    dependencies=[Depends(guard_tei_read)],
)
async def commentary_graph(
    passage_id: Annotated[str, Query(description="段落 ID")],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CommentaryEnvelope:
    """Get the commentary debate/supplement graph for a passage."""
    graph = await get_commentary_graph(session, passage_id)
    return CommentaryEnvelope(
        success=True,
        data=CommentaryGraphResponse(nodes=graph["nodes"], edges=graph["edges"]),
        message="ok",
    )
