"""Unit tests for TCM TEI package."""

import json

import pytest

from tcm_tei.models import (
    Token,
    Sentence,
    Paragraph,
    Variant,
    TextVersion,
    Document,
)
from tcm_tei.comparator import VersionComparator
from tcm_tei.serializer import TEISerializer


# --- Test Data Helpers ---

def _make_sentence(id_: str, text: str) -> Sentence:
    tokens = [Token(id=f"{id_}_{i}", text=ch) for i, ch in enumerate(text)]
    return Sentence(id=id_, tokens=tokens, text=text)


def _make_paragraph(id_: str, *sentences: Sentence) -> Paragraph:
    return Paragraph(id=id_, sentences=list(sentences))


def _make_document_with_two_versions() -> Document:
    """Create a document with two versions for comparison testing."""
    return Document(
        id="zhenjiu_jia_yi_jing",
        title="针灸甲乙经",
        versions=[
            TextVersion(
                id="song_ben",
                label="宋本",
                paragraphs=[
                    _make_paragraph(
                        "para_0",
                        _make_sentence("s0", "黄帝问曰：针道可得闻乎？"),
                        _make_sentence("s1", "岐伯对曰：可得闻也。"),
                    ),
                    _make_paragraph(
                        "para_1",
                        _make_sentence("s2", "凡刺之道，必先治神。"),
                    ),
                ],
                metadata={"dynasty": "宋", "format": "刻本"},
            ),
            TextVersion(
                id="ming_ben",
                label="明刊本",
                paragraphs=[
                    _make_paragraph(
                        "para_0",
                        _make_sentence("s0", "黄帝问曰：针道可得闻乎？"),
                        _make_sentence("s1", "岐伯对曰：可得闻耳。"),
                        # ↑ variant: "也" vs "耳"
                    ),
                    _make_paragraph(
                        "para_1",
                        _make_sentence("s2", "凡刺之道，必先治神。"),
                    ),
                ],
                metadata={"dynasty": "明", "format": "刻本"},
            ),
        ],
    )


class TestToken:
    def test_create_token(self) -> None:
        t = Token(id="tok_0", text="黄", pos="n", lemma="黄")
        assert t.id == "tok_0"
        assert t.text == "黄"
        assert t.pos == "n"

    def test_token_defaults(self) -> None:
        t = Token(id="tok_0", text="帝")
        assert t.pos == ""
        assert t.lemma is None


class TestSentence:
    def test_create_sentence(self) -> None:
        tokens = [Token(id="t0", text="针"), Token(id="t1", text="灸")]
        sent = Sentence(id="sent_0", tokens=tokens)
        assert sent.text == "针灸"

    def test_sentence_text_from_tokens(self) -> None:
        sent = Sentence(
            id="s0",
            tokens=[Token(id="t0", text="黄"), Token(id="t1", text="帝")],
        )
        assert sent.text == "黄帝"


class TestParagraph:
    def test_create_paragraph(self) -> None:
        p = Paragraph(id="p0", section="卷一·针灸禁忌")
        assert p.id == "p0"
        assert p.section == "卷一·针灸禁忌"
        assert p.text == ""

    def test_paragraph_text_from_sentences(self) -> None:
        p = _make_paragraph(
            "p0",
            _make_sentence("s0", "黄帝问。"),
            _make_sentence("s1", "岐伯对。"),
        )
        assert p.text == "黄帝问。岐伯对。"


class TestTextVersion:
    def test_counts(self) -> None:
        v = TextVersion(
            id="v1",
            label="test",
            paragraphs=[
                _make_paragraph("p0", _make_sentence("s0", "一。"), _make_sentence("s1", "二。")),
                _make_paragraph("p1", _make_sentence("s2", "三。")),
            ],
        )
        assert v.paragraph_count == 2
        assert v.sentence_count == 3

    def test_full_text(self) -> None:
        v = TextVersion(
            id="v1",
            label="test",
            paragraphs=[
                _make_paragraph("p0", _make_sentence("s0", "甲"), _make_sentence("s1", "乙")),
            ],
        )
        assert v.full_text == "甲乙"


