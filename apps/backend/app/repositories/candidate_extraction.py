"""CandidateExtraction repository — data access for the Phase A0 pipeline."""

from __future__ import annotations

from sqlalchemy import select

from app.models.candidate_extraction import CandidateExtraction
from app.repositories.base import BaseRepository


class CandidateExtractionRepository(BaseRepository[CandidateExtraction]):
    """Repository for CandidateExtraction rows."""

    model = CandidateExtraction

    async def get_for_update(self, candidate_id: str) -> CandidateExtraction | None:
        """Fetch a candidate with a pessimistic row lock (SELECT ... FOR UPDATE).

        On SQLite the FOR UPDATE clause is a no-op; on PostgreSQL it takes an
        exclusive row lock held until the surrounding transaction commits.
        """
        stmt = (
            select(CandidateExtraction)
            .where(CandidateExtraction.id == candidate_id)
            .with_for_update()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
