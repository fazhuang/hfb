"""Tests for Dashboard service and API."""

from __future__ import annotations

import pytest
from app.models.book import Book
from app.models.person import Person
from app.services.dashboard_service import DashboardService
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


@pytest.mark.asyncio
class TestDashboardService:
    async def test_overview_empty(self, db_session: AsyncSession) -> None:
        svc = DashboardService(db_session)
        overview = await svc.get_overview()
        assert "entity_counts" in overview
        assert "recent_activity" in overview
        assert "system" in overview
        assert overview["system"]["version"] is not None

    async def test_entity_counts(self, db_session: AsyncSession) -> None:
        p = Person(name="统计测试人物", dynasty="唐")
        b = Book(title="统计测试古籍", dynasty="唐", category="医经")
        db_session.add_all([p, b])
        await db_session.flush()

        svc = DashboardService(db_session)
        overview = await svc.get_overview()
        counts = overview["entity_counts"]
        assert counts["persons"] >= 1
        assert counts["books"] >= 1

    async def test_recent_activity(self, db_session: AsyncSession) -> None:
        p = Person(name="活动测试人物", dynasty="宋")
        db_session.add(p)
        await db_session.flush()

        svc = DashboardService(db_session)
        overview = await svc.get_overview()
        activities = overview["recent_activity"]
        assert any("活动测试人物" in a.get("title", "") for a in activities)

    async def test_stats(self, db_session: AsyncSession) -> None:
        p1 = Person(name="唐代人物A", dynasty="唐")
        p2 = Person(name="唐代人物B", dynasty="唐")
        p3 = Person(name="宋代人物", dynasty="宋")
        db_session.add_all([p1, p2, p3])
        await db_session.flush()

        svc = DashboardService(db_session)
        stats = await svc.get_stats()
        assert "dynasty_distribution" in stats
        assert "category_distribution" in stats
        assert "total_entities" in stats

        # Dynasty distribution should have 唐 with count >= 2
        dynasty_map = {d["name"]: d["count"] for d in stats["dynasty_distribution"]}
        assert dynasty_map.get("唐", 0) >= 2
        assert dynasty_map.get("宋", 0) >= 1
