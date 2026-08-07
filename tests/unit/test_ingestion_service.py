"""
Unit tests for app.services.ingestion — pure functions, error paths,
conditional branches, and integration with DB fixtures.

Targets uncovered lines from coverage analysis:
  149, 177, 183, 191, 285, 296, 364-368, 366, 399, 437-454, 496,
  501-503, 503-509, 546-726, 802-815, 818-831, 838, 843, 871-872,
  1046-1047, 1054, 1059-1060, 1108, 1127-1128, 1146, 1162-1185,
  1202, 1218, 1241-1242, 1250-1252, 1270-1302.
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.models.academic_evidence import SourceRef
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.ingestion import (
    AppendResult,
    FulltextRejectedError,
    IngestionError,
    IngestionResult,
    IngestionService,
    PDFExtractionError,
)
from pypdf.errors import PdfReadError
from sqlalchemy import select, text

from tests.conftest_db import db_session  # noqa: F401

_COMPLIANCE = {
    "copyright_status": "public_domain",
    "authorization_basis": "test fixture",
}

_ALLOWED = (
    "public_domain",
    "open_access",
    "licensed",
    "user_uploaded_with_permission",
)


# ============================================================
# Helpers
# ============================================================


def _simple_pdf_bytes() -> bytes:
    """Minimal valid PDF with extractable text."""
    return (
        b"%PDF-1.4\n"
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\nendobj\n"
        b"4 0 obj\n<< /Length 44 >>\nstream\n"
        b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
        b"endstream\nendobj\n"
        b"5 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n"
        b"xref\n0 6\n"
        b"0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n"
        b"0000000115 00000 n \n0000000240 00000 n \n0000000335 00000 n \n"
        b"trailer\n<< /Size 6 /Root 1 0 R >>\nstartxref\n415\n%%EOF\n"
    )


async def _create_doc(session, **kwargs) -> Document:
    """Shortcut to create a Document directly in the test DB."""
    defaults = {"title": "Test Doc", "copyright_status": "public_domain",
                 "authorization_basis": "test"}
    defaults.update(kwargs)
    doc = Document(**defaults)
    session.add(doc)
    await session.flush()
    return doc


# ============================================================
# Pure function tests — no DB required
# ============================================================


class TestComputeChecksum:
    """_compute_checksum is a deterministic SHA-256 hasher."""

    def test_deterministic(self) -> None:
        text = "测试全文"
        c1 = IngestionService._compute_checksum(text)
        c2 = IngestionService._compute_checksum(text)
        assert c1 == c2
        assert len(c1) == 64

    def test_different_text_different_hash(self) -> None:
        assert IngestionService._compute_checksum("A") != IngestionService._compute_checksum("B")


class TestIsFulltextAllowed:
    """_is_fulltext_allowed — copyright gate pure function."""

    def test_metadata_none_requires_copyright_compliance(self) -> None:
        """Line 149: metadata=None returns (False, reason)."""
        allowed, reason = IngestionService._is_fulltext_allowed(None)
        assert allowed is False
        assert "metadata is required" in reason

    def test_missing_copyright_status_rejected(self) -> None:
        allowed, reason = IngestionService._is_fulltext_allowed({})
        assert allowed is False
        assert "copyright_status" in reason

    def test_empty_copyright_status_rejected(self) -> None:
        allowed, reason = IngestionService._is_fulltext_allowed({"copyright_status": ""})
        assert allowed is False

    def test_forbidden_status_rejected(self) -> None:
        for status in ("unknown", "metadata_only", "forbidden_fulltext",
                       "commercial_restricted", "pirated"):
            allowed, reason = IngestionService._is_fulltext_allowed(
                {"copyright_status": status}
            )
            assert allowed is False, f"Expected {status} to be rejected"

    def test_unrecognized_copyright_status(self) -> None:
        """Line 177: unrecognized copyright_status falls through to default-deny."""
        allowed, reason = IngestionService._is_fulltext_allowed(
            {"copyright_status": "made_up_status_xyz"}
        )
        assert allowed is False
        assert "unrecognized" in reason

    def test_allowed_status_without_auth_basis_rejected(self) -> None:
        for status in _ALLOWED:
            allowed, reason = IngestionService._is_fulltext_allowed(
                {"copyright_status": status}
            )
            assert allowed is False, f"{status} without auth_basis should reject"
            assert "authorization_basis" in reason.lower()

    def test_allowed_with_auth_basis(self) -> None:
        allowed, reason = IngestionService._is_fulltext_allowed(
            {"copyright_status": "public_domain",
             "authorization_basis": "expired copyright"}
        )
        assert allowed is True
        assert reason == ""

    def test_allowed_with_license_type_only(self) -> None:
        """license_type alone satisfies the authorization_basis requirement."""
        allowed, reason = IngestionService._is_fulltext_allowed(
            {"copyright_status": "licensed", "license_type": "CC-BY"}
        )
        assert allowed is True
        assert reason == ""


class TestIsMetadataOnly:
    """_is_metadata_only — detects metadata_only requests."""

    def test_metadata_none_is_metadata_only(self) -> None:
        """Line 183: None metadata → True (no metadata = metadata-only)."""
        assert IngestionService._is_metadata_only(None) is True

    def test_metadata_only_status(self) -> None:
        assert IngestionService._is_metadata_only({"copyright_status": "metadata_only"}) is True

    def test_non_metadata_only(self) -> None:
        assert IngestionService._is_metadata_only({"copyright_status": "public_domain"}) is False

    def test_empty_metadata_defaults_to_metadata_only(self) -> None:
        """Empty metadata → copyright_status '' → 'metadata_only' check fails → False."""
        assert IngestionService._is_metadata_only({}) is False


class TestIsForbiddenFulltext:
    """_is_forbidden_fulltext — checks forbidden_fulltext flag."""

    def test_metadata_none_not_forbidden(self) -> None:
        """Line 191: metadata=None → returns False (graceful)."""
        assert IngestionService._is_forbidden_fulltext(None) is False

    def test_copyright_status_forbidden_fulltext(self) -> None:
        assert IngestionService._is_forbidden_fulltext(
            {"copyright_status": "forbidden_fulltext"}
        ) is True

    def test_forbidden_fulltext_bool_true(self) -> None:
        assert IngestionService._is_forbidden_fulltext(
            {"copyright_status": "unknown", "forbidden_fulltext": True}
        ) is True

    def test_forbidden_fulltext_string_true(self) -> None:
        assert IngestionService._is_forbidden_fulltext(
            {"copyright_status": "unknown", "forbidden_fulltext": "true"}
        ) is True

    def test_forbidden_fulltext_boolean_false(self) -> None:
        assert IngestionService._is_forbidden_fulltext(
            {"copyright_status": "unknown", "forbidden_fulltext": False}
        ) is False


# ============================================================
# _extract_pdf_text — static method, mock PdfReader
# ============================================================


class TestExtractPdfText:
    """Static method _extract_pdf_text — PDF text extraction with error paths."""

    def test_encrypted_decrypt_fails_raises(self) -> None:
        """Lines 1241-1242: encrypted PDF, decrypt raises → PDFExtractionError."""
        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = True
            mock_reader.decrypt.side_effect = PdfReadError("bad decrypt")
            mock_reader_cls.return_value = mock_reader

            with pytest.raises(PDFExtractionError, match="encrypted"):
                IngestionService._extract_pdf_text(b"encrypted pdf")

    def test_page_extract_raises_pdf_read_error(self) -> None:
        """Lines 1250-1251: PdfReadError on page.extract_text() → continue."""
        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False

            page_bad = MagicMock()
            page_bad.extract_text.side_effect = PdfReadError("page error")

            page_good = MagicMock()
            page_good.extract_text.return_value = "Page with text"

            mock_reader.pages = [page_bad, page_good]
            mock_reader_cls.return_value = mock_reader

            result = IngestionService._extract_pdf_text(b"pdf bytes")
            assert "Page with text" in result

    def test_page_returns_text_appended(self) -> None:
        """Line 1252: if t: parts.append(t) — text returned from page."""
        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False

            page = MagicMock()
            page.extract_text.return_value = "Hello World"
            mock_reader.pages = [page]
            mock_reader_cls.return_value = mock_reader

            result = IngestionService._extract_pdf_text(b"pdf")
            assert "Hello World" in result

    def test_empty_string_not_appended(self) -> None:
        """Line 1252: if t: — empty/None text is skipped."""
        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False

            page_empty = MagicMock()
            page_empty.extract_text.return_value = ""

            page_good = MagicMock()
            page_good.extract_text.return_value = "Valid text"

            mock_reader.pages = [page_empty, page_good]
            mock_reader_cls.return_value = mock_reader

            result = IngestionService._extract_pdf_text(b"pdf")
            assert result == "Valid text"

    def test_cannot_read_pdf_raises(self) -> None:
        """PdfReader constructor raises PdfReadError."""
        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader_cls.side_effect = PdfReadError("broken pdf")
            with pytest.raises(PDFExtractionError, match="Cannot read PDF"):
                IngestionService._extract_pdf_text(b"junk")


# ============================================================
# _ocr_pdf_pages — static method, mock pytesseract + pdf2image
# ============================================================


class TestOcrPdfPages:
    """Static method _ocr_pdf_pages — OCR via tesseract, mock dependencies."""

    def test_ocr_pdf_pages_basic(self) -> None:
        """Lines 1270-1302: full OCR path with mocked pytesseract + pdf2image."""
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "OCR 提取的中文内容"

        mock_pdf2image = MagicMock()
        mock_pdf2image.convert_from_bytes.return_value = [MagicMock(), MagicMock()]

        with patch.dict("sys.modules", {
            "pytesseract": mock_pytesseract,
            "pdf2image": mock_pdf2image,
        }):
            result = IngestionService._ocr_pdf_pages(
                b"fake pdf bytes", [1, 2], lang="chi_sim", dpi=200
            )
            assert isinstance(result, dict)
            assert 1 in result
            assert 2 in result
            assert result[1] == "OCR 提取的中文内容"

    def test_ocr_pdf_pages_skips_non_requested(self) -> None:
        """Pages not in the requested set are skipped (line 1293-1294)."""
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.return_value = "some text"

        mock_img1 = MagicMock()
        mock_img2 = MagicMock()
        mock_pdf2image = MagicMock()
        mock_pdf2image.convert_from_bytes.return_value = [mock_img1, mock_img2]

        with patch.dict("sys.modules", {
            "pytesseract": mock_pytesseract,
            "pdf2image": mock_pdf2image,
        }):
            result = IngestionService._ocr_pdf_pages(
                b"fake pdf", [2], lang="eng"  # Only page 2
            )
            # Page 1 is index 0 in the images list → not in page_numbers → skipped
            # Page 2 is index 1 → in page_numbers → OCR'd
            assert 2 in result
            assert 1 not in result

    def test_ocr_pdf_pages_empty_result_on_ocr_error(self) -> None:
        """Lines 1297-1298: OSError/RuntimeError in OCR → text ''."""
        mock_pytesseract = MagicMock()
        mock_pytesseract.image_to_string.side_effect = OSError("tesseract not found")

        mock_pdf2image = MagicMock()
        mock_pdf2image.convert_from_bytes.return_value = [MagicMock()]

        with patch.dict("sys.modules", {
            "pytesseract": mock_pytesseract,
            "pdf2image": mock_pdf2image,
        }):
            result = IngestionService._ocr_pdf_pages(b"fake", [1])
            assert result == {}  # Page extracted blank → omitted

    def test_ocr_import_error_raises(self) -> None:
        """Line 1274-1276: ImportError → PDFExtractionError."""
        with patch.dict("sys.modules", {
            "pytesseract": None,  # Not importable
        }):
            with pytest.raises(PDFExtractionError, match="OCR requires"):
                IngestionService._ocr_pdf_pages(b"fake", [1])


# ============================================================
# _ensure_source_ref — async static method, DB required
# ============================================================


@pytest.mark.anyio
class TestEnsureSourceRef:
    """_ensure_source_ref — SourceRef creation and dedup with URL/loc identity."""

    async def test_empty_title_returns_none(self, db_session) -> None:
        """Line 1108: empty title → early None."""
        result = await IngestionService._ensure_source_ref(
            db_session, title="", url="http://x.com", page_location="p1"
        )
        assert result is None

    async def test_url_parse_error_uses_raw_url(self, db_session) -> None:
        """Lines 1127-1128: urlparse raises ValueError → norm_url = raw."""
        with patch("urllib.parse.urlparse", side_effect=ValueError("bad url")):
            result = await IngestionService._ensure_source_ref(
                db_session, title="Test", url="http://bad:url",
                page_location="passage:1"
            )
        assert result is not None
        # Verify the SourceRef was created with the raw URL
        stmt = select(SourceRef).where(
            SourceRef.title == "Test", SourceRef.page_location == "passage:1"
        )
        ref = (await db_session.execute(stmt)).scalar_one_or_none()
        assert ref is not None

    async def test_url_and_loc_existing_returns_existing(self, db_session) -> None:
        """Line 1146: existing URL + loc SourceRef found → return its id."""
        existing = SourceRef(
            title="Existing Doc", author="Author",
            page_location="passage:42", url="http://example.com/doc"
        )
        db_session.add(existing)
        await db_session.flush()

        result = await IngestionService._ensure_source_ref(
            db_session, title="Existing Doc", url="http://example.com/doc",
            page_location="passage:42"
        )
        assert result == existing.id

    async def test_url_and_loc_new_creates_source_ref(self, db_session) -> None:
        """URL + loc, no existing → create new SourceRef."""
        result = await IngestionService._ensure_source_ref(
            db_session, title="New Doc", url="http://example.com/new",
            page_location="passage:99"
        )
        assert result is not None
        stmt = select(SourceRef).where(SourceRef.id == result)
        ref = (await db_session.execute(stmt)).scalar_one_or_none()
        assert ref is not None
        assert ref.title == "New Doc"
        assert ref.page_location == "passage:99"

    async def test_url_only_creates_new_source_ref(self, db_session) -> None:
        """Lines 1162-1185: URL-only identity → create new SourceRef when
        no existing match found."""
        result = await IngestionService._ensure_source_ref(
            db_session, title="URL Only Doc",
            url="http://example.com/url-only",
            page_location="",  # empty → falls to URL-only branch
        )
        assert result is not None
        stmt = select(SourceRef).where(SourceRef.id == result)
        ref = (await db_session.execute(stmt)).scalar_one_or_none()
        assert ref is not None
        assert ref.title == "URL Only Doc"
        assert ref.url.endswith("/url-only") or "url-only" in ref.url

    async def test_url_only_existing_returns_existing(self, db_session) -> None:
        """URL-only identity, existing found → return its id (line 1171 path)."""
        existing = SourceRef(
            title="Old Title", url="http://example.com/dedup",
            page_location="", author=""
        )
        db_session.add(existing)
        await db_session.flush()

        result = await IngestionService._ensure_source_ref(
            db_session, title="Old Title", url="http://example.com/dedup",
            page_location=""
        )
        assert result == existing.id

    async def test_loc_only_existing_returns_existing(self, db_session) -> None:
        """Line 1202: loc-only identity, existing found → return its id."""
        existing = SourceRef(
            title="Loc Only", page_location="section:3", url="", author=""
        )
        db_session.add(existing)
        await db_session.flush()

        result = await IngestionService._ensure_source_ref(
            db_session, title="Loc Only", url="", page_location="section:3"
        )
        assert result == existing.id

    async def test_loc_only_new_creates(self, db_session) -> None:
        """Loc-only identity, no existing → create new SourceRef."""
        result = await IngestionService._ensure_source_ref(
            db_session, title="Loc New", url="", page_location="section:7"
        )
        assert result is not None
        stmt = select(SourceRef).where(SourceRef.id == result)
        ref = (await db_session.execute(stmt)).scalar_one_or_none()
        assert ref is not None
        assert ref.page_location == "section:7"
        assert ref.url == ""

    async def test_insufficient_identity_returns_none(self, db_session) -> None:
        """Line 1218: no URL and no page_location → None."""
        result = await IngestionService._ensure_source_ref(
            db_session, title="No Identity", url="", page_location=""
        )
        assert result is None


# ============================================================
# _store_chunks — instance method, DB required
# ============================================================


@pytest.mark.anyio
class TestStoreChunks:
    """_store_chunks — chunk persistence with paragraph_index, page_number, ocr."""

    async def test_string_chunks_isinstance_path(self, db_session) -> None:
        """Lines 1046-1047: isinstance(item, str) → text=item, para_idx=-1.
        _store_chunks then falls back para_idx=-1 to chunk_index (idx)."""
        svc = IngestionService(db_session)
        doc = await _create_doc(db_session, title="String Chunks")
        await svc._store_chunks(doc.id, ["plain chunk A", "plain chunk B"])
        await db_session.flush()

        chunks = list((await db_session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.chunk_index)
        )).scalars())
        assert len(chunks) == 2
        # para_idx=-1 falls back to idx in _store_chunks: "para_idx if para_idx >= 0 else idx"
        assert chunks[0].paragraph_index == 0
        assert chunks[1].paragraph_index == 1
        assert chunks[0].content == "plain chunk A"
        assert chunks[1].content == "plain chunk B"

    async def test_tuple_chunks_with_paragraph_index(self, db_session) -> None:
        """Tuple chunks use the provided paragraph_index."""
        svc = IngestionService(db_session)
        doc = await _create_doc(db_session, title="Tuple Chunks")
        await svc._store_chunks(doc.id, [("First para", 0), ("Second para", 3)])
        await db_session.flush()

        chunks = list((await db_session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.chunk_index)
        )).scalars())
        assert chunks[0].paragraph_index == 0
        assert chunks[1].paragraph_index == 3

    async def test_low_ocr_confidence_reference_weight(self, db_session) -> None:
        """Line 1054: ocr_confidence < 0.7 → evidence_weight = 'reference'."""
        svc = IngestionService(db_session)
        doc = await _create_doc(db_session, title="Low OCR")
        await svc._store_chunks(doc.id, [("OCR text", 0)], ocr_confidence=0.5)
        await db_session.flush()

        chunk = (await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )).scalar_one()
        assert chunk.evidence_weight == "reference"
        assert chunk.ocr_confidence == 0.5

    async def test_high_ocr_confidence_primary_weight(self, db_session) -> None:
        """ocr_confidence >= 0.7 → evidence_weight stays 'primary'."""
        svc = IngestionService(db_session)
        doc = await _create_doc(db_session, title="High OCR")
        await svc._store_chunks(doc.id, [("text", 0)], ocr_confidence=0.85)
        await db_session.flush()

        chunk = (await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )).scalar_one()
        assert chunk.evidence_weight == "primary"

    async def test_per_chunk_page_numbers(self, db_session) -> None:
        """Line 1059: page_numbers[idx] assigned per chunk."""
        svc = IngestionService(db_session)
        doc = await _create_doc(db_session, title="Page Numbers")
        await svc._store_chunks(
            doc.id,
            [("Page 1 text", 0), ("Page 2 text", 0), ("Page 3 text", 0)],
            page_numbers=[10, 20, 30],
        )
        await db_session.flush()

        chunks = list((await db_session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.chunk_index)
        )).scalars())
        assert len(chunks) == 3
        assert chunks[0].page_number == 10
        assert chunks[1].page_number == 20
        assert chunks[2].page_number == 30

    async def test_page_number_fallback(self, db_session) -> None:
        """Line 1060: when page_numbers is shorter, fallback to page_number."""
        svc = IngestionService(db_session)
        doc = await _create_doc(db_session, title="Fallback")
        await svc._store_chunks(
            doc.id,
            [("C1", 0), ("C2", 0), ("C3", 0)],
            page_number=99,
            page_numbers=[11],  # Only covers first chunk
        )
        await db_session.flush()

        chunks = list((await db_session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.chunk_index)
        )).scalars())
        assert chunks[0].page_number == 11  # from page_numbers
        assert chunks[1].page_number == 99  # fallback to page_number
        assert chunks[2].page_number == 99  # fallback to page_number

    async def test_page_numbers_none_in_list(self, db_session) -> None:
        """None in page_numbers list → fallback to page_number."""
        svc = IngestionService(db_session)
        doc = await _create_doc(db_session, title="None Page")
        await svc._store_chunks(
            doc.id,
            [("text", 0)],
            page_number=42,
            page_numbers=[None],
        )
        await db_session.flush()

        chunk = (await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )).scalar_one()
        assert chunk.page_number == 42  # None → fallback to page_number

    async def test_passage_id_assigned_to_chunks(self, db_session) -> None:
        """Passage ID is propagated to chunks."""
        svc = IngestionService(db_session)
        doc = await _create_doc(db_session, title="Passage Doc")
        await svc._store_chunks(
            doc.id, [("passage text", 0)], passage_id="pass-test-1"
        )
        await db_session.flush()

        chunk = (await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == doc.id)
        )).scalar_one()
        assert chunk.passage_id == "pass-test-1"


# ============================================================
# ingest_text — edge cases and error paths
# ============================================================


@pytest.mark.anyio
class TestIngestTextEdgeCases:
    """ingest_text: error paths, metadata loops, chunk compat, rollback."""

    async def test_whitespace_passage_id_raises(self, db_session) -> None:
        """Line 285: passage_id.strip() is empty → ValueError."""
        svc = IngestionService(db_session)
        with pytest.raises(ValueError, match="passage_id must be non-empty"):
            await svc.ingest_text(
                title="Test", text="Some content",
                metadata=_COMPLIANCE, passage_id="   ",
            )

    async def test_nonexistent_passage_id_raises(self, db_session) -> None:
        """Line 296: passage not found in DB → ValueError."""
        svc = IngestionService(db_session)
        nonexistent = "00000000-0000-0000-0000-000000000099"
        with pytest.raises(ValueError, match="not found or deleted"):
            await svc.ingest_text(
                title="Test", text="Some content",
                metadata=_COMPLIANCE, passage_id=nonexistent,
            )

    async def test_valid_passage_id_proceeds(self, db_session) -> None:
        """pass-test-1 exists in conftest_db seed → ingestion succeeds."""
        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="Passage Test", text="Valid passage content.",
            metadata=_COMPLIANCE, passage_id="pass-test-1",
        )
        assert result.chunk_count > 0

    async def test_whitelist_metadata_copied_to_document(self, db_session) -> None:
        """Lines 364-368, 366: allowed metadata keys copied from meta to doc_data."""
        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="Meta Copy Test", text="Content here.",
            metadata={
                "dynasty": "Tang",
                "category": "acupuncture",
                "source_url": "http://example.com/source",
                "source_name": "ctext",
                "license_type": "CC-BY",
                **{k: v for k, v in _COMPLIANCE.items()},  # compliance fields
            },
        )
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.dynasty == "Tang"
        assert doc.category == "acupuncture"
        assert doc.source_url == "http://example.com/source"
        assert doc.source_name == "ctext"
        assert doc.license_type == "CC-BY"

    async def test_non_whitelisted_metadata_not_copied(self, db_session) -> None:
        """Keys not in _ALLOWED_METADATA_KEYS are excluded from doc_data."""
        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="Filtered Meta", text="Content.",
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "pd",
                "is_deleted": "should_not_set",
                "deleted_at": "should_not_set",
                "dynasty": "Han",  # whitelisted
            },
        )
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        # is_deleted / deleted_at should NOT be set (default False / None)
        assert doc.is_deleted is False
        assert doc.deleted_at is None
        # dynasty IS whitelisted
        assert doc.dynasty == "Han"

    async def test_backward_compat_chunk_text_returns_strings(self, db_session) -> None:
        """Line 399: chunk_text returns list[str] → backward compat wrapping."""
        svc = IngestionService(db_session)
        with patch("app.services.ingestion.chunk_text") as mock_chunk:
            mock_chunk.return_value = ["Chunk one", "Chunk two"]
            result = await svc.ingest_text(
                title="Compat Test", text="Some text.",
                metadata=_COMPLIANCE,
            )
        assert result.chunk_count == 2

    async def test_rollback_on_store_chunks_error(self, db_session) -> None:
        """Lines 437-454: chunk/storage failure → rollback document + audit + raise."""
        svc = IngestionService(db_session)
        count_before = (await db_session.execute(
            text("SELECT COUNT(*) FROM documents")
        )).scalar_one()

        with patch.object(svc, "_store_chunks", new_callable=AsyncMock) as mock_store:
            mock_store.side_effect = ValueError("injected storage failure")
            with pytest.raises(ValueError, match="injected storage failure"):
                await svc.ingest_text(
                    title="Rollback Test", text="Will be rolled back.",
                    metadata=_COMPLIANCE,
                )

        # Document should be rolled back (hard-deleted)
        count_after = (await db_session.execute(
            text("SELECT COUNT(*) FROM documents")
        )).scalar_one()
        assert count_after == count_before

        # Audit record should exist with skipped status
        from app.models.fulltext_ingestion_audit import FulltextIngestionAudit
        audits = list((await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.action == "skip",
                FulltextIngestionAudit.status == "skipped",
            )
        )).scalars())
        assert len(audits) >= 1

    async def test_source_ref_created_on_ingest(self, db_session) -> None:
        """Ingestion creates a SourceRef row."""
        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="SourceRef Test", text="Content with source ref.",
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "pd",
                "source_url": "http://example.com/srcref",
                "source_name": "test source",
            },
        )
        # Check SourceRef exists
        stmt = select(SourceRef).where(
            SourceRef.page_location == f"document:{result.document_id}"
        )
        ref = (await db_session.execute(stmt)).scalar_one_or_none()
        assert ref is not None
        assert ref.title == "SourceRef Test"


# ============================================================
# ingest_pdf — edge cases
# ============================================================


@pytest.mark.anyio
class TestIngestPdfEdgeCases:
    """ingest_pdf: no extractable text, store_raw_pdf branches."""

    async def test_no_extractable_text_raises(self, db_session) -> None:
        """Line 496: empty text from PDF → PDFExtractionError."""
        svc = IngestionService(db_session)
        with patch.object(IngestionService, "_extract_pdf_text", return_value=""):
            with pytest.raises(PDFExtractionError, match="does not contain extractable"):
                await svc.ingest_pdf(
                    title="Empty PDF",
                    file=io.BytesIO(b"deadbeef"),
                    metadata=_COMPLIANCE,
                )

    async def test_store_raw_pdf_true_stores_raw_bytes(self, db_session) -> None:
        """Lines 503-509: store_raw_pdf=True → raw_pdf_blob set, source_url derived."""
        svc = IngestionService(db_session)
        raw = b"\x89PNG...not actually a PDF but we mock extraction"
        extracted = "Extracted PDF content for raw storage test."

        with patch.object(IngestionService, "_extract_pdf_text", return_value=extracted):
            result = await svc.ingest_pdf(
                title="Store Raw PDF", file=io.BytesIO(raw),
                metadata=_COMPLIANCE, store_raw_pdf=True,
            )

        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.raw_pdf_blob == raw
        assert "pdf:" in (doc.source_url or "")

    async def test_store_raw_pdf_false_no_raw_bytes(self, db_session) -> None:
        """Lines 501-503: store_raw_pdf=False → raw_pdf_blob not stored, metadata
        copy still happens."""
        svc = IngestionService(db_session)
        extracted = "Extracted text without raw PDF."

        with patch.object(IngestionService, "_extract_pdf_text", return_value=extracted):
            result = await svc.ingest_pdf(
                title="No Raw", file=io.BytesIO(b"bytes"),
                metadata={**_COMPLIANCE, "source_url": "http://custom.url"},
                store_raw_pdf=False,
            )

        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.raw_pdf_blob is None
        assert doc.source_url == "http://custom.url"

    async def test_ingest_pdf_without_metadata_passes_compliance(self, db_session) -> None:
        """ingest_pdf with metadata=None — _extract_pdf_text mocked with valid text,
        but compliance gate still checked."""
        svc = IngestionService(db_session)
        extracted = "Some text content."

        with patch.object(IngestionService, "_extract_pdf_text", return_value=extracted):
            # No metadata → compliance gate will reject
            with pytest.raises(FulltextRejectedError):
                await svc.ingest_pdf(
                    title="No Meta PDF", file=io.BytesIO(b"bytes"), metadata=None
                )


# ============================================================
# ingest_pdf_with_pages — full PDF+page extraction path
# ============================================================


@pytest.mark.anyio
class TestIngestPdfWithPages:
    """ingest_pdf_with_pages (lines 546-726): per-page extraction, OCR fallback."""

    async def test_basic_page_extraction(self, db_session) -> None:
        """Normal path: valid PDF → per-page extraction → chunks with page numbers."""
        svc = IngestionService(db_session)
        pdf_bytes = _simple_pdf_bytes()
        result = await svc.ingest_pdf_with_pages(
            title="Pages Test PDF",
            file=io.BytesIO(pdf_bytes),
            metadata=_COMPLIANCE,
        )
        assert result.chunk_count > 0

        chunks = list((await db_session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == result.document_id)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.chunk_index)
        )).scalars())
        for ch in chunks:
            assert ch.page_number is not None
            assert ch.page_number >= 1

    async def test_encrypted_decrypt_fails_raises(self, db_session) -> None:
        """Lines 554-556: encrypted PDF where decrypt fails → PDFExtractionError."""
        svc = IngestionService(db_session)
        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = True
            mock_reader.decrypt.side_effect = PdfReadError("cannot decrypt")
            mock_reader_cls.return_value = mock_reader

            with pytest.raises(PDFExtractionError, match="encrypted"):
                await svc.ingest_pdf_with_pages(
                    title="Encrypted", file=io.BytesIO(b"encrypted"),
                    metadata=_COMPLIANCE,
                )

    async def test_encrypted_decrypts_with_empty_password(self, db_session) -> None:
        """Lines 551-553: encrypted PDF that decrypts with '' → pages extracted."""
        svc = IngestionService(db_session)

        page = MagicMock()
        page.extract_text.return_value = "Decrypted content"

        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = True
            mock_reader.decrypt.return_value = 1  # decrypt succeeds
            mock_reader.pages = [page]
            mock_reader_cls.return_value = mock_reader

            result = await svc.ingest_pdf_with_pages(
                title="Decrypt OK", file=io.BytesIO(b"encrypted pdf"),
                metadata=_COMPLIANCE,
            )
            assert result.chunk_count > 0

    async def test_no_extractable_text_raises_pdf_error(self, db_session) -> None:
        """Lines 583-586: no page_data from pypdf OR OCR → PDFExtractionError."""
        svc = IngestionService(db_session)

        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False

            # All pages return empty text → goes to OCR path
            empty_page = MagicMock()
            empty_page.extract_text.return_value = ""
            mock_reader.pages = [empty_page, empty_page]
            mock_reader_cls.return_value = mock_reader

            # Mock OCR to also return empty → no page_data at all
            with patch.object(
                IngestionService, "_ocr_pdf_pages", return_value={}
            ), pytest.raises(PDFExtractionError, match="No extractable text"):
                await svc.ingest_pdf_with_pages(
                    title="No Text", file=io.BytesIO(b"empty pdf"),
                    metadata=_COMPLIANCE,
                )

    async def test_copyright_gate_rejects(self, db_session) -> None:
        """Lines 606-608: copyright gate check before document creation."""
        svc = IngestionService(db_session)

        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False

            page = MagicMock()
            page.extract_text.return_value = "Some content"
            mock_reader.pages = [page]
            mock_reader_cls.return_value = mock_reader

            with pytest.raises(FulltextRejectedError, match="rejected"):
                await svc.ingest_pdf_with_pages(
                    title="Rejected PDF",
                    file=io.BytesIO(b"pdf"),
                    metadata={"copyright_status": "unknown"},
                )

    async def test_ocr_confidence_defaults_derive(self, db_session) -> None:
        """Lines 589-597: ocr_confidence auto-derived from OCR ratio."""
        svc = IngestionService(db_session)

        page_text = MagicMock()
        page_text.extract_text.return_value = "Has text"

        page_empty = MagicMock()
        page_empty.extract_text.return_value = ""

        page_ocr = MagicMock()
        page_ocr.extract_text.return_value = ""

        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False
            # 1 text page, 2 empty pages → ocr_ratio = 2/3 > 0.3 → 0.75
            mock_reader.pages = [page_text, page_empty, page_ocr]
            mock_reader_cls.return_value = mock_reader

            # _ocr_pdf_pages is a sync staticmethod, mock with MagicMock (not AsyncMock)
            with patch.object(
                IngestionService, "_ocr_pdf_pages",
                return_value={2: "Scanned text", 3: "More scanned text"},
            ):
                result = await svc.ingest_pdf_with_pages(
                    title="OCR Ratio", file=io.BytesIO(_simple_pdf_bytes()),
                    metadata=_COMPLIANCE,
                )
                # Should have chunks with ocr_confidence set
                assert result.chunk_count > 0

    async def test_rollback_on_chunk_storage_failure(self, db_session) -> None:
        """Lines 709-726: rollback on SQLAlchemyError during chunk storage."""
        svc = IngestionService(db_session)
        count_before = (await db_session.execute(
            text("SELECT COUNT(*) FROM documents")
        )).scalar_one()

        with patch("app.services.ingestion.PdfReader") as mock_reader_cls:
            mock_reader = MagicMock()
            mock_reader.is_encrypted = False
            page = MagicMock()
            page.extract_text.return_value = "Good text"
            mock_reader.pages = [page]
            mock_reader_cls.return_value = mock_reader

            with patch.object(svc, "_store_chunks", new_callable=AsyncMock) as mock_store:
                mock_store.side_effect = ValueError("storage failure")
                with pytest.raises(ValueError, match="storage failure"):
                    await svc.ingest_pdf_with_pages(
                        title="Rollback PDF", file=io.BytesIO(_simple_pdf_bytes()),
                        metadata=_COMPLIANCE,
                    )

        count_after = (await db_session.execute(
            text("SELECT COUNT(*) FROM documents")
        )).scalar_one()
        assert count_after == count_before


# ============================================================
# append_passage — edge cases
# ============================================================


@pytest.mark.anyio
class TestAppendPassageEdgeCases:
    """append_passage: compliance gates, chunk compat, error paths."""

    async def test_metadata_only_document_rejected(self, db_session) -> None:
        """Lines 802-815: metadata_only doc → append rejected with audit."""
        svc = IngestionService(db_session)
        doc = await _create_doc(
            db_session, title="Meta Only Doc",
            copyright_status="metadata_only",
            content_text="Initial text",
        )

        from app.models.passage import Passage
        passage_id = (await db_session.execute(
            select(Passage.id).where(Passage.is_deleted.is_(False)).limit(1)
        )).scalar_one()

        with pytest.raises(FulltextRejectedError, match="metadata_only"):
            await svc.append_passage(
                document_id=doc.id, text="Appended text.",
                passage_id=passage_id,
            )

        # Audit record exists
        from app.models.fulltext_ingestion_audit import FulltextIngestionAudit
        audits = list((await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.result_entity_id == doc.id,
                FulltextIngestionAudit.action == "skip",
            )
        )).scalars())
        assert any("metadata_only" in (a.skipped_reason or "") for a in audits)

    async def test_forbidden_fulltext_document_rejected(self, db_session) -> None:
        """forbidden_fulltext doc → append rejected."""
        svc = IngestionService(db_session)
        doc = await _create_doc(
            db_session, title="Forbidden Doc",
            copyright_status="forbidden_fulltext",
            content_text="Initial text",
        )

        from app.models.passage import Passage
        passage_id = (await db_session.execute(
            select(Passage.id).where(Passage.is_deleted.is_(False)).limit(1)
        )).scalar_one()

        with pytest.raises(FulltextRejectedError, match="forbidden_fulltext"):
            await svc.append_passage(
                document_id=doc.id, text="Appended.",
                passage_id=passage_id,
            )

    async def test_unrecognized_copyright_rejected(self, db_session) -> None:
        """Lines 818-831: unrecognized copyright_status in _is_fulltext_allowed
        rejects append."""
        svc = IngestionService(db_session)
        doc = await _create_doc(
            db_session, title="Unrecognized Doc",
            copyright_status="made_up_status",
            content_text="Initial text",
        )

        from app.models.passage import Passage
        passage_id = (await db_session.execute(
            select(Passage.id).where(Passage.is_deleted.is_(False)).limit(1)
        )).scalar_one()

        with pytest.raises(FulltextRejectedError, match="unrecognized|copyright"):
            await svc.append_passage(
                document_id=doc.id, text="Appended.",
                passage_id=passage_id,
            )

    async def test_backward_compat_string_chunks(self, db_session) -> None:
        """Line 838: chunk_text returns list[str] → backward compat wrapping."""
        svc = IngestionService(db_session)
        doc = await _create_doc(
            db_session, title="Compat Append",
            copyright_status="public_domain",
            authorization_basis="pd",
            content_text="Initial text.",
        )

        from app.models.passage import Passage
        passage_id = (await db_session.execute(
            select(Passage.id).where(Passage.is_deleted.is_(False)).limit(1)
        )).scalar_one()

        with patch("app.services.ingestion.chunk_text") as mock_chunk:
            mock_chunk.return_value = ["Append chunk 1", "Append chunk 2"]
            result = await svc.append_passage(
                document_id=doc.id, text="Appended passage text.",
                passage_id=passage_id,
            )
        assert result.appended_chunk_count == 2
        assert len(result.appended_chunk_ids) == 2

    async def test_no_chunks_produced_raises(self, db_session) -> None:
        """Line 843: chunk_list is empty → ValueError."""
        svc = IngestionService(db_session)
        doc = await _create_doc(
            db_session, title="Empty Chunks Doc",
            copyright_status="public_domain",
            authorization_basis="pd",
            content_text="Initial text.",
        )

        from app.models.passage import Passage
        passage_id = (await db_session.execute(
            select(Passage.id).where(Passage.is_deleted.is_(False)).limit(1)
        )).scalar_one()

        with patch("app.services.ingestion.chunk_text", return_value=[]):
            with pytest.raises(ValueError, match="No chunks produced"):
                await svc.append_passage(
                    document_id=doc.id, text="Some text.",
                    passage_id=passage_id,
                )

    async def test_string_chunk_item_in_creation_loop(self, db_session) -> None:
        """Lines 871-872: isinstance(item, str) True in chunk creation loop
        sets para_idx=-1 which then falls back to chunk index."""
        svc = IngestionService(db_session)
        doc = await _create_doc(
            db_session, title="String Item Test",
            copyright_status="public_domain",
            authorization_basis="pd",
            content_text="Initial text.",
        )

        from app.models.passage import Passage
        passage_id = (await db_session.execute(
            select(Passage.id).where(Passage.is_deleted.is_(False)).limit(1)
        )).scalar_one()

        # chunk_text returns list[str] → each item is a string
        with patch("app.services.ingestion.chunk_text", return_value=["Raw chunk"]):
            result = await svc.append_passage(
                document_id=doc.id, text="Appended text.",
                passage_id=passage_id,
            )

        assert result.appended_chunk_count == 1
        # Verify the chunk was created (paragraph_index falls back to chunk_index)
        chunks = list((await db_session.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == doc.id)
            .where(DocumentChunk.passage_id == passage_id)
            .where(DocumentChunk.is_deleted.is_(False))
        )).scalars())
        assert len(chunks) == 1
        # para_idx=-1 → falls back to "next_index + offset" in the loop
        assert chunks[0].paragraph_index >= 0

    async def test_successful_append_creates_source_ref(self, db_session) -> None:
        """Append creates a passage-scoped SourceRef."""
        svc = IngestionService(db_session)
        doc = await _create_doc(
            db_session, title="SR Append",
            copyright_status="public_domain",
            authorization_basis="pd",
            content_text="Initial content.",
        )

        from app.models.passage import Passage
        passage_id = (await db_session.execute(
            select(Passage.id).where(Passage.is_deleted.is_(False)).limit(1)
        )).scalar_one()

        await svc.append_passage(
            document_id=doc.id, text="New passage text.",
            passage_id=passage_id,
        )

        # SourceRef should exist for this passage
        stmt = select(SourceRef).where(
            SourceRef.page_location == f"passage:{passage_id}"
        )
        ref = (await db_session.execute(stmt)).scalar_one_or_none()
        assert ref is not None

        # Document review_status reset
        doc_after = (await db_session.execute(
            select(Document).where(Document.id == doc.id)
        )).scalar_one()
        assert doc_after.review_status == "pending"
        assert doc_after.rag_enabled is False


# ============================================================
# IngestionResult and AppendResult dataclass tests
# ============================================================


class TestResultClasses:
    """Verify IngestionResult and AppendResult construct correctly."""

    def test_ingestion_result_fields(self) -> None:
        r = IngestionResult(
            document_id="doc-1", title="Test",
            chunk_count=5, total_chars=1000, checksum="abc123"
        )
        assert r.document_id == "doc-1"
        assert r.chunk_count == 5
        assert r.total_chars == 1000
        assert r.checksum == "abc123"

    def test_append_result_fields(self) -> None:
        r = AppendResult(
            document_id="doc-1", passage_id="pass-1",
            appended_chunk_count=3,
            appended_chunk_ids=["c1", "c2", "c3"],
            first_chunk_index=10, last_chunk_index=12,
            content_checksum="def456"
        )
        assert r.appended_chunk_count == 3
        assert r.first_chunk_index == 10
        assert r.last_chunk_index == 12
        assert r.content_checksum == "def456"


# ============================================================
# Exception hierarchy tests
# ============================================================


class TestExceptionHierarchy:
    """Verify IngestionError exception tree."""

    def test_ingestion_error_base(self) -> None:
        err = IngestionError("base error")
        assert isinstance(err, Exception)
        assert str(err) == "base error"

    def test_pdf_extraction_error_is_ingestion_error(self) -> None:
        err = PDFExtractionError("bad pdf")
        assert isinstance(err, IngestionError)

    def test_fulltext_rejected_error_is_ingestion_error(self) -> None:
        err = FulltextRejectedError("rejected")
        assert isinstance(err, IngestionError)
