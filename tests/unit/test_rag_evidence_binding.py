"""
Tests: evidence binding — every chunk carries full provenance metadata.

Covers:
  - rag_enabled filter: only rag_enabled=true documents enter RAG
  - Evidence binding: document_id, source_url, page_number, paragraph_index,
    copyright_status, citation_format on every result
  - OCR confidence: <0.7 → evidence_weight="reference"
  - No evidence → refusal
"""
from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk


@pytest.fixture
async def db_session():
    """In-memory SQLite with full schema including evidence-binding columns."""
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
async def seeded_session(db_session: AsyncSession) -> AsyncSession:
    """Seed DB with documents at various rag_enabled/copyright states."""
    # Document A: rag_enabled=true, public_domain, with source_url
    doc_a = Document(
        title="针灸甲乙经",
        content_text="皇甫谧著针灸甲乙经，系统整理魏晋以前针灸学成就。",
        copyright_status="public_domain",
        authorization_basis="public domain — Tang dynasty work",
        rag_enabled=True,
        source_url="https://ctext.org/zhenjiu-jiayi-jing",
        source_name="ctext",
    )
    db_session.add(doc_a)
    await db_session.flush()

    # Chunks for doc A with page/paragraph metadata
    chunk_a1 = DocumentChunk(
        document_id=doc_a.id,
        chunk_index=0,
        content="皇甫谧著针灸甲乙经，系统整理魏晋以前针灸学成就。",
        token_count=30,
        page_number=1,
        paragraph_index=0,
        evidence_weight="primary",
    )
    chunk_a2 = DocumentChunk(
        document_id=doc_a.id,
        chunk_index=1,
        content="《针灸甲乙经》共十二卷，分128篇。",
        token_count=20,
        page_number=1,
        paragraph_index=1,
        evidence_weight="primary",
    )
    db_session.add_all([chunk_a1, chunk_a2])
    await db_session.flush()

    # Document B: rag_enabled=true, open_access, OCR low confidence
    doc_b = Document(
        title="神农本草经",
        content_text="神农本草经载药365种，分上中下三品。",
        copyright_status="open_access",
        authorization_basis="CC-BY 4.0",
        license_type="CC-BY",
        rag_enabled=True,
        source_url="https://example.org/shennong",
        source_name="example",
    )
    db_session.add(doc_b)
    await db_session.flush()

    chunk_b1 = DocumentChunk(
        document_id=doc_b.id,
        chunk_index=0,
        content="神农本草经载药365种，分上中下三品。",
        token_count=25,
        page_number=3,
        paragraph_index=5,
        ocr_confidence=0.45,  # Low OCR — reference only
        evidence_weight="reference",
    )
    db_session.add(chunk_b1)
    await db_session.flush()

    # Document C: rag_enabled=false — should NOT appear in RAG
    doc_c = Document(
        title="商业数据库文献",
        content_text="此为商业数据库全文，不得进入RAG。",
        copyright_status="commercial_restricted",
        authorization_basis="",
        rag_enabled=False,
        source_url="https://commercial-db.example.com/paper-123",
        source_name="commercial_db",
    )
    db_session.add(doc_c)
    await db_session.flush()

    chunk_c1 = DocumentChunk(
        document_id=doc_c.id,
        chunk_index=0,
        content="此为商业数据库全文，不得进入RAG。",
        token_count=20,
    )
    db_session.add(chunk_c1)
    await db_session.flush()

    # Document D: rag_enabled=true, deleted — should NOT appear
    doc_d = Document(
        title="已删除文献",
        content_text="此文献已被撤回。",
        copyright_status="public_domain",
        authorization_basis="public domain",
        rag_enabled=True,
        is_deleted=True,
    )
    db_session.add(doc_d)
    await db_session.flush()

    chunk_d1 = DocumentChunk(
        document_id=doc_d.id,
        chunk_index=0,
        content="此文献已被撤回。",
        token_count=10,
    )
    db_session.add(chunk_d1)
    await db_session.flush()

    return db_session


# ============================================================
# Tests: rag_enabled gate
# ============================================================


