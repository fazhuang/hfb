"""
Document service — business logic for documents (文献).
"""

from __future__ import annotations

from typing import Any

from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentCreate, DocumentResponse
from app.services.base import BaseService


class DocumentService(
    BaseService[DocumentRepository, DocumentCreate, DocumentResponse]
):
    """Service for document operations."""

    repository_class = DocumentRepository

    async def _validate_create(self, data: dict[str, Any]) -> None:
        if not data.get("title", "").strip():
            raise ValueError("Document title is required")

    async def search(
        self,
        query: str,
        page: int = 1,
        limit: int = 20,
        copyright_status: str | None = None,
        review_status: str | None = None,
        rag_enabled: bool | None = None,
        source_name: str | None = None,
        dynasty: str | None = None,
        category: str | None = None,
        user_id: str | None = None,
        session_id: str | None = None,
    ):
        """Search documents by text query AND optional metadata filters."""
        return await self.repo.search_query(
            query,
            page=page,
            limit=limit,
            copyright_status=copyright_status,
            review_status=review_status,
            rag_enabled=rag_enabled,
            source_name=source_name,
            dynasty=dynasty,
            category=category,
            user_id=user_id,
            session_id=session_id,
        )
