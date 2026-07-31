"""V4 Research Portal API — session, query, workflow, history, runs endpoints.

STRICT: No ORM access. All data through existing services.
Uses unified trace_lineage module for all trace operations.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Annotated, Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
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
    TraceLineageError,
    build_internal_traces,
    extract_source_documents,
)
from app.services.workspace_service import WorkspaceService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/research", tags=["Research V4"])

guard_research_read = require_permission("research", "read")
guard_research_update = require_permission("research", "update")
guard_research_export = require_permission("research", "export")


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
        session_id=str(research_session.id),
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
            internal_records = await build_internal_traces(
                db,
                result.evidence_trace,
                retrieval_snapshot=academic.last_snapshot,
            )
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
            result_summary=json.dumps(
                {
                    "traces": [r.to_dict() for r in internal_records],
                    "citation_count": len(result.citations),
                    "source_documents": extract_source_documents(result.evidence_trace),
                },
                ensure_ascii=False,
            ),
            citation_count=len(result.citations),
        )
        traceability = V4TraceabilityBlock(
            query_id=qh.id,
            trace_ids=trace_ids,
            citation_count=len(result.citations),
            source_documents=extract_source_documents(result.evidence_trace),
            session_id=str(research_session.id),
        )
        data["query_id"] = qh.id
        data["result"] = result.model_dump()

    return V4ApiEnvelope(
        success=True, data=data, message="ok", traceability=traceability
    )


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    academic = AcademicService(db)
    if body.mode == "graph":
        gs = GraphService(db)
        result = await gs.intelligence(query=body.query)

        # Collect ALL chunk_ids from anywhere in the result dict that looks like evidence
        def _walk_collect(obj: Any) -> set[str]:
            ids: set[str] = set()
            if isinstance(obj, dict):
                cid = obj.get("chunk_id", "")
                if (
                    cid
                    and isinstance(cid, str)
                    and len(cid) > 0
                    and "document_id" in obj
                ):
                    ids.add(cid)
                for v in obj.values():
                    ids |= _walk_collect(v)
            elif isinstance(obj, list):
                for item in obj:
                    ids |= _walk_collect(item)
            return ids

        all_chunk_ids = _walk_collect(result)
        lineage_map: dict[str, dict] = {}
        if all_chunk_ids:
            from sqlalchemy import bindparam
            from sqlalchemy import text as sa_text

            ids_param = bindparam("ids", expanding=True)
            lineage_result = await db.execute(
                sa_text(
                    "SELECT dc.id, dc.passage_id, p.version_id, "
                    "COALESCE("
                    "  (SELECT sr.url FROM source_refs sr WHERE sr.page_location = 'passage:' || p.id AND sr.is_deleted=false LIMIT 1), "
                    "  (SELECT sr.url FROM source_refs sr WHERE sr.page_location LIKE 'passage:%' AND sr.is_deleted=false LIMIT 1), "
                    "  v.source_url, "
                    "  ''"
                    ") as source_uri, "
                    "COALESCE(dc.content, '') as claim_text "
                    "FROM document_chunks dc "
                    "LEFT JOIN passages p ON dc.passage_id = p.id AND p.is_deleted=false "
                    "LEFT JOIN versions v ON p.version_id = v.id AND v.is_deleted=false "
                    "WHERE dc.is_deleted=false AND dc.id IN :ids"
                ).bindparams(ids_param),
                {"ids": list(all_chunk_ids)},
            )
            for row in lineage_result:
                lineage_map[row[0]] = {
                    "passage_id": row[1] or "",
                    "version_id": row[2] or "",
                    "source_uri": row[3] or "",
                    "claim_text": row[4] or "",
                }

        # Recursively hydrate every evidence-like dict in-place
        def _hydrate_recursive(obj: Any) -> Any:
            if isinstance(obj, dict):
                if obj.get("chunk_id") and "document_id" in obj:
                    lm = lineage_map.get(obj.get("chunk_id", ""), {})
                    for k in ("version_id", "passage_id", "source_uri", "claim_text"):
                        if not obj.get(k):
                            obj[k] = lm.get(k, "")
                for k in obj:
                    obj[k] = _hydrate_recursive(obj[k])
            elif isinstance(obj, list):
                return [_hydrate_recursive(item) for item in obj]
            return obj

        result = _hydrate_recursive(result)

        raw_evidence_traces = result.get("evidence_trace", [])
        citations_list = result.get("citations", [])

        if not raw_evidence_traces:
            return V4ApiEnvelope(
                success=False,
                data={"error": "TRACE_LINEAGE_INCOMPLETE"},
                message="No evidence traces found for query",
                traceability=None,
            )

        # Build graph-provenance traces (via GraphEvidence objects)
        from app.schemas.graph import GraphEvidence
        from app.services.trace_lineage import build_viz_traces

        evidence_traces = [
            GraphEvidence(
                document_id=e.get("document_id", ""),
                chunk_id=e.get("chunk_id", ""),
                exact_quote=e.get("exact_quote", ""),
                citation=e.get("citation", ""),
                version_id=e.get("version_id", ""),
                passage_id=e.get("passage_id", ""),
                source_uri=e.get("source_uri", ""),
                claim_text=e.get("claim_text", ""),
            )
            for e in raw_evidence_traces
        ]
        try:
            internal_records = await build_viz_traces(db, evidence_traces)
        except TraceLineageError as e:
            return V4ApiEnvelope(
                success=False,
                data={"error": "TRACE_LINEAGE_INCOMPLETE", "detail": str(e)},
                message="Trace lineage incomplete — chunk has no passage_id mapping",
                traceability=None,
            )
        trace_ids = [r.trace_id for r in internal_records]
        source_docs = sorted({r.document_id for r in internal_records})
    else:
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
            internal_records = await build_internal_traces(
                db,
                evidence_traces,
                retrieval_snapshot=academic.last_snapshot,
            )
        except TraceLineageError as e:
            return V4ApiEnvelope(
                success=False,
                data={"error": "TRACE_LINEAGE_INCOMPLETE", "detail": str(e)},
                message="Trace lineage incomplete — chunk has no passage_id mapping",
                traceability=None,
            )
        trace_ids = [r.trace_id for r in internal_records]
        source_docs = sorted({r.document_id for r in internal_records})

    qh = await ws.create_query_history(
        session_id=body.session_id,
        query_text=body.query,
        query_type=body.mode,
        result_summary=json.dumps(
            {
                "traces": [r.to_dict() for r in internal_records],
                "citation_count": len(citations_list),
                "source_documents": source_docs,
            },
            ensure_ascii=False,
        ),
        citation_count=len(citations_list),
    )

    traceability = V4TraceabilityBlock(
        query_id=qh.id,
        trace_ids=trace_ids,
        citation_count=len(citations_list),
        source_documents=source_docs,
        session_id=body.session_id,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    rwf = ResearchWorkflowService(db)
    run_id = str(uuid4())
    run_started_at = datetime.now(UTC).isoformat()
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
            steps.append(
                V4WorkflowStep(
                    name=step_name, status="pending", result=None, trace_ids=[]
                )
            )
            continue

        try:
            step_result: dict = {}
            step_traces: list = []
            step_trace_ids: list[str] = []

            if step_name == "topic_selection":
                step_output = await rwf.execute_topic_selection(body.topic)
                step_traces = step_output.get("internal_traces", [])
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {
                    "topic": body.topic,
                    "sub_questions": step_output.get("result", {}).get(
                        "sub_questions", 0
                    ),
                }

            elif step_name == "literature_retrieval":
                step_output = await rwf.execute_literature_retrieval(body.topic)
                retrieval_snapshot = step_output.get("snapshot", [])
                immutable_traces = step_output.get("internal_traces", [])
                step_traces = immutable_traces
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {
                    "themes": step_output.get("result", {}).get("themes", 0),
                    "records": len(retrieval_snapshot),
                }

            elif step_name == "evidence_synthesis":
                if not retrieval_snapshot:
                    raise ValueError("No retrieval snapshot")
                step_output = rwf.execute_evidence_synthesis_from_snapshot(
                    body.topic,
                    retrieval_snapshot,
                    internal_traces=immutable_traces,
                )
                synthesis_output = step_output
                step_traces = immutable_traces or []
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {
                    "sections": step_output.get("result", {}).get("sections", 0),
                    "claims": step_output.get("result", {}).get("claims", 0),
                }

            elif step_name == "report_generation":
                if not synthesis_output:
                    raise ValueError("No synthesis output")
                step_output = rwf.execute_report_from_synthesis(
                    body.topic, synthesis_output
                )
                step_traces = immutable_traces or []
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {
                    "sections": step_output.get("result", {}).get("sections", 0),
                    "title": step_output.get("result", {}).get("title", body.topic),
                }

            elif step_name == "citation_export":
                all_evidence = (
                    synthesis_output.get("evidence", []) if synthesis_output else []
                )
                step_output = rwf.execute_citation_export_from_evidence(
                    body.topic,
                    all_evidence,
                    internal_traces=immutable_traces,
                )
                step_traces = immutable_traces or []
                step_trace_ids = step_output.get("trace_ids", [])
                step_result = {
                    "total_citations": step_output.get("result", {}).get(
                        "total_citations", 0
                    )
                }

            # Record QueryHistory for this step
            step_trace_dicts = []
            if step_traces:
                try:
                    step_trace_dicts = [r.to_dict() for r in step_traces]
                except (AttributeError, TypeError):
                    step_trace_dicts = []
            step_source_docs = (
                step_output.get("source_documents", []) if step_output else []
            )

            result_summary = json.dumps(
                {
                    "step": step_name,
                    "traces": step_trace_dicts,
                    "source_documents": step_source_docs,
                },
                ensure_ascii=False,
            )

            qh = await ws.create_query_history(
                session_id=body.session_id,
                query_text=f"[workflow step] {step_name}: {body.topic}",
                query_type="workflow_step",
                result_summary=result_summary,
                citation_count=len(step_trace_ids),
            )
            query_history_ids.append(qh.id)

            steps.append(
                V4WorkflowStep(
                    name=step_name,
                    status="completed",
                    result=step_result,
                    trace_ids=step_trace_ids,
                )
            )

            # P2T1: If literature retrieval produced zero records, fail the
            # workflow with NO_EVIDENCE instead of continuing through steps
            # 3-5 with empty data and returning a misleading "success".
            if step_name == "literature_retrieval" and not retrieval_snapshot:
                workflow_failed = True
                error_code = "NO_EVIDENCE"

        except (ValueError, RuntimeError):
            logger.exception(
                "Workflow step %s failed for session %s", step_name, body.session_id
            )
            workflow_failed = True
            error_code = "WORKFLOW_STEP_FAILED"
            # P2T1: structured error for client — diagnostics in server log only
            steps.append(
                V4WorkflowStep(
                    name=step_name,
                    status="failed",
                    result={
                        "error": "Workflow step encountered an internal error",
                        "error_code": error_code,
                    },
                    trace_ids=[],
                )
            )

    if workflow_failed:
        if error_code == "NO_EVIDENCE":
            msg = f"未找到与「{body.topic}」相关的文献证据，无法生成研究报告。请尝试更换研究主题或调整检索词。"
        else:
            msg = f"Workflow failed: {error_code}"
        return V4ApiEnvelope(
            success=False,
            data=V4WorkflowResponse(
                run_id=run_id,
                session_id=body.session_id,
                steps=steps,
                traceability=None,
            ).model_dump(),
            message=msg,
            traceability=None,
        )

    # Build Markdown artifact
    markdown = rwf.build_markdown_artifact(
        topic=body.topic,
        run_id=run_id,
        steps=steps,
        retrieval_snapshot=retrieval_snapshot or [],
        synthesis_output=synthesis_output or {},
    )
    artifact_id = run_id  # same as run_id for traceability

    # Persist ResearchRun
    run_completed_at = datetime.now(UTC).isoformat()
    await rwf.persist_research_run(
        session_id=body.session_id,
        run_id=run_id,
        topic=body.topic,
        workflow_type=body.workflow_type,
        steps=steps,
        output_artifacts={
            "markdown": markdown,
            "artifact_id": artifact_id,
            "created_at": run_completed_at,
            "citations": [
                {
                    "trace_id": c.get("trace_id", ""),
                    "citation_text": c.get("citation_text", ""),
                    "document_id": c.get("document_id", ""),
                    "quote": c.get("quote", ""),
                }
                for c in (synthesis_output or {}).get("evidence", [])[:200]
            ],
        },
        query_history_ids=query_history_ids,
        started_at=run_started_at,
        completed_at=run_completed_at,
        retrieval_snapshot=retrieval_snapshot or [],
        immutable_traces=immutable_traces or [],
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
        session_id=body.session_id,
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

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
                logger.debug(
                    "Failed to parse query history result_summary", exc_info=True
                )

        history.append(
            {
                "query_id": qh.id,
                "query_text": qh.query_text,
                "query_type": qh.query_type,
                "citation_count": qh.citation_count,
                "trace_count": len(trace_ids_for_record),
                "created_at": qh.created_at.isoformat() if qh.created_at else None,
            }
        )

    return V4ApiEnvelope(
        success=True,
        data={"session_id": session_id, "history": history, "total": len(history)},
        message="ok",
        traceability=V4TraceabilityBlock(
            query_id=session_id,
            trace_ids=sorted(set(trace_ids_all)),
            citation_count=len(trace_ids_all),
            source_documents=sorted(source_docs_all),
            session_id=session_id,
        ),
    )


# ======================================================================
# GET /api/v4/research/reports
# ======================================================================


def _derive_run_status(trace: list[dict]) -> str:
    """Derive run_status from step_execution_trace.

    - any step status 'failed' -> 'failed'
    - any step status 'running' or 'pending' -> 'running'
    - all steps 'completed' -> 'completed'
    - no steps -> 'pending'
    """
    if not trace:
        return "pending"
    _statuses = [step.get("status", "") for step in trace]
    if any(st == "failed" for st in _statuses):
        return "failed"
    if any(st in ("running", "pending") for st in _statuses):
        return "running"
    if all(st == "completed" for st in _statuses):
        return "completed"
    return "pending"


def _derive_report_status(trace: list[dict], artifacts: dict) -> str:
    """Derive report_status from step_execution_trace + output_artifacts.

    - report_generation step status == 'failed' -> 'failed'
    - report_generation step not found or status in ('pending','running') -> 'pending'
    - report_generation step completed but output_artifacts.markdown empty -> 'missing'
    - output_artifacts.markdown non-empty -> 'ready'
    """
    report_step = next(
        (
            step
            for step in trace
            if step.get("step_name") == "report_generation"
            or step.get("name") == "report_generation"
        ),
        None,
    )
    if report_step is not None and report_step.get("status") == "failed":
        return "failed"
    if report_step is None or report_step.get("status") in ("pending", "running"):
        return "pending"
    # report_step is completed — check for markdown
    markdown = (artifacts.get("markdown") or "").strip()
    if not markdown:
        return "missing"
    return "ready"


@router.get(
    "/reports",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_research_read)],
)
async def get_research_reports(
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
    page: int = 1,
    limit: int = 20,
    status: str | None = None,
) -> V4ApiEnvelope:
    """Aggregate research runs across all of the current user's sessions.

    Collects runs from every session, derives run_status from the
    step_execution_trace and report_status from output_artifacts plus
    the report_generation step, then returns a paginated, sorted
    (DESC by started_at) list filtered by report_status when provided.

    Authorization: only sessions belonging to current_user are collected
    (WorkspaceService.list_sessions filters by user_id).
    """
    ws = WorkspaceService(db)
    rwf = ResearchWorkflowService(db)

    # Collect all sessions for this user (generous limit for aggregation)
    sessions = await ws.list_sessions(current_user, limit=500)

    # Aggregate runs from all sessions
    all_items: list[dict] = []
    for s in sessions:
        runs = await rwf.get_research_runs(s.id)
        for run in runs:
            trace: list[dict] = run.get("step_execution_trace") or []
            artifacts: dict = run.get("output_artifacts") or {}

            run_status = _derive_run_status(trace)
            report_status_val = _derive_report_status(trace, artifacts)

            completed_at = run.get("completed_at")
            all_items.append(
                {
                    "session_id": str(run.get("session_id", "")),
                    "session_title": s.title or "",
                    "run_id": str(run.get("run_id", "")),
                    "topic": str(run.get("topic", "")),
                    "run_status": run_status,
                    "report_status": report_status_val,
                    "created_at": str(run.get("started_at", "")),
                    "completed_at": completed_at if completed_at else None,
                    "workflow_type": str(run.get("workflow_type", "")),
                }
            )

    # Sort by created_at DESC (newest first)
    all_items.sort(key=lambda x: x["created_at"], reverse=True)

    # Apply status filter
    if status:
        all_items = [item for item in all_items if item["report_status"] == status]

    total = len(all_items)

    # Apply pagination
    start = (page - 1) * limit
    end = start + limit
    paginated = all_items[start:end]

    return V4ApiEnvelope(
        success=True,
        data={
            "items": paginated,
            "total": total,
            "page": page,
            "limit": limit,
        },
        message="ok",
        traceability=None,
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
    """List all runs belonging to this session.

    Authorization: session ownership validated via user_id check.
    Each run's session_id field is verified against the URL session_id
    before inclusion in the response (defense-in-depth).
    """
    ws = WorkspaceService(db)
    research_session = await ws.get_session(session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Session not found"
        )

    rwf = ResearchWorkflowService(db)
    raw_runs = await rwf.get_research_runs(session_id)

    # Defense-in-depth: validate every run's session_id matches the URL.
    # Runs are JSON blobs inside workflow_state; a malformed or cross-session
    # run must never leak to a different session's response.
    runs: list[dict] = []
    for run in raw_runs:
        run_sid = str(run.get("session_id", ""))
        if run_sid == str(session_id):
            runs.append(run)

    # Aggregate trace data from run manifests
    all_trace_ids: list[str] = []
    all_source_docs: set[str] = set()
    for run in runs:
        manifest = run.get("replay_manifest")
        if manifest:
            for t in manifest.get("traces", []):
                tid = t.get("trace_id", "")
                if tid:
                    all_trace_ids.append(tid)
                did = t.get("document_id", "")
                if did:
                    all_source_docs.add(did)
        else:
            # Fallback: extract from step_execution_trace
            for step in run.get("step_execution_trace", []):
                all_trace_ids.extend(step.get("trace_ids", []))

    return V4ApiEnvelope(
        success=True,
        data={"session_id": session_id, "runs": runs, "total": len(runs)},
        message="ok",
        traceability=V4TraceabilityBlock(
            query_id=session_id,
            trace_ids=sorted(set(all_trace_ids)),
            citation_count=len(set(all_trace_ids)),
            source_documents=sorted(all_source_docs),
            session_id=session_id,
        ),
    )


# ======================================================================
# GET /api/v4/research/session/{session_id}/runs/{run_id}/export
# ======================================================================

EXPORTABLE_FORMATS = frozenset({"markdown"})


@router.get(
    "/session/{session_id}/runs/{run_id}/export",
    dependencies=[Depends(guard_research_export)],
)
async def export_run_markdown(
    session_id: str,
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
    format: str = "markdown",
) -> Response:
    """Export a single run's report as Markdown.

    Authorization:
     - Current user MUST own the session
     - Run MUST belong to the session
     - Run MUST have a non-empty report markdown
     - Unsupported format returns 400
     - Fail-closed: no data leaks across users, sessions, or runs
    """
    # Validate format early
    if format not in EXPORTABLE_FORMATS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported export format: {format}. Supported: {', '.join(sorted(EXPORTABLE_FORMATS))}",
        )

    # Validate session ownership
    ws = WorkspaceService(db)
    research_session = await ws.get_session(session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    # Validate run exists and belongs to this session
    rwf = ResearchWorkflowService(db)
    runs = await rwf.get_research_runs(session_id)
    target_run = None
    for run in runs:
        if run.get("run_id") == run_id:
            target_run = run
            break

    if target_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    # Validate run's session_id matches URL session_id (defense-in-depth)
    run_session_id = target_run.get("session_id", "")
    if str(run_session_id) != str(session_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Run not found",
        )

    # Extract report markdown
    artifacts = target_run.get("output_artifacts") or {}
    markdown = (artifacts.get("markdown") or "").strip()
    if not markdown:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Report is empty — nothing to export",
        )

    safe_run_id = run_id[:8]
    safe_filename = f"hfb-research-report-{safe_run_id}.md"

    return Response(
        content=markdown,
        media_type="text/markdown; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_filename}"',
        },
    )


# ======================================================================
# POST /api/v4/research/runs/{run_id}/replay
# ======================================================================


class ReplayRequest(BaseModel):
    pass


class ReplayResponseData(BaseModel):
    run_id: str
    original_output_sha256: str
    replay_output_sha256: str
    matched: bool
    traceability: V4TraceabilityBlock | None = None


@router.post(
    "/runs/{run_id}/replay",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_research_read)],
)
async def replay_research_run(
    run_id: str,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
    body: ReplayRequest | None = None,
) -> V4ApiEnvelope:
    """Deterministically replay a persisted ResearchRun.

    1. Validates current user owns the session.
    2. Uses the frozen replay_manifest to re-execute synthesis, report, citation export.
    3. Recomputes canonical output hash using the SAME canonical artifact constructor.
    4. Returns matched status.
    """
    rwf = ResearchWorkflowService(db)
    ws = WorkspaceService(db)

    # Find the run across all user sessions — verify ownership
    run_data: dict | None = None

    # Search through user's sessions to find the run
    user_sessions = await ws.list_sessions(current_user, limit=100)
    for s in user_sessions:
        runs = await rwf.get_research_runs(s.id)
        for r in runs:
            if r.get("run_id") == run_id:
                run_data = r
                break
        if run_data:
            break

    if run_data is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Run not found"
        )

    manifest = run_data.get("replay_manifest")
    if not manifest:
        return V4ApiEnvelope(
            success=False,
            data={"error": "NO_REPLAY_MANIFEST"},
            message="Run has no replay manifest — cannot replay",
            traceability=None,
        )

    # Strict manifest validation — all required fields must be present
    required_manifest_fields = [
        "manifest_version",
        "manifest_sha256",
        "corpus_sha256",
        "canonical_input_sha256",
        "canonical_output_sha256",
        "retrieval_snapshot",
        "traces",
        "topic",
        "workflow_type",
    ]
    missing = [f for f in required_manifest_fields if f not in manifest]
    if missing:
        if "manifest_sha256" in missing:
            return V4ApiEnvelope(
                success=False,
                data={"error": "UNVERIFIABLE_MANIFEST", "missing_fields": missing},
                message="Replay manifest has no integrity proof",
                traceability=None,
            )
        return V4ApiEnvelope(
            success=False,
            data={"error": "CORRUPT_MANIFEST", "missing_fields": missing},
            message="Replay manifest is incomplete or corrupt",
            traceability=None,
        )

    # Step 3: Validate manifest_sha256 format — must be 64-char lowercase hex SHA-256
    stored_manifest_hash = manifest["manifest_sha256"]
    if (
        not isinstance(stored_manifest_hash, str)
        or stored_manifest_hash == ""
        or len(stored_manifest_hash) != 64
        or not all(c in "0123456789abcdef" for c in stored_manifest_hash)
    ):
        return V4ApiEnvelope(
            success=False,
            data={"error": "CORRUPT_MANIFEST"},
            message="Replay manifest integrity hash is invalid",
            traceability=None,
        )

    # Step 4: Verify manifest_sha256 — manifest self-integrity
    from app.services.research_workflow_service import canonical_sha256

    manifest_for_hash = {k: v for k, v in manifest.items() if k != "manifest_sha256"}
    recomputed_manifest_hash = canonical_sha256(manifest_for_hash)
    if recomputed_manifest_hash != stored_manifest_hash:
        return V4ApiEnvelope(
            success=False,
            data={"error": "CORRUPT_MANIFEST"},
            message="Replay manifest integrity check failed",
            traceability=None,
        )

    topic = manifest["topic"]
    workflow_type = manifest["workflow_type"]
    pipeline_version = manifest.get("pipeline_version", "1.0.0")
    snapshot = manifest["retrieval_snapshot"]
    traces_data = manifest.get("traces", [])

    # Step 4: Parse and strictly validate all traces — no defaults, no skipping
    from app.services.research_workflow_service import (
        _build_canonical_payload,
        _build_corpus_payload,
        _build_input_payload,
        canonical_sha256,
        canonicalize_traces,
    )
    from app.services.trace_lineage import InternalTraceRecord

    frozen_traces: list[InternalTraceRecord] = []
    trace_required_fields = [
        "trace_id",
        "document_id",
        "chunk_id",
        "passage_id",
        "provenance_kind",
        "retrieval_method",
        "timestamp",
    ]
    for i, td in enumerate(traces_data):
        # Require all fields — no defaults
        missing_trace = [f for f in trace_required_fields if f not in td]
        if missing_trace:
            return V4ApiEnvelope(
                success=False,
                data={
                    "error": "CORRUPT_MANIFEST",
                    "detail": f"Trace[{i}] missing fields: {missing_trace}",
                },
                message="Replay manifest trace is incomplete or corrupt",
                traceability=None,
            )
        # retrieval_score is optional only for graph provenance
        pk = td["provenance_kind"]
        if pk not in ("retrieval", "graph"):
            return V4ApiEnvelope(
                success=False,
                data={
                    "error": "CORRUPT_MANIFEST",
                    "detail": f"Trace[{i}] invalid provenance_kind: {pk}",
                },
                message="Replay manifest trace has invalid provenance",
                traceability=None,
            )
        if pk == "retrieval" and "retrieval_score" not in td:
            return V4ApiEnvelope(
                success=False,
                data={
                    "error": "CORRUPT_MANIFEST",
                    "detail": f"Trace[{i}] retrieval provenance missing retrieval_score",
                },
                message="Replay manifest trace is incomplete",
                traceability=None,
            )

        try:
            rec = InternalTraceRecord(
                trace_id=td["trace_id"],
                document_id=td["document_id"],
                chunk_id=td["chunk_id"],
                passage_id=td["passage_id"],
                provenance_kind=pk,
                retrieval_score=td.get("retrieval_score"),
                retrieval_method=td["retrieval_method"],
                timestamp=td["timestamp"],
            )
            frozen_traces.append(rec)
        except (TypeError, ValueError) as e:
            return V4ApiEnvelope(
                success=False,
                data={
                    "error": "CORRUPT_MANIFEST",
                    "detail": f"Trace[{i}] (trace_id={td.get('trace_id', '?')}) invalid: {e}",
                },
                message="Replay manifest trace validation failed",
                traceability=None,
            )

    if not frozen_traces:
        return V4ApiEnvelope(
            success=False,
            data={"error": "EMPTY_FROZEN_TRACES"},
            message="Replay manifest has no valid traces",
            traceability=None,
        )

    # Step 5-7: Re-compute all hashes with canonical traces
    trace_dicts = [r.to_dict() for r in frozen_traces]
    canonical_traces = canonicalize_traces(trace_dicts)
    trace_passage_map = {ct["trace_id"]: ct["passage_id"] for ct in canonical_traces}
    snapshot_for_corpus = []
    for r in snapshot:
        entry = dict(r)
        tid = entry.get("trace_id", "")
        if tid in trace_passage_map:
            entry.setdefault("passage_id", trace_passage_map[tid])
        snapshot_for_corpus.append(entry)

    trace_ids_frozen = sorted({r.trace_id for r in frozen_traces})
    source_doc_ids_frozen = sorted({r.document_id for r in frozen_traces})

    recomputed_corpus = canonical_sha256(_build_corpus_payload(snapshot_for_corpus))
    recomputed_input = canonical_sha256(
        _build_input_payload(
            topic=topic,
            workflow_type=workflow_type,
            pipeline_version=pipeline_version,
            retrieval_snapshot=snapshot,
            trace_ids=trace_ids_frozen,
            source_document_ids=source_doc_ids_frozen,
            canonical_traces=canonical_traces,
        )
    )

    if recomputed_corpus != manifest["corpus_sha256"]:
        return V4ApiEnvelope(
            success=False,
            data={
                "error": "CORRUPT_MANIFEST",
                "detail": f"corpus_sha256 mismatch: expected {manifest['corpus_sha256']}, got {recomputed_corpus}",
            },
            message="Replay manifest corpus integrity check failed",
            traceability=None,
        )

    if recomputed_input != manifest["canonical_input_sha256"]:
        return V4ApiEnvelope(
            success=False,
            data={
                "error": "CORRUPT_MANIFEST",
                "detail": f"canonical_input_sha256 mismatch: expected {manifest['canonical_input_sha256']}, got {recomputed_input}",
            },
            message="Replay manifest input integrity check failed",
            traceability=None,
        )

    # Step 8: Deterministic replay
    try:
        syn_out = rwf.execute_evidence_synthesis_from_snapshot(
            topic,
            snapshot,
            internal_traces=frozen_traces,
        )
        rep_out = rwf.execute_report_from_synthesis(topic, syn_out)
        cit_out = rwf.execute_citation_export_from_evidence(
            topic,
            syn_out.get("evidence", []),
            internal_traces=frozen_traces,
        )
    except RuntimeError as e:
        return V4ApiEnvelope(
            success=False,
            data={"error": "REPLAY_EXECUTION_FAILED", "detail": str(e)},
            message="Replay execution failed",
            traceability=None,
        )

    # Steps 9-10: Recompute canonical output hash
    from app.services.research_workflow_service import _group_snapshot_into_sections

    synthesis_sections = _group_snapshot_into_sections(snapshot)
    all_evidence = syn_out.get("evidence", [])
    report_sections_for_hash = syn_out.get("sections", [])
    if not report_sections_for_hash:
        from app.services.research_workflow_service import _build_report_sections

        report_sections_for_hash = _build_report_sections(
            topic,
            all_evidence,
            rep_out.get("sections", []),
        )

    replay_payload = _build_canonical_payload(
        topic=topic,
        workflow_type=workflow_type,
        pipeline_version=pipeline_version,
        retrieval_snapshot=snapshot,
        synthesis_sections=synthesis_sections,
        synthesis_evidence=all_evidence,
        report_sections=report_sections_for_hash,
        citations=cit_out.get("result", {}).get("citations", []),
        trace_ids=sorted({r.trace_id for r in frozen_traces}),
        source_document_ids=sorted({r.document_id for r in frozen_traces}),
        canonical_traces=canonical_traces,
    )
    replay_output_sha256 = canonical_sha256(replay_payload)
    original_output_sha256 = manifest["canonical_output_sha256"]

    matched = replay_output_sha256 == original_output_sha256

    replay_trace_ids = sorted({r.trace_id for r in frozen_traces})
    replay_source_docs = sorted({r.document_id for r in frozen_traces})

    return V4ApiEnvelope(
        success=matched,
        data={
            "run_id": run_id,
            "original_output_sha256": original_output_sha256,
            "replay_output_sha256": replay_output_sha256,
            "matched": matched,
            "traceability": {
                "query_id": run_id,
                "trace_ids": replay_trace_ids,
                "citation_count": len(replay_trace_ids),
                "source_documents": replay_source_docs,
            },
        },
        message="ok" if matched else "Replay mismatch — reproducibility failure",
        traceability=V4TraceabilityBlock(
            query_id=run_id,
            trace_ids=replay_trace_ids,
            citation_count=len(replay_trace_ids),
            source_documents=replay_source_docs,
            session_id=run_data.get("session_id"),
        ),
    )


# ======================================================================
# Test-only: seed a research run for E2E testing
# ======================================================================


class SeedRunRequest(BaseModel):
    session_id: str
    topic: str = "E2E 测试研究"
    markdown: str | None = None
    step_execution_trace: list[dict] | None = None
    citations: list[dict] | None = None
    retrieval_snapshot: list[dict] | None = None
    traces: list[dict] | None = None


@router.post(
    "/_test/seed-research-run",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_research_update)],
)
async def seed_research_run(
    body: SeedRunRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> V4ApiEnvelope:
    """Seed a complete ResearchRun into a session's workflow_state.

    STRICT: Only active when SEED_TEST_DATA=1 env var is set.
    Used by E2E tests to create runs without executing the full
    LLM workflow pipeline. Never enabled in production.
    """
    if os.environ.get("SEED_TEST_DATA") != "1":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Test-only endpoint disabled",
        )

    # Validate session ownership
    ws = WorkspaceService(db)
    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    run_id = str(uuid4())

    now = datetime.now(UTC).isoformat()
    default_steps = [
        {
            "name": "topic_selection",
            "status": "completed",
            "result": {},
            "trace_ids": [],
        },
        {
            "name": "literature_retrieval",
            "status": "completed",
            "result": {},
            "trace_ids": [],
        },
        {
            "name": "evidence_synthesis",
            "status": "completed",
            "result": {},
            "trace_ids": [],
        },
        {
            "name": "report_generation",
            "status": "completed",
            "result": {},
            "trace_ids": [],
        },
        {
            "name": "citation_export",
            "status": "completed",
            "result": {},
            "trace_ids": [],
        },
    ]

    default_markdown = (
        "# 研究报告：" + body.topic + "\n\n"
        "## 概述\n\n"
        "这是E2E测试生成的研究报告文本。参考 [doc-01:chk-01]。\n\n"
        "## 结论\n\n"
        "研究结论部分内容 [doc-02:chk-02]。\n\n"
        "**这是粗体文字示例。**"
    )

    default_citations = [
        {
            "trace_id": "doc-01:chk-01",
            "citation_text": "甲乙经·经脉篇",
            "document_id": "doc-01",
            "quote": "经络者，所以行血气而营阴阳。",
        },
        {
            "trace_id": "doc-02:chk-02",
            "citation_text": "灵枢·刺节真邪",
            "document_id": "doc-02",
            "quote": "刺之要，气至而有效。",
        },
    ]

    default_snapshot = [
        {
            "trace_id": "doc-01:chk-01",
            "document_id": "doc-01",
            "chunk_id": "chk-01",
            "claim_text": "经络是人体运行气血的通道，负责营养全身。",
            "quote": "经络者，所以行血气而营阴阳，濡筋骨，利关节者也。",
            "citation_text": "甲乙经·经脉篇",
            "source_ref_title": "针灸甲乙经·卷之一",
            "source_ref_url": "https://example.com/jia-yi-jing/1",
            "source_ref_id": "src-ref-001",
        },
        {
            "trace_id": "doc-02:chk-02",
            "document_id": "doc-02",
            "chunk_id": "chk-02",
            "claim_text": "针灸对经络系统有显著调节效果。",
            "quote": "刺之要，气至而有效，效之信，若风之吹云。",
            "citation_text": "灵枢·刺节真邪",
            "source_ref_title": "黄帝内经·灵枢",
            "source_ref_url": "https://example.com/ling-shu/1",
            "source_ref_id": "src-ref-002",
        },
    ]

    default_traces = [
        {
            "trace_id": "doc-01:chk-01",
            "document_id": "doc-01",
            "chunk_id": "chk-01",
            "passage_id": "passage-001",
            "provenance_kind": "retrieval",
            "retrieval_score": 0.95,
            "retrieval_method": "semantic_search",
            "timestamp": now,
        },
        {
            "trace_id": "doc-02:chk-02",
            "document_id": "doc-02",
            "chunk_id": "chk-02",
            "passage_id": "passage-002",
            "provenance_kind": "retrieval",
            "retrieval_score": 0.92,
            "retrieval_method": "semantic_search",
            "timestamp": now,
        },
    ]

    steps = body.step_execution_trace or default_steps
    run_entry = {
        "run_id": run_id,
        "session_id": str(body.session_id),
        "workflow_type": "full_research_flow",
        "topic": body.topic,
        "query_history_binding": [],
        "started_at": now,
        "completed_at": now,
        "step_execution_trace": steps,
        "output_artifacts": {
            "markdown": body.markdown
            if body.markdown is not None
            else default_markdown,
            "title": "研究报告：" + body.topic,
            "artifact_id": str(uuid4()),
            "created_at": now,
            "citations": body.citations
            if body.citations is not None
            else default_citations,
        },
        "replay_manifest": {
            "retrieval_snapshot": body.retrieval_snapshot
            if body.retrieval_snapshot is not None
            else default_snapshot,
            "traces": body.traces if body.traces is not None else default_traces,
        },
    }

    # Persist into session workflow_state
    ResearchWorkflowService(db)
    session_model = await ws.get_session(body.session_id)
    existing_state: dict[str, Any] = {}
    if session_model and session_model.workflow_state:
        try:
            existing_state = json.loads(session_model.workflow_state)
        except (json.JSONDecodeError, TypeError):
            existing_state = {}
    runs: list[dict] = existing_state.get("runs", [])
    runs.append(run_entry)
    session_model.workflow_state = json.dumps({"runs": runs}, ensure_ascii=False)
    # Persist via WorkspaceService.update_session — keeps ORM calls inside
    # the service layer (V4 route files must stay ORM-free).
    await ws.update_session(body.session_id, title=session_model.title)

    return V4ApiEnvelope(
        success=True,
        data={"run_id": run_id, "session_id": str(body.session_id)},
        message="Seeded run for test purposes",
    )
