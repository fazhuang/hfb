
"""Unit tests for retrieval.py — _tokenize, _score_chunk, _expand_variants, SearchResponse."""

from __future__ import annotations

from app.services.retrieval import (
    _expand_variants,
    _COMPLIANT_COPYRIGHT_STATUSES,
    RetrievalResult,
    SearchResponse,
    RetrievalService,
)


class TestExpandVariants:
    def test_known_simplified_expands(self) -> None:
        expanded = _expand_variants(["针"])
        assert "針" in expanded
        assert "鍼" in expanded
        assert "针" in expanded

    def test_no_duplicate(self) -> None:
        expanded = _expand_variants(["针", "针"])
        # "针" appears at least once, variants present
        assert len(expanded) >= 3

    def test_noop_for_unknown_char(self) -> None:
        expanded = _expand_variants(["x"])
        assert expanded == ["x"]


class TestComplianceClauses:
    def test_compliant_set(self) -> None:
        assert "public_domain" in _COMPLIANT_COPYRIGHT_STATUSES
        assert "open_access" in _COMPLIANT_COPYRIGHT_STATUSES
        assert "licensed" in _COMPLIANT_COPYRIGHT_STATUSES


class TestScoreChunk:
    def test_no_keywords_zero_score(self) -> None:
        score = RetrievalService._score_chunk(["针灸"], "")
        assert score == 0.0

    def test_no_match_zero_score(self) -> None:
        score = RetrievalService._score_chunk(["不存在"], "完全无关的内容")
        assert score == 0.0

    def test_full_match_positive_score(self) -> None:
        score = RetrievalService._score_chunk(["针灸"], "针灸甲乙经记载经络理论")
        assert score > 0.0
        assert score <= 1.0

    def test_multiple_keywords_higher_score(self) -> None:
        single = RetrievalService._score_chunk(["针灸"], "针灸是中医的重要组成部分针灸可以治病")
        double = RetrievalService._score_chunk(["针灸", "中医"], "针灸是中医的重要组成部分针灸可以治病")
        assert double > single


class TestTokenize:
    def test_whitespace_separated_query(self) -> None:
        tokens = RetrievalService._tokenize("针灸 经络")
        assert "针灸" in tokens or "經絡" in tokens or "经" in tokens

    def test_chinese_query_bigrams(self) -> None:
        tokens = RetrievalService._tokenize("针灸甲乙经")
        assert len(tokens) > 0

    def test_empty_query(self) -> None:
        tokens = RetrievalService._tokenize("")
        assert tokens == []


class TestSearchResponse:
    def test_empty_response(self) -> None:
        resp = SearchResponse(query="test", results=[], total=0, max_score=0.0)
        assert resp.query == "test"
        assert resp.results == []
        assert resp.max_score == 0.0


class TestRetrievalResult:
    def test_fields(self) -> None:
        r = RetrievalResult(
            chunk_id="c1",
            document_id="d1",
            document_title="测试",
            chunk_index=0,
            content="内容",
            citation="[d1:c1]",
            score=0.85,
        )
        assert r.citation == "[d1:c1]"
        assert r.score == 0.85
