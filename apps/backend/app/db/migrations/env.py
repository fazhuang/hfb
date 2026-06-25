"""
Alembic environment configuration.

Uses the application's SQLAlchemy async engine and model metadata
to generate migrations automatically.
"""
import asyncio
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
from app.db.base import Base  # noqa: E402, F401
from app.models import Document, Person  # noqa: E402, F401
from app.core.config import settings  # noqa: E402

target_metadata = Base.metadata

# Override sqlalchemy.url from application settings
config.set_main_option("sqlalchemy.url", settings.database_url_sync)


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
    configuration["sqlalchemy.url"] = settings.database_url
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
