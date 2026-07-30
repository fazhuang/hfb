"""
InstitutionRepository — CRUD + status transitions.

Extends BaseRepository with:
  - transition_status (validates via state machine before writing)
  - soft_delete (sets status=deleted + is_deleted + deleted_at in sync)
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.status_machine import validate_transition
from app.models.institution import Institution, InstitutionStatus
from app.repositories.base import BaseRepository


class InstitutionRepository(BaseRepository[Institution]):
    model = Institution

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        return self.search(
            search_fields=["name", "location", "description"],
            query=query,
            page=page,
            limit=limit,
        )

    # ------------------------------------------------------------------
    # Update — block status bypass
    # ------------------------------------------------------------------

    async def update(self, id, **kwargs):
        """Update fields on an entity. Status changes must go through transition_status."""
        if "status" in kwargs:
            raise ValueError(
                "Direct status updates are forbidden. Use transition_status() "
                "to ensure all transitions go through the state machine."
            )
        return await super().update(id, **kwargs)

    # ------------------------------------------------------------------
    # Status machine integration
    # ------------------------------------------------------------------

    async def transition_status(self, id: UUID | str, target: str) -> Institution:
        """Atomically validate and apply a status transition.

        Raises InvalidStatusTransitionError if the transition is illegal.
        Raises NotFoundError if the institution does not exist.

        Always flushes to the database so constraint violations surface immediately.
        """
        from app.core.exceptions import NotFoundError

        instance = await self.get_by_id(id)
        if instance is None:
            raise NotFoundError("Institution", str(id))

        # validate_transition is also called by the ORM @validates, but we
        # call it here too so the error class is InvalidStatusTransitionError
        # (rather than the ValidationException thrown by @validates).
        validate_transition(instance.status, target)

        instance.status = target
        await self.session.flush()
        return instance

    async def soft_delete(self, id: UUID | str) -> bool:
        """Day 1 soft-delete: sets status=deleted + is_deleted + deleted_at in sync."""
        from app.core.exceptions import NotFoundError

        instance = await self.get_by_id(id)
        if instance is None:
            raise NotFoundError("Institution", str(id))

        instance.status = InstitutionStatus.deleted.value
        instance.is_deleted = True  # type: ignore[assignment]
        instance.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.session.flush()
        return True