class TestDocument:
    def test_get_version(self) -> None:
        doc = _make_document_with_two_versions()
        assert doc.get_version("song_ben") is not None
        assert doc.get_version("ghost") is None


class TestVersionComparator:
    def test_identical_versions_no_variants(self) -> None:
        v1 = TextVersion(
            id="v1", label="A",
            paragraphs=[_make_paragraph("p0", _make_sentence("s0", "黄帝问。"))],
        )
        v2 = TextVersion(
            id="v2", label="B",
            paragraphs=[_make_paragraph("p0", _make_sentence("s0", "黄帝问。"))],
        )
        variants = VersionComparator.diff(v1, v2)
        assert len(variants) == 0

    def test_diff_detects_variant(self) -> None:
        doc = _make_document_with_two_versions()
        variants = VersionComparator.diff(doc.versions[0], doc.versions[1])
        # Should find at least one variant: "也" vs "耳"
        assert len(variants) == 1
        v = variants[0]
        assert v.location == "para_0.sent_1"
        assert "也" in v.readings["song_ben"]
        assert "耳" in v.readings["ming_ben"]

    def test_diff_extra_paragraph(self) -> None:
        v1 = TextVersion(
            id="v1", label="A",
            paragraphs=[
                _make_paragraph("p0", _make_sentence("s0", "一。")),
                _make_paragraph("p1", _make_sentence("s1", "二。")),
            ],
        )
        v2 = TextVersion(
            id="v2", label="B",
            paragraphs=[
                _make_paragraph("p0", _make_sentence("s0", "一。")),
            ],
        )
        variants = VersionComparator.diff(v1, v2)
        assert len(variants) == 1
        assert "(absent)" in str(variants[0].readings["v2"])

    def test_align(self) -> None:
        doc = _make_document_with_two_versions()
        aligned = VersionComparator.align(doc.versions[0], doc.versions[1])
        assert len(aligned) == 3  # 2 sentences in para_0 + 1 in para_1
        # All pairs should have both sides (same structure)
        for a, b in aligned:
            assert a is not None
            assert b is not None

    def test_ignore_whitespace(self) -> None:
        v1 = TextVersion(
            id="v1", label="A",
            paragraphs=[_make_paragraph("p0", _make_sentence("s0", "黄帝 问 曰"))],
        )
        v2 = TextVersion(
            id="v2", label="B",
            paragraphs=[_make_paragraph("p0", _make_sentence("s0", "黄帝问曰"))],
        )
        variants_no_ignore = VersionComparator.diff(v1, v2, ignore_whitespace=False)
        variants_ignore = VersionComparator.diff(v1, v2, ignore_whitespace=True)
        assert len(variants_no_ignore) == 1
        assert len(variants_ignore) == 0


class TestTEISerializer:
    def test_json_roundtrip(self) -> None:
        doc = _make_document_with_two_versions()
        json_str = TEISerializer.to_json(doc)
        restored = TEISerializer.from_json(json_str)
        assert restored.id == doc.id
        assert restored.title == doc.title
        assert len(restored.versions) == 2
        assert restored.versions[0].label == "宋本"

    def test_to_json_is_valid(self) -> None:
        doc = _make_document_with_two_versions()
        json_str = TEISerializer.to_json(doc)
        parsed = json.loads(json_str)
        assert parsed["id"] == "zhenjiu_jia_yi_jing"

    def test_to_xml(self) -> None:
        doc = _make_document_with_two_versions()
        xml = TEISerializer.to_xml(doc)
        assert '<?xml version="1.0"' in xml
        assert '<TEI xmlns="http://www.tei-c.org/ns/1.0">' in xml
        assert "针灸甲乙经" in xml
        assert "宋本" in xml
        assert "明刊本" in xml

    def test_variants_to_json(self) -> None:
        doc = _make_document_with_two_versions()
        variants = VersionComparator.diff(doc.versions[0], doc.versions[1])
        json_str = TEISerializer.variants_to_json(variants)
        parsed = json.loads(json_str)
        assert len(parsed) == 1
        assert "location" in parsed[0]
        assert "readings" in parsed[0]
