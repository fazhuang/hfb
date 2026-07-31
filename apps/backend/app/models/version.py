"""
Version (版本) domain model.

Per HFB-DOM-0803: Version is the most important data model — the platform's
core differentiator. All Passage, Citation, Evidence, Graph, and AI research
is anchored on Version.

Example: 北宋刻本, 南宋刻本, 日本刊本 of 针灸甲乙经
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.book import Book


class Version(BaseModel):
    """A specific textual version of a classical book."""

    __tablename__ = "versions"

    book_id: Mapped[str] = mapped_column(
        ForeignKey("books.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属书籍 ID",
    )
    version_name: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="版本名称"
    )
    era: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="朝代/时期"
    )
    year: Mapped[int | None] = mapped_column(nullable=True, comment="版本年份")
    repository: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="收藏机构"
    )
    shelf_mark: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="索书号"
    )
    editor: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="编者/校注者"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="版本描述"
    )
    source_url: Mapped[str | None] = mapped_column(
        String(2000), nullable=True, comment="来源链接"
    )

    # ------------------------------------------------------------------
    # Academic credibility fields (P2T1)
    # ------------------------------------------------------------------
    is_formal_source: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否为正式学术可引用来源",
    )
    rights_statement: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="权利/授权依据"
    )
    persistent_identifier: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="稳定可核验标识"
    )
    withdrawn_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="撤回时间"
    )
    withdraw_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="撤回原因"
    )

    # Relationships
    book: Mapped[Book] = relationship("Book", back_populates="versions")

    @property
    def is_withdrawn(self) -> bool:
        """Shortcut: is this version currently withdrawn?"""
        return self.withdrawn_at is not None

    @property
    def is_academic_citable(self) -> bool:
        """A version is academically citable only when it is:
        - Marked as a formal source
        - Has a repository (holding institution)
        - Has a shelf mark (call number) or persistent identifier
        - Has a source URL (linkable, verifiable)
        - Is NOT withdrawn
        """
        return (
            self.is_formal_source
            and bool(self.repository)
            and bool(self.shelf_mark or self.persistent_identifier)
            and bool(self.source_url)
            and not self.is_withdrawn
        )

    def withdraw(self, reason: str = "未说明") -> None:
        """Withdraw this version — sets withdrawn_at and reason."""
        self.withdrawn_at = datetime.now(UTC)
        self.withdraw_reason = reason

    def restore(self) -> None:
        """Restore a withdrawn version."""
        self.withdrawn_at = None
        self.withdraw_reason = None

    def __repr__(self) -> str:
        return f"<Version id={self.id} name={self.version_name!r}>"
