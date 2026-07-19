"""
Document repository — data access for documents (文献).
"""
from __future__ import annotations

from sqlalchemy import and_, or_, select, func

from app.models.document import Document
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for Document entities."""

    model = Document

    def search_query(
        self,
        query: str,
        page: int = 1,
        limit: int = 20,
        copyright_status: str | None = None,
        review_status: str | None = None,
        rag_enabled: bool | None = None,
        source_name: str | None = None,
    ):
        """Search documents by text query AND optional metadata filters.

        All filters compose with the text search — q and filters are
        combined in a single WHERE clause so total is always accurate.
        """
        conditions = [self.model.is_deleted.is_(False)]

        if query.strip():
            search_fields = ["title", "title_pinyin", "title_english", "abstract", "content_text"]
            search_conditions = [
                getattr(self.model, field).contains(query.strip())
                for field in search_fields
            ]
            conditions.append(or_(*search_conditions))

        if copyright_status:
            conditions.append(self.model.copyright_status == copyright_status)
        if review_status:
            conditions.append(self.model.review_status == review_status)
        if rag_enabled is not None:
            conditions.append(self.model.rag_enabled == rag_enabled)
        if source_name:
            conditions.append(self.model.source_name == source_name)

        where_clause = and_(*conditions)

        stmt = select(self.model).where(where_clause)
        count_stmt = select(func.count()).select_from(
            select(self.model.id).where(where_clause).subquery()
        )

        offset = (page - 1) * limit
        stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(limit)

        items_result = self.session.execute(stmt)
        count_result = self.session.execute(count_stmt)

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def get_by_dynasty(self, dynasty: str, page: int = 1, limit: int = 20):
        """List documents by dynasty."""
        return self.get_all(page=page, limit=limit, order_by=Document.dynasty)
