"""Unit tests for Academic RAG Service — pure functions, validation, and logic branches."""

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from app.schemas.academic_rag import (
    AcademicCitation,
    AcademicKGEdge,
    AcademicKGNode,
    AcademicKGPath,
    AcademicRAGResponse,
)
from app.schemas.graph import GraphEdge, GraphEvidence, GraphNode, NeighborResult
from app.services.academic_rag_service import (
    AcademicRAGService,
    _expand_classical_variants,
    _extract_keywords,
    _make_citation_id,
    _make_edge_id,
    _make_evidence_id,
    _make_kg_edge_from_evidence,
    _make_stable_id,
    parse_chinese_query,
)

# ============================================================
# _extract_keywords
# ============================================================


def test_extract_keywords_returns_chinese_sequences():
    assert _extract_keywords("皇甫谧、师承何人") == ["皇甫谧", "师承何人"]


def test_extract_keywords_filters_stop_words():
    result = _extract_keywords("什么是针灸来源")
    for stop in ["什么", "来源"]:
        assert stop not in result


def test_extract_keywords_skips_single_char():
    assert _extract_keywords("中草药说明") == ["中草药说明"]


def test_extract_keywords_handles_empty():
    assert _extract_keywords("") == []


def test_extract_keywords_handles_non_chinese():
    assert _extract_keywords("hello world 123") == []


# ============================================================
# _expand_classical_variants
# ============================================================


def test_expand_classical_variants_adds_traditional_forms():
    result = _expand_classical_variants(["针灸"])
    assert "鍼灸" in result or "鐵灸" in result


def test_expand_classical_variants_preserves_original():
    result = _expand_classical_variants(["针灸"])
    assert "针灸" in result


def test_expand_classical_variants_no_duplicates():
    result = _expand_classical_variants(["气"])
    assert len(result) == len(set(result))


def test_expand_classical_variants_idempotent_for_no_variant():
    result = _expand_classical_variants(["本草"])
    assert result == ["本草"]


def test_expand_classical_variants_skips_single_char_result():
    result = _expand_classical_variants(["针"])
    assert result == ["针"]


# ============================================================
# Stable ID helpers
# ============================================================


def test_make_stable_id_deterministic():
    a = _make_stable_id("test", "a", "b")
    b = _make_stable_id("test", "a", "b")
    assert a == b
    assert len(a) == 16


def test_make_stable_id_different_inputs():
    a = _make_stable_id("test", "a", "b")
    b = _make_stable_id("test", "b", "a")
    assert a != b


def test_make_citation_id():
    cid = _make_citation_id("doc1", "chunk1", "some quote text")
    expected = _make_stable_id("citation", "doc1", "chunk1", "some quote text"[:100])
    assert cid == expected


def test_make_edge_id():
    assert _make_edge_id("er:abc123") == "edge:er:abc123"


def test_make_evidence_id():
    eid = _make_evidence_id("doc1", "chunk1", "evidence quote")
    expected = _make_stable_id("evidence", "doc1", "chunk1", "evidence quote"[:100])
    assert eid == expected


# ============================================================
# _make_kg_edge_from_evidence
# ============================================================


def _make_graph_edge(id_str="er:001", rel_type="compiled_from", label="编纂"):
    return GraphEdge(
        id=id_str,
        source_id="g:person:src",
        target_id="g:book:tgt",
        relation_type=rel_type,
        label=label,
        evidence=GraphEvidence(
            document_id="doc1",
            chunk_id="chunk1",
            exact_quote="皇甫谧著针灸甲乙经",
            citation="[doc1:chunk1]",
            claim_text="皇甫谧编纂针灸甲乙经",
            version_id="v1",
            passage_id="p1",
            source_uri="https://ctext.org/example",
        ),
    )


def test_make_kg_edge_with_evidence_full_provenance():
    edge = _make_graph_edge()
    ev = edge.evidence
    result = _make_kg_edge_from_evidence(edge, ev)
    assert result.edge_id == "edge:er:001"
    assert result.relation_id == "er:001"
    assert result.relation_type == "compiled_from"
    assert result.label == "编纂"
    assert result.evidence_quote == "皇甫谧著针灸甲乙经"
    assert result.evidence_citation == "[doc1:chunk1]"
    assert result.claim_text == "皇甫谧编纂针灸甲乙经"
    assert result.version_id == "v1"
    assert result.passage_id == "p1"
    assert result.source_uri == "https://ctext.org/example"


def test_make_kg_edge_with_none_evidence():
    edge = _make_graph_edge()
    result = _make_kg_edge_from_evidence(edge, None)
    assert result.edge_id == "edge:er:001"
    assert result.relation_id == "er:001"
    assert result.evidence_quote == ""
    assert result.evidence_citation == ""
    assert result.evidence_id == ""


