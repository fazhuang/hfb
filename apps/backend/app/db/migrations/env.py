"""
Alembic environment configuration.

Uses the application's SQLAlchemy async engine and model metadata
to generate migrations automatically.
"""

import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config object
config = context.config

# Set up Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import all models so Alembic can detect them
import app.models  # noqa: F401
from app.core.config import settings
from app.db.base import Base
from app.models.version_relation import (  # noqa: F401
    PassageMapping,
    VersionDiff,
    VersionRelation,
)

target_metadata = Base.metadata

# Override sqlalchemy.url from application settings or env
database_url = os.environ.get("DATABASE_URL", settings.database_url)

# Offline/sync URL — strip async drivers for DDL generation
if database_url.startswith("postgresql+asyncpg://"):
    sync_database_url = database_url.replace("+asyncpg", "+psycopg2")
elif database_url.startswith("sqlite+aiosqlite:///"):
    sync_database_url = database_url.replace("+aiosqlite", "")
elif database_url.startswith("sqlite:///"):
    sync_database_url = database_url
else:
    sync_database_url = database_url

config.set_main_option("sqlalchemy.url", sync_database_url)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (generate SQL script)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode (async engine)."""
    configuration = config.get_section(config.config_ini_section, {})
    # Online mode needs async drivers. SQLite URLs from DATABASE_URL may use
    # the sync form (sqlite:///...); convert to aiosqlite for async engine.
    async_url = database_url
    if async_url.startswith("sqlite:///"):
        async_url = async_url.replace("sqlite:///", "sqlite+aiosqlite:///", 1)
    elif async_url.startswith("sqlite+aiosqlite:///"):
        pass  # already correct
    configuration["sqlalchemy.url"] = async_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run async migrations via asyncio."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
