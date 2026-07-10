"""
Tests: RAG copyright filter — forbidden statuses excluded from evidence retrieval.

Covers:
  - commercial_restricted documents excluded from RAG
  - pirated documents excluded
  - forbidden_fulltext excluded
  - Only public_domain, open_access, licensed, user_uploaded_with_permission
    with rag_enabled=true enter RAG
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


def _make_doc(
    title: str,
    copyright_status: str,
    rag_enabled: bool = False,
    authorization_basis: str = "",
    source_url: str = "",
) -> Document:
    """Factory for test documents."""
    return Document(
        title=title,
        content_text=f"{title} 全文内容。用于测试版权过滤。",
        copyright_status=copyright_status,
        authorization_basis=authorization_basis,
        rag_enabled=rag_enabled,
        source_url=source_url,
    )


def _make_chunk(doc_id: str, title: str, index: int = 0) -> DocumentChunk:
    """Factory for test chunks."""
    return DocumentChunk(
        document_id=doc_id,
        chunk_index=index,
        content=f"{title} 全文内容。用于测试版权过滤。",
        token_count=20,
        paragraph_index=0,
        evidence_weight="primary",
    )


# ============================================================
# Tests: copyright filter
# ============================================================


@pytest.mark.anyio
class TestCopyrightFilter:
    """Documents with forbidden copyright statuses are excluded from RAG."""

    async def test_commercial_restricted_excluded(self, db_session):
        """commercial_restricted docs excluded even if rag_enabled=True (polluted state)."""
        from app.services.evidence_rag_service import EvidenceRAGService

        # Commercial doc with rag_enabled=True — polluted, must still be excluded
        doc = _make_doc("商业数据库文献", "commercial_restricted", rag_enabled=True)
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "商业数据库文献"))
        await db_session.flush()

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("商业数据库")

        # Must not find commercial_restricted content even with rag_enabled=True
        assert resp.refusal is True or all(
            "商业数据库" not in e.content for e in resp.evidence
        ), "commercial_restricted documents must be excluded from RAG even if rag_enabled=True"

    async def test_pirated_excluded(self, db_session):
        """Pirated documents excluded — even with rag_enabled=True (polluted state)."""
        doc = _make_doc("盗版文献", "pirated", rag_enabled=True)
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "盗版文献"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("盗版")

        assert resp.refusal is True or all(
            "盗版" not in e.content for e in resp.evidence
        ), "pirated documents must be excluded even with rag_enabled=True"

    async def test_forbidden_fulltext_excluded(self, db_session):
        """forbidden_fulltext excluded even with rag_enabled=True (polluted state)."""
        doc = _make_doc("禁止全文", "forbidden_fulltext", rag_enabled=True)
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "禁止全文"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("禁止")

        assert resp.refusal is True or all(
            "禁止全文" not in e.content for e in resp.evidence
        ), "forbidden_fulltext must be excluded even with rag_enabled=True"

    async def test_unknown_copyright_excluded(self, db_session):
        """unknown copyright status excluded — even with rag_enabled=True (polluted state)."""
        doc = _make_doc("未知版权", "unknown", rag_enabled=True)
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "未知版权"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("未知")

        assert resp.refusal is True or all(
            "未知版权" not in e.content for e in resp.evidence
        ), "unknown copyright must be excluded even with rag_enabled=True"


@pytest.mark.anyio
class TestAllowedCopyright:
    """Allowed copyright statuses enter RAG with rag_enabled=true."""

    async def test_public_domain_included(self, db_session):
        """public_domain + rag_enabled=true → searchable."""
        doc = _make_doc(
            "公版文献", "public_domain", rag_enabled=True,
            authorization_basis="public domain",
        )
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "公版文献"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("公版")

        assert resp.refusal is False
        titles = {e.document_title for e in resp.evidence}
        assert "公版文献" in titles

    async def test_open_access_included(self, db_session):
        """open_access + rag_enabled=true → searchable."""
        doc = _make_doc(
            "开放获取文献", "open_access", rag_enabled=True,
            authorization_basis="CC-BY 4.0",
        )
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "开放获取文献"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("开放获取")

        assert resp.refusal is False
        titles = {e.document_title for e in resp.evidence}
        assert "开放获取文献" in titles

    async def test_licensed_included(self, db_session):
        """licensed + rag_enabled=true → searchable."""
        doc = _make_doc(
            "授权文献", "licensed", rag_enabled=True,
            authorization_basis="agreement-2024-001",
        )
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "授权文献"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("授权")

        assert resp.refusal is False
        titles = {e.document_title for e in resp.evidence}
        assert "授权文献" in titles

    async def test_user_uploaded_with_permission_included(self, db_session):
        """user_uploaded_with_permission + rag_enabled=true → searchable."""
        doc = _make_doc(
            "用户上传文献", "user_uploaded_with_permission", rag_enabled=True,
            authorization_basis="user confirmed ownership",
        )
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "用户上传文献"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("用户上传")

        assert resp.refusal is False
        titles = {e.document_title for e in resp.evidence}
        assert "用户上传文献" in titles

    async def test_allowed_without_rag_enabled_excluded(self, db_session):
        """public_domain but rag_enabled=false → excluded."""
        doc = _make_doc(
            "未启用公版", "public_domain", rag_enabled=False,
            authorization_basis="public domain",
        )
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "未启用公版"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("未启用")

        for e in resp.evidence:
            assert "未启用公版" not in e.content, (
                "public_domain with rag_enabled=false must be excluded"
            )


@pytest.mark.anyio
class TestCommercialMetadataExclusion:
    """Business database metadata records must not enter full-text RAG."""

    async def test_commercial_metadata_not_in_rag(self, db_session):
        """Commercial source with metadata_only cannot be retrieved — even with rag_enabled=True."""
        doc = _make_doc(
            "PubMed 文献", "metadata_only", rag_enabled=True,
        )
        db_session.add(doc)
        await db_session.flush()
        db_session.add(_make_chunk(doc.id, "PubMed 文献"))
        await db_session.flush()

        from app.services.evidence_rag_service import EvidenceRAGService

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("PubMed")

        assert resp.refusal is True or all(
            "PubMed" not in e.content for e in resp.evidence
        ), "metadata_only must be excluded from RAG even with rag_enabled=True"

    async def test_multiple_forbidden_statuses_all_excluded(self, db_session):
        """Mix of forbidden statuses with rag_enabled=True (polluted state) — all excluded."""
        forbidden = [
            ("商业1", "commercial_restricted"),
            ("盗版1", "pirated"),
            ("禁止1", "forbidden_fulltext"),
            ("未知1", "unknown"),
        ]
        from app.services.evidence_rag_service import EvidenceRAGService

        for title, cs in forbidden:
            doc = _make_doc(title, cs, rag_enabled=True)
            db_session.add(doc)
            await db_session.flush()
            db_session.add(_make_chunk(doc.id, title))
            await db_session.flush()

        # Also add one allowed doc
        allowed = _make_doc(
            "正常文献", "public_domain", rag_enabled=True,
            authorization_basis="public domain",
        )
        db_session.add(allowed)
        await db_session.flush()
        db_session.add(_make_chunk(allowed.id, "正常文献"))
        await db_session.flush()

        svc = EvidenceRAGService(db_session)
        resp = await svc.query("文献")

        # All evidence must be from the allowed doc
        for e in resp.evidence:
            assert e.document_title == "正常文献", (
                f"Only allowed docs should appear, got: {e.document_title}"
            )
