"""
Base model with UUID primary key, timestamps, and soft-delete support.

Uses a portable UUID type that works with both PostgreSQL and SQLite.
"""

from __future__ import annotations

import os
import uuid as _uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def uuid7() -> str:
    """Return a time-ordered UUIDv7 (RFC 9562) as a 36-char string.

    Layout: 48-bit unix-ms timestamp | 4-bit version (7) | 12-bit rand_a |
    2-bit variant (2) | 62-bit rand_b.
    """
    ts_ms = int(datetime.now(UTC).timestamp() * 1000) & 0xFFFFFFFFFFFF  # 48 bits
    rand = os.urandom(10)  # 80 random bits
    rand_a = int.from_bytes(rand[:2], "big") & 0x0FFF  # 12 bits
    rand_b = int.from_bytes(rand[2:], "big") & 0x3FFFFFFFFFFFFFFF  # 62 bits
    value = (ts_ms << 80) | (0x7 << 76) | (rand_a << 64) | (0x2 << 62) | rand_b
    return str(_uuid.UUID(int=value))


class Base(DeclarativeBase):
    """Base class for all database models."""


class TimestampMixin:
    """Mixin adding created_at and updated_at timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )


class SoftDeleteMixin:
    """Mixin adding soft-delete support."""

    deleted_at: Mapped[datetime | None] = mapped_column(
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
        default=uuid7,
    )