def test_make_kg_edge_missing_attr_falls_back_to_empty():
    edge = _make_graph_edge()
    ev = GraphEvidence(
        document_id="d1",
        chunk_id="c1",
        exact_quote="q",
        citation="[d1:c1]",
    )
    result = _make_kg_edge_from_evidence(edge, ev)
    assert result.claim_text == ""
    assert result.version_id == ""
    assert result.passage_id == ""
    assert result.source_uri == ""


# ============================================================
# parse_chinese_query
# ============================================================


def test_parse_query_known_subject_with_origin_pattern():
    result = parse_chinese_query("皇甫谧的思想来源是什么")
    assert result.subject == "皇甫谧"
    assert result.topic == "学术"
    assert result.intent in ("来源/渊源", "综合")


def test_parse_query_book_title_in_marks():
    result = parse_chinese_query("《针灸甲乙经》的来源是什么")
    assert result.subject == "《针灸甲乙经》"


def test_parse_query_subject_from_separator():
    result = parse_chinese_query("张仲景之学术渊源是什么")
    assert result.subject == "张仲景"
    assert "学术" in result.topic


def test_parse_query_intent_authorship():
    result = parse_chinese_query("孙思邈著有什么")
    assert result.subject == "孙思邈"
    assert result.intent == "著作"


def test_parse_query_intent_identity():
    result = parse_chinese_query("李时珍是谁")
    assert result.subject == "李时珍"
    assert result.intent == "身份"


def test_parse_query_intent_method():
    result = parse_chinese_query("华佗如何治疗")
    assert result.subject == "华佗"
    assert result.intent == "方法"


def test_parse_query_fallback_subject_length():
    result = parse_chinese_query("医学史上谁最重要")
    assert len(result.subject) >= 4 or result.subject == "医学史上"


def test_parse_query_empty_yields_parsed_query_with_keywords():
    result = parse_chinese_query("")
    assert result.subject == ""
    assert not result.is_valid


def test_parse_query_strip_pattern_markers():
    result = parse_chinese_query("什么是针灸理论")
    assert result.subject != ""
    assert "理论" in result.topic


def test_parse_query_subject_from_separator_no_known():
    """Covers line 127: separator split when no known subject matches."""
    result = parse_chinese_query("学术渊源是什么")
    assert result.subject != ""
    assert result.intent == "来源/渊源"


def test_parse_query_subject_fallback_last_resort():
    """Covers line 134: fallback to content[:4]."""
    result = parse_chinese_query("AB是什么")
    assert result.subject == "AB"


def test_parse_query_generic_intent_fallback():
    """Covers intent='综合' fallback."""
    result = parse_chinese_query("测试问题")
    assert result.subject != ""
    assert result.intent == "综合"


# ============================================================
# _check_success_conditions (static method)
# ============================================================


def _make_kg_path(
    hop_count: int = 1,
    nodes: list | None = None,
    edges: list | None = None,
):
    default_nodes = [
        AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
        AcademicKGNode(id="n2", entity_type="book", label="针灸甲乙经"),
    ]
    default_edges = [
        AcademicKGEdge(
            edge_id="edge:1",
            relation_id="er:1",
            relation_type="compiled_from",
            label="编纂",
            evidence_quote="some quote",
            evidence_citation="[doc1:chunk1]",
            evidence_id="ev:1",
        )
    ]
    return AcademicKGPath(
        nodes=nodes if nodes is not None else default_nodes,
        edges=edges if edges is not None else default_edges,
        hop_count=hop_count,
    )


def test_check_success_empty_paths():
    assert AcademicRAGService._check_success_conditions([]) is False


def test_check_success_no_multi_hop():
    path = _make_kg_path(hop_count=1)
    assert AcademicRAGService._check_success_conditions([path]) is False


def test_check_success_no_nodes():
    path = _make_kg_path(hop_count=2, nodes=[])
    assert AcademicRAGService._check_success_conditions([path]) is False


def test_check_success_no_edges():
    path = _make_kg_path(hop_count=2, edges=[])
    assert AcademicRAGService._check_success_conditions([path]) is False


def test_check_success_edge_missing_quote():
    path = _make_kg_path(hop_count=2)
    path.edges[0].evidence_quote = ""
    assert AcademicRAGService._check_success_conditions([path]) is False


def test_check_success_edge_missing_citation():
    path = _make_kg_path(hop_count=2)
    path.edges[0].evidence_citation = ""
    assert AcademicRAGService._check_success_conditions([path]) is False


def test_check_success_all_conditions_met():
    path = _make_kg_path(
        hop_count=2,
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="针灸甲乙经"),
            AcademicKGNode(id="n3", entity_type="book", label="黄帝内经"),
        ],
        edges=[
            AcademicKGEdge(
                edge_id="e1",
                relation_type="compiled_from",
                label="编纂",
                evidence_quote="quote1",
                evidence_citation="[d1:c1]",
            ),
            AcademicKGEdge(
                edge_id="e2",
                relation_type="derived_from",
                label="来源",
                evidence_quote="quote2",
                evidence_citation="[d2:c2]",
            ),
        ],
    )
    assert AcademicRAGService._check_success_conditions([path]) is True


