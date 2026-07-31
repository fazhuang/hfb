"""
RAG Service — hybrid retrieval and context assembly for AI Research Workspace.

Per HFB-PS-1705 AI Research Workspace Product Specification.

MVP approach:
  - Keyword retrieval: SearchService (ILIKE across entities)
  - Query expansion: build_academic_retrieval_query strips question markers,
    segments around known keywords, and fallback to bigram/trigram extraction
    so natural-language questions actually hit passage content.
  - Context assembly: combines passages, versions, book metadata
  - Citation attachment: auto-tags retrieved sources
  - Vector retrieval: reserved for pgvector integration
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.person import Person
from app.models.version import Version
from app.services.academic_service import build_academic_retrieval_query
from app.services.search_service import ENTITY_CONFIG, SearchParams, SearchService


class RAGService:
    """Retrieval-Augmented Generation context builder.

    Assembles relevant context from the knowledge base to ground
    AI responses in the platform's data.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.search_svc = SearchService(session)

    # ------------------------------------------------------------------
    # Retrieve
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        entity_types: list[str] | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant documents/passages for a query.

        Returns ranked list of context chunks with citation metadata.

        The raw query is first expanded via build_academic_retrieval_query to
        extract searchable keywords (segment around known domain terms, strip
        question markers, fallback to bigram/trigram extraction).  If the
        expanded query yields no results, we retry with the original query so
        that short exact-match queries (e.g. "针灸") still work.
        """
        if entity_types is None:
            entity_types = ["passage", "book", "version", "person"]

        # Expand the natural-language query into searchable keywords
        expanded_q = build_academic_retrieval_query(query)

        for attempt_q in (expanded_q, query):
            if not attempt_q.strip():
                continue
            params = SearchParams(
                q=attempt_q,
                entity_types=entity_types,
                limit=top_k * 2,  # fetch more then trim to top-k
            )
            results = await self.search_svc.search(params)
            if results.items:
                break

        # Build rich context chunks
        chunks: list[dict[str, Any]] = []
        for item in results.items[:top_k]:
            chunk = await self._enrich_result(item)
            if chunk:
                chunks.append(chunk)

        return chunks

    async def _enrich_result(self, item: Any) -> dict[str, Any] | None:
        """Enrich a search result with full entity data for context assembly."""
        entity_type = item.entity_type
        entity_id = item.id

        config = ENTITY_CONFIG.get(entity_type)
        if not config:
            return None

        model = config["model"]
        stmt = (
            __import__("sqlalchemy")
            .select(model)
            .where(
                model.id == entity_id,
                model.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        obj = result.scalar_one_or_none()
        if obj is None:
            return None

        chunk: dict[str, Any] = {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "title": item.title,
            "score": item.score,
        }

        if entity_type == "passage":
            chunk["content"] = getattr(obj, "content_text", "")
            chunk["translation"] = getattr(obj, "translation", "")
            chunk["notes"] = getattr(obj, "notes", "")
            chunk["citation"] = (
                f"《{await self._get_book_title(obj)}》#{getattr(obj, 'order', '')}"
            )
            # Also fetch version info
            ver_id = getattr(obj, "version_id", None)
            if ver_id:
                ver_name = await self._get_version_name(ver_id)
                if ver_name:
                    chunk["version"] = ver_name

        elif entity_type == "book":
            chunk["content"] = getattr(obj, "abstract", "")
            chunk["citation"] = (
                f"《{getattr(obj, 'title', '')}》({getattr(obj, 'dynasty', '')})"
            )
            # Fetch author
            author_id = getattr(obj, "author_id", None)
            if author_id:
                author_name = await self._get_person_name(author_id)
                if author_name:
                    chunk["author"] = author_name

        elif entity_type == "person":
            chunk["content"] = getattr(obj, "biography", "")
            chunk["citation"] = (
                f"{getattr(obj, 'name', '')} ({getattr(obj, 'dynasty', '')})"
            )
            chunk["notable_works"] = getattr(obj, "notable_works", "")

        elif entity_type == "version":
            chunk["content"] = getattr(obj, "description", "")
            chunk["citation"] = (
                f"「{getattr(obj, 'version_name', '')}」({getattr(obj, 'era', '')})"
            )
            chunk["repository"] = getattr(obj, "repository", "")

        return chunk

    # ------------------------------------------------------------------
    # Context assembly
    # ------------------------------------------------------------------

    async def assemble_context(
        self,
        query: str,
        top_k: int = 5,
    ) -> str:
        """Assemble a context string for injection into the AI prompt.

        Includes retrieved chunks with citations.
        """
        chunks = await self.retrieve(query, top_k=top_k)
        if not chunks:
            return ""

        parts: list[str] = []
        for i, chunk in enumerate(chunks, 1):
            entity_type = chunk["entity_type"]
            citation = chunk.get("citation", "")
            content = chunk.get("content", "")

            if not content:
                continue

            block = f"[{i}] ({entity_type}) {citation}"
            if chunk.get("author"):
                block += f" — 作者: {chunk['author']}"
            if chunk.get("version"):
                block += f" — 版本: {chunk['version']}"
            block += f"\n{content[:500]}"  # truncate per chunk

            if chunk.get("translation"):
                block += f"\n现代汉语: {chunk['translation'][:300]}"

            parts.append(block)

        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _get_book_title(self, passage: Any) -> str:
        from sqlalchemy import select as sa_select

        chapter_id = getattr(passage, "chapter_id", None)
        if not chapter_id:
            version_id = getattr(passage, "version_id", None)
            if version_id:
                stmt = sa_select(Version).where(Version.id == version_id)
                r = await self.session.execute(stmt)
                ver = r.scalar_one_or_none()
                if ver:
                    stmt2 = sa_select(Book).where(Book.id == ver.book_id)
                    r2 = await self.session.execute(stmt2)
                    book = r2.scalar_one_or_none()
                    if book:
                        return str(getattr(book, "title", "未知"))

        from app.models.chapter import Chapter

        if chapter_id:
            stmt = sa_select(Chapter).where(Chapter.id == chapter_id)
            r = await self.session.execute(stmt)
            ch = r.scalar_one_or_none()
            if ch:
                stmt2 = sa_select(Book).where(Book.id == ch.book_id)
                r2 = await self.session.execute(stmt2)
                book = r2.scalar_one_or_none()
                if book:
                    return str(getattr(book, "title", "未知"))
        return "未知"

    async def _get_version_name(self, version_id: str) -> str | None:
        from sqlalchemy import select as sa_select

        stmt = sa_select(Version).where(Version.id == version_id)
        r = await self.session.execute(stmt)
        ver = r.scalar_one_or_none()
        return str(getattr(ver, "version_name", "")) if ver else None

    async def _get_person_name(self, person_id: str) -> str | None:
        from sqlalchemy import select as sa_select

        stmt = sa_select(Person).where(Person.id == person_id)
        r = await self.session.execute(stmt)
        p = r.scalar_one_or_none()
        return str(getattr(p, "name", "")) if p else None
