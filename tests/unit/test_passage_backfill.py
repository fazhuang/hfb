"""Passage backfill tests — idempotent, exact-match, dry-run safe.

Sprint 4 P0: backfill only maps exact normalized text matches.
Never fabricates passage_id. Never fuzzy-matches. Never maps ambiguous.
"""
from __future__ import annotations

import pytest

from tests.conftest_db import db_session_persistent  # noqa: F401

# =============================================================================
# Importability
# =============================================================================

def test_backfill_script_importable():
    """P0: Script must import without ModuleNotFoundError."""
    from scripts.backfill_passage import _normalize, _run_backfill, backfill
    assert backfill is not None
    assert _normalize is not None
    assert _run_backfill is not None


# =============================================================================
# Normalize
# =============================================================================

def test_normalize_whitespace():
    from scripts.backfill_passage import _normalize
    assert _normalize("  a   b  ") == "a b"
    assert _normalize("a\n\nb") == "a b"
    assert _normalize("针灸  经络") == "针灸 经络"


# =============================================================================
# Exact match success
# =============================================================================

@pytest.mark.asyncio
async def test_backfill_exact_match_unique(db_session_persistent):
    """P0: chunk with exact normalized match → mapped."""
    from app.models.book import Book
    from app.models.chapter import Chapter
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.passage import Passage
    from app.models.version import Version
    from scripts.backfill_passage import backfill

    book = Book(id="book-bf1", title="Test Book", source_url="http://x.com")
    db_session_persistent.add(book)
    ver = Version(id="ver-bf1", book_id=book.id, version_name="v1", era="汉")
    db_session_persistent.add(ver)
    ch = Chapter(id="ch-bf1", title="Ch", book_id=book.id)
    db_session_persistent.add(ch)
    passage = Passage(id="passage-bf1", chapter_id=ch.id, version_id=ver.id,
                      content_text="经络是运行气血的通道。", order=1)
    db_session_persistent.add(passage)

    doc = Document(id="doc-bf1", title="T", dynasty="汉")
    db_session_persistent.add(doc)
    c1 = DocumentChunk(id="chk-bf1-0", document_id=doc.id, chunk_index=0,
                       content="  经络是运行气血的通道。  ", token_count=15)
    c2 = DocumentChunk(id="chk-bf1-1", document_id=doc.id, chunk_index=1,
                       content="无关内容", token_count=5)
    db_session_persistent.add_all([c1, c2])
    await db_session_persistent.flush()

    stats = await backfill(db=db_session_persistent, dry_run=False)
    assert stats["newly_mapped"] == 1
    assert stats["unresolved"] == 1


# =============================================================================
# No match → unresolved
# =============================================================================

@pytest.mark.asyncio
async def test_backfill_no_match_unresolved(db_session_persistent):
    """P0: chunk with zero candidate passages → unresolved."""
    from app.models.book import Book
    from app.models.chapter import Chapter
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.passage import Passage
    from app.models.version import Version
    from scripts.backfill_passage import backfill

    book = Book(id="book-bf2", title="TB2", source_url="http://x.com")
    db_session_persistent.add(book)
    ver = Version(id="ver-bf2", book_id=book.id, version_name="v2", era="唐")
    db_session_persistent.add(ver)
    ch = Chapter(id="ch-bf2", title="Ch2", book_id=book.id)
    db_session_persistent.add(ch)
    passage = Passage(id="passage-bf2", chapter_id=ch.id, version_id=ver.id,
                      content_text="完全不同的内容。", order=1)
    db_session_persistent.add(passage)

    doc = Document(id="doc-bf2", title="T2", dynasty="唐")
    db_session_persistent.add(doc)
    c1 = DocumentChunk(id="chk-bf2-0", document_id=doc.id, chunk_index=0,
                       content="这是一段不在任何passage中的文本。", token_count=15)
    db_session_persistent.add(c1)
    await db_session_persistent.flush()

    stats = await backfill(db=db_session_persistent, dry_run=False)
    assert stats["newly_mapped"] == 0
    assert stats["unresolved"] == 1


# =============================================================================
# Multiple candidates → ambiguous
# =============================================================================

@pytest.mark.asyncio
async def test_backfill_multiple_candidates_ambiguous(db_session_persistent):
    """P0: chunk matches multiple passages → ambiguous, NOT mapped."""
    from app.models.book import Book
    from app.models.chapter import Chapter
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.passage import Passage
    from app.models.version import Version
    from scripts.backfill_passage import backfill

    book = Book(id="book-bf3", title="TB3", source_url="http://x.com")
    db_session_persistent.add(book)
    ver = Version(id="ver-bf3", book_id=book.id, version_name="v3", era="宋")
    db_session_persistent.add(ver)
    ch1 = Chapter(id="ch-bf3-1", title="ChA", book_id=book.id)
    db_session_persistent.add(ch1)
    ch2 = Chapter(id="ch-bf3-2", title="ChB", book_id=book.id)
    db_session_persistent.add(ch2)
    # Two passages with the same text
    p1 = Passage(id="passage-bf3-a", chapter_id=ch1.id, version_id=ver.id,
                 content_text="重复内容。", order=1)
    p2 = Passage(id="passage-bf3-b", chapter_id=ch2.id, version_id=ver.id,
                 content_text="重复内容。", order=2)
    db_session_persistent.add_all([p1, p2])

    doc = Document(id="doc-bf3", title="T3", dynasty="宋")
    db_session_persistent.add(doc)
    c1 = DocumentChunk(id="chk-bf3-0", document_id=doc.id, chunk_index=0,
                       content="重复内容。", token_count=5)
    db_session_persistent.add(c1)
    await db_session_persistent.flush()

    stats = await backfill(db=db_session_persistent, dry_run=False)
    assert stats["newly_mapped"] == 0
    assert stats["ambiguous"] == 1
    # Chunk must still have no passage_id
    await db_session_persistent.refresh(c1)
    assert not c1.passage_id


