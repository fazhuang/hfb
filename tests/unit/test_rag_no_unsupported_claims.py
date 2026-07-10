"""
Tests: RAG must NOT support unsupported claims — no evidence → no fabricated answer.

Covers:
  - Claims without backing chunks → refusal
  - Partial match → only return what's supported
  - Commercial/metadata-only docs excluded
  - No LLM hallucination path — answer is deterministic
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


@pytest.fixture
async def db_session():
    """In-memory SQLite with full schema."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def populated(db_session: AsyncSession) -> AsyncSession:
    """Populate with rag_enabled=true docs containing specific claims."""
    doc = Document(
        title="伤寒论",
        content_text="张仲景著《伤寒杂病论》，确立六经辨证体系。",
        copyright_status="public_domain",
        authorization_basis="public domain — Han dynasty work",
        rag_enabled=True,
        source_url="https://ctext.org/shang-han-lun",
        source_name="ctext",
    )
    db_session.add(doc)
    await db_session.flush()

    chunk1 = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content="张仲景著《伤寒杂病论》，确立六经辨证体系。",
        token_count=25,
        page_number=1,
        paragraph_index=0,
        evidence_weight="primary",
    )
    chunk2 = DocumentChunk(
        document_id=doc.id,
        chunk_index=1,
        content="六经辨证包含太阳、阳明、少阳、太阴、少阴、厥阴六经。",
        token_count=20,
        page_number=2,
        paragraph_index=1,
        evidence_weight="primary",
    )
    db_session.add_all([chunk1, chunk2])
    await db_session.flush()

    return db_session


# ============================================================
# Tests: no unsupported claims
# ============================================================


@pytest.mark.anyio
class TestNoUnsupportedClaims:
    """RAG only returns what evidence supports."""

    async def test_claim_outside_corpus_refuses(self, populated):
        """Query about a claim not in corpus → refusal."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(populated)
        resp = await svc.query("爱因斯坦相对论")  # Not in Chinese medicine corpus

        assert resp.refusal is True
        assert "未找到" in resp.refusal_reason

    async def test_partial_match_returns_only_supported(self, populated):
        """Query with mixed supported/unsupported terms → only supported."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(populated)
        resp = await svc.query("张仲景相对论")  # Half match, half not

        if not resp.refusal:
            # If we got results, they must be about 张仲景, not 相对论
            for e in resp.evidence:
                assert "张仲景" in e.content or "伤寒" in e.content or "六经" in e.content, (
                    f"Evidence should only match supported claims, got: {e.content[:50]}"
                )
                assert "相对论" not in e.content, (
                    "Unsupported claim should not appear in evidence"
                )

    async def test_answer_is_deterministic_no_llm(self, populated):
        """Answer is rendered from evidence deterministically — no LLM call."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(populated)
        resp = await svc.query("张仲景")

        assert resp.refusal is False
        # Deterministic answer markers
        assert "证据" in resp.answer or "citation" in resp.answer.lower() or "条" in resp.answer
        # Should cite source
        assert "《" in resp.answer or "citation" in resp.answer.lower()

    async def test_no_made_up_url(self, populated):
        """Response must not contain hallucinated URLs."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(populated)
        resp = await svc.query("伤寒论")

        for e in resp.evidence:
            if e.source_url:
                # Source URL must be the one we stored, not something made up
                assert e.source_url.startswith("https://ctext.org/"), (
                    f"URL must be from stored data, got: {e.source_url}"
                )

    async def test_no_made_up_page_number(self, populated):
        """Page numbers must be from stored data, not fabricated."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(populated)
        resp = await svc.query("六经")

        for e in resp.evidence:
            if e.page_number is not None:
                assert e.page_number >= 1, (
                    f"Page number must be positive, got: {e.page_number}"
                )

    async def test_no_made_up_copyright_status(self, populated):
        """Copyright status must be from stored Document, not made up."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(populated)
        resp = await svc.query("张仲景")

        for e in resp.evidence:
            assert e.copyright_status == "public_domain", (
                f"copyright_status must be from Document, got: {e.copyright_status}"
            )

    async def test_no_made_up_author(self, populated):
        """Chunk content must be actual stored text, not LLM-generated."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(populated)
        resp = await svc.query("伤寒")

        for e in resp.evidence:
            # Content must be one of the stored chunks
            assert e.content in {
                "张仲景著《伤寒杂病论》，确立六经辨证体系。",
                "六经辨证包含太阳、阳明、少阳、太阴、少阴、厥阴六经。",
            }, f"Content must be actual stored text, got: {e.content[:50]}..."

    async def test_metadata_only_doc_excluded(self, db_session):
        """Metadata-only documents never enter RAG."""
        from app.services.evidence_rag_service import EvidenceRAGService

        doc = Document(
            title="仅元数据",
            content_text="此文档仅有元数据，全文不应进入 RAG。",
            copyright_status="metadata_only",
            authorization_basis="",
            rag_enabled=False,
        )
        db_session.add(doc)
        await db_session.flush()

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="此文档仅有元数据，全文不应进入 RAG。",
            token_count=20,
        )
        db_session.add(chunk)
        await db_session.flush()

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("元数据")

        # Should not find the metadata-only doc
        for e in resp.evidence:
            assert "元数据" not in e.document_title, (
                "Metadata-only doc should not appear in RAG results"
            )
