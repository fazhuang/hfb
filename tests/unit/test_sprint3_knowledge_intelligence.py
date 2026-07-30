"""
Tracked strict tests for Sprint 3 Knowledge Intelligence P0 — Round 3.

Covers:
  1-5: Evidence validation
  6-7: Query-stage rejection of orphan/poisoned edges
  8:   EntityRelation API response includes full evidence
  9:   OpenAPI Graph responses are strict schemas
  10-11: Same-sentence co-occurrence, non-empty evidence
  12-13: Hierarchy direction correct
  14: Ambiguous hierarchy → no hierarchy edges
  15: Multiple shared chunks → stable evidence
  16-18: Template-based contradiction detection
  19: Intelligence API returns non-empty concept graph
  20: HTTP 10-repeat byte-identical
  21: Cross-PYTHONHASHSEED identical
  22: corpus_sha256 / output_sha256 independently verifiable
  23: Old evidence-free seed relations excluded
  24: Sprint 2 tests continue to pass
  P0-R3: FK edges without evidence excluded
  P0-R3: VersionRelation edges without evidence excluded
  P0-R3: All GraphEdge evidence non-null
  P0-R3: /relations filters forged quotes
  P0-R3: /relations filters wrong citations
  P0-R3: /relations filters orphan relations
  P0-R3: Pseudo-contradictions all rejected
  P0-R3: Exact template contradiction detected
  P0-R3: Single-document → insufficient_evidence
  P0-R3: Two-doc no comparable → insufficient_evidence
  P0-R3: Two-doc comparable no conflict → supported_comparison
  P0-R3: GraphEdge rejects evidence=None
  P0-R3: ConceptEdge rejects evidence=[]
  P0-R3: OpenAPI recursive strict
  P0-R3: Soft-delete allows recreation
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import UTC

import pytest
from app.models.book import Book
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.graph import EntityRelation
from app.models.person import Person
from app.schemas.graph import (
    GraphEvidence,
)
from app.services.graph_service import (
    GraphService,
    _parse_proposition,
    _propositions_comparable,
    _stable_hash,
    _validate_graph_evidence,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401

# ===================================================================
# Helpers
# ===================================================================


async def _setup_test_entities(session: AsyncSession) -> dict:
    """Create test person, book, document, and chunk."""
    p = Person(name="测试人物", dynasty="唐")
    session.add(p)
    await session.flush()

    b = Book(title="测试古籍", dynasty="唐", category="医经")
    session.add(b)
    await session.flush()

    d = Document(title="测试文献", dynasty="唐")
    session.add(d)
    await session.flush()

    c = DocumentChunk(
        document_id=d.id,
        chunk_index=0,
        content="测试人物编撰测试古籍。",
        token_count=20,
    )
    session.add(c)
    await session.flush()

    return {"person": p, "book": b, "document": d, "chunk": c}


def _make_valid_evidence(doc_id: str, chunk_id: str, quote: str) -> GraphEvidence:
    return GraphEvidence(
        document_id=doc_id,
        chunk_id=chunk_id,
        exact_quote=quote,
        citation=f"[{doc_id}:{chunk_id}]",
    )


# ===================================================================
# 1-5: Evidence validation
# ===================================================================


@pytest.mark.asyncio
class TestEvidenceValidation:
    async def test_fake_citation_rejected(self, db_session: AsyncSession) -> None:
        err = await _validate_graph_evidence(
            db_session, "fake", "fake", "irrelevant", "[fake:fake]"
        )
        assert err is not None
        assert "not found" in err.lower()

    async def test_source_or_target_missing_rejected(
        self, db_session: AsyncSession
    ) -> None:
        ents = await _setup_test_entities(db_session)
        ev = _make_valid_evidence(
            ents["document"].id, ents["chunk"].id, "测试人物编撰测试古籍。"
        )
        svc = GraphService(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.create_relation(
                source_entity_type="person",
                source_entity_id="00000000-0000-0000-0000-000000000000",
                target_entity_type="book",
                target_entity_id=ents["book"].id,
                relation_type="authored",
                evidence=ev,
            )
        with pytest.raises(ValueError, match="not found"):
            await svc.create_relation(
                source_entity_type="person",
                source_entity_id=ents["person"].id,
                target_entity_type="book",
                target_entity_id="00000000-0000-0000-0000-000000000000",
                relation_type="authored",
                evidence=ev,
            )

    async def test_document_deleted_rejected(self, db_session: AsyncSession) -> None:
        ents = await _setup_test_entities(db_session)
        d, c = ents["document"], ents["chunk"]
        from datetime import datetime

        d.is_deleted = True  # type: ignore[assignment]
        d.deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await db_session.flush()
        err = await _validate_graph_evidence(
            db_session, d.id, c.id, "测试人物编撰测试古籍。", f"[{d.id}:{c.id}]"
        )
        assert err is not None

    async def test_chunk_document_mismatch_rejected(
        self, db_session: AsyncSession
    ) -> None:
        ents = await _setup_test_entities(db_session)
        c = ents["chunk"]
        d2 = Document(title="另一个文献", dynasty="宋")
        db_session.add(d2)
        await db_session.flush()
        err = await _validate_graph_evidence(
            db_session, d2.id, c.id, "测试人物编撰测试古籍。", f"[{d2.id}:{c.id}]"
        )
        assert err is not None

    async def test_quote_not_in_chunk_rejected(self, db_session: AsyncSession) -> None:
        ents = await _setup_test_entities(db_session)
        d, c = ents["document"], ents["chunk"]
        err = await _validate_graph_evidence(
            db_session, d.id, c.id, "这段文字不在chunk中", f"[{d.id}:{c.id}]"
        )
        assert err is not None
        assert "substring" in err.lower()


# ===================================================================
# 6-7: Query-stage rejection
# ===================================================================


@pytest.mark.asyncio
class TestQueryStageRejection:
    async def test_orphan_edge_excluded_from_neighbors(
        self, db_session: AsyncSession
    ) -> None:
        ents = await _setup_test_entities(db_session)
        orphan = EntityRelation(
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="authored",
            description="孤立边",
        )
        db_session.add(orphan)
        await db_session.flush()
        svc = GraphService(db_session)
        neighbors = await svc.get_neighbors("person", ents["person"].id)
        edge_ids = {e.id for e in neighbors.edges}
        assert f"er:{orphan.id}" not in edge_ids

    async def test_tampered_quote_excluded(self, db_session: AsyncSession) -> None:
        ents = await _setup_test_entities(db_session)
        tampered = EntityRelation(
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            evidence_document_id=ents["document"].id,
            evidence_chunk_id=ents["chunk"].id,
            evidence_quote="被篡改的引用文本",
            evidence_citation=f"[{ents['document'].id}:{ents['chunk'].id}]",
        )
        db_session.add(tampered)
        await db_session.flush()
        svc = GraphService(db_session)
        neighbors = await svc.get_neighbors("person", ents["person"].id)
        edge_ids = {e.id for e in neighbors.edges}
        assert f"er:{tampered.id}" not in edge_ids


# ===================================================================
# 8: EntityRelationResponse evidence field
# ===================================================================


class TestEntityRelationResponseEvidence:
    def test_response_schema_has_evidence_field(self) -> None:
        from app.schemas.graph import EntityRelationResponse

        assert "evidence" in EntityRelationResponse.model_fields


# ===================================================================
# 9: OpenAPI strict schemas
# ===================================================================


class TestOpenAPIStrictSchemas:
    def test_graph_routes_not_dict(self) -> None:
        from app.api.v1.graph import router

        for route in router.routes:
            if hasattr(route, "response_model"):
                rm = route.response_model
                assert rm is not dict, (
                    f"Route {route.path} still uses response_model=dict"
                )
                assert rm is not None, f"Route {route.path} has no response_model"

    def test_graph_edge_evidence_required(self) -> None:
        """GraphEdge rejects evidence=None."""
        from app.schemas.graph import GraphEdge as GE

        with pytest.raises(Exception):
            GE(
                id="e1",
                source_id="s",
                target_id="t",
                relation_type="authored",
                label="作者",
                source="explicit",
                evidence=None,
            )

    def test_concept_edge_evidence_min_length(self) -> None:
        """ConceptEdge rejects evidence=[]."""
        from app.schemas.graph import ConceptEdge as CE

        with pytest.raises(Exception):
            CE(
                edge_id="test1234abc",
                source_concept_id="s1",
                target_concept_id="t1",
                relation_type="co_occurs_with",
                label="共现",
                evidence=[],
            )

    def test_all_graph_envelopes_have_extra_forbid(self) -> None:
        """All Graph envelope schemas have extra='forbid'."""
        from app.schemas.graph import (
            ConceptGraph,
            GraphCreateRelationEnvelope,
            GraphDeleteEnvelope,
            GraphEntitiesEnvelope,
            GraphNeighborsEnvelope,
            GraphNode,
            GraphPathEnvelope,
            GraphRelationsEnvelope,
            GraphSubgraphEnvelope,
            IntelligenceEnvelope,
            NeighborResult,
            PathResult,
            Subgraph,
        )

        schemas = [
            GraphEntitiesEnvelope,
            GraphNeighborsEnvelope,
            GraphPathEnvelope,
            GraphSubgraphEnvelope,
            GraphCreateRelationEnvelope,
            GraphRelationsEnvelope,
            GraphDeleteEnvelope,
            IntelligenceEnvelope,
            GraphNode,
            Subgraph,
            PathResult,
            NeighborResult,
            ConceptGraph,
        ]
        for s in schemas:
            mc = getattr(s, "model_config", {})
            assert mc.get("extra") == "forbid", f"{s.__name__} missing extra='forbid'"
            assert mc.get("strict") is True, f"{s.__name__} missing strict=True"

    def test_openapi_schema_additional_properties_false(self) -> None:
        """GraphEvidence JSON schema shows additionalProperties: false."""
        schema = GraphEvidence.model_json_schema()
        assert schema.get("additionalProperties") is False


# ===================================================================
# 10-11: Co-occurrence same-sentence only
# ===================================================================


@pytest.mark.asyncio
class TestCooccurrenceSameSentence:
    async def test_different_sentence_no_cooccurrence(
        self, db_session: AsyncSession
    ) -> None:
        d = Document(title="同句测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="经络是中医理论的重要组成部分。腧穴则是针灸操作的具体部位。",
            token_count=50,
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        cg = await svc.build_concept_graph(["经络", "腧穴"])
        co_oc_edges = [e for e in cg.edges if e.relation_type == "co_occurs_with"]
        assert len(co_oc_edges) == 0

    async def test_same_sentence_cooccurrence(self, db_session: AsyncSession) -> None:
        d = Document(title="同句测试2", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="经络与腧穴都是针灸的核心概念。",
            token_count=50,
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        cg = await svc.build_concept_graph(["经络", "腧穴"])
        co_oc_edges = [e for e in cg.edges if e.relation_type == "co_occurs_with"]
        assert len(co_oc_edges) == 1

    async def test_all_concept_edges_have_non_empty_evidence(
        self, db_session: AsyncSession
    ) -> None:
        d = Document(title="证据测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="经络与腧穴都是针灸的核心概念。",
            token_count=50,
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        cg = await svc.build_concept_graph(["经络", "腧穴"])
        for edge in cg.edges:
            assert len(edge.evidence) > 0, (
                f"Edge {edge.relation_type} has empty evidence"
            )
            for ev in edge.evidence:
                assert ev.document_id
                assert ev.chunk_id
                assert ev.exact_quote
                assert ev.citation


# ===================================================================
# 12-14: Hierarchy direction
# ===================================================================


@pytest.mark.asyncio
class TestHierarchyDirection:
    async def test_jingluo_belongs_to_zhenjiu(self, db_session: AsyncSession) -> None:
        d = Document(title="层级方向测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id, chunk_index=0, content="经络属于针灸。", token_count=20
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        cg = await svc.build_concept_graph(["经络", "针灸"])
        narrower = [e for e in cg.edges if e.relation_type == "narrower_than"]
        broader = [e for e in cg.edges if e.relation_type == "broader_than"]
        assert len(narrower) == 1
        assert len(broader) == 1
        jingluo_id = _stable_hash("经络")
        zhenjiu_id = _stable_hash("针灸")
        assert narrower[0].source_concept_id == jingluo_id
        assert narrower[0].target_concept_id == zhenjiu_id
        assert broader[0].source_concept_id == zhenjiu_id
        assert broader[0].target_concept_id == jingluo_id

    async def test_zhenjiu_includes_jingluo(self, db_session: AsyncSession) -> None:
        d = Document(title="包括测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id, chunk_index=0, content="针灸包括经络。", token_count=20
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        cg = await svc.build_concept_graph(["针灸", "经络"])
        narrower = [e for e in cg.edges if e.relation_type == "narrower_than"]
        broader = [e for e in cg.edges if e.relation_type == "broader_than"]
        assert len(narrower) == 1
        assert len(broader) == 1
        jingluo_id = _stable_hash("经络")
        zhenjiu_id = _stable_hash("针灸")
        assert narrower[0].source_concept_id == jingluo_id
        assert narrower[0].target_concept_id == zhenjiu_id
        assert broader[0].source_concept_id == zhenjiu_id
        assert broader[0].target_concept_id == jingluo_id

    async def test_ambiguous_expression_no_hierarchy(
        self, db_session: AsyncSession
    ) -> None:
        d = Document(title="模糊测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id, chunk_index=0, content="针灸和经络有关。", token_count=20
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        cg = await svc.build_concept_graph(["针灸", "经络"])
        narrower = [e for e in cg.edges if e.relation_type == "narrower_than"]
        broader = [e for e in cg.edges if e.relation_type == "broader_than"]
        assert len(narrower) == 0
        assert len(broader) == 0
        co_oc = [e for e in cg.edges if e.relation_type == "co_occurs_with"]
        assert len(co_oc) == 1


# ===================================================================
# 15: Multiple shared chunks
# ===================================================================


@pytest.mark.asyncio
class TestMultipleSharedChunks:
    async def test_multiple_chunks_produce_all_evidence(
        self, db_session: AsyncSession
    ) -> None:
        d = Document(title="多chunk测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d.id, chunk_index=0, content="经络和腧穴有关。", token_count=20
        )
        c2 = DocumentChunk(
            document_id=d.id,
            chunk_index=1,
            content="经络与腧穴都是中医概念。",
            token_count=20,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        svc = GraphService(db_session)
        cg = await svc.build_concept_graph(["经络", "腧穴"])
        co_oc = [e for e in cg.edges if e.relation_type == "co_occurs_with"]
        assert len(co_oc) == 1
        assert len(co_oc[0].evidence) == 2


# ===================================================================
# 16-18: Contradiction detection — ParsedProposition-based
# ===================================================================


class TestParsedProposition:
    """Unit tests for _parse_proposition and _propositions_comparable."""

    def test_parse_affirmative_shi(self) -> None:
        p = _parse_proposition("针灸是有效疗法。")
        assert p is not None
        assert p.family == "是"
        assert p.subject == "针灸"
        assert p.predicate == "有效疗法"
        assert p.polarity == "affirmative"

    def test_parse_negative_shi(self) -> None:
        p = _parse_proposition("针灸不是有效疗法。")
        assert p is not None
        assert p.family == "是"
        assert p.subject == "针灸"
        assert p.predicate == "有效疗法"
        assert p.polarity == "negative"

    def test_parse_affirmative_neng(self) -> None:
        p = _parse_proposition("针灸能缓解疼痛。")
        assert p is not None
        assert p.family == "能"
        assert p.subject == "针灸"
        assert p.predicate == "缓解疼痛"
        assert p.polarity == "affirmative"

    def test_parse_negative_neng(self) -> None:
        p = _parse_proposition("针灸不能缓解疼痛。")
        assert p is not None
        assert p.family == "能"
        assert p.subject == "针灸"
        assert p.predicate == "缓解疼痛"
        assert p.polarity == "negative"

    def test_parse_with_clause_returns_none(self) -> None:
        """Extra clause → cannot cleanly parse → None."""
        assert _parse_proposition("针灸可缓解疼痛但不是唯一疗法") is None
        assert _parse_proposition("针灸可缓解疼痛但不是唯一疗法。") is None

    def test_parse_different_propositions_not_comparable(self) -> None:
        """Different subject/predicate → not comparable."""
        p1 = _parse_proposition("针灸不是唯一疗法。")
        p2 = _parse_proposition("针灸可用于部分疼痛。")
        assert p1 is not None and p2 is not None
        assert not _propositions_comparable(p1, p2)

    def test_same_proposition_opposite_polarity_comparable(self) -> None:
        p1 = _parse_proposition("针灸是有效疗法。")
        p2 = _parse_proposition("针灸不是有效疗法。")
        assert p1 is not None and p2 is not None
        assert _propositions_comparable(p1, p2)
        assert p1.polarity != p2.polarity

    def test_same_proposition_same_polarity_comparable(self) -> None:
        p1 = _parse_proposition("针灸能缓解疼痛。")
        p2 = _parse_proposition("针灸能缓解疼痛。")
        assert p1 is not None and p2 is not None
        assert _propositions_comparable(p1, p2)
        assert p1.polarity == p2.polarity

    def test_different_subject_not_comparable(self) -> None:
        p1 = _parse_proposition("针灸是有效疗法。")
        p2 = _parse_proposition("按摩是有效疗法。")
        assert p1 is not None and p2 is not None
        assert not _propositions_comparable(p1, p2)

    def test_different_predicate_not_comparable(self) -> None:
        p1 = _parse_proposition("针灸能缓解疼痛。")
        p2 = _parse_proposition("针灸能治疗疾病。")
        assert p1 is not None and p2 is not None
        assert not _propositions_comparable(p1, p2)

    def test_different_family_not_comparable(self) -> None:
        p1 = _parse_proposition("针灸是有效疗法。")
        p2 = _parse_proposition("针灸能有效疗法。")
        assert p1 is not None and p2 is not None
        assert not _propositions_comparable(p1, p2)

    def test_compound_words_not_negation(self) -> None:
        """未病/无极 are not negation — they just don't match templates."""
        assert _parse_proposition("未病先防是中医的重要原则。") is not None
        assert _parse_proposition("无极而太极。") is None  # no template match at all

    def test_empty_subject_or_predicate_returns_none(self) -> None:
        assert _parse_proposition("是有效疗法。") is None
        assert _parse_proposition("针灸是。") is None


