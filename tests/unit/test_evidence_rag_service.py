
"""Unit tests for evidence_rag_service — static methods: _build_citation, _to_citation, _tokenize, _score."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from app.schemas.evidence_rag import EvidenceBoundChunk
from app.services.evidence_rag_service import EvidenceRAGService


class TestBuildCitation:
    def test_full_fields(self) -> None:
        chunk = MagicMock()
        chunk.document_id = "doc-1"
        chunk.id = "chk-1"
        chunk.page_number = 3
        chunk.paragraph_index = 2
        chunk.ocr_confidence = 0.85
        result = EvidenceRAGService._build_citation("针灸甲乙经", chunk, "https://source")
        assert "《针灸甲乙经》" in result
        assert "[doc-1:chk-1]" in result
        assert "p.3" in result
        assert "par.2" in result
        assert "OCR:0.85" in result

    def test_minimal_fields(self) -> None:
        chunk = MagicMock()
        chunk.document_id = "d"
        chunk.id = "c"
        chunk.page_number = None
        chunk.paragraph_index = None
        chunk.ocr_confidence = None
        result = EvidenceRAGService._build_citation("书", chunk, "")
        assert "《书》" in result
        assert "[d:c]" in result


class TestTokenize:
    def test_splits_on_whitespace(self) -> None:
        tokens = EvidenceRAGService._tokenize("针灸 经络 黄帝")
        assert len(tokens) == 3
        assert "针灸" in tokens

    def test_deduplicates(self) -> None:
        tokens = EvidenceRAGService._tokenize("a a b")
        assert tokens == ["a", "b"]

    def test_empty(self) -> None:
        assert EvidenceRAGService._tokenize("") == []


class TestScore:
    def test_zero_on_empty_content(self) -> None:
        assert EvidenceRAGService._score(["kw"], "") == 0.0

    def test_zero_on_no_hits(self) -> None:
        assert EvidenceRAGService._score(["missing"], "unrelated text") == 0.0

    def test_positive_on_hit(self) -> None:
        score = EvidenceRAGService._score(["abc"], "abc def ghi")
        assert score > 0.0
        assert score <= 1.0

    def test_clamped_to_one(self) -> None:
        score = EvidenceRAGService._score(["a"], "a" * 10000)
        assert score <= 1.0
