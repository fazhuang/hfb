"""
EntityRelation model for the Knowledge Graph.

Stores explicit relationships between entities of any type.
Auto-derived FK relations (book→author, passage→version, etc.)
are computed at query time by the GraphService without being stored here.

Entity types: person, book, version, passage
Relation types for cross-entity: authored, compiled, commented_on, cited_in,
  studied, compared, referenced, related_to
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


# Valid entity types for the graph
GRAPH_ENTITY_TYPES = {"person", "book", "version", "passage"}

# Valid explicit relation types (cross-entity, user-curated)
GRAPH_RELATION_TYPES = {
    "authored",        # Person → Book   (作者)
    "compiled",        # Person → Book   (编撰)
    "commented_on",    # Person → Book/Version (注释)
    "cited_in",        # Book/Passage → Book/Passage (引用)
    "studied",         # Person → Book/Passage (研究)
    "compared",        # Version → Version (比较，also in VersionRelation)
    "referenced",      # Entity → Entity (参考)
    "related_to",      # Entity → Entity (一般关联)
}


class EntityRelation(BaseModel):
    """A curated relationship between any two graph entities.

    Differs from VersionRelation (which is version-to-version only) —
    this table handles any entity-type pair plus the version pairs already
    captured in version_relations.

    For the MVP, version-to-version relations are still read from
    version_relations alongside entity_relations; the combined set
    forms the full graph.
    """

    __tablename__ = "entity_relations"

    source_entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="源实体类型: person, book, version, passage",
    )
    source_entity_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="源实体 ID",
    )
    target_entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="目标实体类型: person, book, version, passage",
    )
    target_entity_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        index=True,
        comment="目标实体 ID",
    )
    relation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="关系类型: authored, compiled, commented_on, cited_in, studied, compared, referenced, related_to",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="关系说明"
    )
    evidence: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="关系依据/证据"
    )

    def __repr__(self) -> str:
        return (
            f"<EntityRelation {self.source_entity_type}:{self.source_entity_id[:8]}"
            f" --[{self.relation_type}]--> "
            f"{self.target_entity_type}:{self.target_entity_id[:8]}>"
        )