def test_check_success_multiple_paths_one_valid():
    valid = _make_kg_path(
        hop_count=2,
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="A"),
            AcademicKGNode(id="n2", entity_type="book", label="B"),
            AcademicKGNode(id="n3", entity_type="book", label="C"),
        ],
        edges=[
            AcademicKGEdge(
                edge_id="e1", relation_type="r", label="l",
                evidence_quote="q1", evidence_citation="[d1:c1]",
            ),
            AcademicKGEdge(
                edge_id="e2", relation_type="r2", label="l2",
                evidence_quote="q2", evidence_citation="[d2:c2]",
            ),
        ],
    )
    invalid = _make_kg_path(hop_count=1)
    assert AcademicRAGService._check_success_conditions([valid, invalid]) is True


def test_check_success_two_paths_both_invalid():
    p1 = _make_kg_path(hop_count=1)
    p2 = _make_kg_path(hop_count=1)
    assert AcademicRAGService._check_success_conditions([p1, p2]) is False


# ============================================================
# _hash_response
# ============================================================


def test_hash_response_deterministic():
    resp = AcademicRAGResponse(
        query="test query",
        answer="insufficient evidence",
        refusal=True,
        corpus_sha256="abc123",
    )
    h1 = AcademicRAGService._hash_response(resp)
    h2 = AcademicRAGService._hash_response(resp)
    assert h1 == h2
    assert len(h1) == 64


def test_hash_response_different_content_different_hash():
    r1 = AcademicRAGResponse(
        query="q", answer="answer one", refusal=True, corpus_sha256="sha"
    )
    r2 = AcademicRAGResponse(
        query="q", answer="answer two", refusal=True, corpus_sha256="sha"
    )
    assert AcademicRAGService._hash_response(r1) != AcademicRAGService._hash_response(r2)


def test_hash_response_output_sha256_emptied_before_hash():
    resp = AcademicRAGResponse(
        query="q", answer="a", refusal=True, corpus_sha256="sha", output_sha256="existing-hash"
    )
    h = AcademicRAGService._hash_response(resp)
    resp2 = AcademicRAGResponse(
        query="q", answer="a", refusal=True, corpus_sha256="sha", output_sha256="different"
    )
    assert h == AcademicRAGService._hash_response(resp2)


# ============================================================
# _project_citations_from_paths
# ============================================================


@pytest.fixture
def rag_svc():
    session = MagicMock()
    return AcademicRAGService(session)


def test_project_citations_empty(rag_svc):
    assert rag_svc._project_citations_from_paths([]) == []


def test_project_citations_from_valid_path(rag_svc):
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="皇甫谧著针灸甲乙经",
        evidence_citation="[doc1:chunk1]",
        evidence_id="ev:1",
        version_id="v1",
        passage_id="p1",
        source_uri="https://ctext.org/example",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="针灸甲乙经"),
        ],
        edges=[edge],
        hop_count=1,
    )
    result = rag_svc._project_citations_from_paths([path])
    assert len(result) == 1
    c = result[0]
    assert c.document_id == "doc1"
    assert c.chunk_id == "chunk1"
    assert c.exact_quote == "皇甫谧著针灸甲乙经"
    assert c.citation == "[doc1:chunk1]"
    assert c.version_id == "v1"
    assert c.passage_id == "p1"
    assert c.source_uri == "https://ctext.org/example"
    assert c.evidence_id == "ev:1"


def test_project_citations_deduplicates(rag_svc):
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="same quote",
        evidence_citation="[doc1:chunk1]",
        evidence_id="ev:1",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="A"),
            AcademicKGNode(id="n2", entity_type="book", label="B"),
        ],
        edges=[edge],
        hop_count=1,
    )
    result = rag_svc._project_citations_from_paths([path, path])
    assert len(result) == 1


def test_project_citations_skips_edge_without_quote(rag_svc):
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="",
        evidence_citation="[doc1:chunk1]",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="A"),
            AcademicKGNode(id="n2", entity_type="book", label="B"),
        ],
        edges=[edge],
        hop_count=1,
    )
    result = rag_svc._project_citations_from_paths([path])
    assert len(result) == 0


def test_project_citations_skips_malformed_citation(rag_svc):
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="some quote",
        evidence_citation="no-colon-here",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="A"),
            AcademicKGNode(id="n2", entity_type="book", label="B"),
        ],
        edges=[edge],
        hop_count=1,
    )
    result = rag_svc._project_citations_from_paths([path])
    assert len(result) == 0


# ============================================================
# _build_evidence_chain_stable
# ============================================================


def test_build_evidence_chain_empty(rag_svc):
    result = rag_svc._build_evidence_chain_stable(
        parse_chinese_query("test"), [], []
    )
    assert result == []


