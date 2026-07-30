"""
FulltextIngestionAudit — persistent audit log for full-text ingestion operations.

Context 21: Every full-text ingest, reject, skip, and withdraw action
must produce a durable DB record.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class FulltextIngestionAudit(Base):
    """Persistent audit record for full-text ingestion lifecycle events."""

    __tablename__ = "fulltext_ingestion_audit"

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    # -- What happened --
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="fulltext_ingest | reject | skip | withdraw | chunk_delete | rag_disabled",
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="success",
        comment="success | skipped | rejected | withdrawn",
    )

    # -- Source identity --
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True, comment="来源 URL"
    )
    source_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="摄入来源名称"
    )

    # -- Copyright & authorization --
    copyright_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="版权状态"
    )
    authorization_basis: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="授权依据"
    )
    license_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="许可类型"
    )

    # -- Review --
    review_status: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="审核状态"
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="审核人 user ID"
    )
    reviewed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审核时间"
    )

    # -- Content identity --
    checksum: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="SHA-256 of full-text content"
    )

    # -- Result entity --
    result_entity_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="结果实体类型 (document/chunk/paper)"
    )
    result_entity_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="结果实体 ID"
    )

    # -- Reason --
    reject_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="拒绝/跳过原因"
    )
    skipped_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="跳过原因"
    )

    # -- Actor --
    actor_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="操作人 user ID"
    )

    # -- Extra context --
    details: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="自由格式上下文 (title 等)"
    )
