"""
TEI persistence models — Sentence, Token, Variant.

P0-5: Formal ORM models for TEI hierarchy with real FK chains.
Version → Passage → Sentence → Token
TextualVariant for structured variant storage.

All FK references are real ForeignKey columns with ON DELETE CASCADE
where appropriate. DB CHECK constraints enforce domain boundaries.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import (
    String,
    Text,
    Integer,
    ForeignKey,
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import text as sa_text

from app.db.base import BaseModel


class TextSentence(BaseModel):
    """A sentence within a passage — TEI <s> element."""

    __tablename__ = "text_sentences"

    __table_args__ = (
        UniqueConstraint(
            "passage_id",
            "order",
            name="uq_text_sentences_passage_order",
        ),
    )

    passage_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("passages.id", ondelete="CASCADE"),
        nullable=False,
    )
    order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Sentence order within passage"
    )
    text: Mapped[str] = mapped_column(Text, nullable=False, comment="Sentence text")
    xml_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="TEI xml:id attribute"
    )

    # Relationships
    passage: Mapped[object] = relationship("Passage", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TextSentence order={self.order} text={self.text[:30]!r}>"


class TextToken(BaseModel):
    """A token within a sentence — TEI <w> element."""

    __tablename__ = "text_tokens"

    __table_args__ = (
        UniqueConstraint(
            "sentence_id",
            "order",
            name="uq_text_tokens_sentence_order",
        ),
        CheckConstraint(
            "end_offset IS NULL OR start_offset IS NULL OR end_offset >= start_offset",
            name="ck_text_tokens_offsets",
        ),
    )

    sentence_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("text_sentences.id", ondelete="CASCADE"),
        nullable=False,
    )
    order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Token order within sentence"
    )
    text: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="Token surface form"
    )
    lemma: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="Lemma/base form"
    )
    pos: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True, comment="Part of speech tag"
    )
    start_offset: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Character offset start in sentence"
    )
    end_offset: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True, comment="Character offset end in sentence"
    )

    # Relationships
    sentence: Mapped[object] = relationship("TextSentence", lazy="selectin")

    def __repr__(self) -> str:
        return f"<TextToken text={self.text!r} pos={self.pos}>"


class TextualVariant(BaseModel):
    """A textual variant between two versions — TEI <app> element.

    Structured storage, not just diff_data JSON.
    """

    __tablename__ = "textual_variants"

    __table_args__ = (
        CheckConstraint(
            "verification_status IN ('unverified','verified','rejected')",
            name="ck_textual_variants_verification_status",
        ),
        CheckConstraint(
            "variant_type IS NULL OR variant_type IN "
            "('substitution','addition','deletion','transposition')",
            name="ck_textual_variants_variant_type",
        ),
    )

    source_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("versions.id"), nullable=False, comment="源版本 ID"
    )
    target_version_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("versions.id"), nullable=False, comment="目标版本 ID"
    )
    source_passage_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("passages.id"), nullable=True, comment="源段落 ID"
    )
    target_passage_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("passages.id"), nullable=True, comment="目标段落 ID"
    )
    source_sentence_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("text_sentences.id"), nullable=True, comment="源句子 ID"
    )
    target_sentence_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("text_sentences.id"),
        nullable=True,
        comment="目标句子 ID",
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="异文位置描述"
    )
    lemma: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="词条/引理"
    )
    reading: Mapped[str] = mapped_column(Text, nullable=False, comment="异文内容")
    variant_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="异文类型: substitution, addition, deletion, transposition",
    )
    apparatus: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="校勘记原文"
    )
    verification_status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="unverified",
        server_default=sa_text("'unverified'"),
        comment="校核状态: unverified, verified, rejected",
    )

    def __repr__(self) -> str:
        return f"<TextualVariant {self.location or '?'} reading={self.reading[:30]!r}>"
