"""
Tests for repository layer using in-memory SQLite.

Requires: pytest-asyncio, aiosqlite
"""

import pytest
from app.repositories.document import DocumentRepository
from app.repositories.person import PersonRepository
from sqlalchemy.ext.asyncio import AsyncSession

# Import conftest_db fixtures (must be imported — conftest_db.py is not auto-discovered)
from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


def _id() -> str:
    """Generate a fixed test UUID."""
    import uuid

    return str(uuid.uuid4())


class TestDocumentRepository:
    """Test DocumentRepository with in-memory SQLite."""

    @pytest.mark.asyncio
    async def test_create_and_get(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        doc = await repo.create(
            title="针灸甲乙经",
            dynasty="西晋",
            category="针灸",
            language="zh",
        )
        assert doc.id is not None
        assert doc.title == "针灸甲乙经"

        fetched = await repo.get_by_id(doc.id)
        assert fetched is not None
        assert fetched.title == "针灸甲乙经"

    @pytest.mark.asyncio
    async def test_get_by_id_excludes_soft_deleted(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        doc = await repo.create(title="Test", language="zh")
        await repo.soft_delete(doc.id)

        result = await repo.get_by_id(doc.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_all_paginated(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        for i in range(25):
            await repo.create(title=f"Document {i}", language="zh")

        items, total = await repo.get_all(page=1, limit=10)
        assert len(items) == 10
        assert total == 25

        items2, _ = await repo.get_all(page=3, limit=10)
        assert len(items2) == 5  # last page has 5

    @pytest.mark.asyncio
    async def test_search(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        await repo.create(title="针灸甲乙经", language="zh")
        await repo.create(title="本草纲目", language="zh")
        await repo.create(title="伤寒杂病论", language="zh")

        items, total = await repo.search_query("针灸")
        assert total == 1
        assert items[0].title == "针灸甲乙经"

    @pytest.mark.asyncio
    async def test_soft_delete(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        doc = await repo.create(title="Test", language="zh")

        ok = await repo.soft_delete(doc.id)
        assert ok is True

        result = await repo.get_by_id(doc.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_hard_delete(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        doc = await repo.create(title="Test", language="zh")

        ok = await repo.hard_delete(doc.id)
        assert ok is True

    @pytest.mark.asyncio
    async def test_update(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        doc = await repo.create(title="Old Title", language="zh")

        updated = await repo.update(doc.id, title="New Title", year=282)
        assert updated is not None
        assert updated.title == "New Title"
        assert updated.year == 282

    @pytest.mark.asyncio
    async def test_count(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        for i in range(5):
            await repo.create(title=f"D{i}", language="zh")

        c = await repo.count()
        assert c == 5


class TestPersonRepository:
    """Test PersonRepository."""

    @pytest.mark.asyncio
    async def test_create_and_search(self, db_session: AsyncSession):
        repo = PersonRepository(db_session)
        await repo.create(name="皇甫谧", dynasty="西晋", birth_year=215)
        await repo.create(name="张仲景", dynasty="东汉", birth_year=150)
        await repo.create(name="李时珍", dynasty="明", birth_year=1518)

        items, total = await repo.search_query("皇甫")
        assert total == 1
        assert items[0].name == "皇甫谧"

    @pytest.mark.asyncio
    async def test_get_by_dynasty(self, db_session: AsyncSession):
        repo = PersonRepository(db_session)
        await repo.create(name="皇甫谧", dynasty="西晋", birth_year=215)
        await repo.create(name="张仲景", dynasty="东汉", birth_year=150)
        await repo.create(name="李时珍", dynasty="明", birth_year=1518)
        await repo.create(name="扁鹊", dynasty="东汉", birth_year=None)

        _items, total = await repo.get_by_dynasty("东汉")
        assert total == 2


class TestBaseRepository:
    """Test generic BaseRepository operations."""

    @pytest.mark.asyncio
    async def test_exists(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        doc = await repo.create(title="Test", language="zh")

        assert await repo.exists(doc.id) is True
        assert await repo.exists("00000000-0000-0000-0000-000000000000") is False

    @pytest.mark.asyncio
    async def test_soft_delete_idempotent(self, db_session: AsyncSession):
        repo = DocumentRepository(db_session)
        doc = await repo.create(title="Test", language="zh")

        await repo.soft_delete(doc.id)
        ok2 = await repo.soft_delete(doc.id)
        # Second soft-delete finds no non-deleted record → returns False
        assert ok2 is False
