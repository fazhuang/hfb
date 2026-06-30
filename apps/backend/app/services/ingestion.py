"""
Document ingestion pipeline — PDF and plain-text input → stored document → chunked.

Real PDF extraction via pypdf, transactional safety (no half-created documents),
deterministic paragraph-based chunking.
"""
from __future__ import annotations

from io import BytesIO
from typing import BinaryIO
from uuid import uuid4

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document_chunk import DocumentChunk
from app.repositories.document import DocumentRepository
from app.services.chunking import chunk_text

# Whitelist: allowed metadata keys that can be stored on the Document model.
# Prevents mass-assignment of internal fields (is_deleted, deleted_at, etc.)
# through the ingest metadata parameter.
_ALLOWED_METADATA_KEYS = frozenset({"dynasty", "category", "source_url", "raw_pdf_blob"})


class IngestionError(Exception):
    """Raised when ingestion fails for any reason."""


class PDFExtractionError(IngestionError):
    """Raised when PDF text extraction fails (encrypted, malformed, or no extractable text)."""


class IngestionResult:
    """Result of a document ingestion operation."""

    def __init__(
        self,
        document_id: str,
        title: str,
        chunk_count: int,
        total_chars: int,
    ) -> None:
        self.document_id = document_id
        self.title = title
        self.chunk_count = chunk_count
        self.total_chars = total_chars


class IngestionService:
    """Ingest documents, extract text, and create chunked indices."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)

    # ------------------------------------------------------------------
    # Ingest from plain text
    # ------------------------------------------------------------------

    async def ingest_text(
        self,
        title: str,
        text: str,
        metadata: dict | None = None,
        max_chunk_chars: int = 1000,
    ) -> IngestionResult:
        """Ingest a plain-text document: store → chunk → index.

        Transactionally: if any step fails, no partial document or chunks remain.

        Args:
            title: Document title.
            text: Raw text content (must be non-empty after strip).
            metadata: Optional extra fields (dynasty, category, etc.).
            max_chunk_chars: Max characters per chunk.

        Returns:
            IngestionResult with document_id, chunk_count, total_chars.

        Raises:
            ValueError: if text is empty after stripping.
        """
        stripped = text.strip()
        if not stripped:
            raise ValueError("Cannot ingest empty text")

        # 1. Store document (flushes immediately, catches constraint violations)
        doc_data: dict = {
            "title": title.strip(),
            "content_text": stripped,
        }
        if metadata:
            # ponytail: whitelist to prevent mass assignment of internal fields
            for k, v in metadata.items():
                if k in _ALLOWED_METADATA_KEYS:
                    doc_data.setdefault(k, v)
        doc = await self.doc_repo.create(**doc_data)
        await self.session.flush()

        try:
            # 2. Chunk
            chunks = chunk_text(stripped, max_chars=max_chunk_chars)

            # 3. Store chunks
            await self._store_chunks(doc.id, chunks)

            return IngestionResult(
                document_id=doc.id,
                title=title.strip(),
                chunk_count=len(chunks),
                total_chars=len(stripped),
            )
        except Exception:
            # Roll back: remove the parent document (already flushed)
            await self.doc_repo.hard_delete(doc.id)
            await self.session.flush()
            raise

    # ------------------------------------------------------------------
    # Ingest from PDF file
    # ------------------------------------------------------------------

    async def ingest_pdf(
        self,
        title: str,
        file: BinaryIO,
        metadata: dict | None = None,
        store_raw_pdf: bool = True,
    ) -> IngestionResult:
        """Ingest a PDF file — extract text with pypdf, store content.

        Args:
            title: Document title.
            file: Opened PDF file (binary mode).
            metadata: Optional extra fields (dynasty, category, etc.).
            store_raw_pdf: If True, store the raw PDF bytes on the Document
                record so the original source is always traceable.

        Returns:
            IngestionResult with document_id, chunk_count, total_chars.

        Raises:
            PDFExtractionError: if the PDF is encrypted, malformed, or
                yields no extractable text.
        """
        raw_bytes = file.read()
        text = self._extract_pdf_text(raw_bytes)

        if not text or not text.strip():
            raise PDFExtractionError(
                f"PDF does not contain extractable text ({len(raw_bytes)} bytes)"
            )

        extra: dict = {}
        if metadata:
            extra.update(metadata)
        if store_raw_pdf:
            extra["raw_pdf_blob"] = raw_bytes
            extra["source_url"] = f"pdf:{len(raw_bytes)}bytes"

        return await self.ingest_text(title=title, text=text.strip(), metadata=extra)

    # ------------------------------------------------------------------
    # Chunk storage
    # ------------------------------------------------------------------

    async def _store_chunks(self, document_id: str, chunks: list[str]) -> None:
        for idx, text in enumerate(chunks):
            chunk = DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=idx,
                content=text,
                token_count=len(text),
            )
            self.session.add(chunk)
        await self.session.flush()

    # ------------------------------------------------------------------
    # PDF text extraction (real pypdf, no fallback to placeholder)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_pdf_text(raw_bytes: bytes) -> str:
        """Extract text from PDF bytes using pypdf.

        Returns the concatenated page text, or empty string if no text pages found.
        Raises PDFExtractionError on encrypted or unreadable PDFs.
        """
        try:
            reader = PdfReader(BytesIO(raw_bytes))
        except PdfReadError as e:
            raise PDFExtractionError(f"Cannot read PDF: {e}") from e

        # Check encryption
        if reader.is_encrypted:
            # Try empty password (many academic PDFs use this)
            try:
                reader.decrypt("")
            except Exception:
                raise PDFExtractionError(
                    "PDF is encrypted and cannot be decrypted with empty password"
                )

        parts: list[str] = []
        for page in reader.pages:
            try:
                text = page.extract_text()
            except Exception:
                continue
            if text:
                parts.append(text)

        return "\n\n".join(parts)
