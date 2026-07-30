"""
Book (书籍) domain model.

A Book is a classical text with independent academic identity.
Per HFB-DOM-0802: Book is a Level-1 core entity.

Example: 针灸甲乙经, 黄帝内经, 难经, 伤寒论
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.chapter import Chapter
    from app.models.person import Person
    from app.models.version import Version


class Book(BaseModel):
    """A classical Chinese medical text."""

    __tablename__ = "books"

    title: Mapped[str] = mapped_column(String(500), nullable=False, index=True, comment="书名")
    title_pinyin: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="书名拼音")
    title_english: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="书名英文")
    author_id: Mapped[str | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, comment="作者 ID"
    )
    dynasty: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="成书朝代")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="成书年份")
    category: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="分类")
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内容摘要")
    language: Mapped[str] = mapped_column(
        String(20), default="zh", server_default="zh", nullable=False, comment="语言"
    )
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True, comment="来源链接")

    # Relationships
    author: Mapped[Person | None] = relationship("Person", foreign_keys=[author_id], lazy="selectin")
    versions: Mapped[list[Version]] = relationship("Version", back_populates="book", lazy="selectin")
    chapters: Mapped[list[Chapter]] = relationship("Chapter", back_populates="book", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Book id={self.id} title={self.title!r}>"
