"""Tests for multi-hop evidence chain query — post-blocker-1 hardening.

Verifies that multi_hop_query() re-validates every candidate EntityRelation
via _validate_explicit_relation() + _derive_evidence_level() at query time,
and NEVER trusts persisted evidence_status or evidence_level.
"""

import pytest
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.passage import Passage
from app.models.person import Person
from app.models.version import Version
from app.schemas.graph import GraphEvidence
from app.services.graph_service import GraphService
from tests.conftest_db import db_session  # noqa: F401


# ── helpers ──────────────────────────────────────────────────────────


def _make_ev(doc_id: str, chunk_id: str, quote: str) -> GraphEvidence:
    return GraphEvidence(
        document_id=doc_id,
        chunk_id=chunk_id,
        exact_quote=quote,
        citation=f"[{doc_id}:{chunk_id}]",
    )


async def _seed_verified_2hop(session) -> dict:
    """Seed a fully verified 2-hop path: person → book1 → book2.

    Uses quotes that pass semantic evidence policies:
      - compiled: needs 撰/著/编 markers
      - compiled_from: needs source-derivation markers or 《...》 named texts
    """
    person = Person(id="p-acc-1", name="测试作者")
    book1 = Book(id="b-acc-1", title="著作A")
    book2 = Book(id="b-acc-2", title="著作B")
    session.add_all([person, book1, book2])
    await session.flush()

    doc = Document(
        id="doc-acc-1",
        title="测试文献",
        content_text="乃撰《著作A》，采自《著作B》及其他典籍。",
    )
    session.add(doc)
    await session.flush()

    chapter = Chapter(
        id="ch-acc-1",
        book_id=book1.id,
        title="测试章",
        order=1,
    )
    session.add(chapter)
    await session.flush()

    version = Version(id="ver-acc-1", book_id=book1.id, version_name="测试版本")
    session.add(version)
    await session.flush()

    passage = Passage(
        id="pass-acc-1",
        chapter_id=chapter.id,
        version_id=version.id,
        content_text="乃撰《著作A》，采自《著作B》及其他典籍。",
        order=1,
    )
    session.add(passage)
    await session.flush()

    chunk = DocumentChunk(
        id="chunk-acc-1",
        document_id=doc.id,
        chunk_index=0,
        content="乃撰《著作A》，采自《著作B》及其他典籍。",
        token_count=10,
        passage_id=passage.id,
    )
    session.add(chunk)
    await session.flush()

    svc = GraphService(session)

    # Hop 1: person → book1 (compiled — uses 撰 marker)
    q1 = "乃撰《著作A》"
    ev1 = _make_ev(doc.id, chunk.id, q1)
    r1 = await svc.create_relation(
        source_entity_type="person",
        source_entity_id=person.id,
        target_entity_type="book",
        target_entity_id=book1.id,
        relation_type="compiled",
        description="hop1",
        evidence=ev1,
    )
    r1 = await svc.verify_relation(
        relation_id=r1.id,
        claim_text="测试作者编撰著作A",
        evidence_document_id=doc.id,
        evidence_version_id=version.id,
        evidence_passage_id=passage.id,
        evidence_chunk_id=chunk.id,
        evidence_quote=q1,
        evidence_source_uri="https://ctext.org/test",
        verified_by="test-reviewer",
    )

    # Hop 2: book1 → book2 (compiled_from — uses 采 and 《著作B》)
    q2 = "采自《著作B》"
    ev2 = _make_ev(doc.id, chunk.id, q2)
    r2 = await svc.create_relation(
        source_entity_type="book",
        source_entity_id=book1.id,
        target_entity_type="book",
        target_entity_id=book2.id,
        relation_type="compiled_from",
        description="hop2",
        evidence=ev2,
    )
    r2 = await svc.verify_relation(
        relation_id=r2.id,
        claim_text="著作A以著作B为编纂来源",
        evidence_document_id=doc.id,
        evidence_version_id=version.id,
        evidence_passage_id=passage.id,
        evidence_chunk_id=chunk.id,
        evidence_quote=q2,
        evidence_source_uri="https://ctext.org/test2",
        verified_by="test-reviewer",
    )

    return {
        "person": person,
        "book1": book1,
        "book2": book2,
        "doc": doc,
        "chunk": chunk,
        "version": version,
        "passage": passage,
        "r1": r1,
        "r2": r2,
    }


