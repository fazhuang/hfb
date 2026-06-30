"""
Document (文献) domain model.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, LargeBinary, String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.person import Person

from app.db.base import BaseModel


class Document(BaseModel):
    """A classical text or medical literature document.

    Represents a 文献 entry such as 《针灸甲乙经》 or 《伤寒杂病论》.
    """

    __tablename__ = "documents"

    title: Mapped[str] = mapped_column(String(500), nullable=False, comment="文献标题")
    title_pinyin: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="标题拼音")
    title_english: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="标题英文")
    author_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, comment="关联作者 ID (Person)"
    )
    dynasty: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="朝代")
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="成书年份")
    category: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="分类 (针灸/本草/方剂/养生)")
    abstract: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="摘要")
    content_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="全文文本")
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True, comment="来源链接")
    raw_pdf_blob: Mapped[Optional[bytes]] = mapped_column(LargeBinary, nullable=True, comment="原始 PDF 文件的二进制内容")
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="页数")
    language: Mapped[str] = mapped_column(
        String(20), default="zh", server_default="zh", nullable=False, comment="语言"
    )

    def __init__(self, **kwargs: object) -> None:
        if "language" not in kwargs:
            kwargs["language"] = "zh"
        super().__init__(**kwargs)

    # Relationships
    author: Mapped[Optional["Person"]] = relationship(
        "Person", foreign_keys=[author_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title!r}>"
