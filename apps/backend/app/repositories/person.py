"""
Person repository — data access for persons (人物).
"""
from __future__ import annotations

from app.models.person import Person
from app.repositories.base import BaseRepository


class PersonRepository(BaseRepository[Person]):
    """Repository for Person entities."""

    model = Person

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        """Search persons by name, biography, and expertise."""
        return self.search(
            search_fields=["name", "name_pinyin", "name_zh", "biography", "expertise"],
            query=query,
            page=page,
            limit=limit,
        )

    async def get_by_dynasty(self, dynasty: str, page: int = 1, limit: int = 20):
        """List persons by dynasty."""
        from sqlalchemy import func, select

        stmt = select(Person).where(
            Person.dynasty == dynasty,
            Person.is_deleted.is_(False),
        )
        count = select(func.count()).select_from(
            select(Person.id).where(
                Person.dynasty == dynasty,
                Person.is_deleted.is_(False),
            ).subquery()
        )
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        count_result = await self.session.execute(count)
        return list(result.scalars().all()), count_result.scalar_one()
