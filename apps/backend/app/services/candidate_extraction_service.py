"""Candidate Extraction Service — Phase A0 facade.

Layering: Controller → ``CandidateExtractionService`` → UoW → repositories.
This facade holds no ``AsyncSession``, opens no transaction, and touches no
repository directly; all persistence lives in ``app.db`` unit-of-work modules
(``candidate_create_uow`` for buffering extractions, ``candidate_publish_uow``
for the human-review publish path).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.candidate_create_uow import CandidateCreateUnitOfWork
from app.db.candidate_publish_uow import CandidatePublishUnitOfWork
from app.db.database import get_session_factory
from app.models.academic_evidence import Evidence
from app.models.candidate_extraction import CandidateExtraction
from app.schemas.candidate import CreateCandidateRequest


class CandidateExtractionService:
    """Controller-facing service facade for candidate create + approval."""

    def __init__(
        self,
        create_uow: CandidateCreateUnitOfWork,
        publish_uow: CandidatePublishUnitOfWork,
    ) -> None:
        self._create_uow = create_uow
        self._publish_uow = publish_uow

    async def create(
        self, request: CreateCandidateRequest, user_id: str
    ) -> CandidateExtraction:
        """Buffer an AI/rule extraction as a PENDING candidate.

        Ownership + grounding are validated inside a single transaction before
        the candidate is accepted; invalid anchors are rejected at creation.
        """
        return await self._create_uow.create(request, user_id)

    async def approve(
        self, candidate_id: str, reviewer_id: str, session_id: str
    ) -> Evidence:
        return await self._publish_uow.publish(candidate_id, reviewer_id, session_id)

    async def reject(
        self, candidate_id: str, reviewer_id: str, session_id: str, reason: str
    ) -> None:
        return await self._publish_uow.reject(
            candidate_id, reviewer_id, session_id, reason
        )


def get_candidate_extraction_service(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_session_factory)
    ],
) -> CandidateExtractionService:
    """FastAPI dependency: provide the candidate extraction service."""
    return CandidateExtractionService(
        CandidateCreateUnitOfWork(session_factory),
        CandidatePublishUnitOfWork(session_factory),
    )
