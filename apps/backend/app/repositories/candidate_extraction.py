"""CandidateExtraction repository — data access for the Phase A0 pipeline.

Owns every data access in the approve-and-publish transaction so the service
layer stays free of direct ``db.execute`` / ``db.add`` / ``db.flush`` calls.
"""

from __future__ import annotations

from sqlalchemy import ColumnElement, func, select

from app.models.academic_evidence import Citation, Evidence
from app.models.candidate_audit_log import CandidateAuditLog
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.passage import Passage
from app.models.workspace import ResearchSession
from app.repositories.base import BaseRepository


class CandidateExtractionRepository(BaseRepository[CandidateExtraction]):
    """Repository for CandidateExtraction + its publish-flow dependencies."""

    model = CandidateExtraction

    async def get_for_update(self, candidate_id: str) -> CandidateExtraction | None:
        """Fetch a candidate with a pessimistic row lock (SELECT ... FOR UPDATE)."""
        stmt = (
            select(CandidateExtraction)
            .where(CandidateExtraction.id == candidate_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_session_for_update(
        self, session_id: str
    ) -> ResearchSession | None:
        stmt = (
            select(ResearchSession)
            .where(ResearchSession.id == session_id)
            .with_for_update()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_chunk_for_update(self, chunk_id: str) -> DocumentChunk | None:
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.id == chunk_id)
            .with_for_update()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_document_for_update(self, document_id: str) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .with_for_update()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def get_passage_for_update(self, passage_id: str) -> Passage | None:
        stmt = (
            select(Passage).where(Passage.id == passage_id).with_for_update()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def create_evidence(self, **kwargs: object) -> Evidence:
        evidence = Evidence(**kwargs)
        self.session.add(evidence)
        await self.session.flush()
        return evidence

    async def create_citation(self, **kwargs: object) -> Citation:
        citation = Citation(**kwargs)
        self.session.add(citation)
        return citation

    async def create_audit_log(self, **kwargs: object) -> CandidateAuditLog:
        audit = CandidateAuditLog(**kwargs)
        self.session.add(audit)
        return audit

    async def list_candidates(
        self,
        page: int = 1,
        limit: int = 20,
        status: CandidateStatus | None = None,
        session_id: str | None = None,
    ) -> tuple[list[CandidateExtraction], int]:
        """Paginated candidate list, optionally filtered by status / session."""
        conditions: list[ColumnElement[bool]] = [
            CandidateExtraction.is_deleted.is_(False)
        ]
        if status is not None:
            conditions.append(CandidateExtraction.status == status)
        if session_id is not None:
            conditions.append(CandidateExtraction.session_id == session_id)

        base_stmt = (
            select(CandidateExtraction)
            .where(*conditions)
            .order_by(CandidateExtraction.created_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
        )
        count_stmt = (
            select(func.count())
            .select_from(CandidateExtraction)
            .where(*conditions)
        )
        items = list((await self.session.execute(base_stmt)).scalars().all())
        total = (await self.session.execute(count_stmt)).scalar_one()
        return items, total

    async def mark_drift(
        self, candidate: CandidateExtraction, operator_id: str, reason: str
    ) -> None:
        """Mark DRIFT_INVALID and write an audit row inside the current transaction."""
        candidate.status = CandidateStatus.DRIFT_INVALID
        await self.create_audit_log(
            candidate_id=candidate.id,
            action="drift_flagged",
            operator_id=operator_id,
            pre_payload=candidate.extracted_payload,
            post_payload={"reason": reason},
        )
