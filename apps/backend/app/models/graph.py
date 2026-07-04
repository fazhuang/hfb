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


# Canonical entity types for the graph (ontology-aligned)
GRAPH_ENTITY_TYPES = {
    "person",
    "book",
    "version",
    "passage",
    "text",  # classical text / 经典文献
    "herb",  # herb / 草药
    "prescription",  # prescription / 方剂
    "meridian",  # meridian / 经络
    "symptom",  # symptom / 症候
}

# Ontology: which entity types can appear as source for a relation
ONTOLOGY_SOURCE_TYPES: dict[str, set[str]] = {
    "authored": {"person"},
    "compiled": {"person"},
    "commented_on": {"person"},
    "cited_in": {"person", "book", "version", "passage", "text"},
    "studied": {"person"},
    "compared": {"person", "book", "version"},
    "referenced": {"person", "book", "version", "passage", "text"},
    "related_to": {
        "person",
        "book",
        "version",
        "passage",
        "text",
        "herb",
        "prescription",
        "meridian",
        "symptom",
    },
    "contains": {"book", "text", "version", "prescription"},
    "treats": {"prescription", "herb"},
    "corresponds_to": {"meridian", "herb"},
}

# Ontology: which entity types can appear as target for a relation
ONTOLOGY_TARGET_TYPES: dict[str, set[str]] = {
    "authored": {"book", "text"},
    "compiled": {"book", "text"},
    "commented_on": {"book", "text"},
    "cited_in": {"person", "book", "version", "passage", "text"},
    "studied": {"book", "text", "person", "prescription", "herb"},
    "compared": {"book", "version", "text"},
    "referenced": {"person", "book", "version", "passage", "text"},
    "related_to": {
        "person",
        "book",
        "version",
        "passage",
        "text",
        "herb",
        "prescription",
        "meridian",
        "symptom",
    },
    "contains": {"passage", "prescription", "herb", "symptom"},
    "treats": {"symptom"},
    "corresponds_to": {"meridian", "herb"},
}

# Valid explicit relation types (cross-entity, user-curated)
GRAPH_RELATION_TYPES = set(ONTOLOGY_SOURCE_TYPES.keys()) | {
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
    # ponytail: the active-only unique constraint is managed entirely by
    # alembic migration 9c710fa2d3f0 (partial index WHERE is_deleted=0).
    # We keep a non-unique ORM index for query performance only.
    __table_args__ = (
        Index(
            "ix_entity_relations_lookup",
            "source_entity_type",
            "source_entity_id",
            "target_entity_type",
            "target_entity_id",
            "relation_type",
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
