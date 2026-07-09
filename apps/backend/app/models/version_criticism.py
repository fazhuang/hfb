"""
Version Criticism (版本学) domain models.

Includes Sentence, Token, and Variant for precise textual collation.
"""
from __future__ import annotations
from typing import TYPE_CHECKING, Optional, List
import enum

from sqlalchemy import String, Integer, Text, ForeignKey, Enum, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.passage import Passage


class Sentence(BaseModel):
    """断句。细化到句层级以便于校勘比对。"""
    __tablename__ = "sentences"

    passage_id: Mapped[str] = mapped_column(
        ForeignKey("passages.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属段落 ID"
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False, comment="句子内容")
    order: Mapped[int] = mapped_column(Integer, nullable=False, comment="句子在段落内的序号")

    # 关系
    passage: Mapped[Passage] = relationship("Passage", back_populates="sentences")
    tokens: Mapped[List[Token]] = relationship("Token", back_populates="sentence", cascade="all, delete-orphan")


class Token(BaseModel):
    """字/词词元。用于古籍版本之间异文（Variant）的精确锚定。"""
    __tablename__ = "tokens"
    __table_args__ = (
        Index("idx_token_lookup", "sentence_id", "position"),
    )

    sentence_id: Mapped[str] = mapped_column(
        ForeignKey("sentences.id", ondelete="CASCADE"), nullable=False, comment="所属断句 ID"
    )
    char_text: Mapped[str] = mapped_column(String(50), nullable=False, comment="单个汉字或核心词")
    position: Mapped[int] = mapped_column(Integer, nullable=False, comment="字/词在句中的绝对位置索引")

    # 关系
    sentence: Mapped[Sentence] = relationship("Sentence", back_populates="tokens")
    variants_as_base: Mapped[list[Variant]] = relationship(
        "Variant", foreign_keys="Variant.base_token_id", back_populates="base_token",
        lazy="selectin",
    )
    variants_as_compare: Mapped[list[Variant]] = relationship(
        "Variant", foreign_keys="Variant.compare_token_id", back_populates="compare_token",
        lazy="selectin",
    )


class VariantType(str, enum.Enum):
    SUBSTITUTION = "substitution"  # 字异（字形/通假字/形似错漏，如 阳 ↔ 阴）
    OMISSION = "omission"          # 脱文（对比本较基准本有缺失）
    INSERTION = "insertion"        # 增文（对比本较基准本多出文字）
    TRANSPOSITION = "transposition"# 倒置（相邻文字顺序错乱，如 针刺 ↔ 刺针）
    CORRUPTION = "corruption"      # 讹误（字义完全损坏不可考）


class Variant(BaseModel):
    """异文记录。记录版本 A 与版本 B 之间字词的差异。"""
    __tablename__ = "variants"

    base_token_id: Mapped[str] = mapped_column(
        ForeignKey("tokens.id", ondelete="CASCADE"), nullable=False, index=True, comment="基准版本的Token ID"
    )
    compare_token_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("tokens.id", ondelete="CASCADE"), nullable=True, index=True, comment="比对版本的Token ID"
    )
    variant_type: Mapped[VariantType] = mapped_column(Enum(VariantType), nullable=False, comment="异文类型")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="校勘记/校勘说明")

    # 关系
    base_token: Mapped[Token] = relationship("Token", foreign_keys=[base_token_id], back_populates="variants_as_base")
    compare_token: Mapped[Optional[Token]] = relationship("Token", foreign_keys=[compare_token_id], back_populates="variants_as_compare")