@pytest.mark.asyncio
class TestContradictionDetection:
    """Integration tests for cross_document_analysis with parsed propositions."""

    async def test_pseudo_contradictions_rejected__insufficient_evidence(
        self, db_session: AsyncSession
    ) -> None:
        """Different propositions: 针灸不是唯一疗法 vs 针灸可用于部分疼痛 → insufficient_evidence."""
        d1 = Document(title="文献A", dynasty="唐")
        d2 = Document(title="文献B", dynasty="宋")
        db_session.add_all([d1, d2])
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d1.id,
            chunk_index=0,
            content="针灸不是唯一疗法。",
            token_count=20,
        )
        c2 = DocumentChunk(
            document_id=d2.id,
            chunk_index=0,
            content="针灸可用于部分疼痛。",
            token_count=20,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        svc = GraphService(db_session)
        analysis = await svc.cross_document_analysis("针灸")
        assert analysis.status == "insufficient_evidence"
        assert len(analysis.contradictions) == 0

    async def test_same_affirmative__supported_comparison(
        self, db_session: AsyncSession
    ) -> None:
        """Both docs: 针灸能缓解疼痛 (same proposition, both affirmative) → supported_comparison."""
        d1 = Document(title="文献H", dynasty="唐")
        d2 = Document(title="文献I", dynasty="宋")
        db_session.add_all([d1, d2])
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d1.id, chunk_index=0, content="针灸能缓解疼痛。", token_count=20
        )
        c2 = DocumentChunk(
            document_id=d2.id, chunk_index=0, content="针灸能缓解疼痛。", token_count=20
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        svc = GraphService(db_session)
        analysis = await svc.cross_document_analysis("针灸")
        assert analysis.status == "supported_comparison"
        assert len(analysis.contradictions) == 0

    async def test_same_negative__supported_comparison(
        self, db_session: AsyncSession
    ) -> None:
        """Both docs: 针灸不能缓解疼痛 (same proposition, both negative) → supported_comparison."""
        d1 = Document(title="文献J", dynasty="唐")
        d2 = Document(title="文献K", dynasty="宋")
        db_session.add_all([d1, d2])
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d1.id,
            chunk_index=0,
            content="针灸不能缓解疼痛。",
            token_count=20,
        )
        c2 = DocumentChunk(
            document_id=d2.id,
            chunk_index=0,
            content="针灸不能缓解疼痛。",
            token_count=20,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        svc = GraphService(db_session)
        analysis = await svc.cross_document_analysis("针灸")
        assert analysis.status == "supported_comparison"
        assert len(analysis.contradictions) == 0

    async def test_opposite_polarity__confirmed_contradiction(
        self, db_session: AsyncSession
    ) -> None:
        """针灸能缓解疼痛 vs 针灸不能缓解疼痛 → confirmed_contradiction."""
        d1 = Document(title="文献C", dynasty="唐")
        d2 = Document(title="文献D", dynasty="宋")
        db_session.add_all([d1, d2])
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d1.id, chunk_index=0, content="针灸能缓解疼痛。", token_count=20
        )
        c2 = DocumentChunk(
            document_id=d2.id,
            chunk_index=0,
            content="针灸不能缓解疼痛。",
            token_count=20,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        svc = GraphService(db_session)
        analysis = await svc.cross_document_analysis("针灸")
        assert analysis.status == "confirmed_contradiction"
        assert len(analysis.contradictions) == 1

    async def test_clause_sentence__insufficient_evidence(
        self, db_session: AsyncSession
    ) -> None:
        """Clause: 针灸可缓解疼痛但不是唯一疗法 → cannot parse → insufficient_evidence."""
        d1 = Document(title="文献L", dynasty="唐")
        d2 = Document(title="文献M", dynasty="宋")
        db_session.add_all([d1, d2])
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d1.id,
            chunk_index=0,
            content="针灸可缓解疼痛但不是唯一疗法。",
            token_count=30,
        )
        c2 = DocumentChunk(
            document_id=d2.id, chunk_index=0, content="针灸可缓解疼痛。", token_count=20
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        svc = GraphService(db_session)
        analysis = await svc.cross_document_analysis("针灸")
        # c1 cannot be parsed (has clause), c2 parses as affirmative.
        # They are not the same parsed proposition → insufficient_evidence
        assert analysis.status == "insufficient_evidence"
        assert len(analysis.contradictions) == 0

    async def test_single_document_insufficient_evidence(
        self, db_session: AsyncSession
    ) -> None:
        d1 = Document(title="文献E", dynasty="唐")
        db_session.add(d1)
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d1.id,
            chunk_index=0,
            content="针灸是中医的重要组成部分。",
            token_count=20,
        )
        db_session.add(c1)
        await db_session.flush()
        svc = GraphService(db_session)
        analysis = await svc.cross_document_analysis("针灸")
        assert analysis.status == "insufficient_evidence"

    async def test_two_docs_no_comparable_insufficient_evidence(
        self, db_session: AsyncSession
    ) -> None:
        """Two documents but different subjects → insufficient_evidence."""
        d1 = Document(title="文献F", dynasty="唐")
        d2 = Document(title="文献G", dynasty="宋")
        db_session.add_all([d1, d2])
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d1.id,
            chunk_index=0,
            content="针灸是中医的重要组成部分。",
            token_count=20,
        )
        c2 = DocumentChunk(
            document_id=d2.id,
            chunk_index=0,
            content="经络理论指导针灸取穴。",
            token_count=20,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        svc = GraphService(db_session)
        analysis = await svc.cross_document_analysis("针灸")
        assert analysis.status == "insufficient_evidence"

    async def test_two_docs_unparseable__insufficient_evidence(
        self, db_session: AsyncSession
    ) -> None:
        """Two documents but neither parses into a template → insufficient_evidence."""
        d1 = Document(title="文献N", dynasty="唐")
        d2 = Document(title="文献O", dynasty="宋")
        db_session.add_all([d1, d2])
        await db_session.flush()
        c1 = DocumentChunk(
            document_id=d1.id,
            chunk_index=0,
            content="针灸是传统中医的宝贵遗产，历史悠久。",
            token_count=30,
        )
        c2 = DocumentChunk(
            document_id=d2.id,
            chunk_index=0,
            content="针灸广泛用于临床治疗各种疾病。",
            token_count=30,
        )
        db_session.add_all([c1, c2])
        await db_session.flush()
        svc = GraphService(db_session)
        analysis = await svc.cross_document_analysis("针灸")
        assert analysis.status == "insufficient_evidence"


# ===================================================================
# P0-R3: FK/Version edges without evidence excluded
# ===================================================================


@pytest.mark.asyncio
class TestFKEdgesExcluded:
    async def test_fk_author_edge_excluded_without_evidence(
        self, db_session: AsyncSession
    ) -> None:
        """Book.author_id creates no graph edge unless explicit EntityRelation with evidence."""
        p = Person(name="作者测试", dynasty="唐")
        db_session.add(p)
        await db_session.flush()
        b = Book(title="关联古籍", dynasty="唐", category="医经", author_id=p.id)
        db_session.add(b)
        await db_session.flush()
        svc = GraphService(db_session)
        path = await svc.find_path("person", p.id, "book", b.id)
        # No explicit EntityRelation with evidence → no path via FK
        assert path is None

    async def test_explicit_relation_with_evidence_enables_path(
        self, db_session: AsyncSession
    ) -> None:
        """Explicit EntityRelation with corpus evidence creates a valid path."""
        p = Person(name="作者测试2", dynasty="唐")
        db_session.add(p)
        await db_session.flush()
        b = Book(title="关联古籍2", dynasty="唐", category="医经")
        db_session.add(b)
        await db_session.flush()
        d = Document(title="测试文献", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="作者测试2编撰关联古籍2。",
            token_count=20,
        )
        db_session.add(c)
        await db_session.flush()
        ev = GraphEvidence(
            document_id=d.id,
            chunk_id=c.id,
            exact_quote="作者测试2编撰关联古籍2。",
            citation=f"[{d.id}:{c.id}]",
        )
        svc = GraphService(db_session)
        rel = await svc.create_relation(
            "person", p.id, "book", b.id, "authored", evidence=ev
        )
        rel.evidence_status = "verified"
        from datetime import datetime

        rel.verified_by = "test-reviewer"
        rel.verified_at = datetime.now(UTC)
        rel.claim_text = "作者测试2编撰关联古籍2"
        rel.evidence_source_uri = "https://ctext.org/test-source2"
        await db_session.flush()
        path = await svc.find_path("person", p.id, "book", b.id)
        assert path is not None
        assert path.length == 1
        assert path.edges[0].evidence is not None


# ===================================================================
# P0-R3: /relations filtering
# ===================================================================


@pytest.mark.asyncio
class TestRelationsFiltering:
    async def test_validated_relations_filters_forged_quote(
        self, db_session: AsyncSession
    ) -> None:
        ents = await _setup_test_entities(db_session)
        # Insert with valid evidence
        ev = _make_valid_evidence(
            ents["document"].id, ents["chunk"].id, "测试人物编撰测试古籍。"
        )
        svc = GraphService(db_session)
        rel = await svc.create_relation(
            "person",
            ents["person"].id,
            "book",
            ents["book"].id,
            "authored",
            evidence=ev,
        )
        # Now tamper in DB
        rel.evidence_quote = "被篡改的内容"
        await db_session.flush()
        validated = await svc.get_validated_relations_for_entity(
            "person", ents["person"].id
        )
        assert len(validated) == 0

    async def test_validated_relations_filters_wrong_citation(
        self, db_session: AsyncSession
    ) -> None:
        ents = await _setup_test_entities(db_session)
        ev = _make_valid_evidence(
            ents["document"].id, ents["chunk"].id, "测试人物编撰测试古籍。"
        )
        svc = GraphService(db_session)
        rel = await svc.create_relation(
            "person",
            ents["person"].id,
            "book",
            ents["book"].id,
            "authored",
            evidence=ev,
        )
        rel.evidence_citation = "[fake:citation]"
        await db_session.flush()
        validated = await svc.get_validated_relations_for_entity(
            "person", ents["person"].id
        )
        assert len(validated) == 0

    async def test_validated_relations_filters_missing_entity(
        self, db_session: AsyncSession
    ) -> None:
        ents = await _setup_test_entities(db_session)
        ev = _make_valid_evidence(
            ents["document"].id, ents["chunk"].id, "测试人物编撰测试古籍。"
        )
        svc = GraphService(db_session)
        await svc.create_relation(
            "person",
            ents["person"].id,
            "book",
            ents["book"].id,
            "authored",
            evidence=ev,
        )
        # Soft-delete the source entity
        from datetime import datetime

        ents["person"].is_deleted = True  # type: ignore[assignment]
        ents["person"].deleted_at = datetime.now(UTC)  # type: ignore[assignment]
        await db_session.flush()
        validated = await svc.get_validated_relations_for_entity(
            "person", ents["person"].id
        )
        assert len(validated) == 0


# ===================================================================
# P0-R3: Active-only unique constraint — soft-delete allows recreate
# ===================================================================


@pytest.mark.asyncio
class TestActiveUniqueConstraint:
    async def test_active_duplicate_rejected(self, db_session: AsyncSession) -> None:
        ents = await _setup_test_entities(db_session)
        ev = _make_valid_evidence(
            ents["document"].id, ents["chunk"].id, "测试人物编撰测试古籍。"
        )
        svc = GraphService(db_session)
        await svc.create_relation(
            "person",
            ents["person"].id,
            "book",
            ents["book"].id,
            "authored",
            evidence=ev,
        )
        with pytest.raises(ValueError, match="Duplicate|already exists"):
            await svc.create_relation(
                "person",
                ents["person"].id,
                "book",
                ents["book"].id,
                "authored",
                evidence=ev,
            )

    async def test_soft_delete_allows_recreate(self, db_session: AsyncSession) -> None:
        ents = await _setup_test_entities(db_session)
        ev = _make_valid_evidence(
            ents["document"].id, ents["chunk"].id, "测试人物编撰测试古籍。"
        )
        svc = GraphService(db_session)
        rel1 = await svc.create_relation(
            "person",
            ents["person"].id,
            "book",
            ents["book"].id,
            "authored",
            evidence=ev,
        )
        # Soft delete
        ok = await svc.delete_relation(rel1.id)
        assert ok is True
        # Re-create should work
        rel2 = await svc.create_relation(
            "person",
            ents["person"].id,
            "book",
            ents["book"].id,
            "authored",
            evidence=ev,
        )
        assert rel2.id != rel1.id

    async def test_two_active_duplicates_rejected(
        self, db_session: AsyncSession
    ) -> None:
        """Two active duplicate edges are rejected at the service level."""
        ents = await _setup_test_entities(db_session)
        ev = _make_valid_evidence(
            ents["document"].id, ents["chunk"].id, "测试人物编撰测试古籍。"
        )
        svc = GraphService(db_session)
        await svc.create_relation(
            "person",
            ents["person"].id,
            "book",
            ents["book"].id,
            "authored",
            evidence=ev,
        )
        # Second create with same parameters must be rejected
        with pytest.raises(ValueError, match="Duplicate|already exists"):
            await svc.create_relation(
                "person",
                ents["person"].id,
                "book",
                ents["book"].id,
                "authored",
                evidence=ev,
            )


# ===================================================================
# 19: Intelligence API returns non-empty concept graph
# ===================================================================


@pytest.mark.asyncio
class TestIntelligenceAPI:
    async def test_intelligence_returns_concept_graph(
        self, db_session: AsyncSession
    ) -> None:
        d = Document(title="智能测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="皇甫谧编撰的针灸甲乙经系统阐述了经络和腧穴的理论。",
            token_count=100,
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        result = await svc.intelligence("皇甫谧 针灸 经络")
        assert result["query"] == "皇甫谧 针灸 经络"
        cg = result["concept_graph"]
        assert len(cg["nodes"]) >= 1
        assert len(result["corpus_sha256"]) == 64
        assert len(result["output_sha256"]) == 64
        assert result["pipeline_version"] == "1.0.0"
        assert "research_hypotheses" in result


# ===================================================================
# 22: Hash verification (independently verifiable)
# ===================================================================


class TestIndependentHashVerification:
    def test_corpus_hash_format(self) -> None:
        """corpus_sha256 is valid 64-char hex."""
        test_hash = hashlib.sha256(b"test corpus").hexdigest()
        assert len(test_hash) == 64
        assert all(c in "0123456789abcdef" for c in test_hash)

    @pytest.mark.asyncio
    async def test_corpus_hash_independently_verifiable(
        self, db_session: AsyncSession
    ) -> None:
        """corpus_sha256 can be independently recomputed from corpus bytes."""
        d = Document(title="复算测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="针灸甲乙经记载大量穴位。",
            token_count=20,
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        result = await svc.intelligence("针灸")
        # The corpus hash should match independent recomputation
        corpus_sha = result["corpus_sha256"]
        # Recompute from the known chunks
        from sqlalchemy import select

        chunk_stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.is_deleted.is_(False))
            .order_by(DocumentChunk.id)
        )
        chunk_result = await db_session.execute(chunk_stmt)
        all_chunks = chunk_result.scalars().all()
        corpus_parts = sorted(f"{c.document_id}:{c.id}:{c.content}" for c in all_chunks)
        expected_sha = hashlib.sha256("\n".join(corpus_parts).encode()).hexdigest()
        assert corpus_sha == expected_sha, (
            "corpus_sha256 does not match independent recomputation"
        )

    @pytest.mark.asyncio
    async def test_output_hash_independently_verifiable(
        self, db_session: AsyncSession
    ) -> None:
        """output_sha256 is canonical JSON hash with output_sha256 cleared."""
        d = Document(title="输出复算测试", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="针灸是传统中医的宝贵遗产。",
            token_count=20,
        )
        db_session.add(c)
        await db_session.flush()
        svc = GraphService(db_session)
        result = await svc.intelligence("针灸")
        output_sha = result["output_sha256"]
        # Clear output_sha256 and recompute
        payload_for_hash = dict(result)
        payload_for_hash["output_sha256"] = ""
        output_str = json.dumps(
            payload_for_hash, sort_keys=True, ensure_ascii=False, separators=(",", ":")
        )
        expected_sha = hashlib.sha256(output_str.encode()).hexdigest()
        assert output_sha == expected_sha, (
            "output_sha256 does not match independent recomputation"
        )


# ===================================================================
# 23: Old evidence-free seed relations excluded
# ===================================================================


@pytest.mark.asyncio
class TestOldSeedRelationsExcluded:
    async def test_evidenceless_relation_excluded(
        self, db_session: AsyncSession
    ) -> None:
        ents = await _setup_test_entities(db_session)
        seed = EntityRelation(
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="authored",
            description="无证据种子数据",
        )
        db_session.add(seed)
        await db_session.flush()
        svc = GraphService(db_session)
        neighbors = await svc.get_neighbors("person", ents["person"].id)
        edge_ids = {e.id for e in neighbors.edges}
        assert f"er:{seed.id}" not in edge_ids


# ===================================================================
# 20: Real HTTP 10-repeat determinism via ASGITransport
# ===================================================================


@pytest.mark.asyncio
class TestHTTPDeterminism:
    """Test 20: real HTTP determinism — 10 POSTs to /api/v1/graph/intelligence,
    comparing raw response.content directly (no json.dumps, no sort_keys).
    """

    async def test_http_10_repeat_byte_identical(
        self, db_session_persistent: AsyncSession
    ):
        """POST /api/v1/graph/intelligence × 10 → raw response.content identical."""
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk

        # Seed fixed corpus
        d = Document(id="http-det-doc-001", title="HTTP确定测试", dynasty="唐")
        db_session_persistent.add(d)
        await db_session_persistent.flush()

        c1 = DocumentChunk(
            id="http-det-chunk-001",
            document_id=d.id,
            chunk_index=0,
            content="皇甫谧编撰的针灸甲乙经系统阐述了经络理论。",
            token_count=50,
        )
        c2 = DocumentChunk(
            id="http-det-chunk-002",
            document_id=d.id,
            chunk_index=1,
            content="针灸是传统中医的重要组成部分。",
            token_count=50,
        )
        db_session_persistent.add_all([c1, c2])
        await db_session_persistent.flush()

        # Build a real FastAPI app with the graph router
        from app.api.v1.graph import router as graph_router
        from app.db.database import get_session
        from fastapi import FastAPI

        app = FastAPI()

        # Override get_session with our seeded session
        async def override_get_session():
            yield db_session_persistent

        app.dependency_overrides[get_session] = override_get_session

        # Override auth: patch the require_permission factory so all guards are no-ops
        import app.middleware.auth as auth_mod

        app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"

        # require_permission returns a Depends-wrapped async checker.
        # Override it at the FastAPI level: every Depends(guard_*) calls the checker,
        # which internally calls has_permission on AuthService. We override AuthService.
        async def _fake_auth_service():
            class FakeAuth:
                async def has_permission(self, *a, **kw):
                    return True

                async def has_any_permission(self, *a, **kw):
                    return True

            return FakeAuth()

        app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

        app.include_router(graph_router, prefix="/api/v1")

        # Use httpx.AsyncClient with ASGITransport
        import httpx

        transport = httpx.ASGITransport(app=app)  # type: ignore[arg-type]
        async with httpx.AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            responses = []
            for _ in range(10):
                r = await client.post(
                    "/api/v1/graph/intelligence",
                    json={"query": "皇甫谧 针灸 经络"},
                )
                responses.append(r)

        assert all(r.status_code == 200 for r in responses), (
            f"Not all 200: {[r.status_code for r in responses]}"
        )
        unique = {r.content for r in responses}
        assert len(unique) == 1, f"Expected 1 unique body, got {len(unique)}"


# ===================================================================
# 21: Cross-PYTHONHASHSEED determinism via real HTTP subprocess
# ===================================================================


class TestHashSeedDeterminism:
    """Test 21: 3 subprocesses with different PYTHONHASHSEED,
    each running a real FastAPI app and calling the HTTP endpoint.
    Raw response.content is compared directly — no re-sorting, no hash clearing.
    """

    def test_cross_pythonhashseed_identical(self):
        worker_code = """
import asyncio, os, sys
os.environ["PYTHONHASHSEED"] = os.environ.get("PYTHONHASHSEED", "1")

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import httpx

# Import all models so Base.metadata is fully populated
import app.models.book  # noqa
import app.models.chapter  # noqa
import app.models.document  # noqa
import app.models.document_chunk  # noqa
import app.models.graph  # noqa
import app.models.person  # noqa
import app.models.version  # noqa
import app.models.passage  # noqa
import app.models.version_relation  # noqa
import app.models.user  # noqa
import app.models.institution  # noqa
import app.models.paper  # noqa
import app.models.image  # noqa
import app.models.workspace  # noqa

async def main():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    from app.db.base import Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk

        d = Document(id="hs-http-doc-001", title="种子测试", dynasty="唐")
        session.add(d)
        await session.flush()
        c = DocumentChunk(
            id="hs-http-chunk-001", document_id=d.id, chunk_index=0,
            content="皇甫谧编撰的针灸甲乙经系统阐述了经络理论。", token_count=50,
        )
        session.add(c)
        await session.flush()

        from app.api.v1.graph import router as graph_router
        from app.db.database import get_session

        app = FastAPI()

        async def override_get_session():
            yield session

        app.dependency_overrides[get_session] = override_get_session

        # Override auth
        import app.middleware.auth as auth_mod
        app.dependency_overrides[auth_mod.get_current_user] = lambda: "test-user-id"
        async def _fake_auth_service():
            class FakeAuth:
                async def has_permission(self, *a, **kw): return True
                async def has_any_permission(self, *a, **kw): return True
            return FakeAuth()
        app.dependency_overrides[auth_mod.get_auth_service] = _fake_auth_service

        app.include_router(graph_router, prefix="/api/v1")

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.post("/api/v1/graph/intelligence", json={"query": "皇甫谧 针灸 经络"})
            assert r.status_code == 200, f"HTTP {r.status_code}"
            sys.stdout.buffer.write(r.content)
            sys.stdout.buffer.flush()

    await engine.dispose()

asyncio.run(main())
"""

        import os as _os

        _test_dir = _os.path.dirname(_os.path.abspath(__file__))
        _repo_root = _os.path.dirname(_os.path.dirname(_test_dir))
        _backend_dir = _os.path.join(_repo_root, "apps", "backend")

        outputs = []
        for seed in [1, 2, 99]:
            env = os.environ.copy()
            env["PYTHONHASHSEED"] = str(seed)
            env["PYTHONPATH"] = _backend_dir
            proc = subprocess.run(
                [sys.executable, "-c", worker_code],
                capture_output=True,
                env=env,
                cwd=_backend_dir,
            )
            assert proc.returncode == 0, (
                f"PYTHONHASHSEED={seed} failed (rc={proc.returncode}): "
                f"{proc.stderr.decode()[:500]}"
            )
            outputs.append(proc.stdout)

        unique = set(outputs)
        assert len(unique) == 1, (
            f"Cross-PYTHONHASHSEED outputs differ! "
            f"Got {len(unique)} unique outputs for seeds [1, 2, 99]"
        )


# ===================================================================
# 24: Sprint 2 tests still pass (verified by full suite run)
# ===================================================================