# =============================================================================
# Dry-run does not write
# =============================================================================

@pytest.mark.asyncio
async def test_backfill_dry_run_no_write(db_session_persistent):
    """P0: dry-run must not modify database."""
    from app.models.book import Book
    from app.models.chapter import Chapter
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.passage import Passage
    from app.models.version import Version
    from scripts.backfill_passage import backfill

    book = Book(id="book-bf4", title="TB4", source_url="http://x.com")
    db_session_persistent.add(book)
    ver = Version(id="ver-bf4", book_id=book.id, version_name="v4", era="明")
    db_session_persistent.add(ver)
    ch = Chapter(id="ch-bf4", title="Ch4", book_id=book.id)
    db_session_persistent.add(ch)
    passage = Passage(id="passage-bf4", chapter_id=ch.id, version_id=ver.id,
                      content_text="dry-run测试。", order=1)
    db_session_persistent.add(passage)

    doc = Document(id="doc-bf4", title="T4", dynasty="明")
    db_session_persistent.add(doc)
    c1 = DocumentChunk(id="chk-bf4-0", document_id=doc.id, chunk_index=0,
                       content="dry-run测试。", token_count=10)
    db_session_persistent.add(c1)
    await db_session_persistent.flush()

    stats = await backfill(db=db_session_persistent, dry_run=True)
    assert stats["dry_run"] is True
    assert stats["newly_mapped"] == 1  # counted, not written
    await db_session_persistent.refresh(c1)
    assert not c1.passage_id


# =============================================================================
# Second run → newly_mapped=0
# =============================================================================

@pytest.mark.asyncio
async def test_backfill_second_run_no_new(db_session_persistent):
    """P0: second execution maps zero new chunks."""
    from app.models.book import Book
    from app.models.chapter import Chapter
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.passage import Passage
    from app.models.version import Version
    from scripts.backfill_passage import backfill

    book = Book(id="book-bf5", title="TB5", source_url="http://x.com")
    db_session_persistent.add(book)
    ver = Version(id="ver-bf5", book_id=book.id, version_name="v5", era="清")
    db_session_persistent.add(ver)
    ch = Chapter(id="ch-bf5", title="Ch5", book_id=book.id)
    db_session_persistent.add(ch)
    passage = Passage(id="passage-bf5", chapter_id=ch.id, version_id=ver.id,
                      content_text="第二次运行测试。", order=1)
    db_session_persistent.add(passage)

    doc = Document(id="doc-bf5", title="T5", dynasty="清")
    db_session_persistent.add(doc)
    c1 = DocumentChunk(id="chk-bf5-0", document_id=doc.id, chunk_index=0,
                       content="第二次运行测试。", token_count=10)
    db_session_persistent.add(c1)
    await db_session_persistent.flush()

    stats1 = await backfill(db=db_session_persistent, dry_run=False)
    assert stats1["newly_mapped"] == 1

    stats2 = await backfill(db=db_session_persistent, dry_run=False)
    assert stats2["newly_mapped"] == 0
    assert stats2["mapped_before"] == 1


# =============================================================================
# Orphan detection
# =============================================================================

@pytest.mark.asyncio
async def test_backfill_orphan_detection(db_session_persistent):
    """P0: orphan_passage_ids correctly identifies passage_ids pointing to deleted passages."""
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from scripts.backfill_passage import backfill

    doc = Document(id="doc-bf6", title="T6", dynasty="晋")
    db_session_persistent.add(doc)
    c1 = DocumentChunk(id="chk-bf6-0", document_id=doc.id, chunk_index=0,
                       content="孤儿passage测试。", token_count=10,
                       passage_id="passage-nonexistent")
    db_session_persistent.add(c1)
    await db_session_persistent.flush()

    stats = await backfill(db=db_session_persistent, dry_run=False)
    assert stats["orphan_passage_ids"] >= 1


# =============================================================================
# Already-mapped chunks skipped
# =============================================================================

@pytest.mark.asyncio
async def test_backfill_already_mapped_skipped(db_session_persistent):
    """P0: chunk with existing passage_id is skipped."""
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from scripts.backfill_passage import backfill

    doc = Document(id="doc-bf7", title="T7", dynasty="汉")
    db_session_persistent.add(doc)
    c1 = DocumentChunk(id="chk-bf7-0", document_id=doc.id, chunk_index=0,
                       content="已有映射。", token_count=5,
                       passage_id="existing-passage")
    db_session_persistent.add(c1)
    await db_session_persistent.flush()

    stats = await backfill(db=db_session_persistent, dry_run=False)
    assert stats["already_mapped"] == 1
    assert stats["newly_mapped"] == 0
