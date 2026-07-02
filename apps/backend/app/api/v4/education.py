"""V4 Education API — grounded explanations, no inference beyond corpus.

P0 fix: body.level controls output — beginner/intermediate/advanced produce verifiable structural differences.
P0 fix: fail closed when no evidence.
P0 fix: all claims retain claim → evidence → citation binding at every level.
"""
from __future__ import annotations

import hashlib
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


def _make_trace_id(document_id: str, chunk_id: str) -> str:
    raw = f"{document_id}:{chunk_id}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"tr-{h}"


def _filter_by_level(result, level: str):
    """Apply level-specific filtering to education result.

    beginner: top claim only, minimal evidence binding
    intermediate: all main claims, full provenance
    advanced: all claims + source comparison + provenance, but no out-of-corpus facts

    Returns filtered result data dict. All levels retain claim→evidence→citation binding.
    """
    # Mark which level was applied
    data = result.model_dump()
    data["_applied_level"] = level

    explanation = data.get("explanation", [])
    evidence_trace = data.get("evidence_trace", [])

    if level == "beginner":
        # Most core, minimal evidence — top 1 concept only
        data["explanation"] = explanation[:1] if explanation else []
        # Keep only the evidence for the first concept
        kept_concept_ev = set()
        for c in data["explanation"]:
            for ev in c.get("evidence", []):
                kept_concept_ev.add(ev.get("chunk_id", ""))
        kept_traces = []
        seen_chunks = set()
        for t in evidence_trace:
            if t.get("chunk_id") in kept_concept_ev and t.get("chunk_id") not in seen_chunks:
                seen_chunks.add(t.get("chunk_id"))
                kept_traces.append(t)
        data["evidence_trace"] = kept_traces
        data["metadata"] = {
            **(data.get("metadata") or {}),
            "level_description": "入门 — 核心概念，最少证据",
            "total_claims": len(kept_traces),
        }

    elif level == "intermediate":
        # Full main claims
        data["metadata"] = {
            **(data.get("metadata") or {}),
            "level_description": "中级 — 完整的主要声明和出处",
            "total_claims": len(evidence_trace),
        }
        # No filtering — all claims

    elif level == "advanced":
        # Full claims + source comparison + provenance
        # Group evidence by source document for comparison
        docs: dict[str, list] = {}
        for t in evidence_trace:
            did = t.get("document_id", "unknown")
            if did not in docs:
                docs[did] = []
            docs[did].append(t)

        source_comparison: list[dict] = []
        for did, traces in docs.items():
            source_comparison.append({
                "document_id": did,
                "claim_count": len(traces),
                "claims": [
                    {"claim_text": t.get("claim_text", ""), "chunk_id": t.get("chunk_id", "")}
                    for t in traces[:3]
                ],
            })

        data["source_comparison"] = source_comparison
        data["metadata"] = {
            **(data.get("metadata") or {}),
            "level_description": "高级 — 完整声明、来源比较和出处",
            "source_count": len(docs),
            "total_claims": len(evidence_trace),
        }

    return data


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

    P0: body.level controls output. beginner/intermediate/advanced produce verifiable structural differences.
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

    # Safety gate: verify every education concept has evidence
    for concept in result.explanation:
        if not concept.evidence:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Education concept '{concept.concept}' has no evidence — violates corpus-bound constraint",
            )

    # Fail closed: no evidence at all
    if not result.evidence_trace:
        return V4ApiEnvelope(
            success=False,
            data={"error": "TRACE_LINEAGE_INCOMPLETE", "detail": "No evidence traces available"},
            message="Education cannot proceed: no evidence found for topic",
            traceability=None,
        )

    # Apply level-specific filtering
    filtered_data = _filter_by_level(result, body.level)

    # Build stable trace_ids
    trace_ids: list[str] = []
    seen_tids: set[str] = set()
    internal_records: list[dict] = []
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    for t in result.evidence_trace:
        tid = _make_trace_id(t.document_id, t.chunk_id)
        if tid not in seen_tids:
            seen_tids.add(tid)
            trace_ids.append(tid)
            internal_records.append({
                "trace_id": tid,
                "document_id": t.document_id,
                "chunk_id": t.chunk_id,
                "passage_id": None,
                "retrieval_score": None,
                "retrieval_method": None,
                "timestamp": now,
            })

    source_docs = sorted(set(t.document_id for t in result.evidence_trace))

    # Record query history with full-fidelity internal traces
    qh = await ws.create_query_history(
        session_id=body.session_id,
        query_text=body.topic,
        query_type="education",
        result_summary=json.dumps({
            "level": body.level,
            "traces": internal_records,
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
        data=filtered_data,
        message="ok",
        traceability=traceability,
    )
