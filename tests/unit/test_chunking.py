
"""Unit tests for chunking.py — chunk_text, _split_paragraphs, _char_split."""

from __future__ import annotations

from app.services.chunking import (
    chunk_text,
    _split_paragraphs,
    _char_split,
)


class TestChunkText:
    def test_short_text_single_chunk(self) -> None:
        text = "针灸甲乙经是皇甫谧编撰的经典著作。"
        chunks = chunk_text(text, max_chars=500)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_long_text_multiple_chunks(self) -> None:
        text = "\n\n".join(["段落" + str(i) + "。" * 200 for i in range(10)])
        chunks = chunk_text(text, max_chars=200)
        assert len(chunks) > 1

    def test_empty_text(self) -> None:
        chunks = chunk_text("", max_chars=100)
        assert chunks == []

    def test_whitespace_only(self) -> None:
        chunks = chunk_text("   \n\n  ", max_chars=100)
        assert chunks == []

    def test_with_indices(self) -> None:
        text = "第一段。\n\n第二段。"
        result = chunk_text(text, max_chars=500, return_indices=True)
        assert isinstance(result, list)
        assert len(result) >= 1
        # Each element is (chunk, index)
        assert isinstance(result[0], tuple)
        assert len(result[0]) == 2


class TestSplitParagraphs:
    def test_single_paragraph(self) -> None:
        result = _split_paragraphs("hello world")
        assert len(result) == 1

    def test_double_newline_split(self) -> None:
        text = "段落一。\n\n段落二。"
        result = _split_paragraphs(text)
        assert len(result) == 2

    def test_strips_whitespace(self) -> None:
        result = _split_paragraphs("  hello  \n\n  world  ")
        assert result == ["hello", "world"]

    def test_skips_empty(self) -> None:
        result = _split_paragraphs("\n\n\n\nfoo\n\n")
        assert result == ["foo"]


class TestCharSplit:
    def test_exact(self) -> None:
        result = _char_split("abcd", 2)
        assert result == ["ab", "cd"]

    def test_remainder(self) -> None:
        result = _char_split("abcde", 2)
        assert result == ["ab", "cd", "e"]

    def test_max_chars_larger_than_text(self) -> None:
        result = _char_split("a", 100)
        assert result == ["a"]
