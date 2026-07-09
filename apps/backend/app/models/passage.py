"""
Passage (条文) domain model — the atomic knowledge unit.

Per HFB-DOM-0804: Passage is the platform's minimum knowledge unit.
AI retrieval, graph reasoning, version comparison, academic citation,
and textual criticism all center on Passage.

Each Passage belongs to a specific Chapter (and thus a Book), and
may be linked to a specific Version for version-aware content.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Integer, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.chapter import Chapter
    from app.models.version import Version
    from app.models.version_criticism import Sentence


class Passage(BaseModel):
    """The atomic unit of classical text — independently citable and comparable."""

    __tablename__ = "passages"

    chapter_id: Mapped[str] = mapped_column(
        ForeignKey("chapters.id", ondelete="CASCADE"), nullable=False, index=True, comment="所属章节 ID"
    )
    version_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("versions.id", ondelete="SET NULL"), nullable=True, comment="所属版本 ID (版本特定文本)"
    )
    content_text: Mapped[str] = mapped_column(Text, nullable=False, comment="条文正文")
    translation: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="现代汉语翻译")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="注释")
    order: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="排序")
    tags: Mapped[Optional[str]] = mapped_column(
        String(1000), nullable=True, comment="标签 (逗号分隔)"
    )

    # Relationships
    chapter: Mapped["Chapter"] = relationship("Chapter", lazy="selectin")
    version: Mapped[Optional["Version"]] = relationship("Version", lazy="selectin")
    sentences: Mapped[list["Sentence"]] = relationship(
        "Sentence", back_populates="passage", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        preview = self.content_text[:40] + "..." if len(self.content_text) > 40 else self.content_text
        return f"<Passage id={self.id} text={preview!r}>"
