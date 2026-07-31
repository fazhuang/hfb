"""
Paper (学术论文) domain model.

Per HFB-DOM-0805: Paper is a Level-1 knowledge entity representing
modern academic research — journal articles, theses, conference papers,
monograph chapters, and research project outputs.
"""

from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import BaseModel


class Paper(BaseModel):
    """An academic paper or research publication."""

    __tablename__ = "papers"

    title: Mapped[str] = mapped_column(
        String(1000), nullable=False, index=True, comment="论文标题"
    )
    title_english: Mapped[str | None] = mapped_column(
        String(1000), nullable=True, comment="英文标题"
    )
    authors: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="作者 (JSON array string)"
    )
    journal: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="期刊/会议名"
    )
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="发表年份")
    doi: Mapped[str | None] = mapped_column(
        String(500), nullable=True, unique=True, comment="DOI"
    )
    volume: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="卷")
    issue: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="期")
    pages: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="页码")
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True, comment="摘要")
    keywords: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="关键词 (逗号分隔)"
    )
    language: Mapped[str] = mapped_column(
        String(20), default="zh", server_default="zh", nullable=False, comment="语言"
    )
    paper_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="类型: journal, thesis, conference, chapter, report",
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True, comment="来源链接"
    )
    full_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="全文文本"
    )

    def __repr__(self) -> str:
        return f"<Paper id={self.id} title={self.title!r}>"
