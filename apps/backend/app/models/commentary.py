"""Commentary model — 注疏链 for TCM textual scholarship.

Supports multi-layered self-referential commentary structures:
  注 (annotation) → 疏 (sub-commentary) → 笺 (further elaboration)
Each commentary binds to a passage, optionally to a specific version and
character offset range. Self-referential parent_id enables commentary chains.
"""

from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Commentary(BaseModel):
    """A scholarly annotation/commentary on a passage.

    Supports the full 注疏笺 hierarchy via parent_id self-reference.
    """

    __tablename__ = "commentaries"

    __table_args__ = (
        CheckConstraint(
            "commentary_type IN ('interlinear_gloss', 'end_of_passage', "
            "'sub_commentary', 'commentary_work', 'critique')",
            name="ck_commentaries_type",
        ),
        CheckConstraint(
            "layer IN ('han', 'tang', 'song', 'ming', 'qing', 'modern')",
            name="ck_commentaries_layer",
        ),
        CheckConstraint(
            "relation_type IS NULL OR relation_type IN "
            "('supplements', 'refutes', 'expands', 'annotates', 'interprets')",
            name="ck_commentaries_relation",
        ),
    )

    passage_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("passages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所注段落 ID",
    )
    version_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("versions.id", ondelete="SET NULL"),
        nullable=True,
        comment="所注版本 ID（夹注可能无版本信息）",
    )
    author_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("persons.id", ondelete="SET NULL"),
        nullable=True,
        comment="注者 ID",
    )
    commentary_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="end_of_passage",
        comment="interlinear_gloss | end_of_passage | sub_commentary | commentary_work | critique",
    )
    layer: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="modern",
        comment="年代层: han, tang, song, ming, qing, modern",
    )
    content_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="注文内容",
    )
    target_position_start: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="段落中起始字符偏移"
    )
    target_position_end: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="段落中结束字符偏移"
    )
    parent_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("commentaries.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="自引用 — 回应另一条注疏",
    )
    relation_type: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        comment="supplements | refutes | expands | annotates | interprets",
    )

    def __repr__(self) -> str:
        author = self.author_id[:8] if self.author_id else "?"
        return (
            f"<Commentary type={self.commentary_type} layer={self.layer} by={author}>"
        )
