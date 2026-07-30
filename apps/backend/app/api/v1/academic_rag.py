"""
Academic RAG API — evidence-bound QA endpoint.

POST /api/v1/academic-rag/query

This is the PRODUCTION entry point for academic Chinese questions.
It replaces /graph/intelligence as the RAG QA endpoint.

Execution chain:
  HTTP API → ChineseQueryPlanner → corpus retrieval → GraphService multi-hop
  → evidence validation → deterministic answer renderer → strict response schema
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.academic_rag import (
    AcademicRAGEnvelope,
    AcademicRAGRequest,
    AcademicRAGResponse,
)
from app.services.academic_rag_service import AcademicRAGService

logger = get_logger(__name__)
router = APIRouter(prefix="/academic-rag", tags=["Academic RAG"])

guard_read = require_permission("graph", "read")


@router.post(
    "/query",
    response_model=AcademicRAGEnvelope,
    dependencies=[Depends(guard_read)],
)
async def academic_rag_query(
    body: AcademicRAGRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AcademicRAGEnvelope:
    """Answer an academic Chinese question with evidence-bound response.

    Supports unspaced Chinese questions like: 皇甫谧针灸思想来源是什么？

    Returns:
      - answer: deterministic evidence-based answer (no LLM in path)
      - refusal: true when no reliable evidence is available
      - citations: all evidence citations with provenance
      - kg_paths: continuous multi-hop knowledge graph paths
      - evidence_chain: claim → evidence → citation mapping
      - corpus_sha256 / output_sha256: deterministic hashes
    """
    svc = AcademicRAGService(session)
    try:
        result: AcademicRAGResponse = await svc.answer(body.query)
    except Exception as exc:
        logger.exception("academic_rag_query_failed query=%r", body.query[:200])
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Academic RAG query failed — internal error",
        ) from exc

    return AcademicRAGEnvelope(success=True, data=result, message="ok")
