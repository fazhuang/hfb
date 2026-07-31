"""
Academic Knowledge Graph domain models.

Provides AcademicEntity, AcademicRelation, and RelationConfidence for structured scholarship.
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BaseModel

if TYPE_CHECKING:
    from app.models.academic_evidence import Evidence


class AcademicEntityType(str, enum.Enum):
    ACUPOINT = "acupoint"  # 腧穴 (如 商阳、合谷)
    MERIDIAN = "meridian"  # 经络 (如 手阳明大肠经)
    DISEASE = "disease"  # 疾病/病候 (如 齿痛、寒热)
    PERSON = "person"  # 历史人物 (如 皇甫谧)
    TECHNIQUE = "technique"  # 刺灸方法 (如 灸三壮、刺入三分)


class AcademicEntity(BaseModel):
    """学术知识实体。"""

    __tablename__ = "academic_entities"

    name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True, comment="实体名称"
    )
    entity_type: Mapped[AcademicEntityType] = mapped_column(
        Enum(AcademicEntityType), nullable=False, comment="实体类型"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="定义与说明"
    )


# 关系证据的多对多关联表
relation_evidences = Table(
    "relation_evidences",
    Base.metadata,
    Column(
        "relation_id",
        String(36),
        ForeignKey("academic_relations.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        String(36),
        ForeignKey("evidences.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class AcademicRelation(BaseModel):
    """学术命题关系（图谱三元组）。例如 (商阳穴, 主治, 齿痛)。"""

    __tablename__ = "academic_relations"

    source_entity_id: Mapped[str] = mapped_column(
        ForeignKey("academic_entities.id", ondelete="CASCADE"),
        nullable=False,
        comment="源实体ID",
    )
    target_entity_id: Mapped[str] = mapped_column(
        ForeignKey("academic_entities.id", ondelete="CASCADE"),
        nullable=False,
        comment="靶实体ID",
    )
    relation_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="关系类型，如 'TREAT' (主治), 'LOCATE_AT' (定位)",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="命题关系阐述"
    )

    # 关系
    source_entity: Mapped[AcademicEntity] = relationship(
        "AcademicEntity", foreign_keys=[source_entity_id]
    )
    target_entity: Mapped[AcademicEntity] = relationship(
        "AcademicEntity", foreign_keys=[target_entity_id]
    )
    evidences: Mapped[list[Evidence]] = relationship(
        "Evidence", secondary=relation_evidences, lazy="selectin"
    )


class RelationConfidence(BaseModel):
    """关系置信度计算表。学术可信度在此处动态聚合运算。"""

    __tablename__ = "relation_confidences"

    relation_id: Mapped[str] = mapped_column(
        ForeignKey("academic_relations.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        comment="关联的学术命题",
    )
    calculated_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False, comment="计算得到的可信度评分 (0.00-1.00)"
    )
    logic_checked: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="是否通过医学知识逻辑校验（无明显悖论）",
    )
    calculation_log: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="可信度计算的来源因子权重明细"
    )
    last_calculated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
        comment="最后计算更新时间",
    )

    # 关系
    relation: Mapped[AcademicRelation] = relationship("AcademicRelation")
