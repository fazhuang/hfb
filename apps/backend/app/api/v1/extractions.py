"""Candidate extraction approval API — Phase A0 evidence-native pipeline."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.middleware.auth import get_current_user, require_permission
from app.services.candidate_extraction_service import (
    CandidateExtractionService,
    GroundingDriftException,
    get_candidate_extraction_service,
)
from app.utils.response import api_response

router = APIRouter(tags=["Candidate Extractions"])


class ApproveCandidateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=36)


@router.post(
    "/extractions/{candidate_id}/approve",
    response_model=dict[str, Any],
    dependencies=[Depends(require_permission("extraction", "approve"))],
)
async def approve_candidate(
    candidate_id: str,
    body: ApproveCandidateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[
        CandidateExtractionService, Depends(get_candidate_extraction_service)
    ],
) -> dict[str, Any]:
    """Approve a pending candidate and atomically publish it as Evidence + Citation.

    RBAC runs via ``require_permission``; session/transaction management lives in
    ``CandidateExtractionService`` (the controller never touches a session or
    repository).
    """
    try:
        evidence = await service.approve(candidate_id, user_id, body.session_id)
    except GroundingDriftException as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"GROUNDING_DRIFT: {exc}",
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return api_response(
        data={"evidence_id": evidence.id},
        message="Candidate approved and published",
    )
