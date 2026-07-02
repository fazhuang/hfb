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
    workflow_state: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="当前研究流程快照 (JSON)"
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


class QueryHistory(BaseModel):
    """Records every research query executed within a session.

    P0: Internal full-fidelity trace stored in result_summary JSON.
    API never exposes retrieval_score, retrieval_method, or timestamp.
    """

    __tablename__ = "query_histories"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属研究会话 ID",
    )
    query_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="查询原文"
    )
    query_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="查询类型: report / synthesis / research / education / graph / search",
    )
    result_summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment=(
            "内部全保真追溯 JSON: "
            "{trace_id, document_id, chunk_id, passage_id, "
            "retrieval_score, retrieval_method, timestamp}"
        ),
    )
    citation_count: Mapped[int] = mapped_column(
        default=0, server_default="0", nullable=False, comment="返回的引用条数"
    )

    session: Mapped["ResearchSession"] = relationship(
        "ResearchSession", backref="query_history", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<QueryHistory id={self.id} query_type={self.query_type!r}>"


class CitationCollection(BaseModel):
    """User-saved citation from a research session. Backed by EvidenceTrace."""

    __tablename__ = "citation_collections"

    session_id: Mapped[str] = mapped_column(
        ForeignKey("research_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="所属研究会话 ID",
    )
    trace_json: Mapped[str] = mapped_column(
        Text, nullable=False, comment="完整 EvidenceTrace JSON，不可变"
    )
    citation_text: Mapped[str] = mapped_column(
        Text, nullable=False, comment="格式化引用文本"
    )
    source_document: Mapped[str] = mapped_column(
        String(500), nullable=False, comment="来源文献名"
    )
    tags: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, comment="用户标签"
    )
    notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="用户标注"
    )

    session: Mapped["ResearchSession"] = relationship(
        "ResearchSession", backref="citations", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<CitationCollection id={self.id} source={self.source_document!r}>"