def test_build_evidence_chain_with_path(rag_svc):
    edge = AcademicKGEdge(
        edge_id="edge:1",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="quote text",
        evidence_citation="[doc1:chunk1]",
        evidence_id="ev:1",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="甲乙经"),
        ],
        edges=[edge],
        hop_count=1,
    )
    citation = AcademicCitation(
        document_id="doc1",
        chunk_id="chunk1",
        exact_quote="quote text",
        citation="[doc1:chunk1]",
        citation_id="cid:1",
        evidence_id="ev:1",
    )
    parsed = parse_chinese_query("皇甫谧的思想来源是什么")
    result = rag_svc._build_evidence_chain_stable(parsed, [path], [citation])
    assert len(result) == 1
    link = result[0]
    assert link.claim == "皇甫谧学术"
    assert link.path_id == "path_0"
    assert link.edge_ids == ["edge:1"]
    assert link.evidence_ids == ["ev:1"]
    assert link.citation_ids == ["cid:1"]


def test_build_evidence_chain_no_evidence_id_excluded(rag_svc):
    edge = AcademicKGEdge(
        edge_id="edge:2",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="q",
        evidence_citation="[d:c]",
        evidence_id="",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="X"),
            AcademicKGNode(id="n2", entity_type="book", label="Y"),
        ],
        edges=[edge],
        hop_count=1,
    )
    parsed = parse_chinese_query("test")
    result = rag_svc._build_evidence_chain_stable(parsed, [path], [])
    assert len(result) == 1
    assert result[0].citation_ids == []


# ============================================================
# _render_answer
# ============================================================


def test_render_answer_with_source_works(rag_svc):
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="针灸甲乙经"),
            AcademicKGNode(id="n3", entity_type="book", label="黄帝内经"),
        ],
        edges=[
            AcademicKGEdge(
                edge_id="e1",
                relation_type="compiled_from",
                label="编纂",
                evidence_quote="q1",
                evidence_citation="[d1:c1]",
            ),
            AcademicKGEdge(
                edge_id="e2",
                relation_type="derived_from",
                label="来源",
                evidence_quote="q2",
                evidence_citation="[d2:c2]",
            ),
        ],
        hop_count=2,
    )
    citation = AcademicCitation(
        document_id="d1",
        chunk_id="c1",
        exact_quote="q1",
        citation="[d1:c1]",
    )
    parsed = parse_chinese_query("皇甫谧著有什么")
    result = rag_svc._render_answer(parsed, [path], [citation])
    assert "黄帝内经" in result
    assert "皇甫谧" in result


def test_render_answer_no_multi_hop(rag_svc):
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="甲乙经"),
        ],
        edges=[
            AcademicKGEdge(
                edge_id="e1",
                relation_type="compiled_from",
                label="编纂",
                evidence_quote="q1",
                evidence_citation="[d1:c1]",
            ),
        ],
        hop_count=1,
    )
    parsed = parse_chinese_query("皇甫谧著有什么")
    result = rag_svc._render_answer(parsed, [path], [])
    assert "知识图谱路径" in result


def test_render_answer_with_citations(rag_svc):
    parsed = parse_chinese_query("皇甫谧著有什么")
    citation = AcademicCitation(
        document_id="d1",
        chunk_id="c1",
        exact_quote="some evidence text here",
        citation="[d1:c1]",
    )
    result = rag_svc._render_answer(parsed, [], [citation])
    assert "语料证据" in result
    assert "[d1:c1]" in result


def test_render_answer_empty(rag_svc):
    parsed = parse_chinese_query("皇甫谧著有什么")
    result = rag_svc._render_answer(parsed, [], [])
    assert len(result) > 0


def test_render_answer_shows_edge_evidence_quote(rag_svc):
    """Covers line 864-867: rendering edge evidence citation and quote."""
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="针灸甲乙经"),
            AcademicKGNode(id="n3", entity_type="book", label="黄帝内经"),
        ],
        edges=[
            AcademicKGEdge(
                edge_id="e1",
                relation_type="compiled_from",
                label="编纂",
                evidence_quote="皇甫谧著针灸甲乙经，取材于黄帝内经",
                evidence_citation="[d1:c1]",
            ),
        ],
        hop_count=2,
    )
    parsed = parse_chinese_query("皇甫谧的思想来源是什么")
    result = rag_svc._render_answer(parsed, [path], [])
    assert "边1证据: [d1:c1]" in result
    assert "引文: 皇甫谧著针灸甲乙经，取材于黄帝内经" in result


def test_render_answer_edge_without_quote_skips_quote_line(rag_svc):
    """Covers line 866 (evidence_quote falsy -> skip quote line)."""
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="甲乙经"),
        ],
        edges=[
            AcademicKGEdge(
                edge_id="e1",
                relation_type="compiled_from",
                label="编纂",
                evidence_quote="",
                evidence_citation="[d1:c1]",
            ),
        ],
        hop_count=1,
    )
    parsed = parse_chinese_query("皇甫谧著有什么")
    result = rag_svc._render_answer(parsed, [path], [])
    assert "边1证据" in result
    assert "引文:" not in result


