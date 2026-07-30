"""
Test deduplication logic for literature ingestion.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from app.db.base import Base
from app.models.paper import Paper
from app.services.literature_ingestion import LiteratureItem, filter_new_items
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


class TestFilterNewItems:
    @pytest.mark.asyncio
    async def test_all_new_when_db_empty(self, db_session: AsyncSession):
        items = [
            LiteratureItem(
                title="Paper A",
                source="openalex",
                source_url="https://a.example",
                doi="10.1000/a",
                year=2023,
            ),
            LiteratureItem(
                title="Paper B",
                source="crossref",
                source_url="https://b.example",
                year=2023,
            ),
        ]
        result = await filter_new_items(db_session, items)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_doi_duplicate_filtered(self, db_session: AsyncSession):
        existing = Paper(
            title="Existing Paper",
            doi="10.1000/existing",
            year=2022,
            source_url="https://existing.example",
        )
        db_session.add(existing)
        await db_session.flush()

        items = [
            LiteratureItem(
                title="Re-discovered Paper",
                source="openalex",
                source_url="https://new.example",
                doi="10.1000/existing",
                year=2022,
            ),
        ]
        result = await filter_new_items(db_session, items)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_title_year_duplicate_filtered(self, db_session: AsyncSession):
        existing = Paper(
            title="针灸甲乙经研究",
            year=2019,
            source_url="https://existing.example",
        )
        db_session.add(existing)
        await db_session.flush()

        items = [
            LiteratureItem(
                title="针灸甲乙经研究",
                source="pubmed",
                source_url="https://new.example",
                year=2019,
            ),
        ]
        result = await filter_new_items(db_session, items)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_mixed_new_and_duplicate(self, db_session: AsyncSession):
        existing = Paper(
            title="Old Paper",
            doi="10.1000/old",
            year=2020,
            source_url="https://old.example",
        )
        db_session.add(existing)
        await db_session.flush()

        items = [
            LiteratureItem(
                title="Old Paper",
                source="openalex",
                source_url="https://a.example",
                doi="10.1000/old",
                year=2020,
            ),
            LiteratureItem(
                title="New Paper",
                source="crossref",
                source_url="https://b.example",
                doi="10.1000/new",
                year=2024,
            ),
        ]
        result = await filter_new_items(db_session, items)
        assert len(result) == 1
        assert result[0].title == "New Paper"

    @pytest.mark.asyncio
    async def test_empty_list_returns_empty(self, db_session: AsyncSession):
        result = await filter_new_items(db_session, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_doi_case_insensitive_match(self, db_session: AsyncSession):
        existing = Paper(
            title="Case Test",
            doi="10.1000/CaseSensitive",
            year=2021,
            source_url="https://existing.example",
        )
        db_session.add(existing)
        await db_session.flush()

        items = [
            LiteratureItem(
                title="Case Test",
                source="openalex",
                source_url="https://new.example",
                doi="10.1000/casesensitive",
                year=2021,
            ),
        ]
        result = await filter_new_items(db_session, items)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_title_year_case_insensitive_dedup(self, db_session: AsyncSession):
        """DB dedup must be case-insensitive for non-DOI records."""
        existing = Paper(
            title="ZHENJIU JIAYI JING",
            year=2019,
            source_url="https://existing.example",
        )
        db_session.add(existing)
        await db_session.flush()

        items = [
            LiteratureItem(
                title="zhenjiu jiayi jing",
                source="pubmed",
                source_url="https://new.example",
                year=2019,
            ),
        ]
        result = await filter_new_items(db_session, items)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_title_year_whitespace_insensitive_dedup(self, db_session: AsyncSession):
        """DB dedup must be whitespace-insensitive for non-DOI records."""
        existing = Paper(
            title="Huangfu Mi Study",
            year=2018,
            source_url="https://existing.example",
        )
        db_session.add(existing)
        await db_session.flush()

        items = [
            LiteratureItem(
                title="  Huangfu   Mi   Study  ",
                source="core",
                source_url="https://new.example",
                year=2018,
            ),
        ]
        result = await filter_new_items(db_session, items)
        assert len(result) == 0


class TestCrossSourceDedup:
    """Same paper from different sources should dedup to one record."""

    def test_same_doi_different_sources_same_key(self):
        a = LiteratureItem(
            title="A Study",
            source="openalex",
            source_url="https://oa.example/1",
            doi="10.1000/shared",
            year=2023,
        )
        b = LiteratureItem(
            title="A Study",
            source="crossref",
            source_url="https://cr.example/1",
            doi="10.1000/shared",
            year=2023,
        )
        assert a.dedup_key() == b.dedup_key()

    def test_no_doi_same_title_year_same_key(self):
        a = LiteratureItem(
            title="黄帝内经考",
            source="pubmed",
            source_url="https://pm.example/1",
            year=2020,
        )
        b = LiteratureItem(
            title="黄帝内经考",
            source="core",
            source_url="https://core.example/1",
            year=2020,
        )
        assert a.dedup_key() == b.dedup_key()

    def test_title_case_insensitive_dedup(self):
        """Titles differing only in case should produce same dedup key."""
        a = LiteratureItem(
            title="Zhenjiu Jiayi Jing",
            source="openalex",
            source_url="https://oa.example/1",
            year=2019,
        )
        b = LiteratureItem(
            title="ZHENJIU JIAYI JING",
            source="crossref",
            source_url="https://cr.example/1",
            year=2019,
        )
        assert a.dedup_key() == b.dedup_key()

    def test_title_whitespace_insensitive_dedup(self):
        """Leading/trailing/multiple whitespace should be normalized."""
        a = LiteratureItem(
            title="  Huangfu Mi  Study  ",
            source="openalex",
            source_url="https://oa.example/1",
            year=2020,
        )
        b = LiteratureItem(
            title="huangfu mi study",
            source="pubmed",
            source_url="https://pm.example/1",
            year=2020,
        )
        assert a.dedup_key() == b.dedup_key()
