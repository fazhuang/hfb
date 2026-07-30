"""AcademicEdge -- read-only ORM mapping for the academic_edges SQL view.

Filters entity_relations to academically citeable edges:
  evidence_level >= 2 AND evidence_status = 'verified' AND is_deleted = 0.
"""

from __future__ import annotations

from datetime import datetime
from typing import ClassVar

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AcademicEdge(Base):
    """Read-only mapping for academic_edges view.

    Not a BaseModel subclass -- this is a SQL view, so there is no PK
    generation, no writes, and no soft-delete defaults.  The id column is
    read from the underlying entity_relations.id.
    """

    __tablename__ = "academic_edges"
    __table_args__: ClassVar[tuple] = ({"extend_existing": True},)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    source_entity_type: Mapped[str] = mapped_column(String(50))
    source_entity_id: Mapped[str] = mapped_column(String(36))
    target_entity_type: Mapped[str] = mapped_column(String(50))
    target_entity_id: Mapped[str] = mapped_column(String(36))
    relation_type: Mapped[str] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_document_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    evidence_chunk_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    evidence_quote: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_citation: Mapped[str | None] = mapped_column(
        String(200), nullable=True
    )
    evidence_version_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    evidence_passage_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True
    )
    evidence_source_uri: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )
    evidence_status: Mapped[str] = mapped_column(String(20))
    claim_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    evidence_level: Mapped[int] = mapped_column(Integer)
    confidence_score: Mapped[float] = mapped_column(Float)
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    is_deleted: Mapped[bool] = mapped_column(default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