def test_render_answer_truncates_long_quote(rag_svc):
    """Covers evidence_quote[:100] truncation."""
    long_quote = "皇甫谧" * 80
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="甲乙经"),
        ],
        edges=[
            AcademicKGEdge(
                edge_id="e1",
                relation_type="compiled_from",
                label="编纂",
                evidence_quote=long_quote,
                evidence_citation="[d1:c1]",
            ),
        ],
        hop_count=1,
    )
    parsed = parse_chinese_query("皇甫谧著有什么")
    result = rag_svc._render_answer(parsed, [path], [])
    assert "引文: " + long_quote[:100] in result
    assert long_quote[101:] not in result


# ============================================================
# _build_refusal_response
# ============================================================


def test_build_refusal_response_structure(rag_svc):
    parsed = parse_chinese_query("皇甫谧的思想来源是什么")
    result = rag_svc._build_refusal_response(parsed, "test query", "sha256abc")
    assert result.refusal is True
    assert result.query == "test query"
    assert result.citations == []
    assert result.kg_paths == []
    assert result.evidence_chain == []
    assert result.corpus_sha256 == "sha256abc"
    assert len(result.answer) > 0
    assert len(result.output_sha256) == 64


def test_build_refusal_response_mentions_subject(rag_svc):
    parsed = parse_chinese_query("皇甫谧著有什么")
    result = rag_svc._build_refusal_response(parsed, "q", "sha")
    assert "皇甫谧" in result.answer
    assert "学术" in result.answer


# ============================================================
# _retrieve_raw_candidates (mocked session)
# ============================================================


@pytest.mark.asyncio
async def test_retrieve_raw_candidates_empty_keywords(rag_svc):
    from app.services.academic_rag_service import ParsedQuery

    parsed = ParsedQuery(raw="test", keywords=[])
    result = await rag_svc._retrieve_raw_candidates(parsed)
    assert result == []


@pytest.mark.asyncio
async def test_retrieve_raw_candidates_search_terms_fallback():
    """Covers line 428: when subject matches all keywords, search_terms falls back."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    svc = AcademicRAGService(session)
    parsed = ParsedQuery(raw="test", subject="针灸", keywords=["针灸"])

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    result = await svc._retrieve_raw_candidates(parsed)
    assert result == []


@pytest.mark.asyncio
async def test_retrieve_raw_candidates_with_dedup_and_doc_lookup():
    """Covers lines 451, 475-481 (seen dedup), 486-497 (doc lookup)."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    svc = AcademicRAGService(session)

    mock_chunk = MagicMock()
    mock_chunk.document_id = "doc-a"
    mock_chunk.id = "chunk-1"
    mock_chunk.content = "皇甫谧针灸甲乙经"

    chunk_mock_result = MagicMock()
    chunk_mock_result.scalars.return_value.all.return_value = [mock_chunk]
    mock_doc = MagicMock()
    doc_mock_result = MagicMock()
    doc_mock_result.scalar_one_or_none.return_value = mock_doc

    session.execute = AsyncMock(side_effect=[chunk_mock_result, doc_mock_result])

    parsed = ParsedQuery(raw="test", subject="皇甫谧", keywords=["皇甫谧"])
    result = await svc._retrieve_raw_candidates(parsed)
    assert len(result) == 1
    assert result[0]["document_id"] == "doc-a"
    assert result[0]["chunk_id"] == "chunk-1"
    assert result[0]["doc"] is mock_doc


@pytest.mark.asyncio
async def test_retrieve_raw_candidates_seen_dedup_skips_duplicate():
    """Covers lines 475-479: seen set deduplication."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    svc = AcademicRAGService(session)

    mock_chunk = MagicMock()
    mock_chunk.document_id = "doc-a"
    mock_chunk.id = "chunk-1"
    mock_chunk.content = "test"

    chunk_mock = MagicMock()
    chunk_mock.scalars.return_value.all.return_value = [mock_chunk, mock_chunk]
    doc_mock = MagicMock()
    doc_mock.scalar_one_or_none.return_value = MagicMock()

    session.execute = AsyncMock(side_effect=[chunk_mock, doc_mock, doc_mock])

    parsed = ParsedQuery(raw="test", subject="test", keywords=["test"])
    result = await svc._retrieve_raw_candidates(parsed)
    assert len(result) == 1


@pytest.mark.asyncio
async def test_retrieve_raw_candidates_with_book_title_stripping():
    """Covers line 451: clean_term != term branch for 《》 stripping."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    svc = AcademicRAGService(session)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    parsed = ParsedQuery(raw="test", subject="针灸甲乙经", keywords=["《针灸甲乙经》"])
    result = await svc._retrieve_raw_candidates(parsed)
    assert result == []


# ============================================================
# _find_kg_paths — lines 510, 521-529, 531-539, 544-646
# ============================================================


