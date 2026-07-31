"""Evidence-bound RAG API — POST /api/v1/rag/evidence-query"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.evidence_rag import EvidenceRAGRequest, EvidenceRAGResponse
from app.services.evidence_rag_service import EvidenceRAGService

router = APIRouter(prefix="/rag", tags=["Evidence-Bound RAG"])


@router.post(
    "/evidence-query",
    response_model=EvidenceRAGResponse,
    summary="证据绑定 RAG 查询",
)
async def evidence_query(
    body: EvidenceRAGRequest,
    session: AsyncSession = Depends(get_session),  # noqa: B008
) -> EvidenceRAGResponse:
    """Retrieve rag_enabled=true chunks with full evidence provenance."""
    svc = EvidenceRAGService(session)
    return await svc.query(body.query, top_k=body.top_k)
