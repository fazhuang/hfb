"""Candidate Extraction Service — Phase A0 facade.

Layering: Controller → ``CandidateExtractionService`` → ``CandidatePublishUnitOfWork``
→ repositories. This facade holds no ``AsyncSession``, opens no transaction, and
touches no repository directly; all persistence lives in ``app.db.candidate_publish_uow``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.db.candidate_publish_uow import CandidatePublishUnitOfWork
from app.db.database import get_session_factory
from app.models.academic_evidence import Evidence


class CandidateExtractionService:
    """Controller-facing service facade for candidate approval."""

    def __init__(self, uow: CandidatePublishUnitOfWork) -> None:
        self._uow = uow

    async def approve(
        self, candidate_id: str, reviewer_id: str, session_id: str
    ) -> Evidence:
        return await self._uow.publish(candidate_id, reviewer_id, session_id)


def get_candidate_extraction_service(
    session_factory: Annotated[
        async_sessionmaker[AsyncSession], Depends(get_session_factory)
    ],
) -> CandidateExtractionService:
    """FastAPI dependency: provide the candidate extraction service."""
    return CandidateExtractionService(CandidatePublishUnitOfWork(session_factory))