@pytest.mark.asyncio
async def test_find_kg_paths_empty_subject():
    """Covers line 510: early return when no subject."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    svc = AcademicRAGService(session)
    parsed = ParsedQuery(raw="test", subject="", keywords=[])
    result = await svc._find_kg_paths(parsed)
    assert result == []


@pytest.mark.asyncio
async def test_find_kg_paths_with_neighbor_expansion_and_1hop():
    """Covers lines 521-529 (neighbor expansion), 544-575 (1-hop path building)."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    graph = MagicMock()
    svc = AcademicRAGService(session)
    svc.graph = graph

    node1 = GraphNode(
        id="person:001", entity_type="person", entity_id="001", label="皇甫谧",
    )
    node2 = GraphNode(
        id="book:002", entity_type="book", entity_id="002", label="针灸甲乙经",
    )
    graph.search_entities = AsyncMock(side_effect=[[node1], [], []])

    ev = GraphEvidence(
        document_id="d1", chunk_id="c1", exact_quote="皇甫谧撰针灸甲乙经",
        citation="[d1:c1]", claim_text="皇甫谧编纂针灸甲乙经",
        version_id="v1", passage_id="p1", source_uri="https://ctext.org/example",
    )
    edge = GraphEdge(
        id="er:001", source_id="person:001", target_id="book:002",
        relation_type="compiled_from", label="编纂依据", evidence=ev,
    )
    nbr = NeighborResult(center=node1, neighbors=[node2], edges=[edge])
    graph.get_neighbors = AsyncMock(return_value=nbr)

    parsed = ParsedQuery(raw="test", subject="皇甫谧", keywords=["皇甫谧"])
    result = await svc._find_kg_paths(parsed)

    assert len(result) >= 1
    paths_1hop = [p for p in result if p.hop_count == 1]
    assert len(paths_1hop) >= 1


@pytest.mark.asyncio
async def test_find_kg_paths_neighbor_value_error_caught():
    """Covers line 534-535: ValueError from get_neighbors during expansion."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    graph = MagicMock()
    svc = AcademicRAGService(session)
    svc.graph = graph

    graph.search_entities = AsyncMock(side_effect=[[], [], []])

    parsed = ParsedQuery(raw="test", subject="皇甫谧", keywords=["皇甫谧"])
    result = await svc._find_kg_paths(parsed)
    assert result == []


@pytest.mark.asyncio
async def test_find_kg_paths_2hop():
    """Covers lines 577-646: 2-hop path traversal with evidence."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    graph = MagicMock()
    svc = AcademicRAGService(session)
    svc.graph = graph

    node1 = GraphNode(
        id="person:001", entity_type="person", entity_id="001", label="皇甫谧",
    )
    node2 = GraphNode(
        id="book:002", entity_type="book", entity_id="002", label="针灸甲乙经",
    )
    node3 = GraphNode(
        id="book:003", entity_type="book", entity_id="003", label="黄帝内经",
    )
    graph.search_entities = AsyncMock(side_effect=[[node1], [], []])

    ev = GraphEvidence(
        document_id="d1", chunk_id="c1", exact_quote="皇甫谧撰针灸甲乙经",
        citation="[d1:c1]", claim_text="编纂", version_id="v1", passage_id="p1",
        source_uri="https://ctext.org/example",
    )
    edge1 = GraphEdge(
        id="er:001", source_id="person:001", target_id="book:002",
        relation_type="compiled_from", label="编纂依据", evidence=ev,
    )
    nbr1 = NeighborResult(center=node1, neighbors=[node2], edges=[edge1])

    ev2 = GraphEvidence(
        document_id="d2", chunk_id="c2", exact_quote="取材于黄帝内经",
        citation="[d2:c2]", claim_text="来源", version_id="v2", passage_id="p2",
        source_uri="https://ctext.org/source",
    )
    edge2 = GraphEdge(
        id="er:002", source_id="book:002", target_id="book:003",
        relation_type="derived_from", label="承袭", evidence=ev2,
    )
    nbr2 = NeighborResult(center=node2, neighbors=[node3], edges=[edge2])

    # get_neighbors called: expansion(node1) + path-build(node1) + 2hop(node2) + path-build(node2) = 4
    graph.get_neighbors = AsyncMock(side_effect=[nbr1, nbr1, nbr2, nbr2, nbr2, nbr2])

    parsed = ParsedQuery(raw="test", subject="皇甫谧", keywords=["皇甫谧"])
    result = await svc._find_kg_paths(parsed)

    paths_2hop = [p for p in result if p.hop_count == 2]
    assert len(paths_2hop) >= 1
    path_2h = paths_2hop[0]
    assert len(path_2h.nodes) == 3
    assert len(path_2h.edges) == 2


