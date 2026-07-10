"""
Full-text compliance tests (Context 21) — copyright gate, audit, checksum, withdrawal.

Covers all 6 blocking items from the Codex review.
"""
from __future__ import annotations

import hashlib

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.fulltext_ingestion_audit import FulltextIngestionAudit


@pytest.fixture
async def db_session():
    """In-memory SQLite session with full schema including compliance columns."""
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


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# ============================================================
# Blocker 1: copyright_status gate — reject via IngestionService
# ============================================================


@pytest.mark.anyio
class TestCopyrightGateRejection:
    """Tests that copyright_status=unknown, forbidden_fulltext,
    and metadata_only block full-text storage."""

    async def test_unknown_copyright_rejected_no_chunks(self, db_session):
        """copyright_status=unknown + text → rejected, 0 chunks."""
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError, match="copyright_status=unknown"):
            await svc.ingest_text(
                title="Unknown Copyright Paper",
                text="Some full-text content that should be rejected.",
                metadata={
                    "copyright_status": "unknown",
                    "source_url": "https://example.com/unknown",
                },
            )
        await db_session.flush()

        # No document should have been created
        docs = (await db_session.execute(
            select(Document).where(Document.title == "Unknown Copyright Paper")
        )).scalars().all()
        assert len(docs) == 0

        # No chunks at all
        count = (await db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        assert count == 0

        # Audit record exists
        audits = (await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.action == "reject"
            )
        )).scalars().all()
        assert len(audits) >= 1
        assert audits[0].copyright_status == "unknown"

    async def test_forbidden_fulltext_rejected_no_chunks(self, db_session):
        """forbidden_fulltext=true + text → rejected, 0 chunks."""
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError, match="forbidden_fulltext"):
            await svc.ingest_text(
                title="Forbidden Paper",
                text="FORBIDDEN_FULLTEXT_SENTINEL 未确认版权全文内容，理论上不应进入 RAG。",
                metadata={
                    "source_url": "https://commercial.example/paid",
                    "copyright_status": "unknown",
                    "forbidden_fulltext": True,
                },
            )
        await db_session.flush()

        count = (await db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        assert count == 0

        # Audit: action=reject
        audits = (await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.action == "reject"
            )
        )).scalars().all()
        assert len(audits) >= 1

    async def test_metadata_only_rejected_no_chunks(self, db_session):
        """metadata_only=true + text → rejected, 0 chunks."""
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError, match="metadata_only"):
            await svc.ingest_text(
                title="Metadata Only Paper",
                text="Should not be stored.",
                metadata={"copyright_status": "metadata_only"},
            )
        await db_session.flush()

        count = (await db_session.execute(
            text("SELECT COUNT(*) FROM document_chunks")
        )).scalar_one()
        assert count == 0

        audits = (await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.action == "skip"
            )
        )).scalars().all()
        assert len(audits) >= 1

    async def test_missing_copyright_status_rejected(self, db_session):
        """No copyright_status → rejected (default-deny)."""
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError, match="copyright_status"):
            await svc.ingest_text(
                title="No Copyright Info",
                text="Some text without compliance metadata.",
                metadata={},
            )

    async def test_in_copyright_rejected(self, db_session):
        """copyright_status=commercial_restricted → rejected."""
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError):
            await svc.ingest_text(
                title="Commercial Paper",
                text="Full text here.",
                metadata={"copyright_status": "commercial_restricted"},
            )

    async def test_pirated_rejected(self, db_session):
        """copyright_status=pirated → rejected."""
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError):
            await svc.ingest_text(
                title="Pirated Paper",
                text="Pirated full text.",
                metadata={"copyright_status": "pirated"},
            )


# ============================================================
# Blocker 2: Allowed copyright — success path with checksum
# ============================================================


