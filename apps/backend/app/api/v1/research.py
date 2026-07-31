"""Research workflow API."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.services.research_workflow_service import ResearchWorkflowService
from app.services.workspace_service import WorkspaceService
from app.utils.response import api_response

router = APIRouter(prefix="/research", tags=["Research Workflow"])

guard_research_read = require_permission("research", "read")
guard_research_update = require_permission("research", "update")
guard_research_export = require_permission("research", "export")


class VersionComparisonRequest(BaseModel):
    source_passage_id: UUID
    target_passage_id: UUID


@router.put(
    "/sessions/{session_id}/version-comparison",
    response_model=dict,
    dependencies=[Depends(guard_research_update)],
)
async def configure_version_comparison(
    session_id: UUID,
    body: VersionComparisonRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> dict:
    await _require_owned_session(session, session_id, current_user)
    workflow = ResearchWorkflowService(session)
    try:
        result = await workflow.configure_version_comparison(
            session_id,
            body.source_passage_id,
            body.target_passage_id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return api_response(data=result, message="Version comparison configured")


@router.get(
    "/sessions/{session_id}/version-comparison",
    response_model=dict,
    dependencies=[Depends(guard_research_read)],
)
async def get_version_comparison(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> dict:
    await _require_owned_session(session, session_id, current_user)
    result = await ResearchWorkflowService(session).get_version_comparison(session_id)
    # Return null data instead of 404 — the session exists and belongs
    # to the caller; "no comparison yet" is a valid state, not an error.
    return api_response(data=result)


@router.get(
    "/sessions/{session_id}/export",
    dependencies=[Depends(guard_research_export)],
)
async def export_research_record(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> Response:
    await _require_owned_session(session, session_id, current_user)
    try:
        markdown = await ResearchWorkflowService(session).export_markdown(session_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return Response(
        content=markdown,
        media_type="text/markdown",
        headers={
            "Content-Disposition": (
                f'attachment; filename="hfb-research-record-{session_id}.md"'
            )
        },
    )


async def _require_owned_session(
    db_session: AsyncSession,
    session_id: UUID,
    current_user: str,
) -> None:
    research_session = await WorkspaceService(db_session).get_session(session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research session not found",
        )
