"""Graph V2 API routes — Phase 2a evidence chain queries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.graph import (
    EvidenceChainEnvelope,
    MultiHopQueryRequest,
)
from app.services.graph_service import GraphService

router = APIRouter(prefix="/graph", tags=["Graph V2"])

guard_graph_read = require_permission("graph", "read")


@router.post(
    "/evidence-chains",
    response_model=EvidenceChainEnvelope,
    dependencies=[Depends(guard_graph_read)],
)
async def evidence_chains(
    body: MultiHopQueryRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EvidenceChainEnvelope:
    """Multi-hop evidence chain query over academically verified edges."""
    svc = GraphService(session)
    paths = await svc.multi_hop_query(
        source_type=body.source_type,
        source_id=body.source_id,
        target_type=body.target_type,
        target_id=body.target_id,
        min_evidence_level=body.min_evidence_level,
        max_hops=body.max_hops,
        relation_types=body.relation_types,
    )
    return EvidenceChainEnvelope(success=True, data=paths, message="ok")
