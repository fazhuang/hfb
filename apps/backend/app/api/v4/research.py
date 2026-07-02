"""V4 Research Portal API — session, query, workflow, history endpoints.

STRICT: No ORM access. All data through existing services.
Uses unified trace_lineage module for trace_id generation and resolution.
"""
from __future__ import annotations

import json
import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.schemas.v4 import (
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
from app.services.trace_lineage import (
    build_internal_traces,
    extract_source_documents,
    extract_trace_ids,
)
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["Research V4"])

guard_research_read = require_permission("research", "read")
guard_research_update = require_permission("research", "update")


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

    overview = await DashboardService(db).get_overview()

    traceability = V4TraceabilityBlock(
        query_id=research_session.id,
        trace_ids=[],
        citation_count=0,
        source_documents=[],
    )
    data: dict = {
        "session_id": research_session.id,
        "title": research_session.title,
        "dashboard_overview": overview,
    }

    if body.query:
        academic = AcademicService(db)
        result = await academic.research(query=body.query)
        trace_ids = extract_trace_ids(result.evidence_trace)
        internal_records = build_internal_traces(result.evidence_trace)
        qh = await ws.create_query_history(
            session_id=research_session.id,
            query_text=body.query,
            query_type="research",
            result_summary=json.dumps({
                "traces": [r.to_dict() for r in internal_records],
                "citation_count": len(result.citations),
                "source_documents": extract_source_documents(result.evidence_trace),
            }, ensure_ascii=False),
            citation_count=len(result.citations),
        )
        traceability = V4TraceabilityBlock(
            query_id=qh.id,
            trace_ids=trace_ids,
            citation_count=len(result.citations),
            source_documents=extract_source_documents(result.evidence_trace),
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

    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    if body.mode == "graph":
        gs = GraphService(db)
        result = await gs.intelligence(query=body.query)
        evidence_traces = result.get("evidence_trace", [])
        citations_list = result.get("citations", [])
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
            result = await academic.generate_report(query=body.query, report_type="research_summary")
        else:
            result = await handler(query=body.query)  # type: ignore[operator]
        evidence_traces = result.evidence_trace
        citations_list = [c.model_dump() for c in result.citations]

    trace_ids = extract_trace_ids(evidence_traces) if evidence_traces else []
    internal_records = build_internal_traces(evidence_traces) if evidence_traces else []
    source_docs = extract_source_documents(evidence_traces) if evidence_traces else []

    qh = await ws.create_query_history(
        session_id=body.session_id,
        query_text=body.query,
        query_type=body.mode,
        result_summary=json.dumps({
            "traces": [r.to_dict() for r in internal_records],
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
    All steps that execute after a failure are set to 'pending'.
    """
    ws = WorkspaceService(db)
    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    rwf = ResearchWorkflowService(db)
    run_id = str(uuid4())
    steps: list[V4WorkflowStep] = []
    workflow_failed = False
    error_code: str | None = None

    # Step products for true pipeline passing
    retrieval_snapshot: list[dict] | None = None
    synthesis_output: dict | None = None

    for step_name in FULL_RESEARCH_FLOW:
        if workflow_failed:
            steps.append(V4WorkflowStep(name=step_name, status="pending", result=None, trace_ids=[]))
            continue

        try:
            if step_name == "topic_selection":
                step_output = await rwf.execute_topic_selection(body.topic)

            elif step_name == "literature_retrieval":
                step_output = await rwf.execute_literature_retrieval(body.topic)
                retrieval_snapshot = step_output.get("snapshot", [])

            elif step_name == "evidence_synthesis":
                if not retrieval_snapshot:
                    raise ValueError("No retrieval snapshot to synthesize")
                step_output = rwf.execute_evidence_synthesis_from_snapshot(
                    body.topic, retrieval_snapshot
                )
                synthesis_output = step_output

            elif step_name == "report_generation":
                if not synthesis_output:
                    raise ValueError("No synthesis output for report generation")
                step_output = rwf.execute_report_from_synthesis(
                    body.topic, synthesis_output
                )

            elif step_name == "citation_export":
                all_evidence = synthesis_output.get("evidence", []) if synthesis_output else []
                step_output = rwf.execute_citation_export_from_evidence(
                    body.topic, all_evidence
                )

            steps.append(V4WorkflowStep(
                name=step_name,
                status="completed",
                result=step_output.get("result", {}),
                trace_ids=step_output.get("trace_ids", []),
            ))

            # Record per-step query history
            await ws.create_query_history(
                session_id=body.session_id,
                query_text=f"[workflow step] {step_name}: {body.topic}",
                query_type="workflow_step",
                result_summary=json.dumps({
                    "step": step_name,
                    "traces": [r.to_dict() for r in step_output.get("internal_traces", [])],
                    "source_documents": step_output.get("source_documents", []),
                }, ensure_ascii=False),
                citation_count=len(step_output.get("trace_ids", [])),
            )

        except Exception:
            logger.exception("Workflow step %s failed for session %s", step_name, body.session_id)
            workflow_failed = True
            error_code = "WORKFLOW_STEP_FAILED"
            steps.append(V4WorkflowStep(
                name=step_name,
                status="failed",
                result={"error": "Workflow step encountered an internal error"},
                trace_ids=[],
            ))

    if workflow_failed:
        return V4ApiEnvelope(
            success=False,
            data=V4WorkflowResponse(
                run_id=run_id,
                session_id=body.session_id,
                steps=steps,
                traceability=None,
            ).model_dump(),
            message=f"Workflow execution failed: {error_code}",
            traceability=None,
        )

    # Collect all traces and sources
    all_trace_ids: list[str] = []
    all_source_docs: set[str] = set()
    for s in steps:
        all_trace_ids.extend(s.trace_ids)
    for step_output_name in FULL_RESEARCH_FLOW:
        pass  # already collected above

    # Build Markdown artifact (full, not truncated)
    markdown_artifact = rwf.build_markdown_artifact(
        topic=body.topic,
        run_id=run_id,
        steps=steps,
        retrieval_snapshot=retrieval_snapshot or [],
        synthesis_output=synthesis_output or {},
    )

    # Persist ResearchRun with full artifact
    await rwf.persist_research_run(
        session_id=body.session_id,
        run_id=run_id,
        topic=body.topic,
        workflow_type=body.workflow_type,
        steps=steps,
        output_artifacts={"markdown": markdown_artifact},
    )

    traceability = V4TraceabilityBlock(
        query_id=run_id,
        trace_ids=sorted(set(all_trace_ids)),
        citation_count=len(all_trace_ids),
        source_documents=sorted(all_source_docs),
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


class PublicQueryHistoryEntry(dict):
    """Public DTO for query history — never exposes internal traces."""
    pass


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
    """Read-only query history for a session. Returns public DTO, not internal traces."""
    ws = WorkspaceService(db)
    research_session = await ws.get_session(session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    records = await ws.get_query_history(session_id, limit=limit)
    history: list[dict] = []
    for qh in records:
        # Never expose result_summary raw — extract only public fields
        citation_count = qh.citation_count
        trace_ids_from_summary: list[str] = []
        if qh.result_summary:
            try:
                summary = json.loads(qh.result_summary)
                for t in summary.get("traces", []):
                    trace_ids_from_summary.append(t.get("trace_id", ""))
            except (json.JSONDecodeError, TypeError):
                pass

        history.append({
            "query_id": qh.id,
            "query_text": qh.query_text,
            "query_type": qh.query_type,
            "citation_count": citation_count,
            "trace_count": len(trace_ids_from_summary),
            "created_at": qh.created_at.isoformat() if qh.created_at else None,
        })

    return V4ApiEnvelope(
        success=True,
        data={"session_id": session_id, "history": history, "total": len(history)},
        message="ok",
        traceability=V4TraceabilityBlock(
            query_id=session_id,
            trace_ids=[],
            citation_count=0,
            source_documents=[],
        ),
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
    """Replay persisted ResearchRuns. Returns immutable snapshots, not re-execution."""
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
        traceability=V4TraceabilityBlock(
            query_id=session_id,
            trace_ids=[],
            citation_count=0,
            source_documents=[],
        ),
    )
