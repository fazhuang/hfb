"""
Chapter (章节) domain model.

Chapters structure a book hierarchically. Self-referential parent_id
allows multi-level nesting (卷 → 篇 → 章 → 节).
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.book import Book


class Chapter(BaseModel):
    """A chapter / section within a book."""

    __tablename__ = "chapters"

    book_id: Mapped[str] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属书籍 ID"
    )
    parent_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=True, comment="父章节 ID (自引用层级)"
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="章节标题")
    order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="排序")
    description: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True, comment="章节说明")

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="chapters")
    parent: Mapped[Optional["Chapter"]] = relationship(
        "Chapter", remote_side="Chapter.id", back_populates="children", lazy="selectin"
    )
    children: Mapped[list["Chapter"]] = relationship("Chapter", back_populates="parent", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Chapter id={self.id} title={self.title!r}>"
