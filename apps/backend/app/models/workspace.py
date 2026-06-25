"""
Workspace models — ResearchSession and ResearchNote.

Per HFB-PS-1705 AI Research Workspace Product Specification.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import String, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class ResearchSession(BaseModel):
    """A research session — auto-saved workspace state.

    Tracks which entities the user has open, their notes, and AI chat history.
    """

    __tablename__ = "research_sessions"

    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属用户 ID",
    )
    title: Mapped[str] = mapped_column(
        String(500), default="未命名研究", server_default="未命名研究", nullable=False, comment="会话标题"
    )
    active_entities: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="当前打开的实体 ID 列表 (JSON)"
    )
    chat_history: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="AI 对话历史 (JSON)"
    )
    context_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="研究笔记 (Markdown)"
    )

    # Relationships
    user: Mapped["User"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<ResearchSession id={self.id} title={self.title!r}>"


class ResearchNote(BaseModel):
    """A research note attached to a session or entity."""

    __tablename__ = "research_notes"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    entity_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True, comment="关联实体类型"
    )
    entity_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, comment="关联实体 ID"
    )
    content: Mapped[str] = mapped_column(
        Text, nullable=False, comment="笔记内容 (Markdown)"
    )
    tags: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="标签"
    )

    # Relationships
    session: Mapped["ResearchSession"] = relationship(
        "ResearchSession", backref="notes", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<ResearchNote id={self.id}>"
