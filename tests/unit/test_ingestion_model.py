"""Unit tests for ingestion.py — dataclasses, enums, and exception hierarchy."""

from __future__ import annotations

from app.services.ingestion import (
    _ALLOWED_COPYRIGHT_STATUSES,
    _ALLOWED_METADATA_KEYS,
    _FORBIDDEN_COPYRIGHT_STATUSES,
    AppendResult,
    FulltextRejectedError,
    IngestionError,
    IngestionResult,
    PDFExtractionError,
)


class TestIngestionResult:
    def test_fields(self) -> None:
        r = IngestionResult(
            document_id="doc-1",
            title="测试文档",
            chunk_count=5,
            total_chars=1000,
            checksum="abc123",
        )
        assert r.document_id == "doc-1"
        assert r.title == "测试文档"
        assert r.chunk_count == 5
        assert r.total_chars == 1000
        assert r.checksum == "abc123"


class TestAppendResult:
    def test_fields(self) -> None:
        r = AppendResult(
            document_id="doc-2",
            passage_id="passage-1",
            appended_chunk_count=3,
            appended_chunk_ids=["c1", "c2", "c3"],
            first_chunk_index=0,
            last_chunk_index=2,
            content_checksum="def456",
        )
        assert r.document_id == "doc-2"
        assert r.appended_chunk_count == 3
        assert r.first_chunk_index == 0
        assert r.last_chunk_index == 2


class TestExceptions:
    def test_ingestion_error(self) -> None:
        exc = IngestionError("failed")
        assert isinstance(exc, Exception)
        assert str(exc) == "failed"

    def test_pdf_extraction_error(self) -> None:
        exc = PDFExtractionError("encrypted")
        assert isinstance(exc, IngestionError)

    def test_fulltext_rejected_error(self) -> None:
        exc = FulltextRejectedError("rejected")
        assert isinstance(exc, IngestionError)


class TestConstants:
    def test_allowed_metadata_keys(self) -> None:
        assert "dynasty" in _ALLOWED_METADATA_KEYS
        assert "copyright_status" in _ALLOWED_METADATA_KEYS

    def test_allowed_copyright_statuses(self) -> None:
        assert "public_domain" in _ALLOWED_COPYRIGHT_STATUSES
        assert "open_access" in _ALLOWED_COPYRIGHT_STATUSES

    def test_forbidden_statuses(self) -> None:
        assert "unknown" in _FORBIDDEN_COPYRIGHT_STATUSES
        assert "pirated" in _FORBIDDEN_COPYRIGHT_STATUSES

    def test_disjoint_sets(self) -> None:
        assert not (_ALLOWED_COPYRIGHT_STATUSES & _FORBIDDEN_COPYRIGHT_STATUSES)
