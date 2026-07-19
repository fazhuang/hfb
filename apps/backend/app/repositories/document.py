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

    async def search_query(
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
        """Search documents by text query AND optional metadata filters.

        All filters compose with the text search — q and filters are
        combined in a single WHERE clause so total is always accurate.

        When user_id is None, only system/public documents (uploaded_by IS NULL)
        are returned. When user_id is set, documents owned by that user AND
        system/public documents are both included.

        When session_id is set, results are scoped to documents belonging
        to that session/project. session_id IS NULL = public/system docs.
        """
        conditions = [self.model.is_deleted.is_(False)]

        if session_id is not None:
            # Session scope: only docs belonging to the specified session
            conditions.append(self.model.session_id == session_id)
        elif user_id is not None:
            # User scope: show user's own docs + public/system docs (NULL owner)
            conditions.append(
                or_(
                    self.model.uploaded_by == user_id,
                    self.model.uploaded_by.is_(None),
                )
            )
        else:
            # No user context (anonymous): only public/system docs
            conditions.append(self.model.uploaded_by.is_(None))

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
        if dynasty:
            conditions.append(self.model.dynasty == dynasty)
        if category:
            conditions.append(self.model.category == category)

        where_clause = and_(*conditions)

        stmt = select(self.model).where(where_clause)
        count_stmt = select(func.count()).select_from(
            select(self.model.id).where(where_clause).subquery()
        )

        offset = (page - 1) * limit
        stmt = stmt.order_by(Document.created_at.desc()).offset(offset).limit(limit)

        items_result = await self.session.execute(stmt)
        count_result = await self.session.execute(count_stmt)

        return list(items_result.scalars().all()), count_result.scalar_one()

    async def get_by_dynasty(self, dynasty: str, page: int = 1, limit: int = 20):
        """List documents by dynasty."""
        return self.get_all(page=page, limit=limit, order_by=Document.dynasty)
