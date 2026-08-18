"""
Database connection and session management.

Uses SQLAlchemy 2.0 async engine with connection pooling.

Supports SQLite (for testing) via the DATABASE_URL environment variable.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = get_logger(__name__)

# Allow DATABASE_URL env override for testing with SQLite
_db_url = os.environ.get("DATABASE_URL", settings.database_url)

_engine_kwargs: dict[str, int | bool] = {}
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
    """Verify database connectivity on startup. Creates tables for SQLite.

    SQLite is created via ``Base.metadata.create_all`` (no Alembic), so the
    Phase A0 append-only audit triggers must be installed here explicitly —
    otherwise ``candidate_audit_logs`` would be silently mutable at runtime.
    """
    if _db_url.startswith("sqlite"):
        async with engine.begin() as conn:
            from app.db.base import Base

            await conn.run_sync(Base.metadata.create_all)

            from app.db import audit_triggers

            await audit_triggers.install_audit_log_triggers(conn)

            # Fail-closed verification: the append-only guarantee is only
            # valid if all three triggers are actually present.
            result = await conn.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type='trigger' AND name IN "
                    "('trg_audit_log_no_delete', 'trg_audit_log_no_update', "
                    "'trg_audit_log_no_orphan_insert')"
                )
            )
            installed = {row[0] for row in result}
            expected = {
                "trg_audit_log_no_delete",
                "trg_audit_log_no_update",
                "trg_audit_log_no_orphan_insert",
            }
            if not expected.issubset(installed):
                missing = expected - installed
                logger.error("audit_triggers_missing missing=%s", missing)
                raise RuntimeError(
                    f"CandidateAuditLog append-only triggers failed to install: {missing}"
                )
        logger.info("sqlite_tables_created_triggers_installed")
        return

    try:
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
            # Fail-closed: once the Phase A0 migration has created
            # candidate_audit_logs, the append-only trigger must exist; a
            # dropped/replaced trigger silently breaks the guarantee.
            table_exists = (
                await conn.execute(
                    text("SELECT to_regclass('public.candidate_audit_logs')")
                )
            ).scalar()
            if table_exists:
                result = await conn.execute(
                    text(
                        "SELECT t.tgname FROM pg_trigger t "
                        "JOIN pg_class c ON t.tgrelid = c.oid "
                        "JOIN pg_proc p ON t.tgfoid = p.oid "
                        "WHERE t.tgname='trg_audit_log_immutable' "
                        "AND c.relname='candidate_audit_logs' "
                        "AND p.proname='block_audit_log_changes' "
                        "AND t.tgenabled='O' "
                        "AND NOT t.tgisinternal"
                    )
                )
                installed = {row[0] for row in result}
                if "trg_audit_log_immutable" not in installed:
                    logger.error(
                        "audit_trigger_missing trigger=trg_audit_log_immutable"
                    )
                    raise RuntimeError(
                        "CandidateAuditLog append-only trigger is missing on PostgreSQL"
                    )
        logger.info(
            "database_connected host=%s db=%s",
            settings.POSTGRES_HOST,
            settings.POSTGRES_DB,
        )
    except SQLAlchemyError as e:
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
        except SQLAlchemyError:
            await session.rollback()
            raise


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Dependency: provide the session factory (for explicit DI)."""
    return async_session_factory


async def check_database_health() -> dict[str, Any]:
    """Return database health status."""
    try:
        async with engine.begin() as conn:
            start = __import__("time").time()
            result = await conn.execute(text("SELECT 1"))
            result.fetchone()
            latency_ms = round((__import__("time").time() - start) * 1000, 2)
            return {
                "status": "connected",
                "host": settings.POSTGRES_HOST,
                "port": settings.POSTGRES_PORT,
                "database": settings.POSTGRES_DB,
                "latency_ms": latency_ms,
            }
    except SQLAlchemyError as e:
        return {
            "status": "disconnected",
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB,
            "error": str(e),
        }
