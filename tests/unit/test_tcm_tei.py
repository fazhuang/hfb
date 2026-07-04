"""Unit tests for TCM TEI package."""

import json


from tcm_tei.models import (
    Token,
    Sentence,
    Paragraph,
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
        # LCS separates the variant into two entries: one for each side
        assert len(variants) == 2
        # First: sentence present only in song_ben ("也")
        v0 = variants[0]
        assert v0.location == "para_0.sent_1"
        assert "也" in v0.readings["song_ben"]
        assert v0.readings["ming_ben"] == "(absent)"
        # Second: sentence present only in ming_ben ("耳")
        v1 = variants[1]
        assert v1.location == "para_0.sent_2"
        assert "耳" in v1.readings["ming_ben"]
        assert v1.readings["song_ben"] == "(absent)"

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
        # LCS alignment: para_0 has 2 sentences + 1 variant gap + para_1 has 1 = 4 pairs
        assert len(aligned) == 4
        # First pair: identical sentence
        assert aligned[0][0] is not None and aligned[0][1] is not None
        assert aligned[0][0].text == "黄帝问曰：针道可得闻乎？"
        # Second pair: sentence only in version A (variant: 也)
        assert aligned[1][0] is not None and aligned[1][1] is None
        assert aligned[1][0].text == "岐伯对曰：可得闻也。"
        # Third pair: sentence only in version B (variant: 耳)
        assert aligned[2][0] is None and aligned[2][1] is not None
        assert aligned[2][1].text == "岐伯对曰：可得闻耳。"
        # Fourth pair: identical sentence in para_1
        assert aligned[3][0] is not None and aligned[3][1] is not None
        assert aligned[3][0].text == "凡刺之道，必先治神。"

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
        # Without whitespace-ignore, LCS sees different texts -> 2 unaligned entries
        assert len(variants_no_ignore) == 2
        # With whitespace-ignore, LCS aligns them -> identical -> 0 variants
        assert len(variants_ignore) == 0


def test_lcs_alignment_insertion_does_not_misalign_remainder():
    """A sentence inserted in version B should not misalign all following pairs."""
    v1 = TextVersion(id="v1", label="原本")
    v2 = TextVersion(id="v2", label="增补本")

    para1 = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s2", text="岐伯对曰"),
        Sentence(id="s3", text="经脉流行不止"),
        Sentence(id="s4", text="环周不休"),
    ])
    para2 = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s2", text="岐伯对曰"),
        Sentence(id="sX", text="此乃要言也"),  # inserted
        Sentence(id="s3", text="经脉流行不止"),
        Sentence(id="s4", text="环周不休"),
    ])
    v1.paragraphs = [para1]
    v2.paragraphs = [para2]

    variants = VersionComparator.diff(v1, v2, algorithm="lcs")

    # Should have exactly 1 variant: the inserted sentence
    # Without LCS, position-based would flag s3 & s4 as misaligned too
    assert len(variants) == 1
    assert "sent_2" in variants[0].location  # the X position


def test_lcs_alignment_deletion_does_not_misalign_remainder():
    """A sentence deleted in version B should not misalign all following pairs."""
    v1 = TextVersion(id="v1", label="原本")
    v2 = TextVersion(id="v2", label="删节本")

    para1 = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s2", text="岐伯对曰"),
        Sentence(id="s3", text="经脉流行不止"),
        Sentence(id="s4", text="环周不休"),
    ])
    para2 = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s3", text="经脉流行不止"),
        Sentence(id="s4", text="环周不休"),
    ])
    v1.paragraphs = [para1]
    v2.paragraphs = [para2]

    variants = VersionComparator.diff(v1, v2, algorithm="lcs")

    # Should have exactly 1 variant: the deleted sentence
    assert len(variants) == 1


def test_lcs_alignment_identical_texts_zero_variants():
    """Identical texts should produce zero variants with LCS alignment."""
    v1 = TextVersion(id="v1", label="宋本")
    v2 = TextVersion(id="v2", label="明本")
    para = Paragraph(id="p1", sentences=[
        Sentence(id="s1", text="黄帝问曰"),
        Sentence(id="s2", text="岐伯对曰"),
    ])
    v1.paragraphs = [para]
    v2.paragraphs = [para]

    variants = VersionComparator.diff(v1, v2, algorithm="lcs")
    assert len(variants) == 0


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
        assert len(parsed) == 2
        assert "location" in parsed[0]
        assert "readings" in parsed[0]
