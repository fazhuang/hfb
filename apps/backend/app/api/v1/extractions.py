"""Candidate extraction API — Phase A0 create + review pipeline."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.db.candidate_publish_uow import GroundingDriftException
from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.models.candidate_extraction import CandidateStatus
from app.repositories.candidate_extraction import CandidateExtractionRepository
from app.schemas.candidate import (
    CandidateListResponse,
    CandidateResponse,
    CreateCandidateRequest,
)
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


class CreateCandidateData(BaseModel):
    candidate_id: str


class CreateCandidateResponse(BaseModel):
    success: bool
    timestamp: str
    data: CreateCandidateData
    message: str


@router.post(
    "/extractions",
    response_model=CreateCandidateResponse,
    status_code=201,
    dependencies=[Depends(require_permission("extraction", "create"))],
)
async def create_candidate(
    body: CreateCandidateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[
        CandidateExtractionService, Depends(get_candidate_extraction_service)
    ],
) -> CreateCandidateResponse:
    """Buffer an AI/rule extraction as a PENDING candidate.

    Ownership + grounding anchors are validated server-side in one transaction;
    a candidate whose anchors do not match the live chunk is rejected (422).
    """
    try:
        candidate = await service.create(body, user_id)
    except NotFoundException:
        raise
    except ValidationException:
        raise
    except RuntimeError as exc:
        raise ValidationException(str(exc))

    return CreateCandidateResponse(
        success=True,
        timestamp=datetime.now(UTC).isoformat(),
        data=CreateCandidateData(candidate_id=candidate.id),
        message="Candidate buffered for review",
    )


@router.get(
    "/extractions",
    response_model=CandidateListResponse,
    dependencies=[Depends(require_permission("extraction", "read"))],
)
async def list_candidates(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status: Annotated[CandidateStatus | None, Query()] = None,
    session_id: Annotated[str | None, Query(max_length=36)] = None,
) -> CandidateListResponse:
    """Paginated candidate list for the review queue."""
    repo = CandidateExtractionRepository(session)
    items, total = await repo.list_candidates(
        page=page, limit=limit, status=status, session_id=session_id
    )
    return CandidateListResponse(
        items=[CandidateResponse.model_validate(i) for i in items],
        total=total,
        page=page,
        limit=limit,
    )


@router.get(
    "/extractions/{candidate_id}",
    response_model=CandidateResponse,
    dependencies=[Depends(require_permission("extraction", "read"))],
)
async def get_candidate(
    candidate_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> CandidateResponse:
    """Fetch a single candidate by id."""
    repo = CandidateExtractionRepository(session)
    candidate = await repo.get_by_id(candidate_id)
    if candidate is None:
        raise NotFoundException("CandidateExtraction", candidate_id)
    return CandidateResponse.model_validate(candidate)


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
    repository for the write path).
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


class RejectCandidateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=36)
    reason: str = Field(..., min_length=1, max_length=2000)


class RejectCandidateResponse(BaseModel):
    success: bool
    timestamp: str
    data: dict[str, str]
    message: str


@router.post(
    "/extractions/{candidate_id}/rejection",
    response_model=RejectCandidateResponse,
    dependencies=[Depends(require_permission("extraction", "approve"))],
)
async def reject_candidate(
    candidate_id: str,
    body: RejectCandidateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    service: Annotated[
        CandidateExtractionService, Depends(get_candidate_extraction_service)
    ],
) -> RejectCandidateResponse:
    """Reject a pending candidate (session-owner self-review)."""
    try:
        await service.reject(candidate_id, user_id, body.session_id, body.reason)
    except NotFoundException:
        raise
    except RuntimeError as exc:
        raise ValidationException(str(exc))

    return RejectCandidateResponse(
        success=True,
        timestamp=datetime.now(UTC).isoformat(),
        data={"candidate_id": candidate_id},
        message="Candidate rejected",
    )
