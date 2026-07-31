"""T2: Citation → Evidence → SourceRef FK chain tests.

Contract:
  active citation
  JOIN evidences ON citations.evidence_id = evidences.id
  JOIN source_refs ON evidences.source_ref_id = source_refs.id
  must yield a non-null, non-deleted, URL-compliant SourceRef.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from tests.conftest_db import db_session_persistent  # noqa: F401

# ==========================================================================
# Seed helpers
# ==========================================================================


async def _seed_source_ref(
    db,
    sr_id: str,
    url: str = "http://example.com/book/1",
    title: str = "测试文献",
    page_location: str = "",
) -> str:
    """Create a SourceRef and return its id."""
    await db.execute(
        text(
            "INSERT INTO source_refs (id, title, url, page_location, is_deleted) "
            "VALUES (:id, :title, :url, :loc, false)"
        ),
        {"id": sr_id, "title": title, "url": url, "loc": page_location},
    )
    await db.flush()
    return sr_id


async def _seed_document(db, doc_id: str, title: str = "测试书籍") -> str:
    """Create a Document and return its id."""
    await db.execute(
        text(
            "INSERT INTO documents (id, title, dynasty, copyright_status, authorization_basis, "
            "rag_enabled, is_deleted) "
            "VALUES (:id, :title, '汉', 'public_domain', 'test', true, false)"
        ),
        {"id": doc_id, "title": title},
    )
    await db.flush()
    return doc_id


async def _seed_version(
    db,
    ver_id: str,
    book_id: str | None = None,
    is_formal: bool = True,
    withdrawn: bool = False,
) -> str:
    """Create a Version and return its id. Requires a Book first."""
    if book_id is None:
        book_id = f"book-{ver_id}"
        await db.execute(
            text(
                "INSERT INTO books (id, title, source_url, is_deleted) "
                "VALUES (:id, :title, :url, false)"
            ),
            {"id": book_id, "title": "针灸甲乙经", "url": "http://example.com/book"},
        )
    await db.execute(
        text(
            "INSERT INTO versions (id, book_id, version_name, is_formal_source, "
            "repository, shelf_mark, source_url, withdrawn_at, is_deleted) "
            "VALUES (:id, :book_id, :name, :formal, :repo, :mark, :url, :withdrawn, false)"
        ),
        {
            "id": ver_id,
            "book_id": book_id,
            "name": "宋本",
            "formal": is_formal,
            "repo": "国家图书馆" if is_formal else None,
            "mark": "S.1234" if is_formal else None,
            "url": "http://example.com/ver/1" if is_formal else None,
            "withdrawn": "2026-01-01T00:00:00Z" if withdrawn else None,
        },
    )
    await db.flush()
    return ver_id


async def _seed_passage(
    db, passage_id: str, version_id: str, content: str = "经络是运行气血的通道。"
) -> str:
    """Create a Passage and return its id."""
    # Create chapter if needed
    chapter_id = f"ch-{passage_id}"
    await db.execute(
        text(
            "INSERT INTO chapters (id, title, book_id, is_deleted) "
            "VALUES (:id, :title, :book_id, false) "
            "ON CONFLICT DO NOTHING"
        ),
        {"id": chapter_id, "title": "经络", "book_id": f"book-{version_id}"},
    )
    await db.execute(
        text(
            'INSERT INTO passages (id, chapter_id, version_id, content_text, "order", is_deleted) '
            "VALUES (:id, :chapter_id, :version_id, :content, 1, false) "
            "ON CONFLICT DO NOTHING"
        ),
        {
            "id": passage_id,
            "chapter_id": chapter_id,
            "version_id": version_id,
            "content": content,
        },
    )
    await db.flush()
    return passage_id


async def _seed_document_chunk(
    db,
    chunk_id: str,
    doc_id: str,
    passage_id: str = "",
    content: str = "经脉流行不止，环周不休。",
) -> str:
    """Create a DocumentChunk and return its id."""
    await db.execute(
        text(
            "INSERT INTO document_chunks (id, document_id, chunk_index, content, token_count, "
            "passage_id, is_deleted) "
            "VALUES (:id, :doc_id, 0, :content, :tokens, :passage_id, false)"
        ),
        {
            "id": chunk_id,
            "doc_id": doc_id,
            "content": content,
            "tokens": len(content),
            "passage_id": passage_id or None,
        },
    )
    await db.flush()
    return chunk_id


# ==========================================================================
# T2-1: Successful persistence — 3-table FK JOIN
# ==========================================================================


@pytest.mark.asyncio
async def test_persist_citation_three_table_fk_join(db_session_persistent):
    """T2: After persist, citations.evidence_id → evidences.source_ref_id → source_refs.id JOIN succeeds."""
    from app.services.citation_persistence import CitationPersistenceService

    await _seed_source_ref(
        db_session_persistent, "sr-join-1", url="http://example.com/src"
    )
    doc_id = await _seed_document(db_session_persistent, "doc-join-1")
    ver_id = await _seed_version(db_session_persistent, "ver-join-1", is_formal=True)
    pid = await _seed_passage(db_session_persistent, "passage-join-1", ver_id)
    chk_id = await _seed_document_chunk(
        db_session_persistent, "chk-join-1", doc_id, pid
    )

    svc = CitationPersistenceService(db_session_persistent, creator_id="test-user-id")

    # Create a mock citation that will resolve the seeded SourceRef by URL
    class FakeCitation:
        document_id = doc_id
        chunk_id = chk_id
        exact_quote = "经脉流行不止"
        version_id = ver_id
        passage_id = pid
        source_uri = "http://example.com/src"
        evidence_id = ""

    count = await svc.persist_academic_rag_citations([FakeCitation()], query="经络")
    assert count == 1, f"Expected 1 new citation, got {count}"

    # Verify: Citation → Evidence → SourceRef JOIN
    join_result = await db_session_persistent.execute(
        text("""
        SELECT c.id as citation_id,
               e.id as evidence_id,
               sr.id as source_ref_id,
               sr.url as source_url,
               sr.is_deleted as sr_deleted
        FROM citations c
        JOIN evidences e ON c.evidence_id = e.id AND e.is_deleted = false
        JOIN source_refs sr ON e.source_ref_id = sr.id AND sr.is_deleted = false
        WHERE c.is_deleted = false
          AND c.target_type = 'document'
          AND c.target_id = :doc_id
    """),
        {"doc_id": doc_id},
    )
    rows = join_result.mappings().all()
    assert len(rows) > 0, "JOIN must return at least one row"
    for row in rows:
        assert row["source_url"] is not None, "SourceRef URL must not be null"
        assert row["source_url"] != "", "SourceRef URL must not be empty"
        assert not row["sr_deleted"], "SourceRef must not be deleted"


# ==========================================================================
# T2-2: Missing SourceRef → entire transaction rolls back, no half-written data
# ==========================================================================


@pytest.mark.asyncio
async def test_missing_source_ref_rolls_back_transaction(db_session_persistent):
    """T2: When SourceRef cannot be resolved and auto-create is disabled,
    the entire citation/evidence must not be left as half-written rows."""
    from app.services.citation_persistence import CitationPersistenceService

    doc_id = await _seed_document(db_session_persistent, "doc-nosr-1")

    # Count existing rows before attempt
    before_ev = await db_session_persistent.execute(
        text("SELECT COUNT(*) FROM evidences WHERE is_deleted=false")
    )
    before_cit = await db_session_persistent.execute(
        text("SELECT COUNT(*) FROM citations WHERE is_deleted=false")
    )
    ev_count_before = before_ev.scalar()
    cit_count_before = before_cit.scalar()

    svc = CitationPersistenceService(db_session_persistent, creator_id="test-user-id")

    class FakeCitation:
        document_id = doc_id
        chunk_id = "chk-nosr-1"
        exact_quote = "测试"
        version_id = ""
        passage_id = ""
        source_uri = ""  # No source_uri → cannot resolve SourceRef
        evidence_id = ""

    # This should raise because source_uri + doc_id can't resolve a SourceRef
    # and auto-create is now fail-closed
    with pytest.raises(Exception):
        await svc.persist_academic_rag_citations([FakeCitation()], query="test")

    # Verify: no new evidence or citation rows were created
    after_ev = await db_session_persistent.execute(
        text("SELECT COUNT(*) FROM evidences WHERE is_deleted=false")
    )
    after_cit = await db_session_persistent.execute(
        text("SELECT COUNT(*) FROM citations WHERE is_deleted=false")
    )
    assert after_ev.scalar() == ev_count_before, (
        f"No new evidence rows expected; got {after_ev.scalar()} instead of {ev_count_before}"
    )
    assert after_cit.scalar() == cit_count_before, (
        f"No new citation rows expected; got {after_cit.scalar()} instead of {cit_count_before}"
    )


# ==========================================================================
# T2-3: Withdrawn Version → no usable Citation
# ==========================================================================


@pytest.mark.asyncio
async def test_withdrawn_version_blocks_citation(db_session_persistent):
    """T2: A Version that is withdrawn cannot produce a usable Citation
    through the FK chain. The Citation must either not exist or its JOIN
    to SourceRef must fail."""
    from app.services.citation_persistence import CitationPersistenceService

    await _seed_source_ref(
        db_session_persistent, "sr-wd-1", url="http://example.com/wd"
    )
    doc_id = await _seed_document(db_session_persistent, "doc-wd-1")
    ver_id = await _seed_version(
        db_session_persistent, "ver-wd-1", is_formal=True, withdrawn=True
    )
    pid = await _seed_passage(db_session_persistent, "passage-wd-1", ver_id)
    chk_id = await _seed_document_chunk(db_session_persistent, "chk-wd-1", doc_id, pid)

    svc = CitationPersistenceService(db_session_persistent, creator_id="test-user-id")

    class FakeCitation:
        document_id = doc_id
        chunk_id = chk_id
        exact_quote = "经脉"
        version_id = ver_id
        passage_id = pid
        source_uri = "http://example.com/wd"
        evidence_id = ""

    # The CitationPersistenceService may or may not create the citation
    # depending on implementation. What matters: the 3-table JOIN with
    # withdrawn check must not return rows for withdrawn versions.
    try:
        await svc.persist_academic_rag_citations([FakeCitation()], query="经络")
    except Exception:
        pass

    # Now verify: any citation referencing a withdrawn version's passage
    # must fail the full FK-chain JOIN (or not exist)
    join_result = await db_session_persistent.execute(
        text("""
        SELECT c.id as citation_id,
               e.id as evidence_id,
               sr.id as source_ref_id
        FROM citations c
        JOIN evidences e ON c.evidence_id = e.id AND e.is_deleted = false
        JOIN source_refs sr ON e.source_ref_id = sr.id AND sr.is_deleted = false
        JOIN passages p ON e.source_passage_id = p.id AND p.is_deleted = false
        JOIN versions v ON p.version_id = v.id AND v.is_deleted = false
        WHERE c.is_deleted = false
          AND c.target_id = :doc_id
          AND v.withdrawn_at IS NOT NULL
    """),
        {"doc_id": doc_id},
    )
    withdrawn_citations = join_result.mappings().all()
    assert len(withdrawn_citations) == 0, (
        f"No citation should resolve via a withdrawn Version; found {len(withdrawn_citations)}"
    )


# ==========================================================================
# T2-4: Backfill — fix existing Evidence rows with NULL source_ref_id
# ==========================================================================


@pytest.mark.asyncio
async def test_backfill_missing_source_refs(db_session_persistent):
    """T2: backfill_missing_source_refs should assign SourceRef to orphan Evidence rows."""
    from app.services.citation_persistence import CitationPersistenceService

    await _seed_source_ref(
        db_session_persistent, "sr-bf-1", url="http://example.com/bf"
    )
    doc_id = await _seed_document(db_session_persistent, "doc-bf-1")

    # Insert an Evidence row with NULL source_ref_id (simulating old bad data)
    await db_session_persistent.execute(
        text(
            "INSERT INTO evidences (id, description, evidence_level, source_ref_id, "
            "source_passage_id, creator_id, is_deleted) "
            "VALUES ('ev-orphan-1', 'RAG citation: test', 'LEVEL_3', NULL, NULL, 'test-user-id', false)"
        )
    )
    # Insert a Citation pointing to that orphan Evidence
    await db_session_persistent.execute(
        text(
            "INSERT INTO citations (id, target_type, target_id, evidence_id, "
            "quote_text, note, is_deleted) "
            "VALUES ('cit-orphan-1', 'document', :doc_id, 'ev-orphan-1', 'test quote', '{}', false)"
        ),
        {"doc_id": doc_id},
    )
    await db_session_persistent.flush()

    svc = CitationPersistenceService(db_session_persistent, creator_id="test-user-id")
    fixed = await svc.backfill_missing_source_refs()
    assert fixed >= 1, f"Expected at least 1 backfilled Evidence row, got {fixed}"

    # Verify the Evidence now has a source_ref_id
    result = await db_session_persistent.execute(
        text(
            "SELECT source_ref_id FROM evidences WHERE id='ev-orphan-1' AND is_deleted=false"
        )
    )
    row = result.fetchone()
    assert row is not None, "Orphan evidence should still exist"
    assert row[0] is not None, "source_ref_id must be non-null after backfill"
    assert row[0] != "", "source_ref_id must be non-empty after backfill"

    # Verify the full JOIN now works
    join_result = await db_session_persistent.execute(
        text("""
        SELECT c.id, e.id, sr.id
        FROM citations c
        JOIN evidences e ON c.evidence_id = e.id AND e.is_deleted = false
        JOIN source_refs sr ON e.source_ref_id = sr.id AND sr.is_deleted = false
        WHERE c.id = 'cit-orphan-1' AND c.is_deleted = false
    """)
    )
    assert join_result.fetchone() is not None, (
        "3-table JOIN must succeed after backfill"
    )
