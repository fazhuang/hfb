"""
Image (影像) domain model.

Represents digitized page images, manuscript photos, maps,
and other visual resources tied to domain entities.
"""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Image(BaseModel):
    """A digital image resource linked to a domain entity."""

    __tablename__ = "images"

    related_entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="关联实体类型 (book, version, passage, person, paper)",
    )
    related_entity_id: Mapped[str] = mapped_column(
        String(36), nullable=False, index=True, comment="关联实体 ID"
    )
    url: Mapped[str] = mapped_column(String(2000), nullable=False, comment="图片 URL")
    caption: Mapped[str | None] = mapped_column(Text, nullable=True, comment="图片说明")
    source: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="图片来源"
    )
    license_info: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="授权信息"
    )
    order: Mapped[int | None] = mapped_column(nullable=True, comment="排序")

    def __repr__(self) -> str:
        return f"<Image id={self.id} entity={self.related_entity_type}:{self.related_entity_id}>"
