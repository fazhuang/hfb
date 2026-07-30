"""
Generic service base with validation hooks.
"""
from __future__ import annotations

from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.base import BaseRepository

Repo = TypeVar("Repo", bound=BaseRepository[Any])
SchemaCreate = TypeVar("SchemaCreate")
SchemaResponse = TypeVar("SchemaResponse")


class BaseService[Repo: BaseRepository[Any], SchemaCreate, SchemaResponse]:
    """Generic service layer with validation hooks.

    Subclasses override _validate_create / _validate_update
    to add business rules without touching repositories.
    """

    repository_class: type[Repo]

    def __init__(self, session: AsyncSession) -> None:
        self.repo = self.repository_class(session)
        self.session = session

    # ------------------------------------------------------------------
    # Validation hooks (override in subclasses)
    # ------------------------------------------------------------------

    async def _validate_create(self, data: dict[str, Any]) -> None:
        """Raise ValueError if create data is invalid."""
        return

    async def _validate_update(self, id: UUID, data: dict[str, Any]) -> None:
        """Raise ValueError if update data is invalid."""
        return

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, schema: SchemaCreate) -> Any:
        data = schema.model_dump(exclude_unset=True)
        await self._validate_create(data)
        return await self.repo.create(**data)

    async def get_by_id(self, id: UUID) -> Any | None:
        return await self.repo.get_by_id(id)

    async def list(self, page: int = 1, limit: int = 20) -> tuple[list[Any], int]:
        return await self.repo.get_all(page=page, limit=limit)

    async def update(self, id: UUID, schema: SchemaCreate) -> Any | None:
        data = schema.model_dump(exclude_unset=True)
        await self._validate_update(id, data)
        return await self.repo.update(id, **data)

    async def soft_delete(self, id: UUID) -> bool:
        return await self.repo.soft_delete(id)

    async def hard_delete(self, id: UUID) -> bool:
        return await self.repo.hard_delete(id)