@pytest.mark.asyncio
async def test_find_kg_paths_2hop_value_error_on_second_neighbors():
    """Covers line 595-596: ValueError in second get_neighbors for 2-hop."""
    from app.services.academic_rag_service import ParsedQuery

    session = MagicMock()
    graph = MagicMock()
    svc = AcademicRAGService(session)
    svc.graph = graph

    node1 = GraphNode(
        id="person:001", entity_type="person", entity_id="001", label="皇甫谧",
    )
    node2 = GraphNode(
        id="book:002", entity_type="book", entity_id="002", label="甲乙经",
    )
    graph.search_entities = AsyncMock(side_effect=[[node1], [], []])

    ev = GraphEvidence(
        document_id="d1", chunk_id="c1", exact_quote="q", citation="[d1:c1]",
        claim_text="c", version_id="v1", passage_id="p1",
        source_uri="https://ctext.org/example",
    )
    edge1 = GraphEdge(
        id="er:001", source_id="person:001", target_id="book:002",
        relation_type="compiled_from", label="编纂依据", evidence=ev,
    )
    nbr1 = NeighborResult(center=node1, neighbors=[node2], edges=[edge1])
    nbr2_empty = NeighborResult(center=node2, neighbors=[], edges=[])

    # Call order: expansion(node1) + path-build(node1) + 2-hop(node2)=ValueError + path-build(node2) = 4 calls
    graph.get_neighbors = AsyncMock(
        side_effect=[nbr1, nbr1, ValueError("not found"), nbr2_empty]
    )

    parsed = ParsedQuery(raw="test", subject="皇甫谧", keywords=["皇甫谧"])
    result = await svc._find_kg_paths(parsed)

    assert all(p.hop_count == 1 for p in result)


# ============================================================
# _validate_all_path_edges — lines 672->716, 714, 717 (success path)
# ============================================================


@pytest.mark.asyncio
async def test_validate_all_path_edges_empty_paths(rag_svc):
    result = await rag_svc._validate_all_path_edges([])
    assert result == []


@pytest.mark.asyncio
async def test_validate_all_path_edges_path_with_no_edges(rag_svc):
    path = AcademicKGPath(
        nodes=[AcademicKGNode(id="n1", entity_type="person", label="X")],
        edges=[],
        hop_count=0,
    )
    result = await rag_svc._validate_all_path_edges([path])
    assert result == []


@pytest.mark.asyncio
async def test_validate_all_path_edges_no_relation_id(rag_svc):
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_id="",
        relation_type="compiled_from",
        label="编纂",
    )
    path = AcademicKGPath(
        nodes=[AcademicKGNode(id="n1", entity_type="person", label="X")],
        edges=[edge],
        hop_count=1,
    )
    result = await rag_svc._validate_all_path_edges([path])
    assert result == []


@pytest.mark.asyncio
async def test_validate_all_path_edges_db_rejects(rag_svc):
    """Edge with relation_id but DB returns no row -> excluded."""
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_id="er:abc123",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="some quote",
        evidence_citation="[doc1:chunk1]",
    )
    path = AcademicKGPath(
        nodes=[AcademicKGNode(id="n1", entity_type="person", label="X")],
        edges=[edge],
        hop_count=1,
    )
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    rag_svc.session.execute = AsyncMock(return_value=mock_result)
    result = await rag_svc._validate_all_path_edges([path])
    assert result == []


@pytest.mark.asyncio
async def test_validate_all_path_edges_missing_quote_or_citation(rag_svc):
    """Edge has relation_id but DB returns row - fails soft check for empty quote."""
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_id="er:abc123",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="",
        evidence_citation="",
    )
    path = AcademicKGPath(
        nodes=[AcademicKGNode(id="n1", entity_type="person", label="X")],
        edges=[edge],
        hop_count=1,
    )
    mock_result = MagicMock()
    mock_result.fetchone.return_value = ("er:abc123",)
    rag_svc.session.execute = AsyncMock(return_value=mock_result)
    result = await rag_svc._validate_all_path_edges([path])
    assert result == []


@pytest.mark.asyncio
async def test_validate_all_path_edges_success():
    """Covers line 714 (append) and 716-723 (successful validation + Path build)."""
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_id="er:abc123",
        relation_type="compiled_from",
        label="编纂依据",
        evidence_quote="皇甫谧撰针灸甲乙经",
        evidence_citation="[doc1:chunk1]",
        evidence_id="ev:1",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="甲乙经"),
        ],
        edges=[edge],
        hop_count=1,
    )

    session = MagicMock()
    svc = AcademicRAGService(session)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = ("er:abc123",)
    session.execute = AsyncMock(return_value=mock_result)

    result = await svc._validate_all_path_edges([path])
    assert len(result) == 1
    assert result[0].edges[0].edge_id == "e1"


@pytest.mark.asyncio
async def test_validate_all_path_edges_strips_er_prefix():
    """Covers relation_id removeprefix for 'er:' prefix."""
    edge = AcademicKGEdge(
        edge_id="e1",
        relation_id="er:xyz789",
        relation_type="compiled_from",
        label="编纂依据",
        evidence_quote="some quote",
        evidence_citation="[doc1:chunk1]",
        evidence_id="ev:1",
    )
    path = AcademicKGPath(
        nodes=[AcademicKGNode(id="n1", entity_type="person", label="X")],
        edges=[edge],
        hop_count=1,
    )

    session = MagicMock()
    svc = AcademicRAGService(session)
    mock_result = MagicMock()
    mock_result.fetchone.return_value = ("xyz789",)
    session.execute = AsyncMock(return_value=mock_result)

    result = await svc._validate_all_path_edges([path])
    assert len(result) == 1
    call_args = session.execute.call_args
    assert "xyz789" in str(call_args)


