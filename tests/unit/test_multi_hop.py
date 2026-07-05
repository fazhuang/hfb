"""Tests for multi-hop evidence chain query."""

import pytest
from app.models.graph import EntityRelation
from app.services.graph_service import GraphService
from tests.conftest_db import db_session  # noqa: F401


@pytest.mark.asyncio
async def test_multi_hop_no_academic_edges_returns_empty(db_session):
    """When no edges meet academic criteria, result is empty."""
    svc = GraphService(db_session)
    paths = await svc.multi_hop_query(
        source_type="person", source_id="p1",
        target_type="book", target_id="b1",
        min_evidence_level=2, max_hops=3,
    )
    assert paths == []


@pytest.mark.asyncio
async def test_multi_hop_single_hop_path(db_session):
    """A single academic edge should produce a one-hop path."""
    # Create seed entities: person, book
    from app.models.person import Person
    from app.models.book import Book

    person = Person(id="p-test-1", name="测试人物")
    book = Book(id="b-test-1", title="测试书")
    db_session.add_all([person, book])
    await db_session.flush()

    # Create an academic edge
    edge = EntityRelation(
        source_entity_type="person", source_entity_id="p-test-1",
        target_entity_type="book", target_entity_id="b-test-1",
        relation_type="authored",
        evidence_document_id="doc-1",
        evidence_chunk_id="chunk-1",
        evidence_quote="测试原文引用",
        evidence_citation="测试书·卷一",
        evidence_version_id="ver-1",
        evidence_passage_id="pass-1",
        evidence_source_uri="https://ctext.org/test",
        evidence_status="verified",
        evidence_level=3,
        claim_text="测试人物著测试书",
        verified_by="test-reviewer",
    )
    db_session.add(edge)
    await db_session.flush()

    svc = GraphService(db_session)
    paths = await svc.multi_hop_query(
        source_type="person", source_id="p-test-1",
        target_type="book", target_id="b-test-1",
        min_evidence_level=2, max_hops=3,
    )
    assert len(paths) == 1
    assert paths[0].min_evidence_level == 3
    assert paths[0].total_confidence == 0.85
    assert len(paths[0].hops) == 1
    assert paths[0].hops[0].relation_type == "authored"


@pytest.mark.asyncio
async def test_multi_hop_two_hop_path(db_session):
    """A path with two academic edges."""
    from app.models.person import Person
    from app.models.book import Book

    person = Person(id="p-2h-1", name="作者")
    book1 = Book(id="b-2h-1", title="源书")
    book2 = Book(id="b-2h-2", title="目标书")
    db_session.add_all([person, book1, book2])
    await db_session.flush()

    edge1 = EntityRelation(
        source_entity_type="person", source_entity_id="p-2h-1",
        target_entity_type="book", target_entity_id="b-2h-1",
        relation_type="authored",
        evidence_document_id="doc-1", evidence_chunk_id="chunk-1",
        evidence_quote="quote1", evidence_citation="citation1",
        evidence_version_id="ver-1", evidence_passage_id="pass-1",
        evidence_source_uri="https://ctext.org/test1",
        evidence_status="verified", evidence_level=3,
        claim_text="test", verified_by="test-reviewer",
    )
    edge2 = EntityRelation(
        source_entity_type="book", source_entity_id="b-2h-1",
        target_entity_type="book", target_entity_id="b-2h-2",
        relation_type="compiled_from",
        evidence_document_id="doc-2", evidence_chunk_id="chunk-2",
        evidence_quote="quote2", evidence_citation="citation2",
        evidence_version_id="ver-2", evidence_passage_id="pass-2",
        evidence_source_uri="https://ctext.org/test2",
        evidence_status="verified", evidence_level=2,
        claim_text="test", verified_by="test-reviewer",
    )
    db_session.add_all([edge1, edge2])
    await db_session.flush()

    svc = GraphService(db_session)
    paths = await svc.multi_hop_query(
        source_type="person", source_id="p-2h-1",
        target_type="book", target_id="b-2h-2",
        min_evidence_level=2, max_hops=3,
    )
    assert len(paths) == 1
    assert len(paths[0].hops) == 2
    # total confidence = 0.85 * 0.65 = 0.5525
    assert paths[0].total_confidence == 0.5525
    # min evidence level = 2
    assert paths[0].min_evidence_level == 2
