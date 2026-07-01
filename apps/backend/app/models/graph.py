"""
EntityRelation model for the Knowledge Graph — Sprint 3 P0 hardened.

Every non-FK explicit relation must carry structured corpus evidence:
  evidence_document_id, evidence_chunk_id, evidence_quote, evidence_citation.
Free-text 'evidence' column is deprecated and ignored by graph queries
unless the structured fields are also populated and valid.

Self-loops are rejected unless relation_type allows them.
Duplicate (source_type, source_id, target_type, target_id, relation_type)
are rejected or idempotently returned.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


# Valid entity types for the graph
GRAPH_ENTITY_TYPES = {"person", "book", "version", "passage"}

# Valid explicit relation types (cross-entity, user-curated)
GRAPH_RELATION_TYPES = {
    "authored",
    "compiled",
    "commented_on",
    "cited_in",
    "studied",
    "compared",
    "referenced",
    "related_to",
}

# Relation types that explicitly allow self-loops
SELF_LOOP_ALLOWED_TYPES: set[str] = set()


class EntityRelation(BaseModel):
    """A curated relationship between any two graph entities — Sprint 3 P0.

    Every explicit relation MUST carry structured corpus evidence:
      evidence_document_id, evidence_chunk_id, evidence_quote, evidence_citation.
    FK-derived and VersionRelation edges are computed at query time.
    """

    __tablename__ = "entity_relations"
    __table_args__ = (
        Index(
            "ix_entity_relations_dedup",
            "source_entity_type",
            "source_entity_id",
            "target_entity_type",
            "target_entity_id",
            "relation_type",
            unique=False,
        ),
    )

    source_entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="源实体类型"
    )
    source_entity_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="源实体 ID"
    )
    target_entity_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True, comment="目标实体类型"
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="目标实体 ID"
    )
    relation_type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="关系类型"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="关系说明"
    )
    # Deprecated free-text evidence — kept for backward compat, NOT used in P0 validation
    evidence: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="[DEPRECATED] 自由文本证据 — 不再用于验证"
    )
    # Sprint 3 P0: structured corpus evidence
    evidence_document_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="证据来源 document ID"
    )
    evidence_chunk_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="证据来源 chunk ID"
    )
    evidence_quote: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="chunk 中的确切引用文本"
    )
    evidence_citation: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="格式化引用 [document_id:chunk_id]"
    )

    def __repr__(self) -> str:
        return (
            f"<EntityRelation {self.source_entity_type}:{self.source_entity_id[:8]}"
            f" --[{self.relation_type}]--> "
            f"{self.target_entity_type}:{self.target_entity_id[:8]}>"
        )
