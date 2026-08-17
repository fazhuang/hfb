"""
DocumentChunk — chunked document segment for retrieval.

Each chunk belongs to exactly one Document and stores a sequential
index for deterministic citation (e.g. [doc_id:3]).

Sprint 4 P0: passage_id FK enables trace_id → chunk → document → passage → citation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, JSON, Float, ForeignKey, Index, Integer, String, Text
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
    passage_id: Mapped[str | None] = mapped_column(
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

    # Evidence-binding fields (RAG evidence binding)
    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="源文档页码 (1-based)",
    )
    paragraph_index: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="源文档段落索引 (0-based)",
    )
    ocr_confidence: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="OCR 可信度 0.0-1.0，NULL 表示非 OCR 文本",
    )
    evidence_weight: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="primary",
        server_default="primary",
        comment="证据权重: primary | reference",
    )
    citation_format: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="引文格式模板",
    )

    # Page-level provenance (rag_evidence_binding_v2)
    page_image_hash: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
        comment="页面区域截图或 OCR 文本的 hash (SHA-512/256 或感知 hash)",
    )
    page_image_hash_alg: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint(
            "page_image_hash_alg IN ('sha256', 'sha512', 'phash')",
            name="ck_chunk_page_image_hash_alg",
        ),
        default="sha256",
        server_default="sha256",
        nullable=False,
        comment="page_image_hash 的算法: sha256 | sha512 | phash",
    )
    ocr_engine_version: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="OCR 引擎及参数标识，如 'paddleocr-v2.7_ch_PP-OCRv4'",
    )
    match_method: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="引文匹配方法: exact | fuzzy | ocr_bounding_box",
    )
    quote_bbox: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="引文在页面上的边界框/偏移位置，如 {x0,y0,x1,y1,page} 或 {start,end}",
    )

    # Relationship back to parent document
    document: Mapped[Document] = relationship(
        "Document",
        lazy="selectin",
    )
    # Sprint 4 P0: lineage resolution
    passage: Mapped[Passage | None] = relationship(
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
