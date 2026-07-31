"""
ClassicalVersion (古籍版本目录) domain model.

Records bibliographical metadata for classical editions of texts like
《针灸甲乙经》. Distinct from ``Version`` which models textual recensions
used for collation and comparison.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class ClassicalVersion(BaseModel):
    """A catalogued classical edition with provenance and review metadata."""

    __tablename__ = "classical_versions"

    work_title: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="著作名称"
    )
    version_name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="版本名称"
    )
    dynasty: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="朝代"
    )
    edition_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="版本类型 (刻本/抄本/石印本/排印本/影印本/其他)",
    )
    volume_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="卷数"
    )
    repository: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="收藏机构"
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True, comment="来源链接"
    )
    image_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True, comment="书影链接"
    )
    public_domain_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
        server_default="unknown",
        comment="公共领域状态: confirmed_public_domain | copyright_claimed | unknown | not_applicable",
    )
    ocr_text_available: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否有 OCR 文本",
    )
    citation_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="引用说明"
    )
    academic_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="学术备注"
    )
    review_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending_review",
        server_default="pending_review",
        comment="审核状态: pending_review | under_review | approved | rejected",
    )

    def __repr__(self) -> str:
        return f"<ClassicalVersion id={self.id} work={self.work_title!r} name={self.version_name!r}>"
