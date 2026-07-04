"""
TEI persistence models — Sentence, Token, Variant.

P0-5: Formal ORM models for TEI hierarchy with real FK chains.
Version → Passage → Sentence → Token
TextualVariant for structured variant storage.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import String, Text, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class TextSentence(BaseModel):
    """A sentence within a passage — TEI <s> element."""

    __tablename__ = "text_sentences"

    passage_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="FK to passages table"
    )
    order: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="Sentence order within passage"
    )
    text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="Sentence text"
    )
    xml_id: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, comment="TEI xml:id attribute"
    )

    def __repr__(self) -> str:
        return f"<TextSentence order={self.order} text={self.text[:30]!r}>"


class TextToken(BaseModel):
    """A token within a sentence — TEI <w> element."""

    __tablename__ = "text_tokens"

    sentence_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="FK to text_sentences table"
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

    def __repr__(self) -> str:
        return f"<TextToken text={self.text!r} pos={self.pos}>"


class TextualVariant(BaseModel):
    """A textual variant between two versions — TEI <app> element.

    Structured storage, not just diff_data JSON.
    """

    __tablename__ = "textual_variants"

    source_version_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="源版本 ID"
    )
    target_version_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="目标版本 ID"
    )
    source_passage_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="源段落 ID"
    )
    target_passage_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="目标段落 ID"
    )
    source_sentence_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="源句子 ID"
    )
    target_sentence_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="目标句子 ID"
    )
    location: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="异文位置描述"
    )
    lemma: Mapped[Optional[str]] = mapped_column(
        String(200), nullable=True, comment="词条/引理"
    )
    reading: Mapped[str] = mapped_column(
        Text, nullable=False, comment="异文内容"
    )
    variant_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="异文类型: substitution, addition, deletion, transposition"
    )
    apparatus: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="校勘记原文"
    )
    verification_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="unverified", server_default="'unverified'",
        comment="校核状态: unverified, verified, rejected"
    )

    def __repr__(self) -> str:
        return (
            f"<TextualVariant {self.location or '?'} "
            f"reading={self.reading[:30]!r}>"
        )
