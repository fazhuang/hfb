"""
Document service — business logic for documents (文献).
"""
from __future__ import annotations

from typing import Any

from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentCreate, DocumentResponse
from app.services.base import BaseService


class DocumentService(BaseService[DocumentRepository, DocumentCreate, DocumentResponse]):
    """Service for document operations."""

    repository_class = DocumentRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("title", "").strip():
            raise ValueError("Document title is required")

    async def search(self, query: str, page: int = 1, limit: int = 20):
        return await self.repo.search_query(query, page=page, limit=limit)