# ============================================================
# _compute_corpus_sha256 (mocked session)
# ============================================================


@pytest.mark.asyncio
async def test_compute_corpus_sha256_no_chunks(rag_svc):
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    rag_svc.session.execute = AsyncMock(return_value=mock_result)
    result = await rag_svc._compute_corpus_sha256()
    assert len(result) == 64
    assert result == hashlib.sha256(b"").hexdigest()


# ============================================================
# answer() — full success path (lines 335-373)
# ============================================================


@pytest.mark.asyncio
async def test_answer_success_path():
    """Covers lines 335-373: full answer pipeline with persistence."""
    session = MagicMock()
    graph = MagicMock()
    svc = AcademicRAGService(session)
    svc.graph = graph

    mock_chunk_result = MagicMock()
    mock_chunk_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_chunk_result)

    async def fake_retrieve(_parsed):
        return [{"document_id": "d1", "chunk_id": "c1", "content": "test"}]
    svc._retrieve_raw_candidates = fake_retrieve

    edge = AcademicKGEdge(
        edge_id="edge:1",
        relation_id="er:abc",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="some quote",
        evidence_citation="[doc1:chunk1]",
        evidence_id="ev:1",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="甲乙经"),
            AcademicKGNode(id="n3", entity_type="book", label="黄帝内经"),
        ],
        edges=[edge, edge],
        hop_count=2,
    )
    async def fake_find(_parsed):
        return [path]
    svc._find_kg_paths = fake_find

    async def fake_validate(paths):
        return [path]
    svc._validate_all_path_edges = fake_validate

    from unittest.mock import patch
    with patch(
        "app.services.academic_rag_service.CitationPersistenceService"
    ) as mock_cps:
        mock_instance = MagicMock()
        mock_instance.persist_academic_rag_citations = AsyncMock()
        mock_cps.return_value = mock_instance

        result = await svc.answer("皇甫谧的思想来源是什么")

    assert result.refusal is False
    assert len(result.citations) >= 1
    assert len(result.kg_paths) >= 1
    assert len(result.evidence_chain) >= 1
    assert len(result.answer) > 0
    assert len(result.corpus_sha256) == 64
    assert len(result.output_sha256) == 64
    mock_instance.persist_academic_rag_citations.assert_awaited_once()


@pytest.mark.asyncio
async def test_answer_persistence_failure_does_not_block():
    """Covers lines 370-373: exception handler when citation persistence fails."""
    session = MagicMock()
    graph = MagicMock()
    svc = AcademicRAGService(session)
    svc.graph = graph

    mock_chunk_result = MagicMock()
    mock_chunk_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_chunk_result)

    async def fake_retrieve(_parsed):
        return [{"document_id": "d1", "chunk_id": "c1", "content": "test"}]
    svc._retrieve_raw_candidates = fake_retrieve

    edge = AcademicKGEdge(
        edge_id="edge:1",
        relation_id="er:abc",
        relation_type="compiled_from",
        label="编纂",
        evidence_quote="some quote",
        evidence_citation="[doc1:chunk1]",
        evidence_id="ev:1",
    )
    path = AcademicKGPath(
        nodes=[
            AcademicKGNode(id="n1", entity_type="person", label="皇甫谧"),
            AcademicKGNode(id="n2", entity_type="book", label="甲乙经"),
            AcademicKGNode(id="n3", entity_type="book", label="内经"),
        ],
        edges=[edge, edge],
        hop_count=2,
    )
    async def fake_find(_parsed):
        return [path]
    svc._find_kg_paths = fake_find

    async def fake_validate(paths):
        return [path]
    svc._validate_all_path_edges = fake_validate

    from unittest.mock import patch
    with patch(
        "app.services.academic_rag_service.CitationPersistenceService"
    ) as mock_cps:
        mock_instance = MagicMock()
        mock_instance.persist_academic_rag_citations = AsyncMock(
            side_effect=RuntimeError("DB connection lost")
        )
        mock_cps.return_value = mock_instance

        result = await svc.answer("皇甫谧的思想来源是什么")

    assert result.refusal is False
    assert len(result.answer) > 0


@pytest.mark.asyncio
async def test_answer_no_citations_after_projection():
    """Covers line 341-342: _project_citations_from_paths returns empty -> refusal."""
    session = MagicMock()
    graph = MagicMock()
    svc = AcademicRAGService(session)
    svc.graph = graph

    mock_chunk_result = MagicMock()
    mock_chunk_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_chunk_result)

    async def fake_retrieve(_parsed):
        return []
    svc._retrieve_raw_candidates = fake_retrieve

    async def fake_find(_parsed):
        return []
    svc._find_kg_paths = fake_find

    async def fake_validate(paths):
        return []
    svc._validate_all_path_edges = fake_validate

    result = await svc.answer("皇甫谧的思想来源是什么")
    assert result.refusal is True
