"""V4 Research Portal API — session, query, workflow endpoints.

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
        trace_ids = [t.chunk_id for t in result.evidence_trace]
        qh = await ws.create_query_history(
            session_id=research_session.id,
            query_text=body.query,
            query_type="research",
            result_summary=json.dumps({
                "trace_ids": trace_ids,
                "citation_count": len(result.citations),
                "source_documents": list({t.document_id for t in result.evidence_trace}),
            }, ensure_ascii=False),
            citation_count=len(result.citations),
        )
        traceability = V4TraceabilityBlock(
            query_id=qh.id,
            trace_ids=trace_ids,
            citation_count=len(result.citations),
            source_documents=list({t.document_id for t in result.evidence_trace}),
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

    # Verify session exists and is owned
    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    # Route to appropriate service
    if body.mode == "graph":
        gs = GraphService(db)
        result = await gs.intelligence(query=body.query)
        trace_ids = []  # graph intelligence uses entity-based trace
        citations = []
        source_docs = []
    else:
        academic = AcademicService(db)
        mode_map = {
            "report": academic.generate_report,
            "synthesis": academic.synthesize,
            "research": academic.research,
            "education": academic.educate,
        }
        handler = mode_map[body.mode]
        # For report mode, we need report_type; default to research_summary
        if body.mode == "report":
            result = await academic.generate_report(
                query=body.query, report_type="research_summary"
            )
        else:
            result = await handler(query=body.query)  # type: ignore[operator]
        trace_ids = [t.chunk_id for t in result.evidence_trace]
        citations = [c.model_dump() for c in result.citations]
        source_docs = list({t.document_id for t in result.evidence_trace})

    # Record query history
    qh = await ws.create_query_history(
        session_id=body.session_id,
        query_text=body.query,
        query_type=body.mode,
        result_summary=json.dumps({
            "trace_ids": trace_ids,
            "citation_count": len(citations),
            "source_documents": source_docs,
        }, ensure_ascii=False),
        citation_count=len(citations),
    )

    traceability = V4TraceabilityBlock(
        query_id=qh.id,
        trace_ids=trace_ids,
        citation_count=len(citations),
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
    """Execute a 5-step research workflow. Each step is traceable.

    Produces a ResearchRun (logical entity) stored in session.workflow_state.
    Session != Execution — one session can hold multiple runs.
    """
    ws = WorkspaceService(db)
    research_session = await ws.get_session(body.session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    run_id = str(uuid4())
    academic = AcademicService(db)
    steps: list[V4WorkflowStep] = []
    all_trace_ids: list[str] = []
    all_source_docs: list[str] = []

    for i, step_name in enumerate(FULL_RESEARCH_FLOW):
        try:
            if step_name == "topic_selection":
                # Step 1: Decompose topic into research questions
                result = await academic.research(query=body.topic)
                step_result = {"topic": body.topic, "sub_questions": len(result.decomposition)}
                step_trace = [t.chunk_id for t in result.evidence_trace]
                step_docs = list({t.document_id for t in result.evidence_trace})

            elif step_name == "literature_retrieval":
                # Step 2: Broader synthesis
                result = await academic.synthesize(query=body.topic)
                step_result = {"themes": len(result.themes), "claims": len(result.evidence_trace)}
                step_trace = [t.chunk_id for t in result.evidence_trace]
                step_docs = list({t.document_id for t in result.evidence_trace})

            elif step_name == "evidence_synthesis":
                # Step 3: Generate report to synthesize
                result = await academic.generate_report(
                    query=body.topic, report_type="thematic_analysis"
                )
                step_result = {"sections": len(result.sections), "claims": len(result.evidence_trace)}
                step_trace = [t.chunk_id for t in result.evidence_trace]
                step_docs = list({t.document_id for t in result.evidence_trace})

            elif step_name == "report_generation":
                # Step 4: Full academic report
                result = await academic.generate_report(
                    query=body.topic, report_type="research_summary"
                )
                step_result = {"sections": len(result.sections), "title": result.title}
                step_trace = [t.chunk_id for t in result.evidence_trace]
                step_docs = list({t.document_id for t in result.evidence_trace})

            elif step_name == "citation_export":
                # Step 5: Collect all citations from previous steps
                all_citations = list(set(all_trace_ids))
                step_result = {"total_citations": len(all_citations), "citations": all_citations}
                step_trace = all_citations
                step_docs = all_source_docs
                # Record final query history for export step
                await ws.create_query_history(
                    session_id=body.session_id,
                    query_text=body.topic,
                    query_type="workflow_export",
                    result_summary=json.dumps({
                        "trace_ids": all_citations,
                        "source_documents": all_source_docs,
                    }, ensure_ascii=False),
                    citation_count=len(all_citations),
                )

            all_trace_ids.extend(step_trace)
            all_source_docs.extend(step_docs)

            await ws.create_query_history(
                session_id=body.session_id,
                query_text=f"[workflow step] {step_name}: {body.topic}",
                query_type="workflow_step",
                result_summary=json.dumps({
                    "step": step_name,
                    "trace_ids": step_trace,
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
            steps.append(V4WorkflowStep(
                name=step_name,
                status="failed",
                result={"error": "Workflow step encountered an internal error"},
                trace_ids=[],
            ))

    # Persist ResearchRun in workflow_state
    existing_state = {}
    if research_session.workflow_state:
        try:
            existing_state = json.loads(research_session.workflow_state)
        except (json.JSONDecodeError, TypeError):
            existing_state = {}

    runs = existing_state.get("runs", [])
    runs.append({
        "run_id": run_id,
        "session_id": body.session_id,
        "topic": body.topic,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "steps": [s.model_dump() for s in steps],
    })
    existing_state["runs"] = runs
    research_session.workflow_state = json.dumps(existing_state, ensure_ascii=False)
    research_session.updated_at = datetime.now(timezone.utc)  # type: ignore[assignment]
    await db.flush()

    traceability = V4TraceabilityBlock(
        query_id=run_id,
        trace_ids=list(set(all_trace_ids)),
        citation_count=len(all_trace_ids),
        source_documents=list(set(all_source_docs)),
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
