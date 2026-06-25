"""
Database connection and session management.

Uses SQLAlchemy 2.0 async engine with connection pooling.

Supports SQLite (for testing) via the DATABASE_URL environment variable.
"""
from __future__ import annotations

import os
from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Allow DATABASE_URL env override for testing with SQLite
_db_url = os.environ.get("DATABASE_URL", settings.database_url)

_engine_kwargs: dict = {}
if _db_url.startswith("postgresql"):
    _engine_kwargs = {"pool_size": 10, "max_overflow": 20, "pool_pre_ping": True}

engine = create_async_engine(
    _db_url,
    echo=settings.DEBUG,
    **_engine_kwargs,
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def init_database() -> None:
    """Verify database connectivity on startup. Creates tables for SQLite."""
    if _db_url.startswith("sqlite"):
        async with engine.begin() as conn:
            from app.db.base import Base
            await conn.run_sync(Base.metadata.create_all)
        logger.info("sqlite_tables_created")
        return

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("database_connected host=%s db=%s", settings.POSTGRES_HOST, settings.POSTGRES_DB)
    except Exception as e:
        logger.error("database_connection_failed error=%s", str(e))
        raise


async def close_database() -> None:
    """Dispose of the database engine on shutdown."""
    await engine.dispose()
    logger.info("database_disposed")


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency: yield an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database_health() -> dict:
    """Return database health status."""
    try:
        async with engine.begin() as conn:
            start = __import__("time").time()
            result = await conn.execute(text("SELECT 1"))
            await result.fetchone()
            latency_ms = round((__import__("time").time() - start) * 1000, 2)
            return {
                "status": "connected",
                "host": settings.POSTGRES_HOST,
                "port": settings.POSTGRES_PORT,
                "database": settings.POSTGRES_DB,
                "latency_ms": latency_ms,
            }
    except Exception as e:
        return {
            "status": "disconnected",
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB,
            "error": str(e),
        }
