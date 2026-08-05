
"""Unit tests for citation_persistence.py — _truncate static method."""

from __future__ import annotations

import pytest
from app.services.citation_persistence import CitationPersistenceService


class TestTruncate:
    def test_short_string_unchanged(self) -> None:
        assert CitationPersistenceService._truncate("hello", 10) == "hello"

    def test_long_string_truncated(self) -> None:
        result = CitationPersistenceService._truncate("abcdefghijklmnop", 10)
        assert len(result) == 10
        assert result.endswith("...")

    def test_empty_string(self) -> None:
        assert CitationPersistenceService._truncate("", 10) == ""

    def test_none(self) -> None:
        assert CitationPersistenceService._truncate(None, 10) == ""

    def test_exact_length(self) -> None:
        assert CitationPersistenceService._truncate("12345", 5) == "12345"
