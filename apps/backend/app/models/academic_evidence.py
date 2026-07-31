"""
Academic Evidence & Citation domain models.

Provides SourceRef, Evidence, and Citation structures to anchor academic claims.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.passage import Passage


class EvidenceLevel(int, enum.Enum):
    LEVEL_1 = 1  # 一手出土文献实物（如马王堆帛书、五代竹简等）
    LEVEL_2 = 2  # 传世最早善本/宋刻本（校勘直接物理证据，如宋刻《针灸甲乙经》）
    LEVEL_3 = 3  # 历代正史、经典医学文献注疏（如《外台秘要》、《千金要方》等转引）
    LEVEL_4 = 4  # 现代学术论著、考证推理、词频网络计量分析


class SourceRef(BaseModel):
    """物理引文参考。证明某段话或某个异文存在的外部出版物/实物出处。"""

    __tablename__ = "source_refs"

    title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="物理书名/文献名/论文名"
    )
    author: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="作者/编校者"
    )
    edition_info: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="版本信息/出版社/刊刻年代"
    )
    page_location: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="文献内的定位：卷/页/行/栏"
    )
    url: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="数字化链接/古籍库链接"
    )


class Evidence(BaseModel):
    """学术论据证据。每一条论据均挂载在一个置信度级别上，并绑定其物理或系统内文本来源。"""

    __tablename__ = "evidences"

    description: Mapped[str] = mapped_column(
        Text, nullable=False, comment="证据内容概述/考证逻辑"
    )
    evidence_level: Mapped[EvidenceLevel] = mapped_column(
        Enum(EvidenceLevel), nullable=False, comment="学术证据力等级"
    )
    source_ref_id: Mapped[str | None] = mapped_column(
        ForeignKey("source_refs.id", ondelete="RESTRICT"),
        nullable=True,
        comment="关联的物理文献来源",
    )
    source_passage_id: Mapped[str | None] = mapped_column(
        ForeignKey("passages.id", ondelete="SET NULL"),
        nullable=True,
        comment="关联的系统内数字文献段落",
    )
    creator_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, comment="创建录入人"
    )

    # 关系
    source_ref: Mapped[SourceRef | None] = relationship("SourceRef")
    source_passage: Mapped[Passage | None] = relationship("Passage")


class Citation(BaseModel):
    """学术引用。链接观点、关系、异文与证据之间的中间表。"""

    __tablename__ = "citations"
    __table_args__ = (Index("idx_citation_target", "target_type", "target_id"),)

    target_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="被引用的系统对象类型 (Variant/AcademicRelation/Passage)",
    )
    target_id: Mapped[str] = mapped_column(
        String(36), nullable=False, comment="被引用的对象UUID"
    )
    evidence_id: Mapped[str] = mapped_column(
        ForeignKey("evidences.id", ondelete="CASCADE"),
        nullable=False,
        comment="支撑证据ID",
    )
    quote_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="引用时的佐证原文"
    )
    note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="引用时的考证评注"
    )

    # 关系
    evidence: Mapped[Evidence] = relationship("Evidence")
