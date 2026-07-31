"""
Dashboard Service — system overview, entity stats, recent activity.

Per MVP Chapter 8 — Dashboard and Admin Panel.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import desc, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.document import Document
from app.models.graph import EntityRelation
from app.models.image import Image
from app.models.paper import Paper
from app.models.passage import Passage
from app.models.person import Person
from app.models.user import User
from app.models.version import Version
from app.models.workspace import ResearchNote, ResearchSession

logger = logging.getLogger(__name__)


class DashboardService:
    """Aggregates platform statistics for the dashboard."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Overview
    # ------------------------------------------------------------------

    async def get_overview(self) -> dict[str, Any]:
        """Return dashboard overview data."""
        counts = await self._entity_counts()
        recent = await self._recent_activity()
        system = await self._system_info()

        return {
            "entity_counts": counts,
            "recent_activity": recent,
            "system": system,
        }

    async def _entity_counts(self) -> dict[str, int]:
        """Count all non-deleted entities."""
        models: dict[str, type] = {
            "persons": Person,
            "books": Book,
            "versions": Version,
            "passages": Passage,
            "papers": Paper,
            "images": Image,
            "documents": Document,
            "users": User,
            "entity_relations": EntityRelation,
        }

        counts: dict[str, int] = {}
        for key, model in models.items():
            stmt = select(func.count()).select_from(
                select(model.id).where(model.is_deleted.is_(False)).subquery()
            )
            result = await self.session.execute(stmt)
            counts[key] = result.scalar_one()

        return counts

    async def _recent_activity(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return recent activity across entities."""
        activities: list[dict[str, Any]] = []

        # Recent books
        stmt = (
            select(Book)
            .where(Book.is_deleted.is_(False))
            .order_by(desc(Book.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        for b in result.scalars().all():
            activities.append(
                {
                    "entity_type": "book",
                    "entity_id": b.id,
                    "title": f"新增古籍《{b.title}》",
                    "timestamp": b.created_at.isoformat() if b.created_at else None,
                }
            )

        # Recent persons
        stmt = (
            select(Person)
            .where(Person.is_deleted.is_(False))
            .order_by(desc(Person.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        for p in result.scalars().all():
            activities.append(
                {
                    "entity_type": "person",
                    "entity_id": p.id,
                    "title": f"新增人物 {p.name}",
                    "timestamp": p.created_at.isoformat() if p.created_at else None,
                }
            )

        # Recent passages
        stmt = (
            select(Passage)
            .where(Passage.is_deleted.is_(False))
            .order_by(desc(Passage.created_at))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        for p in result.scalars().all():
            activities.append(
                {
                    "entity_type": "passage",
                    "entity_id": p.id,
                    "title": f"新增条文 {(p.content_text or '')[:50]}",
                    "timestamp": p.created_at.isoformat() if p.created_at else None,
                }
            )

        # Sort by timestamp descending, limit
        activities.sort(key=lambda a: a["timestamp"] or "", reverse=True)
        return activities[:limit]

    async def _system_info(self) -> dict[str, Any]:
        """Return system-level info."""
        from app.core.config import settings

        sessions_count = 0
        notes_count = 0
        try:
            stmt = select(func.count()).select_from(
                select(ResearchSession.id)
                .where(ResearchSession.is_deleted.is_(False))
                .subquery()
            )
            result = await self.session.execute(stmt)
            sessions_count = result.scalar_one()
        except SQLAlchemyError:
            logger.debug("Failed to count research sessions", exc_info=True)

        try:
            stmt = select(func.count()).select_from(
                select(ResearchNote.id)
                .where(ResearchNote.is_deleted.is_(False))
                .subquery()
            )
            result = await self.session.execute(stmt)
            notes_count = result.scalar_one()
        except SQLAlchemyError:
            logger.debug("Failed to count research notes", exc_info=True)

        return {
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "research_sessions": sessions_count,
            "research_notes": notes_count,
        }

    # ------------------------------------------------------------------
    # Entity stats (for charts)
    # ------------------------------------------------------------------

    async def get_stats(self) -> dict[str, Any]:
        """Return detailed stats for dashboard visualizations."""
        overview = await self.get_overview()
        counts = overview["entity_counts"]

        # Dynasty distribution
        dynasty_counts: dict[str, int] = {}
        stmt = (
            select(Person.dynasty, func.count(Person.id))
            .where(Person.is_deleted.is_(False), Person.dynasty.isnot(None))
            .group_by(Person.dynasty)
        )
        result = await self.session.execute(stmt)
        for dynasty, cnt in result:
            dynasty_counts[dynasty] = cnt

        # Book category distribution
        category_counts: dict[str, int] = {}
        stmt = (
            select(Book.category, func.count(Book.id))
            .where(Book.is_deleted.is_(False), Book.category.isnot(None))
            .group_by(Book.category)
        )
        result = await self.session.execute(stmt)
        for cat, cnt in result:
            category_counts[cat] = cnt

        return {
            "entity_counts": counts,
            "dynasty_distribution": [
                {"name": d, "count": c}
                for d, c in sorted(dynasty_counts.items(), key=lambda x: -x[1])
            ],
            "category_distribution": [
                {"name": c, "count": n}
                for c, n in sorted(category_counts.items(), key=lambda x: -x[1])
            ],
            "total_entities": sum(counts.values()),
        }
