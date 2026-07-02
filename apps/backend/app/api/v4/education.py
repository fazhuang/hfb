"""V4 Education API — grounded explanations, no inference beyond corpus."""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.schemas.v4 import (
    V4ApiEnvelope,
    V4EducationLearnRequest,
    V4TraceabilityBlock,
)
from app.services.academic_service import AcademicService
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/education", tags=["Education V4"])

guard_edu = require_permission("ai", "read")


@router.post(
    "/learn",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_edu)],
)
async def education_learn(
    body: V4EducationLearnRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> V4ApiEnvelope:
    """Education mode — citation-grounded, corpus-bound only.

    STRICT SAFETY: No inference beyond corpus evidence.
    All outputs are simplifications/paraphrases of retrieved passages.
    """
    ws = WorkspaceService(db)

    # Verify session exists and is owned by current user
    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    # Delegate to AcademicService.educate — already enforces claim-binding
    academic = AcademicService(db)
    result = await academic.educate(query=body.topic)

    # Additional safety gate: verify every education concept has evidence
    for concept in result.explanation:
        if not concept.evidence:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Education concept '{concept.concept}' has no evidence — violates corpus-bound constraint",
            )

    trace_ids = [t.chunk_id for t in result.evidence_trace]
    source_docs = list({t.document_id for t in result.evidence_trace})

    # Record query history
    qh = await ws.create_query_history(
        session_id=body.session_id,
        query_text=body.topic,
        query_type="education",
        result_summary=json.dumps({
            "level": body.level,
            "trace_ids": trace_ids,
            "citation_count": len(result.citations),
            "source_documents": source_docs,
        }, ensure_ascii=False),
        citation_count=len(result.citations),
    )

    traceability = V4TraceabilityBlock(
        query_id=qh.id,
        trace_ids=trace_ids,
        citation_count=len(result.citations),
        source_documents=source_docs,
    )

    return V4ApiEnvelope(
        success=True,
        data=result.model_dump(),
        message="ok",
        traceability=traceability,
    )
