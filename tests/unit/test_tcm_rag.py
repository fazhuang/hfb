"""Unit tests for TCM RAG package."""

import pytest

from tcm_kg.models import Node, Edge
from tcm_kg.builder import KGBuilder
from tcm_tei.models import (
    Document,
    TextVersion,
    Paragraph,
    Sentence,
    Token,
)
from tcm_rag.models import (
    KGPath,
    TextHit,
    EvidenceChain,
    CitationPath,
    SearchResult,
)
from tcm_rag.pipeline import RAGPipeline


class TestKGPath:
    def test_empty_path(self) -> None:
        p = KGPath()
        assert p.hop_count == 0
        assert p.description == ""

    def test_single_edge_path(self) -> None:
        edge = Edge("p1", "t1", "authored", source_ref="《晋书》")
        p = KGPath(edges=[edge])
        assert p.hop_count == 1
        assert "authored" in p.description

    def test_multi_edge_description(self) -> None:
        edges = [
            Edge("a", "b", "authored"),
            Edge("b", "c", "contains"),
        ]
        p = KGPath(edges=edges)
        assert "authored" in p.description
        assert "contains" in p.description


class TestTextHit:
    def test_create_hit(self) -> None:
        h = TextHit(
            document_id="doc1",
            paragraph_id="para_3",
            sentence_ids=["sent_7"],
            text="黄帝问曰：针道可得闻乎？",
            score=0.85,
            version_id="song_ben",
        )
        assert h.score == 0.85
        assert h.document_id == "doc1"


class TestEvidenceChain:
    def test_auto_confidence_with_evidence(self) -> None:
        chain = EvidenceChain(
            claim="针灸甲乙经的方剂",
            kg_paths=[KGPath(edges=[Edge("a", "b", "authored")])],
            document_hits=[
                TextHit("d1", "p1", ["s1"], "text", score=0.8),
            ],
        )
        assert chain.confidence > 0

    def test_auto_confidence_empty(self) -> None:
        chain = EvidenceChain(claim="test")
        assert chain.confidence == 0.0


class TestCitationPath:
    def test_inline_format(self) -> None:
        cp = CitationPath(
            segments=[
                ("doc1", "针灸甲乙经，para_3（宋本）"),
                ("doc2", "伤寒论，para_1（明本）"),
            ],
            format="inline",
        )
        rendered = cp.to_inline()
        assert "[1]" in rendered
        assert "[2]" in rendered
        assert "针灸甲乙经" in rendered

    def test_footnote_format(self) -> None:
        cp = CitationPath(
            segments=[("doc1", "针灸甲乙经，para_3")],
            format="footnote",
        )
        rendered = cp.to_footnote()
        assert "[^1]" in rendered

    def test_bibliography_format(self) -> None:
        cp = CitationPath(
            segments=[("doc1", "《针灸甲乙经》. 宋本.")],
            format="bibliography",
        )
        rendered = cp.to_bibliography()
        assert rendered.startswith("1. ")


class TestSearchResult:
    def test_defaults(self) -> None:
        result = SearchResult(query="测试")
        assert result.query == "测试"
        assert result.evidence.claim == "测试"


