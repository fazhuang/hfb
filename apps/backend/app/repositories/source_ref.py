"""SourceRef repository — resolution data access for citation persistence."""

from __future__ import annotations

from sqlalchemy import select

from app.models.academic_evidence import SourceRef
from app.repositories.base import BaseRepository


class SourceRefRepository(BaseRepository[SourceRef]):
    """Repository for SourceRef rows."""

    model = SourceRef

    async def resolve_id_for_update(
        self, *, source_uri: str | None, doc_id: str
    ) -> str | None:
        """Resolve a non-deleted SourceRef id, locking it FOR UPDATE.

        Resolution order: by ``url`` (most specific), then by ``page_location``
        (``document:<doc_id>``). Returns the locked id or None.
        """
        if source_uri:
            row = (
                await self.session.execute(
                    select(SourceRef.id)
                    .where(
                        SourceRef.url == source_uri,
                        SourceRef.is_deleted.is_(False),
                    )
                    .with_for_update()
                    .limit(1)
                )
            ).fetchone()
            if row:
                return str(row[0])

        if doc_id:
            row = (
                await self.session.execute(
                    select(SourceRef.id)
                    .where(
                        SourceRef.page_location == f"document:{doc_id}",
                        SourceRef.is_deleted.is_(False),
                    )
                    .with_for_update()
                    .limit(1)
                )
            ).fetchone()
            if row:
                return str(row[0])

        return None
