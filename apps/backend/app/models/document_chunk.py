"""
DocumentChunk — chunked document segment for retrieval.

Each chunk belongs to exactly one Document and stores a sequential
index for deterministic citation (e.g. [doc_id:3]).

Sprint 4 P0: passage_id FK enables trace_id → chunk → document → passage → citation.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from sqlalchemy import Integer, String, Text, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.passage import Passage

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
    passage_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("passages.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Linked passage for lineage resolution (chunk → passage → citation)",
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
    # Sprint 4 P0: lineage resolution
    passage: Mapped[Optional["Passage"]] = relationship(
        "Passage",
        lazy="selectin",
    )

    __table_args__ = (
        Index("idx_chunks_document", "document_id"),
        Index("idx_chunks_doc_index", "document_id", "chunk_index", unique=True),
        Index("idx_chunks_passage", "passage_id"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk doc={self.document_id} idx={self.chunk_index}>"