@pytest.mark.anyio
class TestCopyrightGateSuccess:
    """Tests that public_domain, open_access, licensed with authorization
    succeed and produce chunks + checksum."""

    async def test_public_domain_success_with_checksum(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "皇甫谧编撰《针灸甲乙经》。\n\n系统整理了经络学说。"

        result = await svc.ingest_text(
            title="Public Domain Work",
            text=text_content,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "expired copyright (pre-1928)",
                "source_url": "https://ctext.org/huangfu-mi",
                "source_name": "ctext",
            },
        )
        await db_session.flush()

        assert result.document_id is not None
        assert result.chunk_count > 0
        assert result.checksum == _sha256(text_content)

        # Verify DB state
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.copyright_status == "public_domain"
        assert doc.authorization_basis == "expired copyright (pre-1928)"
        assert doc.content_checksum == _sha256(text_content)
        assert doc.content_text == text_content

        chunks = (await db_session.execute(
            select(DocumentChunk).where(
                DocumentChunk.document_id == result.document_id
            )
        )).scalars().all()
        assert len(chunks) > 0

        # Checksum is recomputable from stored content
        assert doc.content_checksum == _sha256(doc.content_text)

    async def test_open_access_success(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "Open access research about acupuncture meridians."

        result = await svc.ingest_text(
            title="Open Access Paper",
            text=text_content,
            metadata={
                "copyright_status": "open_access",
                "license_type": "CC-BY",
                "authorization_basis": "https://creativecommons.org/licenses/by/4.0/",
                "source_url": "https://example.com/oa-paper",
            },
        )
        await db_session.flush()

        assert result.chunk_count > 0
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.copyright_status == "open_access"
        assert doc.content_checksum == _sha256(text_content)

    async def test_licensed_success(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "Licensed content under institutional agreement."

        result = await svc.ingest_text(
            title="Licensed Paper",
            text=text_content,
            metadata={
                "copyright_status": "licensed",
                "license_type": "custom",
                "authorization_basis": "Institutional agreement #2026-007",
                "source_url": "https://example.com/licensed",
            },
        )
        assert result.chunk_count > 0
        assert result.checksum == _sha256(text_content)

    async def test_user_uploaded_with_permission_success(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "User-uploaded content with confirmed permission."

        result = await svc.ingest_text(
            title="User Uploaded Paper",
            text=text_content,
            metadata={
                "copyright_status": "user_uploaded_with_permission",
                "authorization_basis": "User confirmed ownership via upload form #42",
            },
        )
        assert result.chunk_count > 0

    async def test_public_domain_without_authorization_basis_rejected(self, db_session):
        """public_domain requires authorization_basis or license_type."""
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError, match="authorization_basis"):
            await svc.ingest_text(
                title="PD Without Basis",
                text="Some text.",
                metadata={
                    "copyright_status": "public_domain",
                    # missing authorization_basis / license_type
                },
            )

    async def test_licensed_success_with_only_license_type(self, db_session):
        """license_type alone satisfies the authorization_basis requirement."""
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "Creative Commons licensed content."

        result = await svc.ingest_text(
            title="CC Paper",
            text=text_content,
            metadata={
                "copyright_status": "licensed",
                "license_type": "CC-BY-NC-ND",
            },
        )
        assert result.chunk_count > 0


# ============================================================
# Blocker 3: Persistent audit log
# ============================================================


@pytest.mark.anyio
class TestAuditLogPersistence:
    """Every ingest/reject/skip/withdraw produces a durable audit record."""

    async def test_audit_record_on_success(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="Audit Success",
            text="Text for audit test.",
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "public domain",
                "source_url": "https://example.com/audit",
                "source_name": "test_source",
            },
        )
        await db_session.flush()

        audits = (await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.result_entity_id == result.document_id
            )
        )).scalars().all()
        assert len(audits) >= 1
        a = audits[0]
        assert a.action == "fulltext_ingest"
        assert a.status == "success"
        assert a.checksum == result.checksum
        assert a.copyright_status == "public_domain"
        assert a.result_entity_type == "document"

    async def test_audit_record_on_reject(self, db_session):
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError):
            await svc.ingest_text(
                title="Audit Reject",
                text="Forbidden text.",
                metadata={
                    "copyright_status": "forbidden_fulltext",
                    "source_url": "https://evil.example/paid",
                    "forbidden_fulltext": True,
                },
            )
        await db_session.flush()

        audits = (await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.action == "reject"
            )
        )).scalars().all()
        assert len(audits) >= 1
        a = audits[0]
        assert a.status == "rejected"
        assert a.reject_reason is not None
        assert "forbidden_fulltext" in a.reject_reason.lower()

    async def test_audit_record_on_skip(self, db_session):
        from app.services.ingestion import IngestionService, FulltextRejectedError

        svc = IngestionService(db_session)
        with pytest.raises(FulltextRejectedError):
            await svc.ingest_text(
                title="Audit Skip",
                text="Skipped text.",
                metadata={
                    "copyright_status": "metadata_only",
                    "source_url": "https://example.com/skip",
                },
            )
        await db_session.flush()

        audits = (await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.action == "skip"
            )
        )).scalars().all()
        assert len(audits) >= 1
        a = audits[0]
        assert a.status == "skipped"
        assert a.skipped_reason is not None

    async def test_audit_record_on_withdraw(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title="To Be Withdrawn",
            text="Content that will be withdrawn.",
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "public domain",
            },
        )
        await db_session.flush()

        await svc.withdraw_document(
            document_id=result.document_id,
            reason="Retraction: source removed",
            actor_id="admin-1",
        )
        await db_session.flush()

        audits = (await db_session.execute(
            select(FulltextIngestionAudit).where(
                FulltextIngestionAudit.action == "withdraw"
            )
        )).scalars().all()
        assert len(audits) >= 1
        a = audits[0]
        assert a.status == "withdrawn"
        assert a.result_entity_id == result.document_id
        assert a.reject_reason == "Retraction: source removed"
        assert a.actor_id == "admin-1"


