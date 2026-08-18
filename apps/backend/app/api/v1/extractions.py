"""Candidate extraction approval API — Phase A0 evidence-native pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.core.exceptions import ValidationException
from app.db.candidate_publish_uow import GroundingDriftException
from app.middleware.auth import get_current_user, require_permission
from app.services.candidate_extraction_service import (
    CandidateExtractionService,
    get_candidate_extraction_service,
)

router = APIRouter(tags=["Candidate Extractions"])


class ApproveCandidateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=36)


class ApprovalData(BaseModel):
    evidence_id: str


class ApprovalResponse(BaseModel):
    success: bool
    timestamp: str
    data: ApprovalData
    message: str


@router.post(
    "/extractions/{candidate_id}/approval",
    response_model=ApprovalResponse,
    dependencies=[Depends(require_permission("extraction", "approve"))],
)
async def approve_candidate(
    candidate_id: str,
    body: ApproveCandidateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[
        CandidateExtractionService, Depends(get_candidate_extraction_service)
    ],
) -> ApprovalResponse:
    """Approve a pending candidate and atomically publish it as Evidence + Citation.

    RBAC runs via ``require_permission``; session/transaction management lives in
    ``CandidateExtractionService`` (the controller never touches a session or
    repository).
    """
    try:
        evidence = await service.approve(candidate_id, user_id, body.session_id)
    except GroundingDriftException:
        # Domain exception (409 GROUNDING_DRIFT) → handled by the global handler.
        raise
    except RuntimeError as exc:
        raise ValidationException(str(exc))

    return ApprovalResponse(
        success=True,
        timestamp=datetime.now(UTC).isoformat(),
        data=ApprovalData(evidence_id=evidence.id),
        message="Candidate approved and published",
    )
