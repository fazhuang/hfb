"""
Tests: RAG generation compliance — copyright gate at GenerationPipeline + API level.

Context 22: /api/v1/ai/generate must refuse when retrieval hits only
non-compliant documents (commercial_restricted, metadata_only, forbidden_fulltext,
pirated, unknown), even if rag_enabled=True. Compliant docs must carry provenance.
"""
from __future__ import annotations

import json as _json

import pytest
from sqlalchemy import select
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


async def _seed_doc(session, title, copyright_status, rag_enabled, content, auth_basis="", source_url=""):
    """Seed a single doc + chunk, return (doc_id, chunk_id)."""
    doc = Document(
        title=title,
        content_text=content,
        copyright_status=copyright_status,
        authorization_basis=auth_basis,
        rag_enabled=rag_enabled,
        source_url=source_url,
    )
    session.add(doc)
    await session.flush()
    chunk = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content=content,
        token_count=len(content),
        page_number=1,
        paragraph_index=0,
        evidence_weight="primary",
    )
    session.add(chunk)
    await session.flush()
    return doc.id, chunk.id


# ============================================================
# GenerationPipeline-level copyright gate
# ============================================================


@pytest.mark.anyio
class TestGenerationPipelineCopyrightGate:
    """GenerationPipeline.generate with strict_compliance=True rejects non-compliant."""

    async def test_commercial_restricted_rag_disabled_generation_refuses(self, db_session):
        """commercial_restricted + rag_enabled=False + matching chunk → refusal."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "商业文献", "commercial_restricted", False,
                  "这是一篇商业数据库全文内容。")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("商业数据库", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" in result.answer, (
            f"Expected refusal for commercial_restricted, got: {result.answer[:200]}"
        )
        assert result.results == []
        assert result.citations == []

    async def test_commercial_restricted_rag_enabled_generation_refuses(self, db_session):
        """commercial_restricted + rag_enabled=True (polluted) + matching chunk → refusal."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "商业文献", "commercial_restricted", True,
                  "这是一篇商业数据库全文内容。")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("商业数据库", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" in result.answer, (
            f"Expected refusal for polluted commercial_restricted+rag_enabled=True, got: {result.answer[:200]}"
        )
        assert result.results == []
        assert result.citations == []

    async def test_public_domain_with_auth_basis_generates_with_provenance(self, db_session):
        """public_domain + rag_enabled=True + authorization_basis → success with provenance."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "针灸甲乙经", "public_domain", True,
                  "皇甫谧编撰《针灸甲乙经》，系统整理魏晋以前针灸学成就。",
                  auth_basis="public domain — Tang dynasty work",
                  source_url="https://ctext.org/zhenjiu-jiayi-jing")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("皇甫谧", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" not in result.answer, (
            f"Expected success for compliant doc, got refusal: {result.answer[:200]}"
        )
        assert result.metadata.citation_validation["is_valid"] is True
        assert len(result.citations) >= 1
        # Provenance in results
        for r in result.results:
            assert "source_url" in r, f"Missing source_url in result: {r.keys()}"
            assert "copyright_status" in r, f"Missing copyright_status in result: {r.keys()}"
        # Provenance in citations
        for c in result.citations:
            assert "source_url" in c, f"Missing source_url in citation: {c.keys()}"
            assert "copyright_status" in c, f"Missing copyright_status in citation: {c.keys()}"

    async def test_metadata_only_generation_refuses(self, db_session):
        """metadata_only → refusal in generation pipeline."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "元数据文献", "metadata_only", True,
                  "仅有元数据的文献全文内容。")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("元数据", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" in result.answer

    async def test_forbidden_fulltext_generation_refuses(self, db_session):
        """forbidden_fulltext → refusal in generation pipeline."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "禁止全文文献", "forbidden_fulltext", True,
                  "被禁止全文的文献内容。")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("禁止全文", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" in result.answer

    async def test_pirated_generation_refuses(self, db_session):
        """pirated → refusal in generation pipeline."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "盗版文献", "pirated", True,
                  "盗版网站的全文内容。")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("盗版", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" in result.answer

    async def test_unknown_generation_refuses(self, db_session):
        """unknown copyright → refusal in generation pipeline."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "未知版权文献", "unknown", True,
                  "版权状态未知的文献内容。")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("未知版权", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" in result.answer

    async def test_only_compliant_survives_mixed_corpus(self, db_session):
        """Mix of compliant + non-compliant → only compliant appears, no refusal."""
        from app.services.generation_service import GenerationPipeline

        # Non-compliant (should be filtered)
        await _seed_doc(db_session, "商业库", "commercial_restricted", True,
                  "商业数据库中的皇甫谧相关信息。")
        # Compliant
        await _seed_doc(db_session, "针灸甲乙经", "public_domain", True,
                  "皇甫谧编撰《针灸甲乙经》，系统整理魏晋以前针灸学成就。",
                  auth_basis="public domain",
                  source_url="https://ctext.org/jiayi")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("皇甫谧", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" not in result.answer, (
            f"Should find compliant doc, got refusal: {result.answer[:200]}"
        )
        # All results must be from compliant docs
        for r in result.results:
            assert r.get("copyright_status") in {
                "public_domain", "open_access", "licensed", "user_uploaded_with_permission"
            }, f"Non-compliant copyright_status leaked: {r.get('copyright_status')}"


# ============================================================
# RetrievalService strict_compliance parameter
# ============================================================


@pytest.mark.anyio
class TestRetrievalServiceStrictCompliance:
    """RetrievalService.search with strict_compliance=True filters correctly."""

    async def test_strict_compliance_filters_forbidden(self, db_session):
        """strict_compliance=True excludes commercial_restricted."""
        from app.services.retrieval import RetrievalService

        await _seed_doc(db_session, "商业文献", "commercial_restricted", True,
                  "商业数据库全文内容测试。")
        await _seed_doc(db_session, "公版文献", "public_domain", True,
                  "公版文献全文内容测试。",
                  auth_basis="public domain")

        svc = RetrievalService(db_session)
        resp = await svc.search("全文内容测试", top_k=10, strict_compliance=True)

        # Only compliant doc should appear
        for r in resp.results:
            assert r.metadata.get("copyright_status") != "commercial_restricted", (
                f"commercial_restricted leaked through strict_compliance: {r.document_title}"
            )

    async def test_strict_compliance_requires_rag_enabled(self, db_session):
        """strict_compliance=True requires rag_enabled=True."""
        from app.services.retrieval import RetrievalService

        await _seed_doc(db_session, "公版未启用", "public_domain", False,
                  "一篇公版但未启用RAG的文献全文。",
                  auth_basis="public domain")

        svc = RetrievalService(db_session)
        resp = await svc.search("公版未启用", top_k=10, strict_compliance=True)

        # Should not find — rag_enabled=False
        for r in resp.results:
            assert "公版未启用" not in r.document_title, (
                "rag_enabled=False must be excluded under strict_compliance"
            )

    async def test_non_strict_allows_forbidden(self, db_session):
        """strict_compliance=False (default) allows commercial for non-RAG search."""
        from app.services.retrieval import RetrievalService

        await _seed_doc(db_session, "商业文献", "commercial_restricted", False,
                  "商业数据库全文内容测试。")

        svc = RetrievalService(db_session)
        resp = await svc.search("商业数据库", top_k=10, strict_compliance=False)

        # Default mode finds it
        titles = {r.document_title for r in resp.results}
        assert "商业文献" in titles, (
            f"Non-strict mode should find commercial doc for admin search: {titles}"
        )

    async def test_metadata_includes_provenance(self, db_session):
        """RetrievalResult.metadata has page_number, paragraph_index, source_url, copyright_status."""
        from app.services.retrieval import RetrievalService

        await _seed_doc(db_session, "针灸甲乙经", "public_domain", True,
                  "皇甫谧编撰《针灸甲乙经》。",
                  auth_basis="public domain",
                  source_url="https://ctext.org/jiayi")

        svc = RetrievalService(db_session)
        resp = await svc.search("皇甫谧", top_k=5, strict_compliance=True)

        assert resp.total >= 1
        r = resp.results[0]
        assert "source_url" in r.metadata
        assert "copyright_status" in r.metadata
        assert "page_number" in r.metadata
        assert "paragraph_index" in r.metadata


# ============================================================
# API endpoint level — /api/v1/ai/generate with compliance
# ============================================================


def _make_test_app():
    """Build a FastAPI test app with the v1 router."""
    from fastapi import FastAPI
    from app.middleware.request_id import RequestIDMiddleware
    from app.core.error_handlers import register_error_handlers

    app = FastAPI(debug=False)
    app.add_middleware(RequestIDMiddleware)
    register_error_handlers(app)
    from app.api.v1 import router as v1_router
    app.include_router(v1_router)
    return app


@pytest.fixture
async def api_db_session():
    """In-memory SQLite session for ASGI tests."""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.anyio
async def test_api_generate_commercial_refuses(api_db_session):
    """POST /api/v1/ai/generate with commercial_restricted → refusal."""
    import httpx
    from app.db.database import get_session
    from app.middleware.auth import get_current_user
    from app.api.v1.ai import guard_ai_read

    await _seed_doc(api_db_session, "商业文献", "commercial_restricted", True,
              "这是一篇商业数据库全文内容，涉及皇甫谧研究。")
    await api_db_session.commit()

    app = _make_test_app()

    async def override_get_session():
        yield api_db_session

    async def override_get_current_user():
        return "test-user"

    async def override_guard_ai_read():
        pass

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[guard_ai_read] = override_guard_ai_read

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/ai/generate", json={"query": "皇甫谧", "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()
        inner = data["data"]
        assert "EVIDENCE_GATE_REFUSAL" in inner["answer"], (
            f"Expected refusal for commercial doc, got: {inner['answer'][:200]}"
        )
        assert inner["results"] == []
        assert inner["citations"] == []


@pytest.mark.anyio
async def test_api_generate_public_domain_succeeds_with_provenance(api_db_session):
    """POST /api/v1/ai/generate with public_domain → success + provenance."""
    import httpx
    from app.db.database import get_session
    from app.middleware.auth import get_current_user
    from app.api.v1.ai import guard_ai_read

    await _seed_doc(api_db_session, "针灸甲乙经", "public_domain", True,
              "皇甫谧编撰《针灸甲乙经》，系统整理魏晋以前针灸学成就。",
              auth_basis="public domain — Tang dynasty work",
              source_url="https://ctext.org/zhenjiu-jiayi-jing")
    await api_db_session.commit()

    app = _make_test_app()

    async def override_get_session():
        yield api_db_session

    async def override_get_current_user():
        return "test-user"

    async def override_guard_ai_read():
        pass

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_current_user
    app.dependency_overrides[guard_ai_read] = override_guard_ai_read

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/ai/generate", json={"query": "皇甫谧", "top_k": 5})
        assert resp.status_code == 200
        data = resp.json()
        inner = data["data"]
        assert "EVIDENCE_GATE_REFUSAL" not in inner["answer"], (
            f"Expected success, got refusal: {inner['answer'][:200]}"
        )
        assert len(inner["citations"]) >= 1
        assert len(inner["results"]) >= 1
        # Provenance must be present
        for c in inner["citations"]:
            assert "source_url" in c, f"Citation missing source_url: {_json.dumps(c)}"
            assert "copyright_status" in c, f"Citation missing copyright_status: {_json.dumps(c)}"