# ============================================================
# Blocker 4: Checksum persistence and recomputability
# ============================================================


@pytest.mark.anyio
class TestChecksum:
    async def test_checksum_persisted_on_document(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "测试全文内容 checksum 持久化。"
        expected = _sha256(text_content)

        result = await svc.ingest_text(
            title="Checksum Test",
            text=text_content,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "public domain pre-1928",
            },
        )
        assert result.checksum == expected

        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        assert doc.content_checksum == expected

    async def test_checksum_recomputable(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "第一段内容。\n\n第二段内容。\n\n第三段内容。"

        result = await svc.ingest_text(
            title="Recomputable Test",
            text=text_content,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "public domain",
            },
        )

        # Recompute from stored content_text
        doc = (await db_session.execute(
            select(Document).where(Document.id == result.document_id)
        )).scalar_one()
        recomputed = _sha256(doc.content_text)
        assert recomputed == doc.content_checksum
        assert recomputed == result.checksum

    async def test_checksum_different_for_different_content(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        r1 = await svc.ingest_text(
            title="Doc A",
            text="Content A.",
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "pd",
            },
        )
        r2 = await svc.ingest_text(
            title="Doc B",
            text="Content B.",
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "pd",
            },
        )
        assert r1.checksum != r2.checksum

    async def test_checksum_stable_deterministic(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "Deterministic checksum content."

        r1 = await svc.ingest_text(
            title="Deterministic A",
            text=text_content,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "pd",
            },
        )
        r2 = await svc.ingest_text(
            title="Deterministic B",
            text=text_content,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "pd",
            },
        )
        assert r1.checksum == r2.checksum


# ============================================================
# Blocker 5: Withdrawal removes from retrieval/RAG
# ============================================================


