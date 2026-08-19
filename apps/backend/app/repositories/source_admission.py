"""SourceAdmissionEntry repository — data access for the online checklist."""

from __future__ import annotations

from sqlalchemy import select

from app.models.source_admission import SourceAdmissionEntry
from app.repositories.base import BaseRepository


class SourceAdmissionRepository(BaseRepository[SourceAdmissionEntry]):
    """Repository for source-admission checklist entries."""

    model = SourceAdmissionEntry

    async def get_by_entry_key(
        self, entry_key: str
    ) -> SourceAdmissionEntry | None:
        stmt = select(SourceAdmissionEntry).where(
            SourceAdmissionEntry.entry_key == entry_key,
            SourceAdmissionEntry.is_deleted.is_(False),
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def list_active(self) -> list[SourceAdmissionEntry]:
        stmt = (
            select(SourceAdmissionEntry)
            .where(SourceAdmissionEntry.is_deleted.is_(False))
            .order_by(SourceAdmissionEntry.entry_key)
        )
        return list((await self.session.execute(stmt)).scalars().all())
