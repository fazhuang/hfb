"""Version repository — version validity data access."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select

from app.models.version import Version
from app.repositories.base import BaseRepository


class VersionRepository(BaseRepository[Version]):
    """Repository for Version rows."""

    model = Version

    async def get_withdrawn_at_for_update(
        self, version_id: str
    ) -> tuple[datetime | None] | None:
        """Return the locked ``withdrawn_at`` of a non-deleted version.

        Returns ``None`` when the version does not exist or is soft-deleted
        (fail-closed signal for callers). Otherwise returns a one-element row
        ``(withdrawn_at,)`` where a non-NULL value means the version is withdrawn.
        """
        row = (
            await self.session.execute(
                select(Version.withdrawn_at)
                .where(Version.id == version_id, Version.is_deleted.is_(False))
                .with_for_update()
            )
        ).fetchone()
        return row  # type: ignore[return-value]
