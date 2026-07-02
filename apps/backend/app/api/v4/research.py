"""V4 Research Portal API — session, query, workflow, history, runs endpoints.

STRICT: No ORM access. All data through existing services.
Uses unified trace_lineage module for all trace operations.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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
    TraceLineageError,
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
        try:
            internal_records = await build_internal_traces(db, result.evidence_trace)
        except TraceLineageError as e:
            return V4ApiEnvelope(
                success=False,
                data={"error": "TRACE_LINEAGE_INCOMPLETE", "detail": str(e)},
                message="Trace lineage incomplete — chunk has no passage_id mapping",
                traceability=None,
            )
        trace_ids = [r.trace_id for r in internal_records]

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

    if not evidence_traces:
        return V4ApiEnvelope(
            success=False,
            data={"error": "TRACE_LINEAGE_INCOMPLETE"},
            message="No evidence traces found for query",
            traceability=None,
        )

    try:
        internal_records = await build_internal_traces(db, evidence_traces)
    except TraceLineageError as e:
        return V4ApiEnvelope(
            success=False,
            data={"error": "TRACE_LINEAGE_INCOMPLETE", "detail": str(e)},
            message="Trace lineage incomplete — chunk has no passage_id mapping",
            traceability=None,
        )
    trace_ids = [r.trace_id for r in internal_records]
    source_docs = sorted(set(r.document_id for r in internal_records))

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
    """Execute a 5-step research workflow with immutable trace passing.

    Steps 3-5 pass the same InternalTraceRecord objects — no reconstruction.
    Step failure → subsequent steps pending → overall success=False.
    """
    ws = WorkspaceService(db)
    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    rwf = ResearchWorkflowService(db)
    run_id = str(uuid4())
    run_started_at = datetime.now(timezone.utc).isoformat()
    steps: list[V4WorkflowStep] = []
    workflow_failed = False
    error_code: str | None = None
    query_history_ids: list[str] = []

    # Immutable pass-along state
    retrieval_snapshot: list[dict] | None = None
    immutable_traces: list | None = None
    synthesis_output: dict | None = None

    for step_name in FULL_RESEARCH_FLOW:
        if workflow_failed:
            steps.append(V4WorkflowStep(name=step_name, status="pending", result=None, trace_ids=[]))
            continue

        try:
            step_result: dict = {}
            step_traces: list = []
            step_trace_ids: list[str] = []

            if step_name == "topic_selection":
                step_output = await rwf.execute_topic_selection(body.topic)
                step_traces = step_output.get("internal_traces", [])
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {"topic": body.topic, "sub_questions": step_output.get("result", {}).get("sub_questions", 0)}

            elif step_name == "literature_retrieval":
                step_output = await rwf.execute_literature_retrieval(body.topic)
                retrieval_snapshot = step_output.get("snapshot", [])
                immutable_traces = step_output.get("internal_traces", [])
                step_traces = immutable_traces
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {"themes": step_output.get("result", {}).get("themes", 0),
                               "records": len(retrieval_snapshot)}

            elif step_name == "evidence_synthesis":
                if not retrieval_snapshot:
                    raise ValueError("No retrieval snapshot")
                step_output = rwf.execute_evidence_synthesis_from_snapshot(
                    body.topic, retrieval_snapshot, internal_traces=immutable_traces,
                )
                synthesis_output = step_output
                step_traces = immutable_traces or []
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {"sections": step_output.get("result", {}).get("sections", 0),
                               "claims": step_output.get("result", {}).get("claims", 0)}

            elif step_name == "report_generation":
                if not synthesis_output:
                    raise ValueError("No synthesis output")
                step_output = rwf.execute_report_from_synthesis(body.topic, synthesis_output)
                step_traces = immutable_traces or []
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {"sections": step_output.get("result", {}).get("sections", 0),
                               "title": step_output.get("result", {}).get("title", body.topic)}

            elif step_name == "citation_export":
                all_evidence = synthesis_output.get("evidence", []) if synthesis_output else []
                step_output = rwf.execute_citation_export_from_evidence(
                    body.topic, all_evidence, internal_traces=immutable_traces,
                )
                step_traces = immutable_traces or []
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {"total_citations": step_output.get("result", {}).get("total_citations", 0)}

            # Record QueryHistory for this step
            step_trace_dicts = []
            if step_traces:
                try:
                    step_trace_dicts = [r.to_dict() for r in step_traces]
                except (AttributeError, TypeError):
                    step_trace_dicts = []
            step_source_docs = step_output.get("source_documents", []) if step_output else []

            result_summary = json.dumps({
                "step": step_name,
                "traces": step_trace_dicts,
                "source_documents": step_source_docs,
            }, ensure_ascii=False)

            qh = await ws.create_query_history(
                session_id=body.session_id,
                query_text=f"[workflow step] {step_name}: {body.topic}",
                query_type="workflow_step",
                result_summary=result_summary,
                citation_count=len(step_trace_ids),
            )
            query_history_ids.append(qh.id)

            steps.append(V4WorkflowStep(
                name=step_name,
                status="completed",
                result=step_result,
                trace_ids=step_trace_ids,
            ))

        except Exception:
            logger.exception("Workflow step %s failed for session %s", step_name, body.session_id)
            workflow_failed = True
            error_code = "WORKFLOW_STEP_FAILED"
            steps.append(V4WorkflowStep(name=step_name, status="failed",
                          result={"error": "Workflow step encountered an internal error"},
                          trace_ids=[]))

    if workflow_failed:
        return V4ApiEnvelope(
            success=False,
            data=V4WorkflowResponse(run_id=run_id, session_id=body.session_id,
                                     steps=steps, traceability=None).model_dump(),
            message=f"Workflow failed: {error_code}",
            traceability=None,
        )

    # Build Markdown artifact
    markdown = rwf.build_markdown_artifact(
        topic=body.topic, run_id=run_id, steps=steps,
        retrieval_snapshot=retrieval_snapshot or [],
        synthesis_output=synthesis_output or {},
    )
    artifact_id = run_id  # same as run_id for traceability

    # Persist ResearchRun
    run_completed_at = datetime.now(timezone.utc).isoformat()
    await rwf.persist_research_run(
        session_id=body.session_id,
        run_id=run_id,
        topic=body.topic,
        workflow_type=body.workflow_type,
        steps=steps,
        output_artifacts={"markdown": markdown, "artifact_id": artifact_id,
                          "created_at": run_completed_at},
        query_history_ids=query_history_ids,
        started_at=run_started_at,
        completed_at=run_completed_at,
    )

    # Aggregate trace_ids from all steps
    all_trace_ids: list[str] = []
    all_source_docs: set[str] = set()
    for s in steps:
        all_trace_ids.extend(s.trace_ids)
    if immutable_traces:
        all_source_docs.update(r.document_id for r in immutable_traces)

    traceability = V4TraceabilityBlock(
        query_id=run_id,
        trace_ids=sorted(set(all_trace_ids)),
        citation_count=len(all_trace_ids),
        source_documents=sorted(all_source_docs),
    )

    return V4ApiEnvelope(
        success=True,
        data=V4WorkflowResponse(run_id=run_id, session_id=body.session_id,
                                 steps=steps, traceability=traceability).model_dump(),
        message="ok",
        traceability=traceability,
    )


# ======================================================================
# GET /api/v4/research/session/{session_id}/history
# ======================================================================


class PublicHistoryEntry(BaseModel):
    query_id: str
    query_text: str
    query_type: str
    citation_count: int
    trace_count: int
    created_at: str | None


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
    """Read-only query history. Returns public DTO, never internal traces."""
    ws = WorkspaceService(db)
    research_session = await ws.get_session(session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    records = await ws.get_query_history(session_id, limit=limit)
    history: list[dict] = []
    trace_ids_all: list[str] = []
    source_docs_all: set[str] = set()

    for qh in records:
        trace_ids_for_record: list[str] = []
        if qh.result_summary:
            try:
                summary = json.loads(qh.result_summary)
                for t in summary.get("traces", []):
                    tid = t.get("trace_id", "")
                    if tid:
                        trace_ids_for_record.append(tid)
                        trace_ids_all.append(tid)
                        doc_id = t.get("document_id", "")
                        if doc_id:
                            source_docs_all.add(doc_id)
            except (json.JSONDecodeError, TypeError):
                pass

        history.append({
            "query_id": qh.id,
            "query_text": qh.query_text,
            "query_type": qh.query_type,
            "citation_count": qh.citation_count,
            "trace_count": len(trace_ids_for_record),
            "created_at": qh.created_at.isoformat() if qh.created_at else None,
        })

    return V4ApiEnvelope(
        success=True,
        data={"session_id": session_id, "history": history, "total": len(history)},
        message="ok",
        traceability=V4TraceabilityBlock(
            query_id=session_id,
            trace_ids=sorted(set(trace_ids_all)),
            citation_count=len(trace_ids_all),
            source_documents=sorted(source_docs_all),
        ),
    )


# ======================================================================
# GET /api/v4/research/session/{session_id}/runs
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
    """Replay persisted ResearchRuns. Immutable snapshots."""
    ws = WorkspaceService(db)
    research_session = await ws.get_session(session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    rwf = ResearchWorkflowService(db)
    runs = await rwf.get_research_runs(session_id)

    # Aggregate trace data from runs
    all_trace_ids: list[str] = []
    all_source_docs: set[str] = set()
    for run in runs:
        for step in run.get("step_execution_trace", []):
            all_trace_ids.extend(step.get("trace_ids", []))

    return V4ApiEnvelope(
        success=True,
        data={"session_id": session_id, "runs": runs, "total": len(runs)},
        message="ok",
        traceability=V4TraceabilityBlock(
            query_id=session_id,
            trace_ids=sorted(set(all_trace_ids)),
            citation_count=len(all_trace_ids),
            source_documents=sorted(all_source_docs),
        ),
    )
