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
    Document,     # noqa: F401
    DocumentChunk,  # noqa: F401
    Person,   # noqa: F401
    Book,     # noqa: F401
    Chapter,  # noqa: F401
    Image,    # noqa: F401
    Paper,    # noqa: F401
    Passage,  # noqa: F401
    Version,  # noqa: F401
    Permission,  # noqa: F401
    EntityRelation,  # noqa: F401
)
from app.models.version_relation import VersionRelation, PassageMapping, VersionDiff  # noqa: F401
from app.models.workspace import ResearchSession, ResearchNote, QueryHistory, CitationCollection  # noqa: F401


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create an in-memory SQLite session for testing.

    Each test gets a fresh database with all tables created.
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
