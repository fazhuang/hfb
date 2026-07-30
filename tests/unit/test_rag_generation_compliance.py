"""
Tests: RAG generation compliance — copyright gate at GenerationPipeline + API level.

Context 22: /api/v1/ai/generate must refuse when retrieval hits only
non-compliant documents (commercial_restricted, metadata_only, forbidden_fulltext,
pirated, unknown), even if rag_enabled=True. Compliant docs must carry provenance.
"""
from __future__ import annotations

import json as _json
from datetime import UTC

import pytest
from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


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


async def _seed_doc_withdrawn(session, title, copyright_status, rag_enabled, content, auth_basis="", source_url=""):
    """Seed a compliant doc + chunk, then set withdrawn_at (polluted state).

    Returns (doc_id, chunk_id, doc_withdrawn_at).
    """
    from datetime import datetime
    doc_id, chunk_id = await _seed_doc(session, title, copyright_status, rag_enabled, content, auth_basis, source_url)
    from app.models.document import Document as DocModel
    d = (await session.execute(select(DocModel).where(DocModel.id == doc_id))).scalar_one()
    d.withdrawn_at = datetime.now(UTC)
    # pollute: soft-deleted=False, rag_enabled=True — withdrawn_at is the only guard
    d.is_deleted = False
    d.rag_enabled = True
    # also ensure chunk is not soft-deleted
    from app.models.document_chunk import DocumentChunk as ChunkModel
    c = (await session.execute(select(ChunkModel).where(ChunkModel.id == chunk_id))).scalar_one()
    c.is_deleted = False
    await session.flush()
    return doc_id, chunk_id, d.withdrawn_at


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
# Authorization basis / license_type gate — Context 22 recheck
# ============================================================


