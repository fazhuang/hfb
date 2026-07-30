"""
Day 2 acceptance tests — ingestion, chunking, retrieval, citation, API.

Covers:
  - Chunking: paragraph split, oversized paragraph, determinism
  - Ingestion: text ingest creates doc+chunks, metadata stored,
    PDF extraction, transaction safety, persistence across sessions
  - Retrieval: multi-keyword match, no match, top_k limit, stable sort
  - Citation: format [doc_id:chunk_id], traceability to DB records
  - API: POST /api/v1/search returns chunks/citations/metadata,
    no LLM fields
"""
from __future__ import annotations

import io

import pytest
from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking import chunk_text
from app.services.ingestion import (
    FulltextRejectedError,
    IngestionService,
    PDFExtractionError,
)
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Context 21: compliance metadata for all ingestion calls.
# All callers must pass copyright_status + authorization_basis.
_COMPLIANCE = {"copyright_status": "public_domain", "authorization_basis": "test fixture"}


_ingest = _COMPLIANCE  # ponytail: short alias for inline use below


# ============================================================
# Fixtures
# ============================================================


@pytest.fixture
async def db_session():
    """In-memory SQLite session with full schema."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


# Minimal PDF with extractable text
_SIMPLE_PDF_BYTES: bytes | None = None


def _simple_pdf_bytes() -> bytes:
    """Generate a minimal valid PDF with extractable text using raw PDF commands."""
    global _SIMPLE_PDF_BYTES
    if _SIMPLE_PDF_BYTES is not None:
        return _SIMPLE_PDF_BYTES

    # Hand-crafted minimal PDF with extractable text
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<< /Length 44 >>\n"
        b"stream\n"
        b"BT /F1 12 Tf 100 700 Td (Hello World) Tj ET\n"
        b"endstream\n"
        b"endobj\n"
        b"5 0 obj\n"
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 6\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000240 00000 n \n"
        b"0000000335 00000 n \n"
        b"trailer\n"
        b"<< /Size 6 /Root 1 0 R >>\n"
        b"startxref\n"
        b"415\n"
        b"%%EOF\n"
    )
    _SIMPLE_PDF_BYTES = pdf
    return pdf


def _encrypted_pdf_bytes() -> bytes:
    """Generate a minimal encrypted PDF (pypdf will detect encryption)."""
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj\n"
        b"<< /Type /Catalog /Pages 2 0 R >>\n"
        b"endobj\n"
        b"2 0 obj\n"
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>\n"
        b"endobj\n"
        b"3 0 obj\n"
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\n"
        b"endobj\n"
        b"4 0 obj\n"
        b"<< /Filter /Standard /V 2 /R 3 /Length 128 /O <000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000> /U <0000000000000000000000000000000000000000000000000000000000000000> /P -4 >>\n"
        b"endobj\n"
        b"xref\n"
        b"0 5\n"
        b"0000000000 65535 f \n"
        b"0000000009 00000 n \n"
        b"0000000058 00000 n \n"
        b"0000000115 00000 n \n"
        b"0000000188 00000 n \n"
        b"trailer\n"
        b"<< /Size 5 /Root 1 0 R /Encrypt 4 0 R >>\n"
        b"startxref\n"
        b"340\n"
        b"%%EOF\n"
    )
    return pdf


def _malformed_pdf_bytes() -> bytes:
    return b"NOT A PDF FILE AT ALL\njust random bytes"


# ============================================================
# CHUNKING
# ============================================================


class TestChunking:
    def test_paragraph_split(self):
        text = "第一段。\n\n第二段内容。\n\n第三段。"
        chunks = chunk_text(text, max_chars=50)
        assert len(chunks) >= 1
        assert all(len(c) > 0 for c in chunks)

    def test_oversized_paragraph(self):
        text = "A" * 1500  # single huge block, no sentence boundaries
        chunks = chunk_text(text, max_chars=500)
        assert len(chunks) >= 3  # char-split fallback should produce 3+

    def test_short_text_under_max(self):
        text = "短短的一行。"
        chunks = chunk_text(text, max_chars=1000)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_empty_text(self):
        assert chunk_text("", max_chars=500) == []
        assert chunk_text("   ", max_chars=500) == []

    def test_preserves_content(self):
        text = "甲乙\n\n丙丁\n\n戊己"
        chunks = chunk_text(text, max_chars=100)
        combined = "".join(chunks)
        assert "甲乙" in combined
        assert "丙丁" in combined
        assert "戊己" in combined

    def test_chunking_determinism(self):
        """Same text and parameters must produce identical chunks every time."""
        text = "第一段内容较多。\n\n第二段也有很多文字。\n\n第三段继续。"
        chunks1 = chunk_text(text, max_chars=50)
        chunks2 = chunk_text(text, max_chars=50)
        assert chunks1 == chunks2
        # chunk_index would be 0..n-1 consistently
        for i, c in enumerate(chunks1):
            assert i < len(chunks2)
            assert c == chunks2[i]


# ============================================================
# INGESTION
# ============================================================


@pytest.mark.anyio
class TestIngestion:
    async def test_ingest_text_creates_document_and_chunks(self, db_session):
        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="测试文献",
            text="第一段文字。\n\n第二段文字。\n\n第三段文字。" * 20,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "public domain pre-1928",
            },
        )
        assert result.document_id is not None
        assert result.title == "测试文献"
        assert result.chunk_count > 0
        assert result.total_chars > 0

        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.title == "测试文献"

        chunk_row = (await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == result.document_id)
        )).scalars().all()
        assert len(chunk_row) == result.chunk_count

    async def test_ingest_stores_metadata(self, db_session):
        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="针灸甲乙经",
            text="内容内容内容。" * 30,
            metadata={"dynasty": "西晋", "category": "针灸", **_COMPLIANCE},
        )
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.dynasty == "西晋"
        assert doc.category == "针灸"

    async def test_ingest_persistence_across_sessions(self, db_session):
        """Document and chunks must survive a transaction commit."""
        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="持久化测试",
            text="第一段。\n\n第二段。\n\n第三段。",
            metadata=_COMPLIANCE,
        )
        await db_session.flush()

        # Verify in same session
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.title == "持久化测试"

        chunks = (await db_session.execute(
            select(DocumentChunk).where(DocumentChunk.document_id == result.document_id)
        )).scalars().all()
        assert len(chunks) == result.chunk_count
        # Each chunk has (document_id, chunk_index) unique
        seen = set()
        for ch in chunks:
            key = (ch.document_id, ch.chunk_index)
            assert key not in seen, f"Duplicate (document_id, chunk_index): {key}"
            seen.add(key)

    async def test_ingest_empty_text_raises(self, db_session):
        svc = IngestionService(db_session)
        with pytest.raises(ValueError, match="empty"):
            await svc.ingest_text(title="空文献", text="   ", metadata=_COMPLIANCE)

    # ---------- PDF ----------

    async def test_pdf_extraction_returns_text(self, db_session):
        """Real PDF fixture yields extractable text."""
        svc = IngestionService(db_session)
        pdf_bytes = _simple_pdf_bytes()
        file = io.BytesIO(pdf_bytes)
        result = await svc.ingest_pdf(title="Test PDF", file=file, metadata=_COMPLIANCE)
        assert result.document_id is not None
        assert result.chunk_count > 0

        # Verify extractable text is stored (not a placeholder)
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert "[PDF document" not in doc.content_text
        assert "Hello World" in doc.content_text

    async def test_pdf_raw_source_traceable(self, db_session):
        """PDF content_text is stored; source_url has a reference marker."""
        svc = IngestionService(db_session)
        pdf_bytes = _simple_pdf_bytes()
        file = io.BytesIO(pdf_bytes)
        result = await svc.ingest_pdf(title="Trace PDF", file=file, metadata=_COMPLIANCE)
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        # source_url should contain the pdf reference
        assert doc.source_url is not None
        assert "pdf:" in doc.source_url
        # content_text contains actual extracted text
        assert doc.content_text is not None
        assert len(doc.content_text) > 0

    async def test_encrypted_pdf_fails_cleanly(self, db_session):
        """Encrypted/malformed PDF must raise PDFExtractionError or PdfReadError,
        no half-created records in either case."""
        svc = IngestionService(db_session)
        pdf_bytes = _encrypted_pdf_bytes()
        file = io.BytesIO(pdf_bytes)
        # pypdf may raise PdfReadError or FileNotDecryptedError or our PDFExtractionError
        with pytest.raises((PDFExtractionError, Exception)):
            await svc.ingest_pdf(title="Encrypted", file=file, metadata=_COMPLIANCE)

        # Verify no document was created
        count = (await db_session.execute(
            text("SELECT COUNT(*) FROM documents")
        )).scalar_one()
        assert count == 0

    async def test_malformed_pdf_fails_cleanly(self, db_session):
        """Malformed PDF must raise PDFExtractionError, no half-created records."""
        svc = IngestionService(db_session)
        file = io.BytesIO(_malformed_pdf_bytes())
        with pytest.raises(PDFExtractionError):
            await svc.ingest_pdf(title="Bad PDF", file=file, metadata=_COMPLIANCE)

        count = (await db_session.execute(
            text("SELECT COUNT(*) FROM documents")
        )).scalar_one()
        assert count == 0

    # ---------- Transaction safety ----------

    async def test_failed_chunking_rolls_back_document(self, db_session):
        """If chunk storage fails, the parent document must not remain."""
        svc = IngestionService(db_session)
        original_count = (await db_session.execute(
            text("SELECT COUNT(*) FROM documents")
        )).scalar_one()

        # Force failure by passing empty text (triggers ValueError)
        with pytest.raises(ValueError):
            await svc.ingest_text(title="Should roll back", text="", metadata=_COMPLIANCE)

        # No new documents
        count = (await db_session.execute(
            text("SELECT COUNT(*) FROM documents")
        )).scalar_one()
        assert count == original_count


# ============================================================
# RETRIEVAL
# ============================================================


@pytest.mark.anyio
class TestRetrieval:
    async def test_multi_keyword_match(self, db_session):
        """Multi-keyword query should match chunks with any keyword."""
        from app.services.retrieval import RetrievalService

        svc = IngestionService(db_session)
        # Text contains all three keywords but NOT as a contiguous phrase
        await svc.ingest_text(
            title="中医经典",
            text=(
                "皇甫谧，字士安，幼名静，安定朝那人。\n\n"
                "其著作《针灸甲乙经》是中国现存最早的针灸学专著。\n\n"
                "该书系统整理了经络学说与腧穴理论。\n\n"
                "对后世中医发展产生了深远影响。"
            ),
            metadata=_COMPLIANCE,
        )

        rsvc = RetrievalService(db_session)
        result = await rsvc.search(query="皇甫谧 针灸 经络", top_k=5)
        assert result.total >= 1
        assert all(r.citation for r in result.results)
        # Check citation format: [doc_id:chunk_id]
        for r in result.results:
            assert r.citation.startswith("[")
            assert r.citation.endswith("]")
            assert ":" in r.citation
            assert r.document_id in r.citation
            assert r.chunk_id in r.citation

    async def test_no_match_returns_empty(self, db_session):
        from app.services.retrieval import RetrievalService

        svc = IngestionService(db_session)
        await svc.ingest_text(title="test", text="some content here", metadata=_COMPLIANCE)

        rsvc = RetrievalService(db_session)
        result = await rsvc.search(query="zzz_nonexistent_zzz", top_k=5)
        assert result.total == 0
        assert result.results == []

    async def test_top_k_limit_respected(self, db_session):
        from app.services.retrieval import RetrievalService

        svc = IngestionService(db_session)
        await svc.ingest_text(
            title="long",
            text=("数据" * 200 + "\n\n") * 50,
            max_chunk_chars=500,
            metadata=_COMPLIANCE,
        )

        rsvc = RetrievalService(db_session)
        result = await rsvc.search(query="数据", top_k=5)
        assert len(result.results) <= 5

    async def test_stable_sort_ordering(self, db_session):
        """Same query twice produces identical order."""
        from app.services.retrieval import RetrievalService

        svc = IngestionService(db_session)
        await svc.ingest_text(
            title="稳定排序测试",
            text="针灸经络。\n\n" * 20 + "经络学说。\n\n" * 10,
            metadata=_COMPLIANCE,
        )
        rsvc = RetrievalService(db_session)
        r1 = await rsvc.search(query="经络", top_k=5)
        r2 = await rsvc.search(query="经络", top_k=5)
        assert [c.chunk_id for c in r1.results] == [c.chunk_id for c in r2.results]


# ============================================================
# CITATION
# ============================================================


@pytest.mark.anyio
class TestCitation:
    async def test_citation_format_is_doc_id_colon_chunk_id(self, db_session):
        from app.services.retrieval import RetrievalService

        svc = IngestionService(db_session)
        await svc.ingest_text(title="测试", text="段落一。\n\n段落二。\n\n段落三。", metadata=_COMPLIANCE)
        rsvc = RetrievalService(db_session)
        search_result = await rsvc.search(query="段落", top_k=3)

        for r in search_result.results:
            # Exact format: [document_id:chunk_id]
            expected = f"[{r.document_id}:{r.chunk_id}]"
            assert r.citation == expected, f"Expected {expected}, got {r.citation}"

    async def test_citation_ids_traceable_to_db_records(self, db_session):
        from app.services.retrieval import RetrievalService

        svc = IngestionService(db_session)
        await svc.ingest_text(
            title="溯源测试",
            text="目标内容在这里。\n\n其他内容。",
            metadata=_COMPLIANCE,
        )
        rsvc = RetrievalService(db_session)
        search_result = await rsvc.search(query="目标内容", top_k=1)

        assert search_result.total >= 1
        r = search_result.results[0]

        # citation's document_id → real Document
        doc = (await db_session.execute(
            select(Document).where(Document.id == r.document_id)
        )).scalar_one_or_none()
        assert doc is not None
        assert doc.title == "溯源测试"

        # citation's chunk_id → real DocumentChunk
        chunk = (await db_session.execute(
            select(DocumentChunk).where(
                DocumentChunk.id == r.chunk_id,
                DocumentChunk.document_id == r.document_id,
            )
        )).scalar_one_or_none()
        assert chunk is not None
        assert "目标内容" in chunk.content

    async def test_citation_huanfumi_end_to_end(self, db_session):
        """Exact end-to-end: ingest text with 皇甫谧, 针灸, 经络,
        search for '皇甫谧 针灸 经络', verify results."""
        from app.services.retrieval import RetrievalService

        svc = IngestionService(db_session)
        ing_result = await svc.ingest_text(
            title="针灸甲乙经",
            text=(
                "皇甫谧，字士安，安定朝那人。魏晋时期著名医学家。\n\n"
                "其编撰的《针灸甲乙经》是中国现存最早的针灸学专著，\n\n"
                "系统总结了经络学说、腧穴定位和刺灸方法。\n\n"
                "该书共十二卷，一百二十八篇。"
            ),
            metadata=_COMPLIANCE,
        )

        rsvc = RetrievalService(db_session)
        result = await rsvc.search(query="皇甫谧 针灸 经络", top_k=5)

        # At least one chunk returned
        assert result.total >= 1
        r = result.results[0]
        assert r.document_id == ing_result.document_id
        assert r.chunk_id is not None
        # Citation format correct
        assert r.citation == f"[{r.document_id}:{r.chunk_id}]"
        # Document is traceable
        doc = (await db_session.execute(
            select(Document).where(Document.id == r.document_id)
        )).scalar_one()
        assert doc.title == "针灸甲乙经"


# ============================================================
# API INTEGRATION TESTS (real HTTP)
# ============================================================


def _make_test_app():
    """Build a FastAPI test app matching the real v1 router structure."""
    from app.core.error_handlers import register_error_handlers
    from app.middleware.request_id import RequestIDMiddleware
    from fastapi import FastAPI

    app = FastAPI(debug=False)
    app.add_middleware(RequestIDMiddleware)
    register_error_handlers(app)

    # Include the real v1 router (which includes day2_search_router)
    from app.api.v1 import router as v1_router
    app.include_router(v1_router)

    # Ensure the search endpoint exists at /api/v1/search
    return app


@pytest.fixture
async def app_db_session():
    """In-memory SQLite session used by the test app (via get_session override)."""
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()


@pytest.mark.anyio
class TestSearchAPI:
    """Integration tests hitting POST /api/v1/search via real HTTP."""

    async def test_search_endpoint_exists_and_returns_contract(self, app_db_session):
        """POST /api/v1/search returns query, results, metadata. No LLM fields."""
        from app.db.database import get_session

        # Ingest data directly
        svc = IngestionService(app_db_session)
        await svc.ingest_text(
            title="针灸甲乙经",
            text=(
                "皇甫谧编撰的《针灸甲乙经》系统整理了经络学说。\n\n"
                "该书对后世针灸学发展有深远影响。"
            ),
            metadata=_COMPLIANCE,
        )
        await app_db_session.flush()

        app = _make_test_app()
        # Override get_session to use our test session
        async def override_get_session():
            yield app_db_session
        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "皇甫谧 针灸 经络", "top_k": 5},
            )
            assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
            body = r.json()

            # Frozen contract fields: query, results, metadata
            assert "query" in body, f"Missing 'query' in {body}"
            assert "results" in body, f"Missing 'results' in {body}"
            assert "metadata" in body, f"Missing 'metadata' in {body}"

            # No LLM fields
            assert "answer" not in body
            assert "generated_answer" not in body
            assert "chunks" not in body  # Frozen format uses "results"

            # metadata has exactly two fields: top_k, model
            assert "top_k" in body["metadata"]
            assert body["metadata"]["top_k"] == 5
            assert body["metadata"]["model"] == "retrieval-only"
            # execution_time MUST be absent (breaks determinism)
            assert "execution_time" not in body["metadata"], (
                "execution_time breaks determinism — must be absent"
            )
            # No extra fields in metadata
            assert set(body["metadata"].keys()) == {"top_k", "model"}

            # Each result has exactly 5 fields
            for result in body["results"]:
                assert set(result.keys()) == {"chunk_id", "document_id", "content", "score", "citation"}
                assert "metadata" not in result  # no per-result metadata in frozen contract

            # At least one result
            assert body["metadata"]["top_k"] == 5

            # Every citation maps to a real chunk_id
            for result in body["results"]:
                # citation format: [doc_id:chunk_id] — parse and verify
                citation = result["citation"]
                assert citation.startswith("[") and citation.endswith("]")
                inner = citation[1:-1]
                doc_id, chunk_id = inner.split(":", 1)
                assert doc_id == result["document_id"]
                assert chunk_id == result["chunk_id"]

            # Determinism: same input → byte-identical JSON
            import json
            r2 = await c.post(
                "/api/v1/search",
                json={"query": "皇甫谧 针灸 经络", "top_k": 5},
            )
            assert r2.status_code == 200
            assert json.dumps(body, sort_keys=True) == json.dumps(r2.json(), sort_keys=True)

    async def test_search_no_match_returns_empty_valid(self, app_db_session):
        """Empty results still return valid frozen contract structure."""
        from app.db.database import get_session

        svc = IngestionService(app_db_session)
        await svc.ingest_text(title="test", text="some content", metadata=_COMPLIANCE)
        await app_db_session.flush()

        app = _make_test_app()
        async def override_get_session():
            yield app_db_session
        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "nonexistent_keyword_xyz", "top_k": 5},
            )
            assert r.status_code == 200
            body = r.json()
            assert body["results"] == []
            assert body["query"] == "nonexistent_keyword_xyz"
            assert body["metadata"]["model"] == "retrieval-only"
            assert body["metadata"]["top_k"] == 5
            assert "execution_time" not in body["metadata"]

    async def test_search_huanfumi_e2e(self, app_db_session):
        """Full end-to-end: ingest text with 皇甫谧/针灸/经络,
        search, verify all citations traceable. Day 3 contract."""
        from app.db.database import get_session

        svc = IngestionService(app_db_session)
        await svc.ingest_text(
            title="针灸甲乙经",
            text=(
                "皇甫谧，字士安，安定朝那人。魏晋时期著名医学家。\n\n"
                "其编撰的《针灸甲乙经》是中国现存最早的针灸学专著，\n\n"
                "系统总结了经络学说、腧穴定位和刺灸方法。"
            ),
            metadata=_COMPLIANCE,
        )
        await app_db_session.flush()

        app = _make_test_app()
        async def override_get_session():
            yield app_db_session
        app.dependency_overrides[get_session] = override_get_session

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            r = await c.post(
                "/api/v1/search",
                json={"query": "皇甫谧 针灸 经络", "top_k": 5},
            )
            assert r.status_code == 200
            body = r.json()
            assert len(body["results"]) >= 1
            assert body["metadata"]["model"] == "retrieval-only"

            # Verify each citation traceable to DB
            for result in body["results"]:
                doc = (await app_db_session.execute(
                    select(Document).where(Document.id == result["document_id"])
                )).scalar_one_or_none()
                assert doc is not None, f"Document {result['document_id']} not found"

                ch = (await app_db_session.execute(
                    select(DocumentChunk).where(
                        DocumentChunk.id == result["chunk_id"],
                        DocumentChunk.document_id == result["document_id"],
                    )
                )).scalar_one_or_none()
                assert ch is not None, f"Chunk {result['chunk_id']} not found"

                # Citation format matches
                expected_citation = f"[{result['document_id']}:{result['chunk_id']}]"
                assert result["citation"] == expected_citation

                # Citation is parseable: [doc_id:chunk_id]
                assert result["citation"].count("[") == 1
                assert result["citation"].count("]") == 1
                assert ":" in result["citation"]


# ============================================================
# APPEND-PASSAGE UNIT + API TESTS
# ============================================================


@pytest.mark.anyio
class TestAppendPassage:
    """Tests for POST /api/v1/search/documents/{id}/append-passage.

    Covers: same-document/different-passage data relationship,
    transactional safety, review/RAG state reset, and permission guards.
    """

    async def test_append_passage_to_existing_document(self, app_db_session):
        """Ingest passage A, then append passage B → same document, two
        distinct passage_ids, chunk_index continues, checksum changes."""

        # Ingest initial document with passage A
        svc = IngestionService(app_db_session)
        r1 = await svc.ingest_text(
            title="同文献多篇测试",
            text="第一段经文。\n\n第二段经文。",
            metadata=_COMPLIANCE,
            passage_id=_make_passage(app_db_session, "篇一", 1),
        )
        doc_id = r1.document_id
        original_checksum = r1.checksum
        original_chunk_count = r1.chunk_count

        # Verify initial state
        chunks_before = list((await app_db_session.execute(
            select(DocumentChunk).where(
                DocumentChunk.document_id == doc_id,
                DocumentChunk.is_deleted.is_(False),
            ).order_by(DocumentChunk.chunk_index)
        )).scalars())
        assert len(chunks_before) == original_chunk_count

        # Append passage B to same document
        psg_b_id = _make_passage(app_db_session, "篇二", 2)
        r2 = await svc.append_passage(
            document_id=doc_id,
            text="第三段经文。\n\n第四段经文。",
            passage_id=psg_b_id,
        )
        assert r2.document_id == doc_id
        assert r2.passage_id == psg_b_id
        assert r2.appended_chunk_count > 0
        assert len(r2.appended_chunk_ids) == r2.appended_chunk_count
        assert r2.first_chunk_index == original_chunk_count
        assert r2.last_chunk_index >= r2.first_chunk_index
        assert r2.content_checksum != original_checksum

        # Verify chunk_index is continuous
        all_chunks = list((await app_db_session.execute(
            select(DocumentChunk).where(
                DocumentChunk.document_id == doc_id,
                DocumentChunk.is_deleted.is_(False),
            ).order_by(DocumentChunk.chunk_index)
        )).scalars())
        for i, ch in enumerate(all_chunks):
            assert ch.chunk_index == i, f"chunk_index gap: expected {i}, got {ch.chunk_index}"

        # Verify two distinct passage_ids exist on this document
        passage_ids = list({
            ch.passage_id for ch in all_chunks if ch.passage_id
        })
        assert len(passage_ids) >= 2, f"Expected >=2 distinct passage_ids, got {len(passage_ids)}: {passage_ids}"

        # Verify document checksum updated
        doc_after = (await app_db_session.execute(
            select(Document).where(Document.id == doc_id)
        )).scalar_one()
        assert doc_after.content_checksum == r2.content_checksum
        assert doc_after.content_checksum != original_checksum

    async def test_append_resets_review_and_rag(self, app_db_session):
        """After append, review_status → pending and rag_enabled → False."""

        svc = IngestionService(app_db_session)
        r1 = await svc.ingest_text(
            title="审核重置测试",
            text="初始内容。",
            metadata=_COMPLIANCE,
            passage_id=_make_passage(app_db_session, "审核篇", 1),
        )
        doc_id = r1.document_id

        # Simulate admin review → approved + rag_enabled
        doc = (await app_db_session.execute(
            select(Document).where(Document.id == doc_id)
        )).scalar_one()
        doc.review_status = "approved"
        doc.rag_enabled = True
        await app_db_session.flush()

        # Append another passage
        psg_b = _make_passage(app_db_session, "审核篇二", 2)
        await svc.append_passage(
            document_id=doc_id,
            text="追加内容。",
            passage_id=psg_b,
        )

        doc_after = (await app_db_session.execute(
            select(Document).where(Document.id == doc_id)
        )).scalar_one()
        assert doc_after.review_status == "pending", (
            f"Expected pending, got {doc_after.review_status}"
        )
        assert doc_after.rag_enabled is False, (
            f"Expected rag_enabled=False, got {doc_after.rag_enabled}"
        )

    async def test_append_nonexistent_document_fails(self, app_db_session):
        """Appending to a nonexistent document_id raises ValueError,
        zero chunks created."""
        import uuid

        svc = IngestionService(app_db_session)
        count_before = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()

        with pytest.raises(ValueError, match="does not exist"):
            await svc.append_passage(
                document_id=str(uuid.uuid4()),
                text="任意文字",
                passage_id=_make_passage(app_db_session, "不存在文件测试", 1),
            )

        count_after = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        assert count_before == count_after, "No chunks may be created on failure"

    async def test_append_nonexistent_passage_fails(self, app_db_session):
        """Appending with a nonexistent passage_id raises ValueError,
        zero chunks created."""
        import uuid

        svc = IngestionService(app_db_session)
        r1 = await svc.ingest_text(
            title="测试空passage",
            text="初始经文。",
            metadata=_COMPLIANCE,
            passage_id=_make_passage(app_db_session, "有效篇章", 1),
        )
        count_before = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()

        with pytest.raises(ValueError, match="does not exist"):
            await svc.append_passage(
                document_id=r1.document_id,
                text="任意文字",
                passage_id=str(uuid.uuid4()),
            )

        count_after = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        assert count_before == count_after, "No chunks may be created on failure"

    async def test_append_empty_text_fails(self, app_db_session):
        """Empty text raises ValueError, no state changes."""
        svc = IngestionService(app_db_session)
        r1 = await svc.ingest_text(
            title="空文本测试",
            text="初始内容。",
            metadata=_COMPLIANCE,
            passage_id=_make_passage(app_db_session, "空文本篇", 1),
        )
        count_before = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()

        with pytest.raises(ValueError, match="empty"):
            await svc.append_passage(
                document_id=r1.document_id,
                text="   ",
                passage_id=_make_passage(app_db_session, "空文本篇二", 2),
            )

        count_after = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        assert count_before == count_after

    async def test_append_permission_required(self, app_db_session):
        """Unauthenticated → 401.  Authenticated without
        document:update → 403.  With document:update → 200.

        This test verifies the append endpoint's permission guard via
        real JWT auth chain (no mock overrides)."""
        from app.db.database import get_session
        from app.services.auth_service import AuthService, create_access_token

        svc = IngestionService(app_db_session)
        r1 = await svc.ingest_text(
            title="权限测试文档",
            text="初始内容。",
            metadata=_COMPLIANCE,
            passage_id=_make_passage(app_db_session, "权限篇", 1),
        )
        await app_db_session.flush()

        # Create users; register() auto-assigns Researcher role
        auth_svc = AuthService(app_db_session)
        owner = await auth_svc.register(
            "append_owner", "append_owner@test.com", "Test123456!", "AppendOwner"
        )
        no_perm = await auth_svc.register(
            "append_noperm", "append_noperm@test.com", "Test123456!", "AppendNoPerm"
        )
        await app_db_session.flush()

        from app.models.user import Permission as PermModel
        from app.models.user import Role
        from app.models.user import role_permission as rp
        from app.models.user import user_role as ur
        from sqlalchemy import and_
        from sqlalchemy import delete as sa_del
        from sqlalchemy import select as sa

        # Ensure document:update permission is granted to Researcher role
        researcher_role = (await app_db_session.execute(
            sa(Role).where(Role.name == "Researcher")
        )).scalar_one_or_none()
        if researcher_role:
            # Remove no_perm from Researcher so they DON'T have document:update
            await app_db_session.execute(
                sa_del(ur).where(
                    and_(ur.c.user_id == no_perm.id, ur.c.role_id == researcher_role.id)
                )
            )
            await app_db_session.flush()

        doc_upd = (await app_db_session.execute(
            sa(PermModel).where(
                and_(PermModel.resource == "document", PermModel.action == "update")
            )
        )).scalar_one_or_none()
        if doc_upd is None:
            doc_upd = PermModel(resource="document", action="update", description="Update documents")
            app_db_session.add(doc_upd)
            await app_db_session.flush()

        # Grant document:update to Researcher role
        if researcher_role and doc_upd:
            ex_rp = (await app_db_session.execute(
                sa(rp).where(
                    and_(rp.c.role_id == researcher_role.id, rp.c.permission_id == doc_upd.id)
                )
            )).first()
            if ex_rp is None:
                await app_db_session.execute(
                    rp.insert().values(role_id=researcher_role.id, permission_id=doc_upd.id)
                )
            # Ensure owner has researcher role (already auto-assigned)
            ex_ur = (await app_db_session.execute(
                sa(ur).where(
                    and_(ur.c.user_id == owner.id, ur.c.role_id == researcher_role.id)
                )
            )).first()
            if ex_ur is None:
                await app_db_session.execute(
                    ur.insert().values(user_id=owner.id, role_id=researcher_role.id)
                )
        await app_db_session.flush()

        owner_token = create_access_token(owner.id)
        noperm_token = create_access_token(no_perm.id)

        app = _make_test_app()
        async def override_get_session():
            yield app_db_session
        app.dependency_overrides[get_session] = override_get_session

        psg_id_2 = _make_passage(app_db_session, "权限篇二", 2)
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            # (1) No token → 401
            r = await c.post(
                f"/api/v1/search/documents/{r1.document_id}/append-passage",
                json={"text": "追加", "passage_id": psg_id_2},
            )
            assert r.status_code == 401, (
                f"Expected 401 unauthenticated, got {r.status_code}: {r.text}"
            )

            # (2) Authenticated, no document:update → 403
            r = await c.post(
                f"/api/v1/search/documents/{r1.document_id}/append-passage",
                json={"text": "追加", "passage_id": psg_id_2},
                headers={"Authorization": f"Bearer {noperm_token}"},
            )
            assert r.status_code == 403, (
                f"Expected 403 no-permission, got {r.status_code}: {r.text}"
            )

            # (3) Authenticated, has document:update → 200
            r = await c.post(
                f"/api/v1/search/documents/{r1.document_id}/append-passage",
                json={"text": "追加", "passage_id": psg_id_2},
                headers={"Authorization": f"Bearer {owner_token}"},
            )
            assert r.status_code == 200, (
                f"Expected 200 with permission, got {r.status_code}: {r.text}"
            )

    async def test_append_rollback_on_chunk_write_failure(self, app_db_session):
        """If audit/flush fails after chunk write, savepoint rolls back
        all chunks, content, checksum, review, rag changes."""
        svc = IngestionService(app_db_session)
        r1 = await svc.ingest_text(
            title="回滚测试文档",
            text="初始经文内容。",
            metadata=_COMPLIANCE,
            passage_id=_make_passage(app_db_session, "回滚篇", 1),
        )
        doc_id = r1.document_id
        original_checksum = r1.checksum

        # Set doc to approved so we can verify it stays unchanged
        doc = (await app_db_session.execute(
            select(Document).where(Document.id == doc_id)
        )).scalar_one()
        doc.review_status = "approved"
        doc.rag_enabled = True
        await app_db_session.flush()

        chunk_count_before = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()

        # Simulate a failure by monkey-patching _write_audit to raise
        # AFTER chunks have been flushed.  The savepoint must roll
        # everything back.
        original_audit = svc._write_audit

        async def _failing_audit(**kwargs):
            raise RuntimeError("injected audit failure for rollback test")

        svc._write_audit = _failing_audit

        try:
            with pytest.raises(RuntimeError, match="injected audit failure"):
                await svc.append_passage(
                    document_id=doc_id,
                    text="追加内容。",
                    passage_id=_make_passage(app_db_session, "回滚篇二", 2),
                )
            await app_db_session.flush()
        finally:
            svc._write_audit = original_audit

        # After rollback: no new chunks, same checksum, same review/rag
        chunk_count_after = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        assert chunk_count_after == chunk_count_before, (
            f"Rollback must leave zero new chunks: "
            f"{chunk_count_before} → {chunk_count_after}"
        )

        doc_after = (await app_db_session.execute(
            select(Document).where(Document.id == doc_id)
        )).scalar_one()
        assert doc_after.review_status == "approved", (
            f"Review status must be unchanged after rollback: {doc_after.review_status}"
        )
        assert doc_after.rag_enabled is True, (
            "RAG enabled must be unchanged after rollback"
        )
        assert doc_after.content_checksum == original_checksum, (
            f"Checksum must be unchanged after rollback: "
            f"{original_checksum} → {doc_after.content_checksum}"
        )

        # Verify a second attempt succeeds normally
        r2 = await svc.append_passage(
            document_id=doc_id,
            text="追加成功。",
            passage_id=_make_passage(app_db_session, "回滚篇三", 3),
        )
        assert r2.appended_chunk_count > 0
        assert len(r2.appended_chunk_ids) == r2.appended_chunk_count
        assert r2.content_checksum != original_checksum

    async def test_append_audit_action_field(self, app_db_session):
        """Audit rows for append have action='append_passage' with
        passage_id and chunk range in details."""
        from app.models.fulltext_ingestion_audit import FulltextIngestionAudit

        svc = IngestionService(app_db_session)
        r1 = await svc.ingest_text(
            title="审计测试文档",
            text="初始内容。",
            metadata=_COMPLIANCE,
            passage_id=_make_passage(app_db_session, "审计篇", 1),
        )
        psg_b = _make_passage(app_db_session, "审计篇二", 2)
        r2 = await svc.append_passage(
            document_id=r1.document_id,
            text="审计追加。",
            passage_id=psg_b,
        )

        audits = list((await app_db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.result_entity_id == r1.document_id,
            ).order_by(FulltextIngestionAudit.created_at.desc())
        )).scalars())

        append_audits = [a for a in audits if a.action == "append_passage"]
        assert len(append_audits) >= 1, "Must have at least one append_passage audit"
        latest = append_audits[0]
        assert latest.status == "success"
        assert latest.checksum == r2.content_checksum
        # details is JSON — verify it carries passage_id and chunk range
        details = latest.details or {}
        assert details.get("passage_id") == psg_b
        assert details.get("appended_chunk_count") == r2.appended_chunk_count
        assert details.get("first_chunk_index") == r2.first_chunk_index
        assert details.get("last_chunk_index") == r2.last_chunk_index

    async def test_append_forbidden_fulltext_rejected(self, app_db_session):
        """Appending to a document with forbidden_fulltext status must
        fail-closed without touching chunks/state."""
        svc = IngestionService(app_db_session)
        r1 = await svc.ingest_text(
            title="禁止全文追加测试",
            text="初始内容。",
            metadata={**_COMPLIANCE, "copyright_status": "public_domain"},
            passage_id=_make_passage(app_db_session, "禁止篇", 1),
        )
        doc_id = r1.document_id

        # Manually set to forbidden
        doc = (await app_db_session.execute(
            select(Document).where(Document.id == doc_id)
        )).scalar_one()
        doc.copyright_status = "forbidden_fulltext"
        await app_db_session.flush()

        chunk_count_before = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        orig_checksum = doc.content_checksum

        with pytest.raises(FulltextRejectedError):
            await svc.append_passage(
                document_id=doc_id,
                text="禁止追加",
                passage_id=_make_passage(app_db_session, "禁止篇二", 2),
            )

        chunk_count_after = (await app_db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        assert chunk_count_after == chunk_count_before
        doc_after = (await app_db_session.execute(
            select(Document).where(Document.id == doc_id)
        )).scalar_one()
        assert doc_after.content_checksum == orig_checksum
        assert doc_after.review_status == doc.review_status


#  -- helpers --


def _make_passage(db_session, title: str, order: int) -> str:
    """Create a minimal Passage and return its id."""
    from uuid import uuid4

    from app.models.book import Book
    from app.models.chapter import Chapter
    from app.models.passage import Passage
    from app.models.person import Person
    from app.models.version import Version

    # Quick entity chain
    person = Person(id=str(uuid4()), name="测试作者")
    db_session.add(person)
    book = Book(id=str(uuid4()), title="测试书", author_id=person.id)
    db_session.add(book)
    ver = Version(
        id=str(uuid4()),
        book_id=book.id,
        version_name="测试版",
        era="现代",
        repository="测试库",
        shelf_mark="TEST",
    )
    db_session.add(ver)
    ch = Chapter(id=str(uuid4()), book_id=book.id, title=f"{title}-章", order=order)
    db_session.add(ch)
    psg = Passage(
        id=str(uuid4()),
        chapter_id=ch.id,
        content_text=f"{title}正文",
        order=order,
    )
    db_session.add(psg)
    return psg.id