@pytest.mark.anyio
class TestWithdrawal:
    async def _ingest_and_verify(self, db_session, title, text):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        result = await svc.ingest_text(
            title=title,
            text=text,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "public domain",
            },
        )
        await db_session.flush()
        return svc, result

    async def test_withdraw_soft_deletes_document_and_chunks(self, db_session):
        svc, result = await self._ingest_and_verify(
            db_session, "Withdraw Test", "Content to be withdrawn.\n\nSecond paragraph."
        )
        doc_id = result.document_id
        chunk_count = result.chunk_count
        assert chunk_count > 0

        await svc.withdraw_document(doc_id, reason="Test withdrawal")
        await db_session.flush()

        # Document is soft-deleted — get_by_id returns None (filters is_deleted=False)
        from app.models.document import Document as DocModel
        doc = (await db_session.execute(
            select(DocModel).where(DocModel.id == doc_id)
        )).scalar_one_or_none()
        assert doc is not None
        assert doc.is_deleted is True
        assert doc.withdrawn_at is not None
        assert doc.withdraw_reason == "Test withdrawal"
        assert doc.rag_enabled is False

        # All chunks are soft-deleted
        chunks = (await db_session.execute(
            select(DocumentChunk).where(
                DocumentChunk.document_id == doc_id
            )
        )).scalars().all()
        assert len(chunks) > 0
        for ch in chunks:
            assert ch.is_deleted is True

    async def test_withdrawn_document_not_in_retrieval(self, db_session):
        from app.services.retrieval import RetrievalService

        svc, result = await self._ingest_and_verify(
            db_session,
            "Withdrawn Retrieval Test",
            "WITHDRAWN_SENTINEL_TOKEN 第一段。\n\n第二段包含独特标记的内容。",
        )

        # Pre-withdrawal: retrieval finds it
        rsvc = RetrievalService(db_session)
        before = await rsvc.search("WITHDRAWN_SENTINEL_TOKEN", top_k=5)
        assert before.total >= 1
        assert any("WITHDRAWN_SENTINEL_TOKEN" in r.content for r in before.results)

        # Withdraw
        await svc.withdraw_document(result.document_id, reason="Test")
        await db_session.flush()

        # Post-withdrawal: retrieval does NOT find it
        after = await rsvc.search("WITHDRAWN_SENTINEL_TOKEN", top_k=5)
        for r in after.results:
            assert r.document_id != result.document_id, (
                f"Withdrawn document {result.document_id} still in retrieval"
            )

    async def test_withdrawn_document_not_in_corpus_sha256(self, db_session):
        from app.services.academic_rag_service import AcademicRAGService

        svc, result = await self._ingest_and_verify(
            db_session,
            "Corpus SHA Withdrawal Test",
            "CORPUS_SENTINEL 一段独特的测试全文内容用于语料库校验。",
        )

        rag = AcademicRAGService(db_session)
        sha_before = await rag._compute_corpus_sha256()

        # Withdraw
        await svc.withdraw_document(result.document_id, reason="Test")
        await db_session.flush()

        sha_after = await rag._compute_corpus_sha256()
        assert sha_before != sha_after, (
            "corpus_sha256 must change after withdrawal"
        )

    async def test_withdraw_only_affects_target_document(self, db_session):
        from app.services.retrieval import RetrievalService

        svc, target = await self._ingest_and_verify(
            db_session, "Target", "TARGET_SENTINEL 目标文献内容。"
        )
        _, other = await self._ingest_and_verify(
            db_session, "Other", "OTHER_SENTINEL 另一篇文献内容保持不变。"
        )
        await db_session.flush()

        # Withdraw only target
        await svc.withdraw_document(target.document_id, reason="Test")
        await db_session.flush()

        rsvc = RetrievalService(db_session)
        # Target is gone
        target_result = await rsvc.search("TARGET_SENTINEL", top_k=5)
        for r in target_result.results:
            assert r.document_id != target.document_id

        # Other still visible
        other_result = await rsvc.search("OTHER_SENTINEL", top_k=5)
        assert other_result.total >= 1
        assert any(r.document_id == other.document_id for r in other_result.results)


