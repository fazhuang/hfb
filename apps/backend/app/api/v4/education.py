"""V4 Education API — grounded explanations, level-controlled output.

P0: body.level controls output with verifiable structural differences.
P0: beginner filters citations/traces/source_docs consistently.
P0: advanced source_comparison from verified evidence only.
P0: V4 education DTO — never leaks internal trace fields.
"""
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
from app.services.trace_lineage import (
    build_internal_traces,
    extract_source_documents,
    extract_trace_ids,
    make_trace_id,
)
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/education", tags=["Education V4"])

guard_edu = require_permission("ai", "read")


# ==========================================================================
# V4 Education public DTO — strict fields, no internal trace leakage
# ==========================================================================


def _build_education_public_data(result, level: str, evidence_traces) -> dict:
    """Build V4 education public response data for a specific level.

    Returns a strict DTO — no `data: Any` with arbitrary fields.
    All levels retain claim → evidence → citation binding.
    """
    explanation = result.explanation
    all_citations = result.citations
    all_evidence = evidence_traces

    # Filter based on level
    if level == "beginner":
        # Top concept only, consistent filtering across all outputs
        kept_concepts = explanation[:1]
        kept_chunk_ids = set()
        kept_doc_ids = set()
        for c in kept_concepts:
            for ev in c.evidence:
                kept_chunk_ids.add(ev.chunk_id)
                kept_doc_ids.add(ev.document_id)

        kept_traces = [t for t in all_evidence if t.chunk_id in kept_chunk_ids]
        kept_trace_ids = extract_trace_ids(kept_traces)
        kept_citations = [c for c in all_citations if c.chunk_id in kept_chunk_ids]
        kept_source_docs = sorted(kept_doc_ids)

        data = {
            "academic_type": "education",
            "applied_level": "beginner",
            "topic": result.query,
            "concepts": [
                {
                    "concept": c.concept,
                    "paragraphs": c.paragraphs,
                    "citation_count": len(c.citations),
                }
                for c in kept_concepts
            ],
            "citations": [c.model_dump() for c in kept_citations],
            "citation_count": len(kept_citations),
            "level_description": "入门 — 核心概念，最少证据",
        }
        return data, kept_trace_ids, kept_source_docs

    elif level == "intermediate":
        trace_ids = extract_trace_ids(all_evidence)
        data = {
            "academic_type": "education",
            "applied_level": "intermediate",
            "topic": result.query,
            "concepts": [
                {
                    "concept": c.concept,
                    "level": c.level,
                    "paragraphs": c.paragraphs,
                    "citation_count": len(c.citations),
                    "evidence_count": len(c.evidence),
                }
                for c in explanation
            ],
            "citation_count": len(all_citations),
            "level_description": "中级 — 完整的主要声明和出处",
        }
        return data, trace_ids, extract_source_documents(all_evidence)

    elif level == "advanced":
        trace_ids = extract_trace_ids(all_evidence)
        # Build source comparison from verified evidence only
        docs: dict[str, list] = {}
        for t in all_evidence:
            did = t.document_id
            if did not in docs:
                docs[did] = []
            docs[did].append({
                "claim_text": t.claim_text,
                "chunk_id": t.chunk_id,
                "trace_id": make_trace_id(t.document_id, t.chunk_id),
            })

        source_comparison = [
            {
                "document_id": did,
                "claim_count": len(claims),
                "claims": claims[:5],
            }
            for did, claims in docs.items()
        ]

        data = {
            "academic_type": "education",
            "applied_level": "advanced",
            "topic": result.query,
            "concepts": [
                {
                    "concept": c.concept,
                    "level": c.level,
                    "paragraphs": c.paragraphs,
                    "citation_count": len(c.citations),
                    "evidence_count": len(c.evidence),
                }
                for c in explanation
            ],
            "source_comparison": source_comparison,
            "citation_count": len(all_citations),
            "source_count": len(docs),
            "level_description": "高级 — 完整声明、来源比较和出处",
        }
        return data, trace_ids, extract_source_documents(all_evidence)

    else:
        raise ValueError(f"Unknown level: {level}")


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

    P0: body.level controls output with verifiable structural differences.
    P0: beginner: top concept, consistent citation/trace/source_doc filtering.
    P0: intermediate: all main claims, full provenance.
    P0: advanced: all claims + source comparison + provenance.
    """
    ws = WorkspaceService(db)

    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    academic = AcademicService(db)
    result = await academic.educate(query=body.topic)

    # Safety gate: every concept must have evidence
    for concept in result.explanation:
        if not concept.evidence:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Education concept '{concept.concept}' has no evidence",
            )

    # Fail closed: no evidence traces
    if not result.evidence_trace:
        return V4ApiEnvelope(
            success=False,
            data={"error": "TRACE_LINEAGE_INCOMPLETE"},
            message="Education cannot proceed: no evidence found",
            traceability=None,
        )

    # Build level-filtered public data
    edu_data, trace_ids, source_docs = _build_education_public_data(
        result, body.level, result.evidence_trace
    )

    # Build full-fidelity internal traces
    internal_records = build_internal_traces(result.evidence_trace)

    # Record query history
    qh = await ws.create_query_history(
        session_id=body.session_id,
        query_text=body.topic,
        query_type="education",
        result_summary=json.dumps({
            "level": body.level,
            "traces": [r.to_dict() for r in internal_records],
            "citation_count": len(result.citations),
            "source_documents": extract_source_documents(result.evidence_trace),
        }, ensure_ascii=False),
        citation_count=len(result.citations),
    )

    traceability = V4TraceabilityBlock(
        query_id=qh.id,
        trace_ids=trace_ids,
        citation_count=edu_data.get("citation_count", len(result.citations)),
        source_documents=source_docs,
    )

    return V4ApiEnvelope(
        success=True,
        data=edu_data,
        message="ok",
        traceability=traceability,
    )
