"""Candidate extraction approval API — Phase A0 evidence-native pipeline."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.db.database import async_session_factory
from app.middleware.auth import get_auth_service, get_current_user, require_permission
from app.services.auth_service import AuthService
from app.services.candidate_extraction_service import (
    GroundingDriftException,
    approve_and_publish_candidate,
)
from app.utils.response import api_response

router = APIRouter(tags=["Candidate Extractions"])


class ApproveCandidateRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=36)


@router.post(
    "/extractions/{candidate_id}/approve",
    response_model=dict,
    dependencies=[Depends(require_permission("extraction", "approve"))],
)
async def approve_candidate(
    candidate_id: str,
    body: ApproveCandidateRequest,
    user_id: Annotated[str, Depends(get_current_user)],
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    """Approve a pending candidate and atomically publish it as Evidence + Citation.

    The RBAC gate runs on the request's shared session (via ``require_permission``
    above); the publish itself runs on a *fresh* session so the single-transaction
    ``db.begin()`` contract is never re-entered by the auth/permission queries.
    """
    # Fetch the reviewer from the auth session — keeps the publish session clean.
    reviewer = await auth_svc.user_repo.get_by_id(user_id)
    if reviewer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )

    async with async_session_factory() as session:
        try:
            evidence = await approve_and_publish_candidate(
                session, candidate_id, reviewer, body.session_id
            )
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
