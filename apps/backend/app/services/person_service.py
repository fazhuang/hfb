"""
Person service — business logic for persons (人物).
"""

from __future__ import annotations

from typing import Any

from app.repositories.person import PersonRepository
from app.schemas.person import PersonCreate, PersonResponse
from app.services.base import BaseService


class PersonService(BaseService[PersonRepository, PersonCreate, PersonResponse]):
    """Service for person operations."""

    repository_class = PersonRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("name", "").strip():
            raise ValueError("Person name is required")

    async def search(
        self,
        query: str,
        page: int = 1,
        limit: int = 20,
        include_pending: bool = False,
    ):
        return await self.repo.search_query(
            query, page=page, limit=limit, include_pending=include_pending
        )

    async def get_by_dynasty(
        self,
        dynasty: str,
        page: int = 1,
        limit: int = 20,
        include_pending: bool = False,
    ):
        return await self.repo.get_by_dynasty(
            dynasty, page=page, limit=limit, include_pending=include_pending
        )

    async def list_persons(
        self,
        page: int = 1,
        limit: int = 20,
        q: str = "",
        domain_status: str | None = None,
        research_relation_role: str | None = None,
    ):
        return await self.repo.list_persons(
            page=page,
            limit=limit,
            q=q,
            domain_status=domain_status,
            research_relation_role=research_relation_role,
        )


