
"""Unit tests for _make_snippet and _compute_score (search_service.py)."""
from __future__ import annotations

from app.services.search_service import _make_snippet, _compute_score


class TestSnippet:
    def test_match_mid_text(self) -> None:
        text = "ABCDEFG搜索词HIJKLMNOP" + "X" * 200
        snip = _make_snippet(text, "搜索词")
        assert snip is not None
        assert "搜索词" in snip

    def test_match_at_start(self) -> None:
        text = "搜索词" + "X" * 300
        snip = _make_snippet(text, "搜索词")
        assert snip is not None
        assert "搜索词" in snip
        assert not (snip or "").startswith("…")

    def test_none_text_returns_none(self) -> None:
        assert _make_snippet(None, "q") is None

    def test_empty_query_returns_prefix(self) -> None:
        text = "Y" * 250
        snip = _make_snippet(text, "")
        assert len(snip or "") == 200

    def test_no_match_returns_prefix(self) -> None:
        text = "Z" * 250
        snip = _make_snippet(text, "absent")
        assert len(snip or "") == 200


class TestScore:
    def test_zero_match_count(self) -> None:
        assert _compute_score(0, 5, False) == 0.0

    def test_title_bonus(self) -> None:
        with_title = _compute_score(1, 5, True)
        without_title = _compute_score(1, 5, False)
        assert with_title > without_title

    def test_clamped_to_one(self) -> None:
        score = _compute_score(100, 10, True)
        assert score <= 1.0

    def test_rounds_to_three_decimals(self) -> None:
        score = _compute_score(2, 7, False)
        # round(x, 3) should not have more than 3 decimal digits
        assert score == round(score, 3)