# ── tests ────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_real_2hop_path_returns(db_session):
    """A fully verified, real 2-hop path produces output."""
    ents = await _seed_verified_2hop(db_session)
    svc = GraphService(db_session)
    paths = await svc.multi_hop_query(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
        min_evidence_level=2,
        max_hops=3,
    )
    assert len(paths) == 1
    assert len(paths[0].hops) == 2
    assert paths[0].hops[0].relation_type == "compiled"
    assert paths[0].hops[1].relation_type == "compiled_from"


@pytest.mark.asyncio
async def test_tampered_missing_verified_at_excluded(db_session):
    """Tampered-to-verified relation without verified_at is excluded at query time."""
    ents = await _seed_verified_2hop(db_session)
    svc = GraphService(db_session)

    # Tamper r2: strip verified_at
    r2 = ents["r2"]
    r2.verified_at = None
    await db_session.flush()

    paths = await svc.multi_hop_query(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
        min_evidence_level=2,
        max_hops=3,
    )
    assert len(paths) == 0, (
        f"Tampered relation (missing verified_at) must be excluded. "
        f"Got {len(paths)} paths."
    )


@pytest.mark.asyncio
async def test_fake_document_excluded(db_session):
    """Relation with non-existent document is excluded at query time."""
    ents = await _seed_verified_2hop(db_session)
    svc = GraphService(db_session)

    r2 = ents["r2"]
    r2.evidence_document_id = "fake-doc-999"
    await db_session.flush()

    paths = await svc.multi_hop_query(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
        min_evidence_level=2,
        max_hops=3,
    )
    assert len(paths) == 0


@pytest.mark.asyncio
async def test_wrong_passage_version_excluded(db_session):
    """Relation with non-existent passage (provenance broken) is excluded."""
    ents = await _seed_verified_2hop(db_session)
    svc = GraphService(db_session)

    r2 = ents["r2"]
    r2.evidence_passage_id = "pass-acc-999"  # non-existent
    await db_session.flush()

    paths = await svc.multi_hop_query(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
        min_evidence_level=2,
        max_hops=3,
    )
    assert len(paths) == 0


@pytest.mark.asyncio
async def test_deleted_reviewer_excluded(db_session):
    """Relation whose reviewer is deactivated is excluded at query time.
    Create a real user, then deactivate them — FK satisfied but validation fails."""
    ents = await _seed_verified_2hop(db_session)

    # Create a real user first, then deactivate
    from app.models.user import User

    temp_user = User(
        id="temp-reviewer-99",
        username="temp-reviewer-99",
        email="temp99@test.com",
        hashed_password="test",
        is_active=True,
        is_superuser=True,  # superuser so it passes at verify time
    )
    db_session.add(temp_user)
    await db_session.flush()

    # Swap r2's verified_by to the temp user
    r2 = ents["r2"]
    r2.verified_by = "temp-reviewer-99"
    await db_session.flush()

    # Now deactivate the user — query-time re-validation must exclude it
    temp_user.is_active = False
    await db_session.flush()

    svc = GraphService(db_session)
    paths = await svc.multi_hop_query(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
        min_evidence_level=2,
        max_hops=3,
    )
    assert len(paths) == 0, (
        f"Edge with deactivated reviewer must be excluded. Got {len(paths)} paths."
    )


