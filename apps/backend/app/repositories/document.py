"""
Document repository — data access for documents (文献).
"""
from __future__ import annotations

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document entities."""

    model = Document

    def search_query(self, query: str, page: int = 1, limit: int = 20):
        """Search documents by title, abstract, and content."""
        return self.search(
            search_fields=["title", "title_pinyin", "title_english", "abstract", "content_text"],
            query=query,
            page=page,
            limit=limit,
        )

    async def get_by_dynasty(self, dynasty: str, page: int = 1, limit: int = 20):
        """List documents by dynasty."""
        return self.get_all(page=page, limit=limit, order_by=Document.dynasty)