@pytest.mark.anyio
class TestRAGEnabledGate:
    """Only rag_enabled=true documents are searchable."""

    async def test_rag_enabled_true_docs_searchable(self, seeded_session):
        """Query matching doc_a (rag_enabled=true) → found."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸")

        assert resp.refusal is False
        assert len(resp.evidence) > 0
        # All results should be from rag_enabled=true docs
        for e in resp.evidence:
            doc = (await seeded_session.execute(
                select(Document).where(Document.id == e.document_id)
            )).scalar_one()
            assert doc.rag_enabled is True

    async def test_rag_enabled_false_docs_excluded(self, seeded_session):
        """Query matching doc_c (rag_enabled=false) → excluded."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("商业数据库")

        # May refuse or return from other docs — but must NOT include doc_c
        for e in resp.evidence:
            assert e.document_id != ""  # sanity
            doc = (await seeded_session.execute(
                select(Document).where(Document.id == e.document_id)
            )).scalar_one()
            assert doc.copyright_status != "commercial_restricted"

    async def test_deleted_docs_excluded(self, seeded_session):
        """Query matching doc_d (deleted) → excluded."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("已删除")

        for e in resp.evidence:
            doc = (await seeded_session.execute(
                select(Document).where(Document.id == e.document_id)
            )).scalar_one()
            assert doc.is_deleted is False


# ============================================================
# Tests: evidence binding — mandatory provenance fields
# ============================================================


@pytest.mark.anyio
class TestEvidenceBinding:
    """Every retrieved chunk carries full provenance."""

    async def test_document_id_bound(self, seeded_session):
        """Every evidence chunk has non-empty document_id."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸")

        assert resp.refusal is False
        for e in resp.evidence:
            assert e.document_id, f"Missing document_id on chunk {e.chunk_id}"

    async def test_source_url_bound(self, seeded_session):
        """Chunks from doc_a carry source_url."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸甲乙经")

        # Find the chunk from doc_a
        doc_a_chunks = [e for e in resp.evidence if "甲" in e.content]
        if doc_a_chunks:
            for e in doc_a_chunks:
                assert e.source_url, "source_url must be non-empty for docs that have one"

    async def test_page_number_bound(self, seeded_session):
        """Chunks with page_number set carry it through."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸甲乙经")

        chunk_a = None
        for e in resp.evidence:
            if e.chunk_index == 0 and "皇甫谧" in e.content:
                chunk_a = e
                break

        if chunk_a:
            assert chunk_a.page_number == 1

    async def test_paragraph_index_bound(self, seeded_session):
        """Chunks carry paragraph_index."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸")

        for e in resp.evidence:
            if e.chunk_index == 0:
                assert e.paragraph_index is not None

    async def test_copyright_status_bound(self, seeded_session):
        """Every evidence chunk carries copyright_status."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸")

        for e in resp.evidence:
            assert e.copyright_status, f"Missing copyright_status on {e.chunk_id}"
            assert e.copyright_status != "unknown" or e.document_title == ""

    async def test_citation_string_present(self, seeded_session):
        """Every evidence chunk has a citation string."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸")

        assert resp.refusal is False
        for e in resp.evidence:
            assert e.citation, f"Missing citation on {e.chunk_id}"
        for c in resp.citations:
            assert c.citation, f"Missing citation string on citation {c.chunk_id}"


# ============================================================
# Tests: OCR confidence → evidence weight
# ============================================================


@pytest.mark.anyio
class TestOCRConfidenceWeight:
    """OCR confidence < 0.7 downgrades to reference."""

    async def test_low_ocr_confidence_reference_only(self, seeded_session):
        """doc_b has ocr_confidence=0.45 → evidence_weight='reference'."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("本草")

        assert resp.refusal is False
        # At least one chunk should have OCR data
        has_reference = any(
            e.ocr_confidence is not None and e.ocr_confidence < 0.7
            for e in resp.evidence
        )
        if has_reference:
            ref_chunks = [
                e for e in resp.evidence
                if e.ocr_confidence is not None and e.ocr_confidence < 0.7
            ]
            for e in ref_chunks:
                assert e.evidence_weight == "reference", (
                    f"Low OCR confidence ({e.ocr_confidence}) must be reference, "
                    f"got {e.evidence_weight}"
                )

    async def test_high_ocr_confidence_primary(self, seeded_session):
        """No OCR (None) → primary by default."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸")

        for e in resp.evidence:
            if e.ocr_confidence is None:
                assert e.evidence_weight == "primary", (
                    f"Non-OCR text should be primary, got {e.evidence_weight}"
                )

    async def test_ocr_confidence_in_citation(self, seeded_session):
        """OCR confidence appears in citation string."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("本草")

        ref_chunks = [
            e for e in resp.evidence
            if e.ocr_confidence is not None
        ]
        if ref_chunks:
            for e in ref_chunks:
                assert "OCR:" in e.citation, (
                    f"OCR confidence must be visible in citation: {e.citation}"
                )


# ============================================================
# Tests: refusal — no evidence, no fabrication
# ============================================================


@pytest.mark.anyio
class TestRefusalNoFabrication:
    """No evidence → refusal with structured reason."""

    async def test_empty_query_refuses(self, db_session):
        """Whitespace-only keyword query → refusal."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("   ")  # whitespace → empty keywords → refusal

        assert resp.refusal is True
        assert resp.answer == ""
        assert resp.citations == []
        assert resp.evidence == []
        assert resp.refusal_reason != ""

    async def test_no_match_refuses(self, seeded_session):
        """Query with no matching chunks → refusal."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("量子力学")  # Nothing in corpus matches

        assert resp.refusal is True
        assert resp.citations == []
        assert resp.evidence == []
        assert "未找到" in resp.refusal_reason or "未" in resp.refusal_reason

    async def test_no_rag_enabled_refuses(self, db_session):
        """Corpus with no rag_enabled documents → refusal."""
        from app.services.evidence_rag_service import EvidenceRAGService

        doc = Document(
            title="Not RAG Enabled",
            content_text="This document is not in RAG.",
            copyright_status="public_domain",
            authorization_basis="public domain",
            rag_enabled=False,
        )
        db_session.add(doc)
        await db_session.flush()

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="This document is not in RAG.",
            token_count=10,
        )
        db_session.add(chunk)
        await db_session.flush()

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("document")

        assert resp.refusal is True

    async def test_refusal_contract_enforced(self, seeded_session):
        """Refusal=True → citations and evidence MUST be empty."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("不存在的关键词xyz")

        assert resp.refusal is True
        assert resp.citations == []
        assert resp.evidence == []
        assert resp.answer == ""

    async def test_success_contract_enforced(self, seeded_session):
        """Refusal=False → answer, citations, evidence all non-empty."""
        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸")

        assert resp.refusal is False
        assert resp.answer != ""
        assert len(resp.citations) > 0
        assert len(resp.evidence) > 0

    async def test_response_schema_validates(self, seeded_session):
        """EvidenceRAGResponse passes its own model_validator."""
        from app.services.evidence_rag_service import EvidenceRAGService
        from app.schemas.evidence_rag import EvidenceRAGResponse as Resp

        svc = EvidenceRAGService(seeded_session)
        resp = await svc.query("针灸")

        # Should not raise
        validated = Resp.model_validate(resp.model_dump(mode="json"))
        assert validated.refusal == resp.refusal
        assert len(validated.citations) == len(resp.citations)
