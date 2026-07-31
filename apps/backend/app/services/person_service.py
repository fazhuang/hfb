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

    async def search(self, query: str, page: int = 1, limit: int = 20):
        return await self.repo.search_query(query, page=page, limit=limit)

    async def get_by_dynasty(self, dynasty: str, page: int = 1, limit: int = 20):
        return await self.repo.get_by_dynasty(dynasty, page=page, limit=limit)