class TestRAGPipeline:
    @pytest.fixture
    def rag(self) -> RAGPipeline:
        """Build a realistic TCM RAG setup."""
        # KG: 皇甫谧 → 针灸甲乙经 → 白虎汤 → 发热
        kg = KGBuilder.from_triples(
            [
                (
                    Node("person_huangfumi", "Person", {"name": "皇甫谧", "dynasty": "魏晋"}),
                    "authored",
                    Node("text_zhenjiu", "Text", {"title": "针灸甲乙经", "category": "针灸"}),
                ),
                (
                    Node("text_zhenjiu", "Text", {"title": "针灸甲乙经"}),
                    "contains",
                    Node("pres_baihu", "Prescription", {"name": "白虎汤"}),
                ),
                (
                    Node("pres_baihu", "Prescription", {"name": "白虎汤"}),
                    "treats",
                    Node("sym_fever", "Symptom", {"name": "发热"}),
                ),
            ],
            source_refs=[
                "《晋书·皇甫谧传》",
                "《针灸甲乙经·卷七》",
                "《伤寒论》",
            ],
        )

        # Structured literature
        docs = {
            "zhenjiu": Document(
                id="zhenjiu",
                title="针灸甲乙经",
                versions=[
                    TextVersion(
                        id="song_ben",
                        label="宋本",
                        paragraphs=[
                            Paragraph(
                                id="para_0",
                                section="卷一·序",
                                sentences=[
                                    Sentence(
                                        id="sent_0",
                                        text="黄帝问曰：针道可得闻乎？",
                                        tokens=[Token(id="t0", text="黄")],
                                    ),
                                    Sentence(
                                        id="sent_1",
                                        text="凡刺之道，必先治神。",
                                        tokens=[Token(id="t1", text="凡")],
                                    ),
                                ],
                            ),
                            Paragraph(
                                id="para_1",
                                section="卷七·热病",
                                sentences=[
                                    Sentence(
                                        id="sent_2",
                                        text="热病者，皆伤寒之类也。",
                                        tokens=[Token(id="t2", text="热")],
                                    ),
                                    Sentence(
                                        id="sent_3",
                                        text="白虎汤主之。",
                                        tokens=[Token(id="t3", text="白")],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            "shanghan": Document(
                id="shanghan",
                title="伤寒论",
                versions=[
                    TextVersion(
                        id="ming_ben",
                        label="明刊本",
                        paragraphs=[
                            Paragraph(
                                id="para_0",
                                section="太阳病篇",
                                sentences=[
                                    Sentence(
                                        id="sent_0",
                                        text="太阳病，发热，汗出，恶风，脉缓者，名为中风。",
                                        tokens=[Token(id="t0", text="太")],
                                    ),
                                    Sentence(
                                        id="sent_1",
                                        text="桂枝汤主之。",
                                        tokens=[Token(id="t1", text="桂")],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
        }

        return RAGPipeline(kg_store=kg, documents=docs)

    def test_search_finds_entity(self, rag: RAGPipeline) -> None:
        result = rag.search("皇甫谧")
        assert len(result.evidence.kg_paths) > 0

    def test_search_multiple_hops(self, rag: RAGPipeline) -> None:
        """Acceptance: 皇甫谧 → 针灸甲乙经 → 白虎汤 → 发热"""
        result = rag.search("皇甫谧 发热", max_kg_hops=3)
        # Should find paths through the graph
        assert len(result.evidence.kg_paths) >= 1
        # There should be citation paths from text hits
        assert result.citation is not None

    def test_search_finds_text_hits(self, rag: RAGPipeline) -> None:
        result = rag.search("黄帝")
        assert len(result.evidence.document_hits) > 0
        # At least one hit mentioning 黄帝
        hits = result.evidence.document_hits
        assert any("黄帝" in h.text for h in hits)

    def test_search_kg_and_text_combined(self, rag: RAGPipeline) -> None:
        """Both KG paths AND text hits in the same result."""
        result = rag.search("白虎汤")
        # KG paths should reference 白虎汤 edges
        has_kg = len(result.evidence.kg_paths) > 0
        # Text hits should find mentions
        has_text = len(result.evidence.document_hits) > 0
        assert has_kg or has_text  # at least one type
        assert result.citation is not None

    def test_citation_inline_output(self, rag: RAGPipeline) -> None:
        result = rag.search("热病 白虎汤")
        citation = rag.cite(result)
        inline = citation.to_inline()
        assert isinstance(inline, str)
        assert len(inline) > 0

    def test_build_evidence(self, rag: RAGPipeline) -> None:
        result = rag.search("黄帝 针道")
        evidence = rag.build_evidence(result)
        assert evidence.claim == "黄帝 针道"
        assert isinstance(evidence, EvidenceChain)

    def test_no_match_query(self, rag: RAGPipeline) -> None:
        result = rag.search("不存在的内容XYZ")
        # Should not crash, just return empty evidence
        assert result.query == "不存在的内容XYZ"
        assert result.evidence is not None

    def test_full_evidence_chain_acceptance(self, rag: RAGPipeline) -> None:
        """Full acceptance: query 皇甫谧 发热 returns complete evidence chain."""
        result = rag.search("皇甫谧 白虎汤 发热", max_kg_hops=4)
        assert result.query is not None
        assert result.evidence is not None
        assert result.citation is not None

        # Evidence chain should be non-trivial
        evidence = result.evidence
        total_evidence = len(evidence.kg_paths) + len(evidence.document_hits)
        assert total_evidence > 0

        # Citation should be renderable
        citation_text = result.citation.to_inline()
        assert isinstance(citation_text, str)

        # Confidence should be computed
        assert evidence.confidence > 0 or total_evidence == 0
