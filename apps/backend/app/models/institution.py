"""
Institution (机构) domain model.

Represents universities, research institutes, archives and other organizations
relevant to Huangfu Mi studies.

Fields restricted per Day 1 spec:
  - id, name, type, location, description, status
  - created_at, updated_at (inherited from BaseModel)
"""
from __future__ import annotations

import enum

from sqlalchemy import String, Text, CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class InstitutionType(str, enum.Enum):
    """Valid institution types per Day 1 spec."""
    research = "research"
    university = "university"
    archive = "archive"
    institution = "institution"


class InstitutionStatus(str, enum.Enum):
    """Day 1 status machine states."""
    draft = "draft"
    active = "active"
    archived = "archived"
    deleted = "deleted"


class Institution(BaseModel):
    """An organization relevant to Huangfu Mi studies.

    Examples: 复旦大学, 人民卫生出版社, 中国中医科学院, 甘肃博物馆.
    """

    __tablename__ = "institutions"

    name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="机构名称"
    )
    type: Mapped[str] = mapped_column(
        String(50), nullable=False, comment="类型: research / university / archive / institution"
    )
    location: Mapped[str | None] = mapped_column(
        String(300), nullable=True, comment="所在地"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="机构简介"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=InstitutionStatus.draft.value,
        server_default="draft",
        comment="状态: draft / active / archived / deleted",
    )

    __table_args__ = (
        CheckConstraint(
            "type IN ('research', 'university', 'archive', 'institution')",
            name="ck_institutions_type",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'archived', 'deleted')",
            name="ck_institutions_status",
        ),
    )

    def __repr__(self) -> str:
        return f"<Institution id={self.id} name={self.name!r} type={self.type}>"
