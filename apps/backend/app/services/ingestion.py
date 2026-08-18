"""
Document ingestion pipeline — PDF and plain-text input → stored document → chunked.

Real PDF extraction via pypdf, transactional safety (no half-created documents),
deterministic paragraph-based chunking, full-text compliance gate (Context 21).
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import UTC
from io import BytesIO
from typing import Any, BinaryIO
from uuid import uuid4

from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.academic_evidence import SourceRef
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.fulltext_ingestion_audit import FulltextIngestionAudit
from app.repositories.document import DocumentRepository
from app.services.chunking import chunk_text

logger = logging.getLogger(__name__)

# Module-level RapidOCR singleton — model load is ~1s, so reusing it across
# pages avoids a per-page reload (which would add ~30+ min on a 1000-page scan).
# RapidOCR (onnxruntime + PP-OCRv4) replaces PaddleOCR: paddlepaddle 3.0.0 on
# py3.13 has a deterministic CPU allocator bug (RuntimeError "No allocator
# found") on certain page layouts, corrupting every 4th page. RapidOCR runs the
# same PP-OCRv4 models on onnxruntime with no such failure.
_rapid_ocr: Any = None


def _get_rapid_ocr() -> Any:
    global _rapid_ocr
    if _rapid_ocr is None:
        from rapidocr_onnxruntime import RapidOCR

        _rapid_ocr = RapidOCR()
    return _rapid_ocr


# Whitelist: allowed metadata keys that can be stored on the Document model.
# Prevents mass-assignment of internal fields (is_deleted, deleted_at, etc.)
# through the ingest metadata parameter.
_ALLOWED_METADATA_KEYS = frozenset(
    {
        "dynasty",
        "category",
        "source_url",
        "raw_pdf_blob",
        "copyright_status",
        "license_type",
        "authorization_basis",
        "source_name",
        "uploaded_by",
        "session_id",
        "pdf_sha256",
    }
)

# Copyright statuses that permit full-text storage and chunking.
_ALLOWED_COPYRIGHT_STATUSES = frozenset(
    {
        "public_domain",
        "open_access",
        "licensed",
        "user_uploaded_with_permission",
    }
)

# Copyright statuses that explicitly forbid full-text storage.
_FORBIDDEN_COPYRIGHT_STATUSES = frozenset(
    {
        "unknown",
        "metadata_only",
        "forbidden_fulltext",
        "commercial_restricted",
        "pirated",
    }
)

# Defense-in-depth resource ceilings for PDF ingestion (enforced inside
# ingest_pdf_with_pages, independent of the route-level admission gate).
_MAX_PDF_PAGES = 2000
_MAX_PDF_PAGE_TEXT_CHARS = 100_000
_MAX_OCR_PAGE_COUNT = 200
_MAX_OCR_SECONDS = 300


class IngestionError(Exception):
    """Raised when ingestion fails for any reason."""


class PDFExtractionError(IngestionError):
    """Raised when PDF text extraction fails (encrypted, malformed, or no extractable text)."""


class FulltextRejectedError(IngestionError):
    """Raised when full-text ingestion is rejected by the compliance gate."""


class IngestionResult:
    """Result of a document ingestion operation."""

    def __init__(
        self,
        document_id: str,
        title: str,
        chunk_count: int,
        total_chars: int,
        checksum: str = "",
    ) -> None:
        self.document_id = document_id
        self.title = title
        self.chunk_count = chunk_count
        self.total_chars = total_chars
        self.checksum = checksum


class AppendResult:
    """Result of an append-passage operation."""

    def __init__(
        self,
        document_id: str,
        passage_id: str,
        appended_chunk_count: int,
        appended_chunk_ids: list[str],
        first_chunk_index: int,
        last_chunk_index: int,
        content_checksum: str,
    ) -> None:
        self.document_id = document_id
        self.passage_id = passage_id
        self.appended_chunk_count = appended_chunk_count
        self.appended_chunk_ids = appended_chunk_ids
        self.first_chunk_index = first_chunk_index
        self.last_chunk_index = last_chunk_index
        self.content_checksum = content_checksum


class IngestionService:
    """Ingest documents, extract text, and create chunked indices.

    Context 21: Every full-text ingest path enforces copyright gate before
    saving content_text, raw_pdf_blob, or creating DocumentChunks.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)

    # ------------------------------------------------------------------
    # Copyright gate
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_checksum(text: str) -> str:
        """Compute SHA-256 checksum of normalized text content."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_fulltext_allowed(metadata: dict | None) -> tuple[bool, str]:
        """Check whether full-text storage is permitted based on copyright fields.

        Returns (allowed, reason). Default-deny: only explicitly allowed
        copyright_status values with non-empty authorization_basis pass.
        """
        if metadata is None:
            return False, "metadata is required for copyright compliance"

        copyright_status = (metadata.get("copyright_status") or "").strip()

        if not copyright_status:
            return False, "copyright_status is required and must be set"

        # Explicit forbidden values
        if copyright_status in _FORBIDDEN_COPYRIGHT_STATUSES:
            return (
                False,
                f"copyright_status={copyright_status} forbids full-text storage",
            )

        # Explicit allowed values
        if copyright_status in _ALLOWED_COPYRIGHT_STATUSES:
            authorization_basis = (
                metadata.get("authorization_basis")
                or metadata.get("license_type")
                or ""
            ).strip()
            if not authorization_basis:
                return False, (
                    f"copyright_status={copyright_status} requires "
                    "authorization_basis or license_type to be non-empty"
                )
            return True, ""

        return False, f"unrecognized copyright_status: {copyright_status}"

    @staticmethod
    def _is_metadata_only(metadata: dict | None) -> bool:
        """Check if the request is explicitly metadata-only."""
        if metadata is None:
            return True  # no metadata = no copyright info = metadata-only
        copyright_status = (metadata.get("copyright_status") or "").strip()
        return copyright_status == "metadata_only"

    @staticmethod
    def _is_forbidden_fulltext(metadata: dict | None) -> bool:
        """Check if full-text is explicitly forbidden."""
        if metadata is None:
            return False
        cs = (metadata.get("copyright_status") or "").strip()
        mf = metadata.get("forbidden_fulltext")
        if cs == "forbidden_fulltext":
            return True
        return bool(mf is True or str(mf).lower() == "true")

    # ------------------------------------------------------------------
    # Audit logging
    # ------------------------------------------------------------------

    async def _write_audit(
        self,
        action: str,
        status: str,
        *,
        source_url: str | None = None,
        source_name: str | None = None,
        copyright_status: str | None = None,
        authorization_basis: str | None = None,
        license_type: str | None = None,
        checksum: str | None = None,
        result_entity_type: str | None = None,
        result_entity_id: str | None = None,
        reject_reason: str | None = None,
        skipped_reason: str | None = None,
        actor_id: str | None = None,
        details: dict | None = None,
    ) -> None:
        audit = FulltextIngestionAudit(
            action=action,
            status=status,
            source_url=source_url,
            source_name=source_name,
            copyright_status=copyright_status,
            authorization_basis=authorization_basis,
            license_type=license_type,
            checksum=checksum,
            result_entity_type=result_entity_type,
            result_entity_id=result_entity_id,
            reject_reason=reject_reason,
            skipped_reason=skipped_reason,
            actor_id=actor_id,
            details=details,
        )
        self.session.add(audit)
        await self.session.flush()

    # ------------------------------------------------------------------
    # Ingest from plain text
    # ------------------------------------------------------------------

    async def ingest_text(
        self,
        title: str,
        text: str,
        metadata: dict | None = None,
        max_chunk_chars: int = 1000,
        passage_id: str | None = None,
        page_number: int | None = None,
        ocr_confidence: float | None = None,
    ) -> IngestionResult:
        """Ingest a plain-text document: compliance gate → store → chunk → audit.

        Context 21: copyright_status gate enforced BEFORE any full-text storage.
        metadata_only and forbidden_fulltext are hard-rejected with audit log.

        Args:
            title: Document title.
            text: Raw text content (must be non-empty after strip).
            metadata: Must include copyright_status and authorization_basis
                or license_type for full-text to be stored.
            max_chunk_chars: Max characters per chunk.
            passage_id: Optional Passage ID for V4 lineage resolution.
            page_number: Optional page number (1-based) for citation binding.
            ocr_confidence: Optional OCR confidence 0.0-1.0 for OCR-generated text.

        Returns:
            IngestionResult with document_id, chunk_count, total_chars, checksum.

        Raises:
            ValueError: if text is empty after stripping, or if passage_id
                references a non-existent Passage.
            FulltextRejectedError: if copyright gate blocks full-text storage.
        """
        stripped = text.strip()
        if not stripped:
            raise ValueError("Cannot ingest empty text")

        meta = metadata or {}

        # Sprint 4 P0: validate passage exists when passage_id provided
        if passage_id is not None:
            if not passage_id.strip():
                raise ValueError("passage_id must be non-empty when provided")
            from sqlalchemy import select as sql_select

            from app.models.passage import Passage

            p_stmt = sql_select(Passage.id).where(
                Passage.id == passage_id.strip(),
                Passage.is_deleted.is_(False),
            )
            p_result = await self.session.execute(p_stmt)
            if p_result.one_or_none() is None:
                raise ValueError(f"Passage {passage_id} not found or deleted")

        # ------ Copyright compliance gate ------
        if self._is_forbidden_fulltext(meta):
            await self._write_audit(
                action="reject",
                status="rejected",
                source_url=meta.get("source_url"),
                source_name=meta.get("source_name"),
                copyright_status=meta.get("copyright_status", "forbidden_fulltext"),
                authorization_basis=meta.get("authorization_basis"),
                license_type=meta.get("license_type"),
                reject_reason="forbidden_fulltext: full-text storage explicitly forbidden",
                details={"title": title.strip()},
            )
            raise FulltextRejectedError(
                "Full-text storage rejected: forbidden_fulltext is set"
            )

        if self._is_metadata_only(meta):
            await self._write_audit(
                action="skip",
                status="skipped",
                source_url=meta.get("source_url"),
                source_name=meta.get("source_name"),
                copyright_status="metadata_only",
                authorization_basis=meta.get("authorization_basis"),
                license_type=meta.get("license_type"),
                skipped_reason="metadata_only: full-text storage not permitted",
                details={"title": title.strip()},
            )
            raise FulltextRejectedError(
                "Full-text storage rejected: metadata_only, "
                "full-text content cannot be saved"
            )

        allowed, reason = self._is_fulltext_allowed(meta)
        if not allowed:
            await self._write_audit(
                action="reject",
                status="rejected",
                source_url=meta.get("source_url"),
                source_name=meta.get("source_name"),
                copyright_status=meta.get("copyright_status", "unknown"),
                authorization_basis=meta.get("authorization_basis"),
                license_type=meta.get("license_type"),
                reject_reason=reason,
                details={"title": title.strip()},
            )
            raise FulltextRejectedError(f"Full-text storage rejected: {reason}")

        # ------ Compute checksum ------
        checksum = self._compute_checksum(stripped)

        # ------ 1. Store document ------
        copyright_status = (meta.get("copyright_status") or "").strip()
        authorization_basis = (
            meta.get("authorization_basis") or meta.get("license_type") or ""
        ).strip()
        doc_data: dict = {
            "title": title.strip(),
            "content_text": stripped,
            "copyright_status": copyright_status,
            "authorization_basis": authorization_basis,
            "license_type": meta.get("license_type"),
            "content_checksum": checksum,
            "source_name": meta.get("source_name"),
        }
        if metadata:
            for k, v in metadata.items():
                if k in _ALLOWED_METADATA_KEYS:
                    doc_data.setdefault(k, v)
        doc = await self.doc_repo.create(**doc_data)
        await self.session.flush()

        # P0: Create SourceRef on every ingest — passage-scoped when
        # passage_id is provided, document-scoped otherwise.
        source_url = doc_data.get("source_url") or (
            meta.get("source_url") if metadata else None
        )
        page_loc = (
            f"passage:{passage_id.strip()}"
            if passage_id and passage_id.strip()
            else f"document:{doc.id}"
        )
        await self._ensure_source_ref(
            self.session,
            title=title.strip(),
            url=source_url or "",
            author=doc_data.get("source_name")
            or (meta.get("source_name") if metadata else None),
            page_location=page_loc,
            edition_info=meta.get("edition") if metadata else None,
        )

        try:
            # 2. Chunk with paragraph indices
            chunks_with_indices = chunk_text(
                stripped, max_chars=max_chunk_chars, return_indices=True
            )
            # If return_indices=True, result is list of (text, first_paragraph_index)
            # ponytail: backward compat — if old chunk_text returns list[str], wrap
            if chunks_with_indices and isinstance(chunks_with_indices[0], str):
                chunk_data: list[tuple[str, int]] = [
                    (t, -1)
                    for t in chunks_with_indices  # type: ignore[arg-type]
                ]
            else:
                chunk_data = chunks_with_indices  # type: ignore[assignment]

            # 3. Store chunks with paragraph_index, page_number, ocr_confidence
            await self._store_chunks(
                doc.id,
                chunk_data,
                passage_id=passage_id,
                page_number=page_number,
                ocr_confidence=ocr_confidence,
            )

            # 4. Audit: success
            await self._write_audit(
                action="fulltext_ingest",
                status="success",
                source_url=doc.source_url or meta.get("source_url"),
                source_name=doc.source_name or meta.get("source_name"),
                copyright_status=doc.copyright_status,
                authorization_basis=doc.authorization_basis,
                license_type=doc.license_type,
                checksum=checksum,
                result_entity_type="document",
                result_entity_id=doc.id,
                details={"title": title.strip(), "chunk_count": len(chunk_data)},
            )

            return IngestionResult(
                document_id=doc.id,
                title=title.strip(),
                chunk_count=len(chunk_data),
                total_chars=len(stripped),
                checksum=checksum,
            )
        except (SQLAlchemyError, ValueError, OSError):
            # Roll back: remove the parent document (already flushed)
            await self._write_audit(
                action="skip",
                status="skipped",
                source_url=meta.get("source_url"),
                source_name=meta.get("source_name"),
                copyright_status=copyright_status,
                authorization_basis=authorization_basis,
                license_type=meta.get("license_type"),
                skipped_reason="chunking/storage failure, document rolled back",
                result_entity_type="document",
                result_entity_id=doc.id,
                details={"title": title.strip()},
            )
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
        passage_id: str | None = None,
        ocr_confidence: float | None = None,
    ) -> IngestionResult:
        """Ingest a PDF file — extract text with pypdf, store content.

        Context 21: The same copyright gate as ingest_text applies.
        PDF raw bytes are stored only if copyright is allowed AND
        store_raw_pdf is True.

        Args:
            title: Document title.
            file: Opened PDF file (binary mode).
            metadata: Must include copyright_status and authorization_basis.
            store_raw_pdf: If True, store the raw PDF bytes on the Document
                record so the original source is always traceable.
            passage_id: Optional Passage ID for V4 lineage resolution.
            ocr_confidence: Optional OCR confidence 0.0-1.0 for OCR-generated PDFs.

        Returns:
            IngestionResult with document_id, chunk_count, total_chars, checksum.

        Raises:
            PDFExtractionError: if the PDF is encrypted, malformed, or
                yields no extractable text.
            FulltextRejectedError: if copyright gate blocks full-text storage.
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
            extra["source_url"] = (
                extra.get("source_url") or f"pdf:{len(raw_bytes)}bytes"
            )

        return await self.ingest_text(
            title=title,
            text=text.strip(),
            metadata=extra,
            passage_id=passage_id,
            ocr_confidence=ocr_confidence,
        )

    # ------------------------------------------------------------------
    # Ingest from PDF with per-page tracking
    # ------------------------------------------------------------------

    async def ingest_pdf_with_pages(
        self,
        title: str,
        file: BinaryIO,
        metadata: dict | None = None,
        store_raw_pdf: bool = True,
        passage_id: str | None = None,
        ocr_confidence: float | None = None,
        max_chunk_chars: int = 1000,
        ocr_lang: str = "chi_sim",
        ocr_dpi: int = 300,
    ) -> IngestionResult:
        """Ingest a PDF with per-chunk page number tracking.

        Unlike ingest_pdf which applies a single page_number to all chunks,
        this method extracts text page-by-page and assigns each chunk the
        page number it came from. Critical for "PDF page X → chunk Y →
        citation Z" auditability.

        Falls back to OCR (tesseract) when pypdf cannot extract text from
        a page (e.g. scanned image PDFs). The pdf2image + pytesseract
        toolchain is used for OCR fallback.

        The copyright gate is enforced BEFORE document creation.
        """
        raw_bytes = file.read()

        # Defense-in-depth: verify the byte signature before pypdf parses it.
        if not raw_bytes.startswith(b"%PDF-"):
            raise PDFExtractionError("Uploaded file is not a valid PDF (missing %PDF- signature)")

        # First try pypdf for text extraction
        try:
            reader = PdfReader(BytesIO(raw_bytes))
        except PdfReadError as e:
            raise PDFExtractionError(f"Cannot read PDF: {e}") from e
        except Exception as e:
            raise PDFExtractionError(f"Malformed PDF: {e}") from e

        if len(reader.pages) > _MAX_PDF_PAGES:
            raise PDFExtractionError(
                f"PDF has {len(reader.pages)} pages, exceeding the {_MAX_PDF_PAGES}-page limit"
            )

        if reader.is_encrypted:
            try:
                reader.decrypt("")
            except PdfReadError:
                raise PDFExtractionError(
                    "PDF is encrypted and cannot be decrypted with empty password"
                )

        page_data: list[tuple[int, str]] = []
        ocr_pages: list[int] = []

        for i, page in enumerate(reader.pages, start=1):
            try:
                t = page.extract_text()
            except PdfReadError:
                t = None
            except Exception:  # noqa: BLE001 — per-page parse failure → treat as unscannable
                t = None
            if t and t.strip():
                # fail-closed: a page whose text exceeds the ceiling is a
                # malformed/oversized input, not something to silently truncate.
                if len(t) > _MAX_PDF_PAGE_TEXT_CHARS:
                    raise PDFExtractionError(
                        f"Page {i} has {len(t)} chars, exceeding the "
                        f"{_MAX_PDF_PAGE_TEXT_CHARS}-char page limit"
                    )
                page_data.append((i, t.strip()))
            else:
                ocr_pages.append(i)

        # OCR fallback for pages without embedded text
        if ocr_pages:
            if len(ocr_pages) > _MAX_OCR_PAGE_COUNT:
                raise PDFExtractionError(
                    f"PDF requires OCR on {len(ocr_pages)} pages, exceeding the "
                    f"{_MAX_OCR_PAGE_COUNT}-page OCR limit"
                )
            # OCR runs in the event-loop thread; asyncio.wait_for only cancels
            # the await — the blocking work keeps running in the background and
            # the request fails closed. It cannot kill the underlying thread.
            try:
                ocr_texts = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._ocr_pdf_pages,
                        raw_bytes,
                        ocr_pages,
                        lang=ocr_lang,
                        dpi=ocr_dpi,
                    ),
                    timeout=_MAX_OCR_SECONDS,
                )
            except TimeoutError:
                raise PDFExtractionError(
                    f"OCR exceeded the {_MAX_OCR_SECONDS}-second time limit"
                ) from None
            for pg_num, text in ocr_texts.items():
                if text and text.strip():
                    page_data.append((pg_num, text.strip()))

            # Sort by page number after merging OCR results
            page_data.sort(key=lambda x: x[0])

        if not page_data:
            raise PDFExtractionError(
                f"No extractable text found in any page of PDF ({len(raw_bytes)} bytes)"
            )

        # Set ocr_confidence from OCR mix if not explicitly provided
        if ocr_confidence is None and ocr_pages:
            len(reader.pages) - len(ocr_pages)
            ocr_ratio = len(ocr_pages) / max(len(reader.pages), 1)
            if ocr_ratio > 0.8:
                ocr_confidence = 0.65  # mostly OCR
            elif ocr_ratio > 0.3:
                ocr_confidence = 0.75  # mixed
            else:
                ocr_confidence = 0.85  # mostly text

        # Copyright gate — enforce BEFORE document creation
        meta = metadata or {}
        if store_raw_pdf:
            meta = dict(meta)
            meta["raw_pdf_blob"] = raw_bytes
            meta["source_url"] = meta.get("source_url") or f"pdf:{len(raw_bytes)}bytes"

        allowed, reason = self._is_fulltext_allowed(meta)
        if not allowed:
            raise FulltextRejectedError(f"Full-text storage rejected: {reason}")

        # Compute checksum over concatenated page text
        full_text = "\n\n".join(t for _, t in page_data)
        checksum = self._compute_checksum(full_text)

        # 1. Create document
        copyright_status = (meta.get("copyright_status") or "").strip()
        authorization_basis = (
            meta.get("authorization_basis") or meta.get("license_type") or ""
        ).strip()
        doc_data: dict = {
            "title": title.strip(),
            "content_text": full_text,
            "copyright_status": copyright_status,
            "authorization_basis": authorization_basis,
            "license_type": meta.get("license_type"),
            "content_checksum": checksum,
            "source_name": meta.get("source_name"),
            "source_url": meta.get("source_url"),
        }
        if meta:
            for k, v in meta.items():
                if k in _ALLOWED_METADATA_KEYS:
                    doc_data.setdefault(k, v)
        doc = await self.doc_repo.create(**doc_data)
        await self.session.flush()

        # P0: Create SourceRef on every ingest — passage-scoped when
        # passage_id is provided, document-scoped otherwise.
        source_url = doc_data.get("source_url")
        page_loc = (
            f"passage:{passage_id.strip()}"
            if passage_id and passage_id.strip()
            else f"document:{doc.id}"
        )
        await self._ensure_source_ref(
            self.session,
            title=title.strip(),
            url=source_url or "",
            author=doc_data.get("source_name"),
            page_location=page_loc,
            edition_info=meta.get("edition"),
        )

        try:
            # 2. Chunk each page independently, tracking page_number
            all_chunk_data: list[tuple[str, int]] = []
            all_page_numbers: list[int | None] = []

            for page_num, page_text in page_data:
                page_chunks = chunk_text(
                    page_text, max_chars=max_chunk_chars, return_indices=True
                )
                if page_chunks and isinstance(page_chunks[0], str):
                    page_chunk_pairs: list[tuple[str, int]] = [
                        (t, -1)
                        for t in page_chunks  # type: ignore[arg-type]
                    ]
                else:
                    page_chunk_pairs = page_chunks  # type: ignore[assignment]

                for chunk_text_str, para_idx in page_chunk_pairs:
                    all_chunk_data.append((chunk_text_str, para_idx))
                    all_page_numbers.append(page_num)

            # 3. Store chunks with per-chunk page numbers
            await self._store_chunks(
                doc.id,
                all_chunk_data,
                passage_id=passage_id,
                ocr_confidence=ocr_confidence,
                page_numbers=all_page_numbers,
            )

            # 4. Audit
            await self._write_audit(
                action="fulltext_ingest",
                status="success",
                source_url=doc.source_url,
                source_name=doc.source_name,
                copyright_status=doc.copyright_status,
                authorization_basis=doc.authorization_basis,
                license_type=doc.license_type,
                checksum=checksum,
                result_entity_type="document",
                result_entity_id=doc.id,
                details={
                    "title": title.strip(),
                    "chunk_count": len(all_chunk_data),
                    "page_count": len(page_data),
                },
            )

            return IngestionResult(
                document_id=doc.id,
                title=title.strip(),
                chunk_count=len(all_chunk_data),
                total_chars=sum(len(t) for t, _ in all_chunk_data),
                checksum=checksum,
            )
        except (SQLAlchemyError, ValueError, OSError):
            # Roll back: remove the parent document
            await self._write_audit(
                action="skip",
                status="skipped",
                source_url=meta.get("source_url"),
                source_name=meta.get("source_name"),
                copyright_status=copyright_status,
                authorization_basis=authorization_basis,
                license_type=meta.get("license_type"),
                skipped_reason="chunking/storage failure, document rolled back",
                result_entity_type="document",
                result_entity_id=doc.id,
                details={"title": title.strip()},
            )
            await self.doc_repo.hard_delete(doc.id)
            await self.session.flush()
            raise

    # ------------------------------------------------------------------
    # Append passage chunks to an existing document
    # ------------------------------------------------------------------

    async def append_passage(
        self,
        document_id: str,
        text: str,
        passage_id: str,
        max_chunk_chars: int = 1000,
    ) -> AppendResult:
        """Append passage-bound chunks to an existing document.

        Wraps all work inside a SQLAlchemy savepoint (begin_nested).
        On any failure the savepoint is rolled back — no partial chunks,
        no stale checksum, and no half-updated review status survive.

        Post-append: the document's review_status is reset to 'pending'
        and rag_enabled is set to False — re-review is required before
        RAG retrieval can use the new content.
        """
        from datetime import datetime

        from sqlalchemy import func as _func
        from sqlalchemy import select as _sel

        stripped = text.strip()
        if not stripped:
            raise ValueError("Cannot append empty text to document")

        # 1. Document must exist, be non-deleted
        doc = await self.doc_repo.get_by_id(document_id)
        if doc is None or doc.is_deleted:
            raise ValueError(f"Document {document_id} does not exist or is deleted")

        # 2. Passage must exist, be non-deleted
        from app.models.passage import Passage

        p_stmt = _sel(Passage.id).where(
            Passage.id == passage_id.strip(),
            Passage.is_deleted.is_(False),
        )
        p_result = await self.session.execute(p_stmt)
        if p_result.scalar_one_or_none() is None:
            raise ValueError(f"Passage {passage_id} does not exist or is deleted")

        # 3. Re-run full-text compliance gate from the document's own metadata.
        #    We do NOT accept override metadata — the append is to the SAME
        #    source document so its original compliance attributes govern.
        meta = {
            "copyright_status": doc.copyright_status,
            "authorization_basis": doc.authorization_basis,
            "license_type": doc.license_type,
            "source_name": doc.source_name,
            "source_url": doc.source_url,
        }
        if self._is_forbidden_fulltext(meta):
            await self._write_audit(
                action="reject",
                status="rejected",
                source_url=doc.source_url,
                source_name=doc.source_name,
                copyright_status=doc.copyright_status,
                authorization_basis=doc.authorization_basis,
                license_type=doc.license_type,
                reject_reason="forbidden_fulltext: append rejected",
                result_entity_type="document",
                result_entity_id=document_id,
                details={"passage_id": passage_id},
            )
            raise FulltextRejectedError(
                "Append rejected: document has forbidden_fulltext status"
            )
        if self._is_metadata_only(meta):
            await self._write_audit(
                action="skip",
                status="skipped",
                source_url=doc.source_url,
                source_name=doc.source_name,
                copyright_status=doc.copyright_status,
                authorization_basis=doc.authorization_basis,
                license_type=doc.license_type,
                skipped_reason="metadata_only: append rejected",
                result_entity_type="document",
                result_entity_id=document_id,
                details={"passage_id": passage_id},
            )
            raise FulltextRejectedError("Append rejected: document is metadata_only")
        allowed, reason = self._is_fulltext_allowed(meta)
        if not allowed:
            await self._write_audit(
                action="reject",
                status="rejected",
                source_url=doc.source_url,
                source_name=doc.source_name,
                copyright_status=doc.copyright_status,
                authorization_basis=doc.authorization_basis,
                license_type=doc.license_type,
                reject_reason=reason,
                result_entity_type="document",
                result_entity_id=document_id,
                details={"passage_id": passage_id},
            )
            raise FulltextRejectedError(f"Append rejected by compliance gate: {reason}")

        # 4. Chunk the new text
        chunks_with_indices = chunk_text(
            stripped, max_chars=max_chunk_chars, return_indices=True
        )
        if chunks_with_indices and isinstance(chunks_with_indices[0], str):
            chunk_list: list[tuple[str, int]] = [(t, -1) for t in chunks_with_indices]
        else:
            chunk_list = chunks_with_indices

        if not chunk_list:
            raise ValueError("No chunks produced from input text")

        # ---- Savepoint-bounded atomic block ----
        sp = await self.session.begin_nested()
        try:
            # 5. Row-lock the document (FOR UPDATE) to prevent concurrent
            #    append races on chunk_index and checksum.
            await self.session.execute(
                _sel(Document.id)
                .where(
                    Document.id == document_id,
                )
                .with_for_update()
            )

            # 6. Compute next chunk_index under the lock
            max_idx_result = await self.session.execute(
                _sel(_func.coalesce(_func.max(DocumentChunk.chunk_index), -1)).where(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.is_deleted.is_(False),
                )
            )
            next_index = max_idx_result.scalar_one() + 1

            # 7. Create chunks with consecutive indices
            chunk_ids: list[str] = []
            for offset, item in enumerate(chunk_list):
                if isinstance(item, str):
                    chunk_text_val = item
                    para_idx = -1
                else:
                    chunk_text_val, para_idx = item

                cid = str(uuid4())
                chunk = DocumentChunk(
                    id=cid,
                    document_id=document_id,
                    chunk_index=next_index + offset,
                    content=chunk_text_val,
                    token_count=len(chunk_text_val),
                    passage_id=passage_id.strip(),
                    paragraph_index=para_idx
                    if para_idx >= 0
                    else (next_index + offset),
                    evidence_weight="primary",
                )
                self.session.add(chunk)
                chunk_ids.append(cid)

            await self.session.flush()

            # 7b. Create/ensure passage-scoped SourceRef for the appended passage.
            #    Must live inside the savepoint so a failure here rolls back
            #    all chunks and the stale SourceRef together.
            await self._ensure_source_ref(
                self.session,
                title=doc.title.strip(),
                url=doc.source_url or "",
                author=doc.source_name,
                page_location=f"passage:{passage_id.strip()}",
                edition_info=None,
            )

            # 8. Rebuild full content text and recompute checksum
            all_chunks_result = await self.session.execute(
                _sel(DocumentChunk.content)
                .where(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.is_deleted.is_(False),
                )
                .order_by(DocumentChunk.chunk_index)
            )
            all_text = "\n\n".join(row[0] for row in all_chunks_result)
            new_checksum = hashlib.sha256(all_text.encode("utf-8")).hexdigest()

            # 9. Update document: content, checksum, review status, rag
            now = datetime.now(UTC)
            doc.content_text = all_text
            doc.content_checksum = new_checksum
            doc.review_status = "pending"
            doc.rag_enabled = False
            doc.updated_at = now

            # 10. Audit log
            await self._write_audit(
                action="append_passage",
                status="success",
                source_url=doc.source_url,
                source_name=doc.source_name,
                copyright_status=doc.copyright_status,
                authorization_basis=doc.authorization_basis,
                license_type=doc.license_type,
                checksum=new_checksum,
                result_entity_type="document",
                result_entity_id=document_id,
                details={
                    "passage_id": passage_id,
                    "appended_chunk_count": len(chunk_ids),
                    "first_chunk_index": next_index,
                    "last_chunk_index": next_index + len(chunk_ids) - 1,
                },
            )

            await sp.commit()

            return AppendResult(
                document_id=document_id,
                passage_id=passage_id,
                appended_chunk_count=len(chunk_ids),
                appended_chunk_ids=chunk_ids,
                first_chunk_index=next_index,
                last_chunk_index=next_index + len(chunk_ids) - 1,
                content_checksum=new_checksum,
            )
        except (SQLAlchemyError, ValueError, RuntimeError):
            await sp.rollback()
            raise

    # ------------------------------------------------------------------
    # Withdraw
    # ------------------------------------------------------------------

    async def withdraw_document(
        self,
        document_id: str,
        reason: str = "",
        actor_id: str | None = None,
    ) -> None:
        """Withdraw a document: soft-delete it AND all its chunks, audit log.

        After withdrawal, the document and all chunks are soft-deleted.
        Retrieval/RAG services filter by both Document.is_deleted and
        DocumentChunk.is_deleted, so the content becomes invisible to all
        retrieval paths.
        """
        from datetime import datetime

        from sqlalchemy import update as sql_update

        # Soft-delete the document
        now = datetime.now(UTC)
        doc_stmt = (
            sql_update(Document)
            .where(Document.id == document_id)
            .values(
                is_deleted=True,
                deleted_at=now,
                withdrawn_at=now,
                withdraw_reason=reason,
                rag_enabled=False,
            )
        )
        await self.session.execute(doc_stmt)

        # Soft-delete all chunks
        chunk_stmt = (
            sql_update(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .values(is_deleted=True, deleted_at=now)
        )
        await self.session.execute(chunk_stmt)

        # Audit
        doc = await self.doc_repo.get_by_id(document_id)
        await self._write_audit(
            action="withdraw",
            status="withdrawn",
            source_url=getattr(doc, "source_url", None),
            source_name=getattr(doc, "source_name", None),
            copyright_status=getattr(doc, "copyright_status", None),
            authorization_basis=getattr(doc, "authorization_basis", None),
            license_type=getattr(doc, "license_type", None),
            checksum=getattr(doc, "content_checksum", None),
            result_entity_type="document",
            result_entity_id=document_id,
            reject_reason=reason,
            actor_id=actor_id,
            details={"title": getattr(doc, "title", "")},
        )

        await self.session.flush()

    # ------------------------------------------------------------------
    # Chunk storage
    # ------------------------------------------------------------------

    async def _store_chunks(
        self,
        document_id: str,
        chunks: list[str] | list[tuple[str, int]],
        passage_id: str | None = None,
        page_number: int | None = None,
        ocr_confidence: float | None = None,
        page_numbers: list[int | None] | None = None,
        page_image_hashes: list[str | None] | None = None,
    ) -> None:
        """Store chunks with optional paragraph_index, page_number, ocr_confidence.

        page_numbers, when provided, assigns per-chunk page numbers (by index).
        Falls back to the single page_number parameter when page_numbers is None
        or doesn't have a value at the chunk's index.

        page_image_hashes, when provided, assigns per-chunk page image hashes
        (by index) for later visual provenance / OCR correction.
        """
        for idx, item in enumerate(chunks):
            if isinstance(item, str):
                text = item
                para_idx = -1
            else:
                text, para_idx = item

            ocr = ocr_confidence
            evidence_weight = "primary"
            if ocr is not None and ocr < 0.7:
                evidence_weight = "reference"

            # Per-chunk page number: prefer page_numbers[idx] if available
            pn: int | None = None
            if page_numbers is not None and idx < len(page_numbers):
                pn = page_numbers[idx]
            if pn is None:
                pn = page_number

            # Per-chunk page image hash (visual provenance)
            pih: str | None = None
            if page_image_hashes is not None and idx < len(page_image_hashes):
                pih = page_image_hashes[idx]

            chunk = DocumentChunk(
                id=str(uuid4()),
                document_id=document_id,
                chunk_index=idx,
                content=text,
                token_count=len(text),
                passage_id=passage_id.strip()
                if passage_id and passage_id.strip()
                else None,
                page_number=pn,
                paragraph_index=para_idx
                if para_idx >= 0
                else idx,  # fallback to chunk_index
                ocr_confidence=ocr,
                evidence_weight=evidence_weight,
                page_image_hash=pih,
            )
            self.session.add(chunk)
        await self.session.flush()

    # ------------------------------------------------------------------
    # SourceRef helpers (P0: Codex requirement — persist source_refs during ingestion)
    # ------------------------------------------------------------------

    @staticmethod
    async def _ensure_source_ref(
        session: AsyncSession,
        title: str,
        url: str,
        author: str | None = None,
        page_location: str | None = None,
        edition_info: str | None = None,
    ) -> str | None:
        """Create a source_refs row if one doesn't already exist for this identity.

        Stable-identity dedup: a non-empty, normalised URL is the primary key.
        When no URL is available, the composite (title, page_location) is used
        so that two documents with the same title but different scopes (e.g.
        different versions) each get their own SourceRef row.  Without either
        URL or page_location the call is a no-op (no identity to dedup on).

        Returns the source_ref ID if created or found, None if identity is
        insufficient to create a row.
        """
        title_clean = (title or "").strip()
        if not title_clean:
            return None

        from urllib.parse import urlparse, urlunparse
        from uuid import uuid4

        from sqlalchemy import and_
        from sqlalchemy import select as _select

        # --- normalise URL for stable dedup ----------------------------------
        norm_url = ""
        raw = (url or "").strip()
        if raw:
            try:
                p = urlparse(raw)
                # Drop fragment, drop trailing slash on path for dedup
                path = p.path.rstrip("/") or "/"
                norm_url = urlunparse(
                    (p.scheme.lower(), p.netloc.lower(), path, p.params, p.query, "")
                )
            except (ValueError, TypeError):
                norm_url = raw

        loc = (page_location or "").strip()

        if norm_url and loc:
            # URL + page_location identity — passage-scoped or document-scoped.
            # Two different passages with the same URL must produce distinct
            # SourceRef rows.
            stmt = _select(SourceRef.id).where(
                and_(
                    SourceRef.url == norm_url,
                    SourceRef.page_location == loc,
                    SourceRef.is_deleted.is_(False),
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return existing

            ref = SourceRef(
                title=title_clean,
                author=author or "",
                edition_info=edition_info or "",
                page_location=loc,
                url=norm_url,
            )
            session.add(ref)
            await session.flush()
            return str(ref.id) if ref.id else str(uuid4())

        if norm_url:
            # URL-only identity — legacy document-scoped dedup when no
            # page_location is provided.
            stmt = _select(SourceRef.id).where(
                and_(
                    SourceRef.url == norm_url,
                    SourceRef.is_deleted.is_(False),
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return existing

            ref = SourceRef(
                title=title_clean,
                author=author or "",
                edition_info=edition_info or "",
                page_location=loc,
                url=norm_url,
            )
            session.add(ref)
            await session.flush()
            # SQLAlchemy may not populate the default-generated id until flush
            # — if ref.id is still None, return a newly generated uuid4 string
            # so the caller always receives a real non-None id.
            return str(ref.id) if ref.id else str(uuid4())

        if loc:
            # No URL — use composite (title, page_location) identity.
            # This means same-title documents with different page_locations
            # (e.g. different ingested versions) get separate SourceRef rows.
            stmt = _select(SourceRef.id).where(
                and_(
                    SourceRef.title == title_clean,
                    SourceRef.page_location == loc,
                    SourceRef.is_deleted.is_(False),
                    SourceRef.url == "",
                )
            )
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            if existing:
                return existing

            ref = SourceRef(
                title=title_clean,
                author=author or "",
                edition_info=edition_info or "",
                page_location=loc,
                url="",
            )
            session.add(ref)
            await session.flush()
            return str(ref.id) if ref.id else str(uuid4())

        # Insufficient identity — no URL and no page_location.
        # Return None so callers treat this as "no SourceRef available"
        # (fail-closed).
        return None

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
            except PdfReadError:
                raise PDFExtractionError(
                    "PDF is encrypted and cannot be decrypted with empty password"
                )

        parts: list[str] = []
        for page in reader.pages:
            try:
                t = page.extract_text()
            except PdfReadError:
                continue
            if t:
                parts.append(t)

        return "\n\n".join(parts)

    @staticmethod
    def _ocr_pdf_pages(
        raw_bytes: bytes,
        page_numbers: list[int],
        lang: str = "chi_sim",
        dpi: int = 300,
        batch_size: int = 30,
    ) -> dict[int, str]:
        """OCR specific pages of a scanned PDF.

        Primary engine: PaddleOCR (PP-OCRv4 ch model) — far better than
        tesseract on classical Chinese, especially vertical (right-to-left)
        column layout. Output is reordered into reading order per page.

        Falls back to tesseract when PaddleOCR is unavailable.

        Renders in batches of `batch_size` pages so a 1000+ page scan never
        holds all rendered bitmaps in memory at once (all-at-once would OOM
        at ~12GB of raw RGB for a 1100-page A4 scan).
        """
        try:
            import pdf2image  # noqa: F401
            from pdf2image import convert_from_bytes
        except ImportError as e:
            raise PDFExtractionError(f"OCR requires pdf2image: {e}") from e

        result: dict[int, str] = {}
        sorted_pages = sorted(page_numbers)

        for i in range(0, len(sorted_pages), batch_size):
            chunk = sorted_pages[i : i + batch_size]
            images = convert_from_bytes(
                raw_bytes,
                dpi=dpi,
                first_page=chunk[0],
                last_page=chunk[-1],
                fmt="png",
                thread_count=2,
            )
            for offset, img in enumerate(images):
                pg = chunk[0] + offset
                if pg not in page_numbers:
                    continue
                text = IngestionService._paddle_ocr_image(img, lang=lang)
                if text:
                    result[pg] = text

        return result

    @staticmethod
    def _paddle_ocr_image(img: Any, lang: str = "chi_sim") -> str:
        """OCR one rendered page image with RapidOCR, tesseract fallback.

        Returns the page text in reading order (right-to-left columns for
        vertical pages, top-to-bottom rows for horizontal pages), or '' when
        neither engine is available / both fail.
        """
        try:
            from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        except ImportError:
            return IngestionService._tesseract_ocr_image(img, lang=lang)

        try:
            import numpy as np

            ocr = _get_rapid_ocr()
            res, _elapse = ocr(np.array(img))
            return IngestionService._paddle_reorder(res)
        except Exception:
            return IngestionService._tesseract_ocr_image(img, lang=lang)

    @staticmethod
    def _paddle_reorder(res: Any) -> str:
        """Reorder OCR line boxes into reading order.

        Accepts RapidOCR result shape: list of [box, text, score_str], or None.
        Detects vertical layout (classical Chinese columns read right-to-left)
        vs horizontal, then emits lines in the correct sequence joined by
        newlines. Column clustering uses a fixed 40px center gap.
        """
        if not res:
            return ""
        lines: list[dict[str, Any]] = []
        for line in res:
            box, txt, _score = line[0], line[1], line[2]
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            x0, y0 = min(xs), min(ys)
            x1, y1 = max(xs), max(ys)
            w, h = x1 - x0, y1 - y0
            lines.append(
                {"x": x0, "y": y0, "cx": (x0 + x1) / 2, "w": w, "h": h, "txt": txt}
            )
        if not lines:
            return ""
        n_vert = sum(1 for ln in lines if ln["h"] > ln["w"] * 1.5)
        n_horiz = sum(1 for ln in lines if ln["w"] > ln["h"] * 1.5)
        if n_vert > n_horiz:
            # Vertical layout: columns right-to-left, lines top-to-bottom.
            lines.sort(key=lambda ln: -ln["cx"])
            cols: list[dict[str, Any]] = []
            for ln in lines:
                placed = False
                for c in cols:
                    if abs(c["cx"] - ln["cx"]) < 40:
                        c["lines"].append(ln)
                        placed = True
                        break
                if not placed:
                    cols.append({"cx": ln["cx"], "lines": [ln]})
            ordered: list[str] = []
            for c in cols:
                c["lines"].sort(key=lambda ln: ln["y"])
                ordered.extend(ln["txt"] for ln in c["lines"])
            return "\n".join(ordered)
        # Horizontal layout: top-to-bottom, then left-to-right.
        lines.sort(key=lambda ln: (round(ln["y"] / 25), ln["x"]))
        return "\n".join(ln["txt"] for ln in lines)

    @staticmethod
    def _tesseract_ocr_image(img: Any, lang: str = "chi_sim") -> str:
        """Legacy tesseract OCR fallback for a single rendered page image."""
        try:
            import pytesseract
        except ImportError:
            return ""
        try:
            text = pytesseract.image_to_string(img, lang=lang, config="--psm 6")
        except (OSError, RuntimeError):
            text = ""
        return text.strip() if text and text.strip() else ""
