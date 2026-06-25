"""
Base model with UUID primary key, timestamps, and soft-delete support.

Uses a portable UUID type that works with both PostgreSQL and SQLite.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


class TimestampMixin:
    """Mixin adding created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin adding soft-delete support."""

    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        server_default=None,
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )


class BaseModel(Base, TimestampMixin, SoftDeleteMixin):
    """Concrete base model with UUID PK, timestamps, and soft-delete fields.

    Uses String(36) for the UUID primary key to be portable across
    PostgreSQL and SQLite backends. PostgreSQL will use a native UUID
    type in production; the string representation is equivalent.
    """

    __abstract__ = True

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
