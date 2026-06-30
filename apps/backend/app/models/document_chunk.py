"""
DocumentChunk — chunked document segment for retrieval.

Each chunk belongs to exactly one Document and stores a sequential
index for deterministic citation (e.g. [doc_id:3]).
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.document import Document

from app.db.base import BaseModel


class DocumentChunk(BaseModel):
    """A contiguous text segment from a document, used for retrieval."""

    __tablename__ = "document_chunks"

    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent document ID",
    )
    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Sequential index within the document (0-based)",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Chunk text content",
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Approximate character count (no tokenizer needed)",
    )

    # Relationship back to parent document
    document: Mapped["Document"] = relationship(
        "Document",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index("idx_chunks_doc_index", "document_id", "chunk_index", unique=True),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"
