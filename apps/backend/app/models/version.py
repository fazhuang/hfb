"""
Version (版本) domain model.

Per HFB-DOM-0803: Version is the most important data model — the platform's
core differentiator. All Passage, Citation, Evidence, Graph, and AI research
is anchored on Version.

Example: 北宋刻本, 南宋刻本, 日本刊本 of 针灸甲乙经
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.book import Book


class Version(BaseModel):
    """A specific textual version of a classical book."""

    __tablename__ = "versions"

    book_id: Mapped[str] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属书籍 ID"
    )
    version_name: Mapped[str] = mapped_column(String(300), nullable=False, comment="版本名称")
    era: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="朝代/时期")
    year: Mapped[Optional[int]] = mapped_column(nullable=True, comment="版本年份")
    repository: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="收藏机构")
    shelf_mark: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="索书号")
    editor: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="编者/校注者")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="版本描述")
    source_url: Mapped[Optional[str]] = mapped_column(String(2000), nullable=True, comment="来源链接")

    # Relationships
    book: Mapped["Book"] = relationship("Book", back_populates="versions")

    def __repr__(self) -> str:
        return f"<Version id={self.id} name={self.version_name!r}>"
