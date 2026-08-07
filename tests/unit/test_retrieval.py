"""Unit tests for RetrievalService — edge cases in search, tokenization, and scoring."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.services.retrieval import (
    RetrievalService,
    _expand_variants,
)
from app.services.retrieval import SearchResponse as RetrievalSearchResponse

# ---------------------------------------------------------------------------
# RetrievalService.search — edge cases
# ---------------------------------------------------------------------------

class TestSearchEmptyKeywords:
    """Line 220: empty keywords return early."""

    @pytest.mark.asyncio
    async def test_empty_query_returns_empty_response(self):
        session = AsyncMock()
        svc = RetrievalService(session)
        result = await svc.search("   ", top_k=10)
        assert isinstance(result, RetrievalSearchResponse)
        assert result.results == []
        assert result.total == 0
        assert result.max_score == 0.0
        assert result.query == "   "


class TestSearchAuthorIdFilter:
    """Line 260: author_id filter path."""

    @pytest.mark.asyncio
    async def test_author_id_filter_adds_where_clause(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        # Return empty chunks
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute.return_value = mock_result

        svc = RetrievalService(session)
        result = await svc.search("keyword", top_k=5, author_id="author-1")
        assert isinstance(result, RetrievalSearchResponse)
        assert result.results == []


# ---------------------------------------------------------------------------
# RetrievalService._tokenize — variant expansion
# ---------------------------------------------------------------------------

class TestExpandVariants:
    """Tests for _expand_variants helper."""

    def test_expands_simplified_to_traditional(self):
        result = _expand_variants(["针经"])
        assert "鍼經" in result or "針經" in result

    def test_no_variants_returns_original(self):
        result = _expand_variants(["abc"])
        assert result == ["abc"]

    def test_multiple_keywords_expand_all(self):
        result = _expand_variants(["针", "经"])
        # Should contain original keywords
        assert "针" in result
        assert "经" in result

    def test_empty_keywords_returns_empty(self):
        result = _expand_variants([])
        assert result == []

    def test_does_not_duplicate(self):
        result = _expand_variants(["无"])
        # 无 has a variant "無", should be in result but not duplicated
        assert len(result) == len(set(result))


class TestSearchEvidenceMetadata:
    """Lines 314-317: evidence_weight and ocr_confidence metadata fields."""

    @pytest.mark.asyncio
    async def test_chunk_with_evidence_weight_added_to_metadata(self):
        session = AsyncMock()
        session.execute = AsyncMock()

        # Build a mock chunk with evidence_weight and ocr_confidence
        chunk = MagicMock()
        chunk.id = "chunk-1"
        chunk.document_id = "doc-1"
        chunk.chunk_index = 0
        chunk.content = "test keyword content"
        chunk.token_count = 100
        chunk.page_number = None
        chunk.paragraph_index = None
        chunk.evidence_weight = "primary"
        chunk.ocr_confidence = None

        mock_chunks_result = MagicMock()
        mock_chunks_result.scalars.return_value.all.return_value = [chunk]

        # Document lookup result
        mock_doc_row = MagicMock()
        mock_doc_row.__iter__.return_value = iter(["doc-1", "Test Doc", "https://example.com", "public_domain", True])

        session.execute.side_effect = [mock_chunks_result, [mock_doc_row]]

        svc = RetrievalService(session)
        result = await svc.search("keyword", top_k=5)
        assert len(result.results) == 1
        assert result.results[0].metadata.get("evidence_weight") == "primary"

    @pytest.mark.asyncio
    async def test_chunk_with_ocr_confidence_added_to_metadata(self):
        session = AsyncMock()
        session.execute = AsyncMock()

        chunk = MagicMock()
        chunk.id = "chunk-1"
        chunk.document_id = "doc-1"
        chunk.chunk_index = 0
        chunk.content = "test keyword content"
        chunk.token_count = 100
        chunk.page_number = None
        chunk.paragraph_index = None
        chunk.evidence_weight = ""
        chunk.ocr_confidence = 0.95

        mock_chunks_result = MagicMock()
        mock_chunks_result.scalars.return_value.all.return_value = [chunk]

        mock_doc_row = MagicMock()
        mock_doc_row.__iter__.return_value = iter(["doc-1", "Test Doc", "https://example.com", "public_domain", True])

        session.execute.side_effect = [mock_chunks_result, [mock_doc_row]]

        svc = RetrievalService(session)
        result = await svc.search("keyword", top_k=5)
        assert len(result.results) == 1
        assert result.results[0].metadata.get("ocr_confidence") == 0.95

    @pytest.mark.asyncio
    async def test_chunk_with_page_number_added_to_metadata(self):
        session = AsyncMock()
        session.execute = AsyncMock()

        chunk = MagicMock()
        chunk.id = "chunk-1"
        chunk.document_id = "doc-1"
        chunk.chunk_index = 0
        chunk.content = "test keyword content"
        chunk.token_count = 100
        chunk.page_number = 42
        chunk.paragraph_index = 3
        chunk.evidence_weight = "reference"
        chunk.ocr_confidence = None

        mock_chunks_result = MagicMock()
        mock_chunks_result.scalars.return_value.all.return_value = [chunk]

        mock_doc_row = MagicMock()
        mock_doc_row.__iter__.return_value = iter(["doc-1", "Test Doc", "https://example.com", "public_domain", True])

        session.execute.side_effect = [mock_chunks_result, [mock_doc_row]]

        svc = RetrievalService(session)
        result = await svc.search("keyword", top_k=5)
        assert len(result.results) == 1
        assert result.results[0].metadata.get("page_number") == 42
        assert result.results[0].metadata.get("paragraph_index") == 3


# ---------------------------------------------------------------------------
# RetrievalService._score_chunk
# ---------------------------------------------------------------------------

class TestScoreChunk:
    """Static _score_chunk method."""

    def test_content_with_all_keywords_scores_high(self):
        score = RetrievalService._score_chunk(["key1", "key2"], "key1 and key2 appear here")
        assert score > 0.4

    def test_content_with_no_keywords_scores_zero(self):
        score = RetrievalService._score_chunk(["x", "y"], "no match here")
        assert score == 0.0

    def test_empty_content_scores_zero(self):
        score = RetrievalService._score_chunk(["key"], "")
        assert score == 0.0

    def test_empty_keywords_scores_zero(self):
        score = RetrievalService._score_chunk([], "some content")
        assert score == 0.0
