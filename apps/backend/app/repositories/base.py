"""
Base repository with common CRUD operations.

All entity repositories inherit from this base.
"""
from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import func, select, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository for CRUD operations."""

    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Create
    # ------------------------------------------------------------------

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get_by_id(self, id: UUID | str) -> ModelT | None:
        """Get by UUID primary key (excludes soft-deleted)."""
        normalized_id = str(id)
        stmt = select(self.model).where(
            self.model.id == normalized_id,
            self.model.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(
        self,
        page: int = 1,
        limit: int = 20,
        order_by: Any = None,
    ) -> tuple[list[ModelT], int]:
        """Paginated list (excludes soft-deleted).

        Returns (items, total_count).
        """
        base_stmt = select(self.model).where(self.model.is_deleted.is_(False))
        count_stmt = select(func.count()).select_from(
            select(self.model.id).where(self.model.is_deleted.is_(False)).subquery()
        )

        if order_by is not None:
            base_stmt = base_stmt.order_by(order_by)

        offset = (page - 1) * limit
        base_stmt = base_stmt.offset(offset).limit(limit)

        items_result = await self.session.execute(base_stmt)
        count_result = await self.session.execute(count_stmt)

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def exists(self, id: UUID | str) -> bool:
        """Check if entity exists (non-deleted)."""
        normalized_id = str(id)
        stmt = select(self.model.id).where(
            self.model.id == normalized_id,
            self.model.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        """Count non-deleted records."""
        stmt = select(func.count()).select_from(
            select(self.model.id).where(self.model.is_deleted.is_(False)).subquery()
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    async def search(
        self,
        search_fields: list[str],
        query: str,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[list[ModelT], int]:
        """Full-text search across given columns (LIKE with contains)."""
        from sqlalchemy import and_, or_

        conditions = [
            getattr(self.model, field).contains(query) for field in search_fields
        ]
        where_clause = and_(
            or_(*conditions),
            self.model.is_deleted.is_(False),
        )

        stmt = select(self.model).where(where_clause)
        count_stmt = select(func.count()).select_from(
            select(self.model.id).where(where_clause).subquery()
        )

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        items_result = await self.session.execute(stmt)
        count_result = await self.session.execute(count_stmt)

        return list(items_result.scalars().all()), count_result.scalar_one()

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    async def update(self, id: UUID | str, **kwargs: Any) -> ModelT | None:
        """Update fields on an existing entity."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        await self.session.flush()
        return instance

    # ------------------------------------------------------------------
    # Delete (Soft)
    # ------------------------------------------------------------------

    async def soft_delete(self, id: UUID | str) -> bool:
        """Soft-delete an entity (sets is_deleted = True)."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        from datetime import datetime, timezone

        instance.is_deleted = True  # type: ignore[assignment]
        instance.deleted_at = datetime.now(timezone.utc)  # type: ignore[assignment]
        await self.session.flush()
        return True

    async def hard_delete(self, id: UUID | str) -> bool:
        """Permanently delete an entity."""
        stmt = sa_delete(self.model).where(self.model.id == str(id))
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
