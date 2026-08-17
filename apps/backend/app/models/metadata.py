"""Metadata — resource-linked metadata record (HFB-DEV-0505 §11).

A minimal, generic metadata table so ``candidate_extractions.metadata_id`` can
carry a real foreign key instead of a dangling string. Each metadata record is
1:1 with a domain resource, referenced by ``(entity_type, entity_id)``.
"""

from __future__ import annotations

from sqlalchemy import JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Metadata(BaseModel):
    """Generic resource metadata (extensibility anchor for Phase A0+)."""

    __tablename__ = "metadata"
    __table_args__ = (
        UniqueConstraint("entity_type", "entity_id", name="uq_metadata_entity"),
    )

    entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="关联实体类型"
    )
    entity_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="关联实体 ID"
    )
    payload: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, comment="元数据 JSON 载荷"
    )

    def __repr__(self) -> str:
        return f"<Metadata id={self.id} {self.entity_type}:{self.entity_id}>"