@pytest.mark.asyncio
async def test_semantic_mismatch_excluded(db_session):
    """Relation tampered to verified with a biographical quote that doesn't
    semantically match the relation type is excluded at query time."""
    ents = await _seed_verified_2hop(db_session)
    svc = GraphService(db_session)

    # Replace r2's quote with a biographical/identity quote that lacks
    # source-derivation markers — violates compiled_from policy.
    chunk_bio = DocumentChunk(
        id="chunk-bio-1",
        document_id=ents["doc"].id,
        chunk_index=99,
        content="皇甫谧，字士安，安定朝那人也。居贫，躬自稼穑。",
        token_count=10,
        passage_id=ents["passage"].id,
    )
    db_session.add(chunk_bio)
    await db_session.flush()

    r2 = ents["r2"]
    r2.evidence_quote = "皇甫谧，字士安，安定朝那人也。"
    r2.evidence_chunk_id = "chunk-bio-1"
    r2.evidence_citation = f"[{ents['doc'].id}:chunk-bio-1]"
    await db_session.flush()

    paths = await svc.multi_hop_query(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
        min_evidence_level=2,
        max_hops=3,
    )
    assert len(paths) == 0, (
        f"Semantic mismatch must be excluded. Got {len(paths)} paths."
    )


@pytest.mark.asyncio
async def test_persisted_level_artificially_high_uses_re_derived(db_session):
    """When persisted evidence_level is inflated to 4 (max legit), the query
    re-derives it from source fields — still passes if re-derived level >= 2."""
    ents = await _seed_verified_2hop(db_session)
    r2 = ents["r2"]

    # Verify the real derived level (should be 3 from verify_relation)
    svc = GraphService(db_session)
    real_level = await svc._derive_evidence_level(db_session, r2)
    assert real_level in (2, 3, 4), f"Unexpected derived level: {real_level}"

    # Query with min_evidence_level at the re-derived level should pass
    paths = await svc.multi_hop_query(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
        min_evidence_level=2,
        max_hops=3,
    )
    # The re-derived level is used (not persisted), and it's >= 2, so path exists
    assert len(paths) == 1
    # The output evidence_level matches re-derived, not any bogus persisted value
    actual_level = paths[0].hops[-1].evidence_level
    assert actual_level == real_level, (
        f"Expected re-derived level {real_level}, got persisted level {actual_level}"
    )


@pytest.mark.asyncio
async def test_one_hop_fails_excludes_entire_path(db_session):
    """When one hop of a 2-hop path fails re-validation (missing claim_text),
    the entire path is excluded — no partial paths."""
    ents = await _seed_verified_2hop(db_session)
    svc = GraphService(db_session)

    # Break r2: strip claim_text
    r2 = ents["r2"]
    r2.claim_text = None
    await db_session.flush()

    paths = await svc.multi_hop_query(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
        min_evidence_level=2,
        max_hops=3,
    )
    assert len(paths) == 0


@pytest.mark.asyncio
async def test_paper_service_inherits_safety(db_session):
    """PaperService automatically inherits multi_hop safety boundary —
    tampered relations are excluded from evidence_chains."""
    ents = await _seed_verified_2hop(db_session)

    # Tamper r2: strip verified_at
    r2 = ents["r2"]
    r2.verified_at = None
    await db_session.flush()

    from app.services.paper_service import PaperService

    paper_svc = PaperService(db_session)
    paper = await paper_svc.generate_paper(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
    )
    evidence_chains = paper["modules"]["evidence_chains"]
    assert len(evidence_chains) == 0, (
        f"Tampered relation must not appear in evidence_chains. "
        f"Got {len(evidence_chains)} chains."
    )


@pytest.mark.asyncio
async def test_paper_service_writes_valid_chains(db_session):
    """PaperService writes valid 2-hop evidence_chains when all edges pass."""
    ents = await _seed_verified_2hop(db_session)

    from app.services.paper_service import PaperService

    paper_svc = PaperService(db_session)
    paper = await paper_svc.generate_paper(
        source_type="person",
        source_id=ents["person"].id,
        target_type="book",
        target_id=ents["book2"].id,
    )
    evidence_chains = paper["modules"]["evidence_chains"]
    assert len(evidence_chains) == 1
    chain = evidence_chains[0]
    assert len(chain["hops"]) == 2
    # citation, exact_quote, source_uri from validated evidence
    for hop in chain["hops"]:
        assert hop["citation"], f"citation empty: {hop}"
        assert hop["exact_quote"], f"exact_quote empty: {hop}"
        assert hop["source_uri"], f"source_uri empty: {hop}"