@pytest.mark.anyio
class TestAuthorizationBasisGate:
    """query-time auth-basis check: public_domain + rag_enabled=True
    but empty authorization_basis & license_type → refused."""

    # ------------------------------------------------------------------
    # EvidenceRAGService
    # ------------------------------------------------------------------

    async def test_evidence_rag_public_domain_no_auth_refused(self, db_session):
        """EvidenceRAGService: public_domain + rag_enabled=True + no auth → refusal=True."""
        from app.services.evidence_rag_service import EvidenceRAGService

        await _seed_doc(db_session, "公版无授权", "public_domain", True,
                        "公版文献但没有授权依据的全文内容。",
                        auth_basis="")

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("公版无授权")

        assert resp.refusal is True, (
            f"Expected refusal for no-auth doc, got refusal={resp.refusal}"
        )
        assert resp.citations == []
        assert resp.evidence == []

    async def test_evidence_rag_license_type_only_allowed(self, db_session):
        """EvidenceRAGService: license_type non-empty → allowed even without authorization_basis."""
        from app.services.evidence_rag_service import EvidenceRAGService

        doc_id, _ = await _seed_doc(db_session, "许可公版", "public_domain", True,
                                     "授权公版文献的全文内容。",
                                     auth_basis="")
        # patch license_type after _seed_doc
        from app.models.document import Document as DocModel
        d = (await db_session.execute(
            select(DocModel).where(DocModel.id == doc_id)
        )).scalar_one()
        d.license_type = "CC-BY"
        await db_session.flush()

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("授权公版")

        assert resp.refusal is False, (
            f"license_type alone should satisfy auth gate, got refusal={resp.refusal}"
        )
        assert len(resp.evidence) > 0

    # ------------------------------------------------------------------
    # GenerationPipeline
    # ------------------------------------------------------------------

    async def test_generation_pipeline_no_auth_refused(self, db_session):
        """GenerationPipeline: public_domain + rag_enabled=True + no auth → EVIDENCE_GATE_REFUSAL."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "公版无授权", "public_domain", True,
                        "公版文献但没有授权依据的全文内容。",
                        auth_basis="")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("公版无授权", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" in result.answer, (
            f"Expected refusal, got: {result.answer[:200]}"
        )
        assert result.results == []
        assert result.citations == []

    async def test_generation_pipeline_license_type_only_allowed(self, db_session):
        """GenerationPipeline: license_type non-empty → still allowed."""
        from app.services.generation_service import GenerationPipeline

        doc_id, _ = await _seed_doc(db_session, "许可公版", "public_domain", True,
                                     "授权公版文献的全文内容。",
                                     auth_basis="")
        from app.models.document import Document as DocModel
        d = (await db_session.execute(
            select(DocModel).where(DocModel.id == doc_id)
        )).scalar_one()
        d.license_type = "CC-BY"
        await db_session.flush()

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("授权公版", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" not in result.answer, (
            f"license_type alone should satisfy auth gate, got: {result.answer[:200]}"
        )
        assert len(result.citations) >= 1

    # ------------------------------------------------------------------
    # API endpoint — /api/v1/ai/generate
    # ------------------------------------------------------------------

    async def test_api_generate_public_domain_no_auth_refused(self, api_db_session):
        """POST /api/v1/ai/generate: public_domain + rag_enabled=True + no auth → refusal."""
        import httpx
        from app.api.v1.ai import guard_ai_read
        from app.db.database import get_session
        from app.middleware.auth import get_current_user

        await _seed_doc(api_db_session, "无授权公版", "public_domain", True,
                        "公版文献但没有授权依据的全文内容。",
                        auth_basis="")
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
            resp = await client.post("/api/v1/ai/generate", json={"query": "授权公版", "top_k": 5})
            assert resp.status_code == 200
            data = resp.json()
            inner = data["data"]
            assert "EVIDENCE_GATE_REFUSAL" in inner["answer"], (
                f"Expected refusal for no-auth doc, got: {inner['answer'][:200]}"
            )
            assert inner["results"] == []
            assert inner["citations"] == []

    async def test_api_generate_license_type_only_allowed(self, api_db_session):
        """POST /api/v1/ai/generate: license_type alone → success."""
        import httpx
        from app.api.v1.ai import guard_ai_read
        from app.db.database import get_session
        from app.middleware.auth import get_current_user

        doc_id, _ = await _seed_doc(api_db_session, "许可公版", "public_domain", True,
                                     "授权公版文献的全文内容。",
                                     auth_basis="")
        from app.models.document import Document as DocModel
        d = (await api_db_session.execute(
            select(DocModel).where(DocModel.id == doc_id)
        )).scalar_one()
        d.license_type = "CC-BY"
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
            resp = await client.post("/api/v1/ai/generate", json={"query": "授权公版", "top_k": 5})
            assert resp.status_code == 200
            data = resp.json()
            inner = data["data"]
            assert "EVIDENCE_GATE_REFUSAL" not in inner["answer"], (
                f"license_type alone should satisfy auth gate, got: {inner['answer'][:200]}"
            )
            assert len(inner["citations"]) >= 1


# ============================================================
# Withdrawn-at pollution gate — Context 22 recheck
# ============================================================


@pytest.mark.anyio
class TestWithdrawnAtGate:
    """withdrawn_at != NULL + is_deleted=False + rag_enabled=True
    + all other fields compliant → must refusal."""

    # ------------------------------------------------------------------
    # EvidenceRAGService
    # ------------------------------------------------------------------

    async def test_evidence_rag_withdrawn_pollution_refused(self, db_session):
        """EvidenceRAGService: withdrawn doc with everything else clean → refusal=True, evidence=[]."""
        from app.services.evidence_rag_service import EvidenceRAGService

        await _seed_doc_withdrawn(db_session, "撤回文献", "public_domain", True,
                                   "已撤回但其他字段都合规的全文内容。",
                                   auth_basis="public domain")

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("已撤回")

        assert resp.refusal is True, (
            f"Withdrawn doc must be refused, got refusal={resp.refusal}"
        )
        assert resp.citations == []
        assert resp.evidence == []

    async def test_evidence_rag_clean_withdrawn_none_allowed(self, db_session):
        """EvidenceRAGService: withdrawn_at=NULL + all compliant → allowed."""
        from app.services.evidence_rag_service import EvidenceRAGService

        await _seed_doc(db_session, "正常公版", "public_domain", True,
                        "正常公版文献全文内容。",
                        auth_basis="public domain")

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("正常公版")

        assert resp.refusal is False, (
            f"Clean doc must be allowed, got refusal={resp.refusal}"
        )
        assert len(resp.evidence) > 0

    # ------------------------------------------------------------------
    # GenerationPipeline
    # ------------------------------------------------------------------

    async def test_generation_pipeline_withdrawn_pollution_refused(self, db_session):
        """GenerationPipeline: withdrawn doc → EVIDENCE_GATE_REFUSAL, results=[], citations=[]."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc_withdrawn(db_session, "撤回文献", "public_domain", True,
                                   "已撤回但其他字段都合规的全文内容。",
                                   auth_basis="public domain")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("已撤回", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" in result.answer, (
            f"Expected refusal for withdrawn doc, got: {result.answer[:200]}"
        )
        assert result.results == []
        assert result.citations == []
        assert result.metadata.error_code == "EMPTY_RETRIEVAL"

    async def test_generation_pipeline_clean_withdrawn_none_allowed(self, db_session):
        """GenerationPipeline: withdrawn_at=NULL + compliant → success with provenance."""
        from app.services.generation_service import GenerationPipeline

        await _seed_doc(db_session, "正常公版", "public_domain", True,
                        "皇甫谧编撰《针灸甲乙经》，系统整理魏晋以前针灸学成就。",
                        auth_basis="public domain",
                        source_url="https://ctext.org/jiayi")

        pipeline = GenerationPipeline(db_session)
        result = await pipeline.generate("皇甫谧", top_k=5)

        assert "EVIDENCE_GATE_REFUSAL" not in result.answer, (
            f"Clean doc must be allowed, got: {result.answer[:200]}"
        )
        assert result.metadata.citation_validation["is_valid"] is True
        assert len(result.citations) >= 1
        # provenance
        for c in result.citations:
            assert "source_url" in c

    # ------------------------------------------------------------------
    # API endpoint — /api/v1/ai/generate
    # ------------------------------------------------------------------

    async def test_api_generate_withdrawn_pollution_refused(self, api_db_session):
        """POST /api/v1/ai/generate: withdrawn doc → refusal envelope, results=[], citations=[]."""
        import httpx
        from app.api.v1.ai import guard_ai_read
        from app.db.database import get_session
        from app.middleware.auth import get_current_user

        await _seed_doc_withdrawn(api_db_session, "撤回文献", "public_domain", True,
                                   "已撤回但其他字段都合规的全文内容。",
                                   auth_basis="public domain")
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
            resp = await client.post("/api/v1/ai/generate", json={"query": "撤回文献", "top_k": 5})
            assert resp.status_code == 200
            data = resp.json()
            inner = data["data"]
            assert "EVIDENCE_GATE_REFUSAL" in inner["answer"], (
                f"Expected refusal for withdrawn doc, got: {inner['answer'][:200]}"
            )
            assert inner["results"] == []
            assert inner["citations"] == []

    async def test_api_generate_clean_withdrawn_none_allowed(self, api_db_session):
        """POST /api/v1/ai/generate: withdrawn_at=NULL → success with provenance."""
        import httpx
        from app.api.v1.ai import guard_ai_read
        from app.db.database import get_session
        from app.middleware.auth import get_current_user

        await _seed_doc(api_db_session, "正常公版", "public_domain", True,
                        "皇甫谧编撰《针灸甲乙经》，系统整理魏晋以前针灸学成就。",
                        auth_basis="public domain",
                        source_url="https://ctext.org/jiayi")
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
                f"Clean doc must succeed, got: {inner['answer'][:200]}"
            )
            assert len(inner["citations"]) >= 1
            assert len(inner["results"]) >= 1


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
    from app.core.error_handlers import register_error_handlers
    from app.middleware.request_id import RequestIDMiddleware
    from fastapi import FastAPI

    app = FastAPI(debug=False)
    app.add_middleware(RequestIDMiddleware)
    register_error_handlers(app)
    from app.api.v1 import router as v1_router
    app.include_router(v1_router)
    return app


@pytest.fixture
async def api_db_session():
    """In-memory SQLite session for ASGI tests."""
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

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
    from app.api.v1.ai import guard_ai_read
    from app.db.database import get_session
    from app.middleware.auth import get_current_user

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
    from app.api.v1.ai import guard_ai_read
    from app.db.database import get_session
    from app.middleware.auth import get_current_user

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
