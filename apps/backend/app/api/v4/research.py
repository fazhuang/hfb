"""V4 Research Portal API — session, query, workflow, history endpoints.

STRICT: No ORM access. All data through existing services.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.schemas.v4 import (
    InternalTraceRecord,
    V4ApiEnvelope,
    V4ResearchQueryRequest,
    V4ResearchSessionRequest,
    V4ResearchWorkflowRequest,
    V4TraceabilityBlock,
    V4WorkflowResponse,
    V4WorkflowStep,
)
from app.services.academic_service import AcademicService
from app.services.dashboard_service import DashboardService
from app.services.graph_service import GraphService
from app.services.research_workflow_service import ResearchWorkflowService
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["Research V4"])

guard_research_read = require_permission("research", "read")
guard_research_update = require_permission("research", "update")

# ======================================================================
# Helpers — stable trace_id generation, internal record construction
# ======================================================================


def _make_trace_id(document_id: str, chunk_id: str) -> str:
    """Generate a stable, parseable trace_id distinct from chunk_id.

    Format: tr-{first 8 of sha256(doc_id:chunk_id)}
    """
    import hashlib
    raw = f"{document_id}:{chunk_id}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"tr-{h}"


def _make_internal_traces(evidence_traces: list) -> list[dict]:
    """Build full-fidelity InternalTraceRecord dicts from EvidenceTrace list."""
    now = datetime.now(timezone.utc).isoformat()
    records: list[dict] = []
    seen: set[str] = set()
    for t in evidence_traces:
        tid = _make_trace_id(t.document_id, t.chunk_id)
        if tid in seen:
            continue
        seen.add(tid)
        rec = InternalTraceRecord(
            trace_id=tid,
            document_id=t.document_id,
            chunk_id=t.chunk_id,
            passage_id=None,  # ponytail: DocumentChunk has no passage_id FK; blocked
            retrieval_score=None,
            retrieval_method=None,
            timestamp=now,
        )
        records.append(rec.model_dump())
    return records


def _extract_trace_ids(evidence_traces: list) -> list[str]:
    """Extract stable trace_ids from EvidenceTrace list."""
    seen: set[str] = set()
    ids: list[str] = []
    for t in evidence_traces:
        tid = _make_trace_id(t.document_id, t.chunk_id)
        if tid not in seen:
            seen.add(tid)
            ids.append(tid)
    return ids


def _extract_source_docs(evidence_traces: list) -> list[str]:
    return sorted(set(t.document_id for t in evidence_traces))


# ======================================================================
# POST /api/v4/research/session
# ======================================================================


@router.post(
    "/session",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_research_update)],
)
async def create_research_session(
    body: V4ResearchSessionRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> V4ApiEnvelope:
    """Create a research session. Optionally runs an initial query."""
    ws = WorkspaceService(db)
    title = body.title or "未命名研究"
    research_session = await ws.create_session(current_user, title)

    # Dashboard overview
    overview = await DashboardService(db).get_overview()

    traceability = None
    data: dict = {
        "session_id": research_session.id,
        "title": research_session.title,
        "dashboard_overview": overview,
    }

    # Optional initial query
    if body.query:
        academic = AcademicService(db)
        result = await academic.research(query=body.query)
        trace_ids = _extract_trace_ids(result.evidence_trace)
        internal_records = _make_internal_traces(result.evidence_trace)
        qh = await ws.create_query_history(
            session_id=research_session.id,
            query_text=body.query,
            query_type="research",
            result_summary=json.dumps({
                "traces": internal_records,
                "citation_count": len(result.citations),
                "source_documents": _extract_source_docs(result.evidence_trace),
            }, ensure_ascii=False),
            citation_count=len(result.citations),
        )
        traceability = V4TraceabilityBlock(
            query_id=qh.id,
            trace_ids=trace_ids,
            citation_count=len(result.citations),
            source_documents=_extract_source_docs(result.evidence_trace),
        )
        data["query_id"] = qh.id
        data["result"] = result.model_dump()

    return V4ApiEnvelope(success=True, data=data, message="ok", traceability=traceability)


# ======================================================================
# POST /api/v4/research/query
# ======================================================================


@router.post(
    "/query",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_research_read)],
)
async def execute_research_query(
    body: V4ResearchQueryRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> V4ApiEnvelope:
    """Execute a research query. Delegates to AcademicService or GraphService."""
    ws = WorkspaceService(db)

    # Verify session exists and is owned (IDOR check)
    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Route to appropriate service
    if body.mode == "graph":
        gs = GraphService(db)
        result = await gs.intelligence(query=body.query)
        # graph mode: extract traces from intelligence result
        evidence_traces = result.get("evidence_trace", [])
        citations_list = result.get("citations", [])
        trace_ids = _extract_trace_ids(evidence_traces) if evidence_traces else []
        internal_records = _make_internal_traces(evidence_traces) if evidence_traces else []
        source_docs = _extract_source_docs(evidence_traces) if evidence_traces else []
    else:
        academic = AcademicService(db)
        mode_map = {
            "report": academic.generate_report,
            "synthesis": academic.synthesize,
            "research": academic.research,
            "education": academic.educate,
        }
        handler = mode_map[body.mode]
        if body.mode == "report":
            result = await academic.generate_report(
                query=body.query, report_type="research_summary"
            )
        else:
            result = await handler(query=body.query)  # type: ignore[operator]
        trace_ids = _extract_trace_ids(result.evidence_trace)
        internal_records = _make_internal_traces(result.evidence_trace)
        citations_list = [c.model_dump() for c in result.citations]
        source_docs = _extract_source_docs(result.evidence_trace)

    # Record query history with full-fidelity internal traces
    qh = await ws.create_query_history(
        session_id=body.session_id,
        query_text=body.query,
        query_type=body.mode,
        result_summary=json.dumps({
            "traces": internal_records,
            "citation_count": len(citations_list),
            "source_documents": source_docs,
        }, ensure_ascii=False),
        citation_count=len(citations_list),
    )

    traceability = V4TraceabilityBlock(
        query_id=qh.id,
        trace_ids=trace_ids,
        citation_count=len(citations_list),
        source_documents=source_docs,
    )

    return V4ApiEnvelope(
        success=True,
        data=result if isinstance(result, dict) else result.model_dump(),
        message="ok",
        traceability=traceability,
    )


# ======================================================================
# POST /api/v4/research/workflow
# ======================================================================


FULL_RESEARCH_FLOW = [
    "topic_selection",
    "literature_retrieval",
    "evidence_synthesis",
    "report_generation",
    "citation_export",
]


@router.post(
    "/workflow",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_research_update)],
)
async def execute_research_workflow(
    body: V4ResearchWorkflowRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> V4ApiEnvelope:
    """Execute a 5-step research workflow with true step-to-step product passing.

    Each step consumes the prior step's output. Failure stops the pipeline.
    Workflow orchestration delegated to ResearchWorkflowService.
    """
    ws = WorkspaceService(db)
    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    rwf = ResearchWorkflowService(db)
    run_id = str(uuid4())
    steps: list[V4WorkflowStep] = []
    all_trace_ids: list[str] = []
    all_source_docs: list[str] = []
    workflow_failed = False

    # Step products for true pipeline passing
    retrieval_snapshot: list[dict] | None = None  # step 2 output
    synthesis_evidence: list[dict] | None = None  # step 3 output
    report_evidence: list[dict] | None = None  # step 4 output

    for i, step_name in enumerate(FULL_RESEARCH_FLOW):
        if workflow_failed:
            steps.append(V4WorkflowStep(
                name=step_name,
                status="pending",
                result=None,
                trace_ids=[],
            ))
            continue

        try:
            step_trace: list[str] = []
            step_docs: list[str] = []
            step_result: dict = {}

            if step_name == "topic_selection":
                result = await rwf.execute_topic_selection(body.topic)
                step_result = {"topic": body.topic, "sub_questions": result.get("sub_questions", 0)}
                step_trace = result.get("trace_ids", [])
                step_docs = result.get("source_documents", [])

            elif step_name == "literature_retrieval":
                result = await rwf.execute_literature_retrieval(body.topic)
                retrieval_snapshot = result.get("snapshot", [])
                step_result = {"themes": result.get("themes", 0), "records": len(retrieval_snapshot)}
                step_trace = result.get("trace_ids", [])
                step_docs = result.get("source_documents", [])

            elif step_name == "evidence_synthesis":
                if not retrieval_snapshot:
                    raise ValueError("No retrieval snapshot to synthesize")
                result = await rwf.execute_evidence_synthesis(
                    body.topic, retrieval_snapshot
                )
                synthesis_evidence = result.get("evidence", [])
                step_result = {"sections": result.get("sections", 0), "claims": len(synthesis_evidence)}
                step_trace = result.get("trace_ids", [])
                step_docs = result.get("source_documents", [])

            elif step_name == "report_generation":
                if not synthesis_evidence:
                    raise ValueError("No synthesis evidence to generate report from")
                result = await rwf.execute_report_generation(
                    body.topic, synthesis_evidence
                )
                report_evidence = result.get("evidence", [])
                step_result = {"sections": result.get("sections", 0), "title": result.get("title", body.topic)}
                step_trace = result.get("trace_ids", [])
                step_docs = result.get("source_documents", [])

                # Generate Markdown artifact
                markdown = await rwf.build_markdown_artifact(
                    topic=body.topic,
                    run_id=run_id,
                    retrieval_snapshot=retrieval_snapshot or [],
                    synthesis_evidence=synthesis_evidence or [],
                    report_evidence=report_evidence,
                )
                step_result["markdown_artifact"] = markdown[:200] + "..." if len(markdown) > 200 else markdown

            elif step_name == "citation_export":
                if not report_evidence and not synthesis_evidence:
                    raise ValueError("No evidence to export citations from")
                result = await rwf.execute_citation_export(
                    body.topic, report_evidence or synthesis_evidence or []
                )
                citations = result.get("citations", [])
                step_result = {"total_citations": len(citations), "citations": citations}
                step_trace = result.get("trace_ids", [])
                step_docs = result.get("source_documents", [])

                # Record final query history for export
                await ws.create_query_history(
                    session_id=body.session_id,
                    query_text=body.topic,
                    query_type="workflow_export",
                    result_summary=json.dumps({
                        "traces": result.get("internal_traces", []),
                        "source_documents": step_docs,
                    }, ensure_ascii=False),
                    citation_count=len(citations),
                )

            all_trace_ids.extend(step_trace)
            all_source_docs.extend(step_docs)

            # Record per-step query history
            await ws.create_query_history(
                session_id=body.session_id,
                query_text=f"[workflow step] {step_name}: {body.topic}",
                query_type="workflow_step",
                result_summary=json.dumps({
                    "step": step_name,
                    "traces": result.get("internal_traces", []),
                    "source_documents": step_docs,
                }, ensure_ascii=False),
                citation_count=len(step_trace),
            )

            steps.append(V4WorkflowStep(
                name=step_name,
                status="completed",
                result=step_result,
                trace_ids=step_trace,
            ))

        except Exception:
            logger.exception("Workflow step %s failed for session %s", step_name, body.session_id)
            workflow_failed = True
            steps.append(V4WorkflowStep(
                name=step_name,
                status="failed",
                result={"error": "Workflow step encountered an internal error"},
                trace_ids=[],
            ))

    # If any step failed, return failure — don't persist a completed run
    if workflow_failed:
        return V4ApiEnvelope(
            success=False,
            data=V4WorkflowResponse(
                run_id=run_id,
                session_id=body.session_id,
                steps=steps,
                traceability=None,
            ).model_dump(),
            message="Workflow execution failed — one or more steps encountered errors",
            traceability=None,
        )

    # Persist ResearchRun via ResearchWorkflowService (not direct ORM)
    await rwf.persist_research_run(
        session_id=body.session_id,
        run_id=run_id,
        topic=body.topic,
        steps=steps,
    )

    traceability = V4TraceabilityBlock(
        query_id=run_id,
        trace_ids=sorted(set(all_trace_ids)),
        citation_count=len(all_trace_ids),
        source_documents=sorted(set(all_source_docs)),
    )

    return V4ApiEnvelope(
        success=True,
        data=V4WorkflowResponse(
            run_id=run_id,
            session_id=body.session_id,
            steps=steps,
            traceability=traceability,
        ).model_dump(),
        message="ok",
        traceability=traceability,
    )


# ======================================================================
# GET /api/v4/research/session/{session_id}/history — read query history
# ======================================================================


@router.get(
    "/session/{session_id}/history",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_research_read)],
)
async def get_session_query_history(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
    limit: int = 50,
) -> V4ApiEnvelope:
    """Read-only query history for a session. Returns persisted records."""
    ws = WorkspaceService(db)
    research_session = await ws.get_session(session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    records = await ws.get_query_history(session_id, limit=limit)
    history = []
    for qh in records:
        summary = None
        if qh.result_summary:
            try:
                summary = json.loads(qh.result_summary)
            except (json.JSONDecodeError, TypeError):
                summary = None
        history.append({
            "query_id": qh.id,
            "query_text": qh.query_text,
            "query_type": qh.query_type,
            "citation_count": qh.citation_count,
            "created_at": qh.created_at.isoformat() if qh.created_at else None,
            "result_summary": summary,
        })

    return V4ApiEnvelope(
        success=True,
        data={"session_id": session_id, "history": history, "total": len(history)},
        message="ok",
    )


# ======================================================================
# GET /api/v4/research/session/{session_id}/runs — replay persisted runs
# ======================================================================


@router.get(
    "/session/{session_id}/runs",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_research_read)],
)
async def get_session_runs(
    session_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> V4ApiEnvelope:
    """Replay persisted ResearchRuns for a session. Returns immutable snapshots."""
    ws = WorkspaceService(db)
    research_session = await ws.get_session(session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    rwf = ResearchWorkflowService(db)
    runs = await rwf.get_research_runs(session_id)

    return V4ApiEnvelope(
        success=True,
        data={"session_id": session_id, "runs": runs, "total": len(runs)},
        message="ok",
    )
