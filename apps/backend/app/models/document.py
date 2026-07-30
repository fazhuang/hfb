"""
Document (文献) domain model.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
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
    title_pinyin: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="标题拼音")
    title_english: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="标题英文")
    author_id: Mapped[str | None] = mapped_column(
        ForeignKey("persons.id", ondelete="SET NULL"), nullable=True, comment="关联作者 ID (Person)"
    )
    dynasty: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="朝代")
    year: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="成书年份")
    category: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="分类 (针灸/本草/方剂/养生)")
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True, comment="摘要")
    content_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="全文文本")
    source_url: Mapped[str | None] = mapped_column(String(2000), nullable=True, comment="来源链接")
    raw_pdf_blob: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, comment="原始 PDF 文件的二进制内容")
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="页数")
    language: Mapped[str] = mapped_column(
        String(20), default="zh", server_default="zh", nullable=False, comment="语言"
    )

    # ----------------------------------------------------------------
    # Full-text compliance fields (Context 21)
    # ----------------------------------------------------------------
    copyright_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="unknown",
        server_default="unknown",
        comment="版权状态: public_domain|open_access|licensed|user_uploaded_with_permission|unknown|metadata_only|forbidden_fulltext|commercial_restricted|pirated",
    )
    license_type: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="许可类型: CC-BY|CC-BY-NC|CC-BY-SA|CC0|custom"
    )
    authorization_basis: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="授权依据 (license URL / agreement ref / basis statement)"
    )
    review_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="pending_review",
        server_default="pending_review",
        comment="审核状态: pending_review|under_review|approved|rejected",
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        String(36), nullable=True, comment="审核人 user ID"
    )
    reviewed_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="审核时间"
    )
    rag_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否允许进入 RAG (审核通过 + 版权允许后置为 true)",
    )
    content_checksum: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="全文 SHA-256 checksum"
    )
    pdf_sha256: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="原始 PDF blob 的 SHA-256 hash"
    )
    source_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="摄入来源名称 (openalex/crossref/user_upload/等)"
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), nullable=True, index=True,
        comment="所属研究项目/会话 ID — NULL = 公共/系统文献，不归属特定项目",
    )
    uploaded_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="上传者 user ID — NULL = 系统种子/公共文献",
    )
    withdrawn_at: Mapped[DateTime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="撤回时间"
    )
    withdraw_reason: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="撤回原因"
    )

    def __init__(self, **kwargs: object) -> None:
        if "language" not in kwargs:
            kwargs["language"] = "zh"
        super().__init__(**kwargs)

    # Relationships
    author: Mapped[Person | None] = relationship(
        "Person", foreign_keys=[author_id], lazy="selectin"
    )

    __table_args__ = (
        Index("idx_documents_pdf_sha256", "pdf_sha256"),
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} title={self.title!r}>"
