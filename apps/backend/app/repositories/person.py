"""
Person repository — data access for persons (人物).
"""

from __future__ import annotations

from app.models.person import Person
from app.repositories.base import BaseRepository


class PersonRepository(BaseRepository[Person]):
    """Repository for Person entities."""

    model = Person

    async def search_query(
        self,
        query: str,
        page: int = 1,
        limit: int = 20,
        include_pending: bool = False,
    ) -> tuple[list[Person], int]:
        """Search persons by name, biography, and expertise."""
        from sqlalchemy import and_, func, or_, select

        search_fields = ["name", "name_pinyin", "name_zh", "biography", "expertise"]
        conditions = [
            getattr(Person, field).contains(query) for field in search_fields
        ]

        where_conditions = [or_(*conditions), Person.is_deleted.is_(False)]
        if not include_pending:
            where_conditions.append(Person.domain_status == "verified")

        where_clause = and_(*where_conditions)

        stmt = select(Person).where(where_clause)
        count_stmt = select(func.count()).select_from(
            select(Person.id).where(where_clause).subquery()
        )

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        items_result = await self.session.execute(stmt)
        count_result = await self.session.execute(count_stmt)

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def get_by_dynasty(
        self,
        dynasty: str,
        page: int = 1,
        limit: int = 20,
        include_pending: bool = False,
    ) -> tuple[list[Person], int]:
        """List persons by dynasty."""
        from sqlalchemy import and_, func, select

        conditions = [
            Person.dynasty == dynasty,
            Person.is_deleted.is_(False),
        ]
        if not include_pending:
            conditions.append(Person.domain_status == "verified")

        where_clause = and_(*conditions)

        stmt = select(Person).where(where_clause)
        count = select(func.count()).select_from(
            select(Person.id).where(where_clause).subquery()
        )
        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        result = await self.session.execute(stmt)
        count_result = await self.session.execute(count)
        return list(result.scalars().all()), count_result.scalar_one()

    async def list_persons(
        self,
        page: int = 1,
        limit: int = 20,
        q: str = "",
        domain_status: str | None = None,
        research_relation_role: str | None = None,
    ) -> tuple[list[Person], int]:
        """List persons with optional search query, domain status, and research relation role filters."""
        from sqlalchemy import and_, func, or_, select

        conditions = [Person.is_deleted.is_(False)]

        if domain_status and domain_status != "all":
            conditions.append(Person.domain_status == domain_status)
        if research_relation_role and research_relation_role != "all":
            roles = [r.strip() for r in research_relation_role.split(",") if r.strip()]
            if len(roles) == 1:
                conditions.append(Person.research_relation_role == roles[0])
            elif len(roles) > 1:
                conditions.append(Person.research_relation_role.in_(roles))

        if q and q.strip():
            query_str = q.strip()
            search_fields = [
                "name",
                "name_pinyin",
                "name_zh",
                "biography",
                "expertise",
                "domain_relation_summary",
            ]
            conditions.append(
                or_(*[getattr(Person, field).contains(query_str) for field in search_fields])
            )

        where_clause = and_(*conditions)

        stmt = select(Person).where(where_clause).order_by(Person.created_at.desc())
        count_stmt = select(func.count()).select_from(
            select(Person.id).where(where_clause).subquery()
        )

        offset = (page - 1) * limit
        stmt = stmt.offset(offset).limit(limit)

        items_result = await self.session.execute(stmt)
        count_result = await self.session.execute(count_stmt)

        return list(items_result.scalars().all()), count_result.scalar_one()


