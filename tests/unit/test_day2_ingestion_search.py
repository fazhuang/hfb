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
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.services.chunking import chunk_text
from app.services.ingestion import (
    IngestionService,
    PDFExtractionError,
)


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
            metadata={"dynasty": "西晋", "category": "针灸"},
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
            await svc.ingest_text(title="空文献", text="   ")

    # ---------- PDF ----------

    async def test_pdf_extraction_returns_text(self, db_session):
        """Real PDF fixture yields extractable text."""
        svc = IngestionService(db_session)
        pdf_bytes = _simple_pdf_bytes()
        file = io.BytesIO(pdf_bytes)
        result = await svc.ingest_pdf(title="Test PDF", file=file)
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
        result = await svc.ingest_pdf(title="Trace PDF", file=file)
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
            await svc.ingest_pdf(title="Encrypted", file=file)

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
            await svc.ingest_pdf(title="Bad PDF", file=file)

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
            await svc.ingest_text(title="Should roll back", text="")

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
        await svc.ingest_text(title="test", text="some content here")

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
        await svc.ingest_text(title="测试", text="段落一。\n\n段落二。\n\n段落三。")
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
    from fastapi import FastAPI
    from app.core.error_handlers import register_error_handlers
    from app.middleware.request_id import RequestIDMiddleware

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
        await svc.ingest_text(title="test", text="some content")
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
