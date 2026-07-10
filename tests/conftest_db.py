"""
Database testing utilities — in-memory SQLite for unit tests.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base

# Import all models to ensure they are registered on Base.metadata
from app.models import (
    ClassicalVersion,  # noqa: F401
    Document,  # noqa: F401
    DocumentChunk,  # noqa: F401
    Commentary,  # noqa: F401
    Person,  # noqa: F401
    Book,  # noqa: F401
    Chapter,  # noqa: F401
    Image,  # noqa: F401
    Paper,  # noqa: F401
    Passage,  # noqa: F401
    Version,  # noqa: F401
    Permission,  # noqa: F401
    EntityRelation,  # noqa: F401
)
from app.models.institution import Institution  # noqa: F401
from app.models.tcm_entity import TCMEntity  # noqa: F401
from app.models.tei import TextSentence, TextToken, TextualVariant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.version_relation import VersionRelation, PassageMapping, VersionDiff  # noqa: F401
from app.models.workspace import (  # noqa: F401
    ResearchSession,  # noqa: F401
    ResearchNote,  # noqa: F401
    QueryHistory,  # noqa: F401
    CitationCollection,  # noqa: F401
)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory SQLite session for testing.

    Each test gets a fresh database with all tables created.
    Foreign keys are enforced via PRAGMA.
    A default test user is seeded to satisfy FK constraints.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # P0-5: Enforce foreign keys in SQLite
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        # P0-5: pre-seed test user for FK-dependent tests (ResearchSession etc.)
        from app.models.passage import Passage
        from app.models.person import Person as PersonModel
        from app.models.chapter import Chapter
        from app.models.version import Version
        from app.models.book import Book

        # Seed FK chain for Passage-dependent tests (Commentary etc.)
        test_book = Book(id="test-book-1", title="Test Book")
        session.add(test_book)
        await session.flush()
        test_chapter = Chapter(
            id="test-chapter-1", book_id=test_book.id, title="Test Chapter", order=1
        )
        session.add(test_chapter)
        await session.flush()
        test_version = Version(id="test-version-1", book_id=test_book.id, version_name="Test Version")
        session.add(test_version)
        await session.flush()

        for pid in ("pass-test-1", "pass-test-2", "pass-test-3"):
            session.add(Passage(
                id=pid,
                chapter_id=test_chapter.id,
                version_id=test_version.id,
                content_text=f"Passage {pid}",
                order=int(pid[-1]),
            ))
        for pid_obj in ("person-test-1", "person-test-2", "person-test-3"):
            session.add(PersonModel(id=pid_obj, name=f"Person {pid_obj}"))
        await session.flush()
        test_user = User(
            id="test-user-1",
            username="test-user-1",
            email="test@test.com",
            hashed_password="test",
            is_active=True,
            is_superuser=True,
        )
        session.add(test_user)
        await session.flush()

        # P0-3: pre-seed reviewer user + role + permission for verify_relation tests
        from app.models.user import Role, Permission as PermModel
        from app.models.user import user_role as ur_table
        from app.models.user import role_permission as rp_table

        reviewer = User(
            id="test-reviewer",
            username="test-reviewer",
            email="reviewer@test.com",
            hashed_password="test",
            is_active=True,
            is_superuser=False,
        )
        session.add(reviewer)
        await session.flush()

        review_role = Role(
            id="role-reviewer",
            name="Reviewer",
            description="Test reviewer role",
            is_system=True,
        )
        session.add(review_role)
        await session.flush()

        review_perm = PermModel(
            id="perm-graph-review",
            resource="graph",
            action="review",
            description="Review graph evidence",
        )
        session.add(review_perm)
        await session.flush()

        await session.execute(
            ur_table.insert().values(user_id=reviewer.id, role_id=review_role.id)
        )
        await session.execute(
            rp_table.insert().values(
                role_id=review_role.id, permission_id=review_perm.id
            )
        )
        await session.flush()
        yield session

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session_persistent() -> AsyncGenerator[AsyncSession, None]:
    """Create a persistent in-memory SQLite session.

    Tables persist across the test but are cleaned up afterwards.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