# ============================================================
# Blocker 6: API schema fields
# ============================================================


class TestIngestTextRequestSchema:
    def test_schema_has_compliance_fields(self):
        from app.schemas.chunk_search import IngestTextRequest

        # Default values
        req = IngestTextRequest(title="Test", text="Content")
        assert req.copyright_status == "unknown"
        assert req.license_type is None
        assert req.authorization_basis is None
        assert req.source_url is None
        assert req.source_name is None
        assert req.metadata_only is False
        assert req.forbidden_fulltext is False

    def test_schema_forbids_extra_fields(self):
        from app.schemas.chunk_search import IngestTextRequest

        with pytest.raises(Exception):
            IngestTextRequest(
                title="Test",
                text="Content",
                unknown_field="should fail",
            )

    def test_schema_accepts_all_compliance_fields(self):
        from app.schemas.chunk_search import IngestTextRequest

        req = IngestTextRequest(
            title="Test",
            text="Content",
            copyright_status="public_domain",
            license_type="CC-BY",
            authorization_basis="https://creativecommons.org/licenses/by/4.0/",
            source_url="https://example.com/source",
            source_name="test_source",
            metadata_only=False,
            forbidden_fulltext=False,
        )
        assert req.copyright_status == "public_domain"
        assert req.license_type == "CC-BY"
        assert req.authorization_basis == "https://creativecommons.org/licenses/by/4.0/"


# ============================================================
# IngestionResult checksum field
# ============================================================


@pytest.mark.anyio
class TestIngestionResultCompliance:
    async def test_result_has_checksum(self, db_session):
        from app.services.ingestion import IngestionService

        svc = IngestionService(db_session)
        text_content = "Checksum in result object."
        result = await svc.ingest_text(
            title="Result Checksum",
            text=text_content,
            metadata={
                "copyright_status": "public_domain",
                "authorization_basis": "pd",
            },
        )
        assert result.checksum == _sha256(text_content)
        assert len(result.checksum) == 64  # SHA-256 hex


# ============================================================
# Models: compliance fields exist
# ============================================================


class TestDocumentModelCompliance:
    def test_document_has_compliance_columns(self):
        assert hasattr(Document, "copyright_status")
        assert hasattr(Document, "license_type")
        assert hasattr(Document, "authorization_basis")
        assert hasattr(Document, "review_status")
        assert hasattr(Document, "reviewed_by")
        assert hasattr(Document, "reviewed_at")
        assert hasattr(Document, "rag_enabled")
        assert hasattr(Document, "content_checksum")
        assert hasattr(Document, "source_name")
        assert hasattr(Document, "withdrawn_at")
        assert hasattr(Document, "withdraw_reason")

    def test_audit_model_has_required_columns(self):
        assert hasattr(FulltextIngestionAudit, "action")
        assert hasattr(FulltextIngestionAudit, "status")
        assert hasattr(FulltextIngestionAudit, "source_url")
        assert hasattr(FulltextIngestionAudit, "source_name")
        assert hasattr(FulltextIngestionAudit, "copyright_status")
        assert hasattr(FulltextIngestionAudit, "authorization_basis")
        assert hasattr(FulltextIngestionAudit, "license_type")
        assert hasattr(FulltextIngestionAudit, "review_status")
        assert hasattr(FulltextIngestionAudit, "reviewed_by")
        assert hasattr(FulltextIngestionAudit, "reviewed_at")
        assert hasattr(FulltextIngestionAudit, "checksum")
        assert hasattr(FulltextIngestionAudit, "result_entity_type")
        assert hasattr(FulltextIngestionAudit, "result_entity_id")
        assert hasattr(FulltextIngestionAudit, "reject_reason")
        assert hasattr(FulltextIngestionAudit, "skipped_reason")
        assert hasattr(FulltextIngestionAudit, "actor_id")
        assert hasattr(FulltextIngestionAudit, "details")
