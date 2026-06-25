"""
VersionRelation and PassageMapping models.

VersionRelation — models the lineage between versions (derived_from, revised_from, etc.)
PassageMapping — links equivalent passages across different versions.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.version import Version
    from app.models.passage import Passage


class VersionRelation(BaseModel):
    """Records the relationship between two versions — lineage, revision, etc.

    Per HFB-DOM-0803 Ch.9: relation types:
      - derived_from (承袭)
      - revised_from (修订)
      - corrected_by (校勘)
      - annotated_by (注释)
      - compared_with (比较)
      - referenced_by (引用)
    """

    __tablename__ = "version_relations"

    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="源版本 ID",
    )
    target_version_id: Mapped[str] = mapped_column(
        ForeignKey("versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="目标版本 ID",
    )
    relation_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="关系类型: derived_from, revised_from, corrected_by, annotated_by, compared_with, referenced_by",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="关系说明"
    )
    evidence: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="关系依据/证据"
    )

    # Relationships
    source_version: Mapped["Version"] = relationship(
        "Version", foreign_keys=[source_version_id], lazy="selectin"
    )
    target_version: Mapped["Version"] = relationship(
        "Version", foreign_keys=[target_version_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<VersionRelation {self.source_version_id} --[{self.relation_type}]--> {self.target_version_id}>"


class PassageMapping(BaseModel):
    """Maps equivalent passages across different versions.

    Per HFB-DOM-0803 Ch.12: passages must be mappable across versions.
    Supports 1:1, 1:N, N:1 mappings.

    The mapping links a passage in one version to the equivalent passage
    in another version, allowing cross-version reading and comparison.
    """

    __tablename__ = "passage_mappings"

    source_passage_id: Mapped[str] = mapped_column(
        ForeignKey("passages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="源版本中的 Passage ID",
    )
    target_passage_id: Mapped[str] = mapped_column(
        ForeignKey("passages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="目标版本中的 Passage ID",
    )
    mapping_type: Mapped[str] = mapped_column(
        String(50),
        default="equivalent",
        server_default="equivalent",
        nullable=False,
        comment="映射类型: equivalent(等同), variant(异文), missing(缺失), added(新增)",
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="映射说明"
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, comment="是否已校核"
    )

    # Relationships
    source_passage: Mapped["Passage"] = relationship(
        "Passage", foreign_keys=[source_passage_id], lazy="selectin"
    )
    target_passage: Mapped["Passage"] = relationship(
        "Passage", foreign_keys=[target_passage_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PassageMapping {self.source_passage_id} -> {self.target_passage_id} [{self.mapping_type}]>"


class VersionDiff(BaseModel):
    """Stores a pre-computed or manually curated diff between two versions.

    Per HFB-DOM-0803 Ch.13: differences must be structurally stored.
    """

    __tablename__ = "version_diffs"

    source_version_id: Mapped[str] = mapped_column(
        ForeignKey("versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_version_id: Mapped[str] = mapped_column(
        ForeignKey("versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    diff_data: Mapped[str] = mapped_column(
        Text, nullable=False, comment="JSON-encoded diff result"
    )
    diff_summary: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="差异摘要"
    )
    total_differences: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, comment="差异总数"
    )

    def __repr__(self) -> str:
        return f"<VersionDiff {self.source_version_id} vs {self.target_version_id}>"
