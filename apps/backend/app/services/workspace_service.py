"""
Workspace Service — research session and note management.

Per HFB-PS-1705 AI Research Workspace Product Specification.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import (
    CitationCollection,
    QueryHistory,
    ResearchNote,
    ResearchSession,
)


class WorkspaceService:
    """Manages research sessions and notes."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Sessions
    # ------------------------------------------------------------------

    async def create_session(self, user_id: str, title: str = "未命名研究") -> ResearchSession:
        session = ResearchSession(user_id=user_id, title=title)
        self.session.add(session)
        await self.session.flush()
        return session

    async def get_session(self, session_id: UUID | str) -> ResearchSession | None:
        stmt = select(ResearchSession).where(
            ResearchSession.id == str(session_id),
            ResearchSession.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sessions(self, user_id: str, limit: int = 20) -> list[ResearchSession]:
        stmt = (
            select(ResearchSession)
            .where(
                ResearchSession.user_id == user_id,
                ResearchSession.is_deleted.is_(False),
            )
            .order_by(ResearchSession.updated_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_session(
        self,
        session_id: UUID | str,
        title: str | None = None,
        active_entities: list[str] | None = None,
        context_notes: str | None = None,
    ) -> ResearchSession | None:
        session = await self.get_session(session_id)
        if session is None:
            return None

        if title is not None:
            session.title = title
        if active_entities is not None:
            session.active_entities = json.dumps(active_entities, ensure_ascii=False)
        if context_notes is not None:
            session.context_notes = context_notes

        session.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.session.flush()
        return session

    async def append_chat_message(
        self,
        session_id: UUID | str,
        role: str,
        content: str,
    ) -> ResearchSession | None:
        session = await self.get_session(session_id)
        if session is None:
            return None

        history: list[dict[str, str]] = []
        if session.chat_history:
            try:
                history = json.loads(session.chat_history)
            except json.JSONDecodeError:
                history = []

        history.append({"role": role, "content": content, "timestamp": datetime.now(UTC).isoformat()})

        # Keep last 100 messages
        if len(history) > 100:
            history = history[-100:]

        session.chat_history = json.dumps(history, ensure_ascii=False)
        session.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.session.flush()
        return session

    async def get_chat_history(self, session_id: UUID | str) -> list[dict[str, str]]:
        session = await self.get_session(session_id)
        if session is None or not session.chat_history:
            return []
        try:
            return json.loads(session.chat_history)
        except json.JSONDecodeError:
            return []

    async def delete_session(self, session_id: UUID | str) -> bool:
        session = await self.get_session(session_id)
        if session is None:
            return False
        session.is_deleted = True  # type: ignore[assignment]
        session.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.session.flush()
        return True

    # ------------------------------------------------------------------
    # Notes
    # ------------------------------------------------------------------

    async def create_note(
        self,
        session_id: UUID | str,
        content: str,
        entity_type: str | None = None,
        entity_id: str | None = None,
        tags: str | None = None,
    ) -> ResearchNote:
        note = ResearchNote(
            session_id=str(session_id),
            content=content,
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id else None,
            tags=tags,
        )
        self.session.add(note)
        await self.session.flush()
        return note

    async def list_notes(
        self, session_id: UUID | str, limit: int = 50
    ) -> list[ResearchNote]:
        stmt = (
            select(ResearchNote)
            .where(
                ResearchNote.session_id == str(session_id),
                ResearchNote.is_deleted.is_(False),
            )
            .order_by(ResearchNote.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_note(
        self, note_id: UUID | str, content: str | None = None, tags: str | None = None
    ) -> ResearchNote | None:
        stmt = select(ResearchNote).where(ResearchNote.id == str(note_id), ResearchNote.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        note = result.scalar_one_or_none()
        if note is None:
            return None

        if content is not None:
            note.content = content
        if tags is not None:
            note.tags = tags

        note.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.session.flush()
        return note

    async def delete_note(self, note_id: UUID | str) -> bool:
        stmt = select(ResearchNote).where(ResearchNote.id == str(note_id), ResearchNote.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        note = result.scalar_one_or_none()
        if note is None:
            return False
        note.is_deleted = True  # type: ignore[assignment]
        note.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await self.session.flush()
        return True

    async def get_note_with_session(
        self, note_id: UUID | str
    ) -> tuple[ResearchNote, ResearchSession] | None:
        """Get a note with its parent session for ownership verification."""
        stmt = (
            select(ResearchNote, ResearchSession)
            .join(ResearchSession, ResearchNote.session_id == ResearchSession.id)
            .where(
                ResearchNote.id == str(note_id),
                ResearchNote.is_deleted.is_(False),
            )
        )
        result = await self.session.execute(stmt)
        row = result.one_or_none()
        return row if row else None

    # ------------------------------------------------------------------
    # QueryHistory — V4 product layer
    # ------------------------------------------------------------------

    async def create_query_history(
        self,
        session_id: UUID | str,
        query_text: str,
        query_type: str,
        result_summary: str | None = None,
        citation_count: int = 0,
    ) -> QueryHistory:
        qh = QueryHistory(
            session_id=str(session_id),
            query_text=query_text,
            query_type=query_type,
            result_summary=result_summary,
            citation_count=citation_count,
        )
        self.session.add(qh)
        await self.session.flush()
        return qh

    async def get_query_history(
        self, session_id: UUID | str, limit: int = 50
    ) -> list[QueryHistory]:
        stmt = (
            select(QueryHistory)
            .where(QueryHistory.session_id == str(session_id))
            .order_by(QueryHistory.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    # ------------------------------------------------------------------
    # CitationCollection — V4 product layer
    # ------------------------------------------------------------------

    async def create_citation(
        self,
        session_id: UUID | str,
        trace_json: str,
        citation_text: str,
        source_document: str,
        tags: str | None = None,
        notes: str | None = None,
    ) -> CitationCollection:
        cc = CitationCollection(
            session_id=str(session_id),
            trace_json=trace_json,
            citation_text=citation_text,
            source_document=source_document,
            tags=tags,
            notes=notes,
        )
        self.session.add(cc)
        await self.session.flush()
        return cc

    async def list_citations(
        self, session_id: UUID | str, limit: int = 100
    ) -> list[CitationCollection]:
        stmt = (
            select(CitationCollection)
            .where(CitationCollection.session_id == str(session_id))
            .order_by(CitationCollection.created_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_citation(self, citation_id: UUID | str) -> CitationCollection | None:
        """Get a citation by ID for ownership verification."""
        stmt = select(CitationCollection).where(
            CitationCollection.id == str(citation_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_citation(
        self,
        citation_id: UUID | str,
        tags: str | None = None,
        notes: str | None = None,
    ) -> CitationCollection | None:
        stmt = select(CitationCollection).where(
            CitationCollection.id == str(citation_id)
        )
        result = await self.session.execute(stmt)
        citation = result.scalar_one_or_none()
        if citation is None:
            return None
        if tags is not None:
            citation.tags = tags
        if notes is not None:
            citation.notes = notes
        await self.session.flush()
        return citation

    async def delete_citation(self, citation_id: UUID | str) -> bool:
        stmt = select(CitationCollection).where(
            CitationCollection.id == str(citation_id)
        )
        result = await self.session.execute(stmt)
        citation = result.scalar_one_or_none()
        if citation is None:
            return False
        await self.session.delete(citation)
        await self.session.flush()
        return True
