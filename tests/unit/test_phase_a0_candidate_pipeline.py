"""Phase A0 — candidate extraction pipeline: 12 hard acceptance gates.

Loads the ``gold_benchmark_v03.json`` baseline and exercises the full
approve-and-publish contract across SQLite (grounding, triggers, rollback) and
real PostgreSQL (null-safe trigger, pessimistic-lock concurrency).

Tests 9 and 10 are skipped automatically when no PostgreSQL test database is
reachable (``POSTGRES_TEST_DB``, default ``hfb_test``).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.db import audit_triggers
from app.db.base import Base
from app.models.academic_evidence import Evidence, SourceRef
from app.models.book import Book
from app.models.candidate_audit_log import CandidateAuditLog
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.models.chapter import Chapter
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.passage import Passage
from app.models.user import User
from app.models.version import Version
from app.models.workspace import ResearchSession
from app.services.candidate_extraction_service import (
    CandidatePublishUnitOfWork,
    GroundingDriftException,
)

# Reuse the SQLite session fixture (conftest_db is not auto-discovered).
from tests.conftest_db import db_session  # noqa: F401

# ---------------------------------------------------------------------------
# Gold baseline
# ---------------------------------------------------------------------------

GOLD_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "gold_benchmark_v03.json"
GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

CANON = GOLD["canonical_body_text"]
CANON_SHA = GOLD["canonical_body_text_sha256"]
SR_URL = "https://zh.wikisource.org/wiki/鍼灸甲乙經_(四庫全書本)/卷03"

# Candidate extraction anchors: first 80 chars of the canonical body.
EXACT = CANON[:80]
START_CHAR = 0
END_CHAR = len(EXACT)

OWNER_ID = "owner-a0"

DEFAULT_PAYLOAD = {
    "description": "卷三腧穴定位证据",
    "evidence_level": 3,
    "quote_text": None,
    "note": "gold_benchmark_v03 基线",
}


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# Sanity: the declared baseline hash must match the canonical body bytes.
assert _sha256(CANON) == CANON_SHA, "gold_benchmark_v03 canonical hash mismatch"


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


async def build_world(
    session: AsyncSession,
    *,
    owner_id: str = OWNER_ID,
    chunk_content: str = CANON,
    passage_version_id: str = "ver-a0",
    with_source_ref: bool = True,
) -> dict:
    """Build the full FK chain required by the candidate pipeline."""
    owner = User(
        id=owner_id,
        username=f"u-{owner_id}",
        email=f"{owner_id}@test.com",
        hashed_password="x",
        is_active=True,
        is_superuser=True,
    )
    session.add(owner)
    book = Book(id="book-a0", title="鍼灸甲乙經")
    session.add(book)
    chapter = Chapter(id="chap-a0", book_id="book-a0", title="卷三", order=0)
    session.add(chapter)
    version = Version(id="ver-a0", book_id="book-a0", version_name="四庫全書本")
    session.add(version)
    passage = Passage(
        id="pas-a0",
        chapter_id="chap-a0",
        version_id=passage_version_id,
        content_text=chunk_content,
        order=0,
    )
    session.add(passage)
    doc = Document(id="doc-a0", title="鍼灸甲乙經 卷三", language="zh")
    session.add(doc)
    source_ref = None
    if with_source_ref:
        source_ref = SourceRef(
            id="sr-a0", title="四庫全書本 鍼灸甲乙經 卷三", url=SR_URL
        )
        session.add(source_ref)
    chunk = DocumentChunk(
        id="chunk-a0",
        document_id="doc-a0",
        passage_id="pas-a0",
        chunk_index=0,
        content=chunk_content,
        page_image_hash_alg="sha256",
    )
    session.add(chunk)
    research_session = ResearchSession(id="sess-a0", user_id=owner_id, title="A0")
    session.add(research_session)
    await session.flush()
    return {
        "owner": owner,
        "book": book,
        "chapter": chapter,
        "version": version,
        "passage": passage,
        "doc": doc,
        "source_ref": source_ref,
        "chunk": chunk,
        "session": research_session,
    }


async def make_candidate(
    session: AsyncSession,
    *,
    chunk_id: str = "chunk-a0",
    session_id: str = "sess-a0",
    creator_id: str = OWNER_ID,
    version_id: str = "ver-a0",
    expected_sha: str = CANON_SHA,
    start_char: int = START_CHAR,
    end_char: int = END_CHAR,
    exact_text: str = EXACT,
    ai_model: str = "hfb-test-model",
) -> CandidateExtraction:
    """Insert a pending candidate grounded on the gold baseline."""
    candidate = CandidateExtraction(
        session_id=session_id,
        created_by=creator_id,
        chunk_id=chunk_id,
        version_id=version_id,
        expected_chunk_sha256=expected_sha,
        expected_nfc_sha256=expected_sha,
        unicode_normalization="NFC",
        start_char=start_char,
        end_char=end_char,
        exact_text=exact_text,
        input_snapshot={
            "source_uri": SR_URL,
            "revid": GOLD["revid"],
            "governance_mode": GOLD["governance_mode"],
        },
        page_image_hash=None,
        page_image_hash_alg="sha256",
        extraction_type="proposed_evidence",
        extracted_payload=DEFAULT_PAYLOAD,
        extractor_name="hfb-test-extractor",
        ai_model=ai_model,
        ai_version="1.0.0",
        prompt_version="p1",
        processing_time=0.01,
        confidence=0.99,
    )
    session.add(candidate)
    await session.flush()
    return candidate


async def _reviewer(session: AsyncSession, user_id: str = OWNER_ID) -> User:
    return await session.get(User, user_id)


def _make_uow(session: AsyncSession) -> CandidatePublishUnitOfWork:
    factory = async_sessionmaker(
        session.bind, class_=AsyncSession, expire_on_commit=False
    )
    return CandidatePublishUnitOfWork(factory)


async def _publish(
    session: AsyncSession, candidate_id: str, reviewer_id: str, session_id: str
) -> Evidence:
    return await _make_uow(session).publish(candidate_id, reviewer_id, session_id)


async def _install_sqlite_triggers(session: AsyncSession) -> None:
    await session.execute(text(audit_triggers.SQLITE_NO_DELETE_SQL))
    await session.execute(text(audit_triggers.SQLITE_NO_UPDATE_SQL))
    await session.execute(text(audit_triggers.SQLITE_NO_ORPHAN_INSERT_SQL))


# ---------------------------------------------------------------------------
# PostgreSQL fixture (tests 9 & 10)
# ---------------------------------------------------------------------------


def _pg_test_url() -> str:
    db = os.environ.get("POSTGRES_TEST_DB", "hfb_test")
    return (
        f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db}"
    )


@pytest_asyncio.fixture
async def pg_world() -> AsyncSession:
    """Yield a Postgres-backed session (tables + triggers created fresh)."""
    engine = create_async_engine(_pg_test_url())
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 — skip when PG is unavailable
        await engine.dispose()
        pytest.skip(f"PostgreSQL unavailable: {exc}")

    # Reset the whole schema each test. This also clears any migration-created
    # views/objects (e.g. academic_edges) that would otherwise break drop_all.
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.run_sync(Base.metadata.create_all)
        await audit_triggers.install_audit_log_triggers(conn)

    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with factory() as session:
            yield {"session": session, "factory": factory}
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# Gates 1–2: isolation & authorization
# ---------------------------------------------------------------------------


class TestIsolationAndAuthorization:
    @pytest.mark.asyncio
    async def test_cross_session_isolation_404(self, db_session: AsyncSession) -> None:
        await build_world(db_session)
        candidate = await make_candidate(db_session)
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await _publish(
                db_session, candidate.id, reviewer.id, "other-session"
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_private_document_session_isolation_404(
        self, db_session: AsyncSession
    ) -> None:
        """A candidate on a private document bound to another session → 404."""
        world = await build_world(db_session)
        world["doc"].session_id = "other-session"
        await db_session.flush()
        candidate = await make_candidate(db_session)
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_cross_private_document_uploader_isolation_404(
        self, db_session: AsyncSession
    ) -> None:
        """A candidate on a private document uploaded by another user → 404."""
        world = await build_world(db_session)
        db_session.add(
            User(
                id="other-user-a0",
                username="other-user",
                email="other@test.com",
                hashed_password="x",
                is_active=True,
                is_superuser=False,
            )
        )
        await db_session.flush()
        world["doc"].uploaded_by = "other-user-a0"
        await db_session.flush()
        candidate = await make_candidate(db_session)
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )
        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Gates 3–6: grounding drift
# ---------------------------------------------------------------------------


class TestGroundingDrift:
    @pytest.mark.asyncio
    async def test_subtext_match_but_chunk_sha256_changed_drift(
        self, db_session: AsyncSession
    ) -> None:
        world = await build_world(db_session)
        candidate = await make_candidate(db_session)
        # Append outside the [start, end] span: substring still matches, but
        # the overall chunk SHA-256 changes.
        world["chunk"].content = CANON + "（篡改）"
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(GroundingDriftException):
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )
        await db_session.refresh(candidate)
        assert candidate.status == CandidateStatus.DRIFT_INVALID

    @pytest.mark.asyncio
    async def test_chunk_passage_version_mismatch_rejection(
        self, db_session: AsyncSession
    ) -> None:
        world = await build_world(db_session)
        db_session.add(Version(id="ver-other", book_id="book-a0", version_name="异本"))
        await db_session.flush()
        candidate = await make_candidate(db_session, version_id="ver-other")
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(GroundingDriftException):
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )
        await db_session.refresh(candidate)
        assert candidate.status == CandidateStatus.DRIFT_INVALID
        assert world["passage"].version_id == "ver-a0"

    @pytest.mark.asyncio
    async def test_missing_passage_id_rejection(
        self, db_session: AsyncSession
    ) -> None:
        world = await build_world(db_session)
        world["chunk"].passage_id = None
        await db_session.flush()
        candidate = await make_candidate(db_session)
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(GroundingDriftException):
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )
        await db_session.refresh(candidate)
        assert candidate.status == CandidateStatus.DRIFT_INVALID

    @pytest.mark.asyncio
    async def test_context_safe_drift_commit_without_exception_rollback(
        self, db_session: AsyncSession
    ) -> None:
        world = await build_world(db_session)
        candidate = await make_candidate(db_session)
        world["chunk"].content = CANON + "X"
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(GroundingDriftException):
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )

        # Drift must be COMMITTED (visible), not rolled back.
        await db_session.refresh(candidate)
        assert candidate.status == CandidateStatus.DRIFT_INVALID

        audit_rows = (
            await db_session.execute(
                select(CandidateAuditLog).where(
                    CandidateAuditLog.candidate_id == candidate.id
                )
            )
        ).scalars().all()
        assert len(audit_rows) == 1
        assert audit_rows[0].action == "drift_flagged"


# ---------------------------------------------------------------------------
# Gates 7–8: SQLite append-only triggers
# ---------------------------------------------------------------------------


class TestSQLiteTriggers:
    @pytest.mark.asyncio
    async def test_database_trigger_blocks_audit_update_delete(
        self, db_session: AsyncSession
    ) -> None:
        await build_world(db_session)  # seed owner user for operator_id FK
        candidate = await make_candidate(db_session)
        await _install_sqlite_triggers(db_session)
        db_session.add(
            CandidateAuditLog(
                id="aud-1", candidate_id=candidate.id, action="approved", operator_id=OWNER_ID
            )
        )
        await db_session.flush()

        with pytest.raises(IntegrityError, match="append-only"):
            await db_session.execute(
                text("UPDATE candidate_audit_logs SET action='tampered' WHERE id='aud-1'")
            )
        with pytest.raises(IntegrityError, match="append-only"):
            await db_session.execute(
                text("DELETE FROM candidate_audit_logs WHERE id='aud-1'")
            )

    @pytest.mark.asyncio
    async def test_sqlite_null_safe_trigger_blocks_tamper(
        self, db_session: AsyncSession
    ) -> None:
        await build_world(db_session)
        candidate = await make_candidate(db_session)
        await _install_sqlite_triggers(db_session)
        db_session.add(
            CandidateAuditLog(
                id="aud-2",
                candidate_id=candidate.id,
                action="drift_flagged",
                operator_id=OWNER_ID,
                input_snapshot=None,
                pre_payload=None,
            )
        )
        await db_session.flush()

        # De-linking candidate_id is the ONE sanctioned transition, but here we
        # also tamper a NULL column → must be blocked by the IS null-safe trigger.
        with pytest.raises(IntegrityError, match="append-only"):
            await db_session.execute(
                text(
                    "UPDATE candidate_audit_logs "
                    "SET candidate_id=NULL, input_snapshot='tampered' WHERE id='aud-2'"
                )
            )


class TestSQLiteRuntimeTriggers:
    @pytest.mark.asyncio
    async def test_init_database_installs_triggers_without_manual_setup(
        self, tmp_path, monkeypatch
    ) -> None:
        """The SQLite startup path must install + verify the append-only triggers.

        No manual trigger installation here — this exercises the same code path
        as ``app.db.database.init_database()`` at runtime.
        """
        import app.db.database as db_mod

        db_path = tmp_path / "runtime.db"
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
        monkeypatch.setattr(db_mod, "_db_url", f"sqlite+aiosqlite:///{db_path}")
        monkeypatch.setattr(db_mod, "engine", engine)

        try:
            await db_mod.init_database()

            async with engine.connect() as conn:
                rows = (
                    await conn.execute(
                        text("SELECT name FROM sqlite_master WHERE type='trigger'")
                    )
                ).all()
                names = {r[0] for r in rows}
            assert "trg_audit_log_no_delete" in names
            assert "trg_audit_log_no_update" in names
            assert "trg_audit_log_no_orphan_insert" in names

            # Tamper is blocked without any test-level trigger installation.
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "INSERT INTO candidate_audit_logs "
                        "(id, candidate_id, action, operator_id) "
                        "VALUES ('aud-runtime', 'some-candidate', 'approved', 'some-user')"
                    )
                )
                with pytest.raises(IntegrityError, match="append-only"):
                    await conn.execute(
                        text(
                            "UPDATE candidate_audit_logs SET action='tampered' "
                            "WHERE id='aud-runtime'"
                        )
                    )
                # Orphan inserts (candidate_id NULL) are also rejected.
                with pytest.raises(IntegrityError, match="candidate_id"):
                    await conn.execute(
                        text(
                            "INSERT INTO candidate_audit_logs "
                            "(id, action, operator_id) "
                            "VALUES ('aud-orphan', 'approved', 'some-user')"
                        )
                    )
        finally:
            await engine.dispose()


# ---------------------------------------------------------------------------
# Gate 9/10: PostgreSQL (real)
# ---------------------------------------------------------------------------


class TestPostgresTriggers:
    @pytest.mark.asyncio
    async def test_postgresql_null_safe_trigger_blocks_tamper(self, pg_world) -> None:
        session = pg_world["session"]
        await build_world(session)
        candidate = await make_candidate(session)
        session.add(
            CandidateAuditLog(
                id="aud-pg",
                candidate_id=candidate.id,
                action="drift_flagged",
                operator_id=OWNER_ID,
                pre_payload=None,
            )
        )
        await session.flush()

        with pytest.raises(DBAPIError, match="append-only"):
            await session.execute(
                text(
                    "UPDATE candidate_audit_logs "
                    "SET candidate_id=NULL, pre_payload='{\"tampered\": true}' "
                    "WHERE id='aud-pg'"
                )
            )
        await session.rollback()

    @pytest.mark.asyncio
    async def test_postgresql_orphan_insert_rejected(self, pg_world) -> None:
        """An audit-log INSERT with candidate_id NULL must be rejected."""
        session = pg_world["session"]
        await build_world(session)

        with pytest.raises(DBAPIError, match="candidate_id"):
            await session.execute(
                text(
                    "INSERT INTO candidate_audit_logs (id, action, operator_id) "
                    "VALUES ('aud-orphan-pg', 'approved', :op)"
                ),
                {"op": OWNER_ID},
            )
        await session.rollback()

    @pytest.mark.asyncio
    async def test_postgresql_concurrent_approval_single_publish(
        self, pg_world
    ) -> None:
        session = pg_world["session"]
        factory = pg_world["factory"]
        await build_world(session)
        candidate = await make_candidate(session)
        await session.commit()

        async def approve() -> Evidence:
            return await CandidatePublishUnitOfWork(factory).publish(
                candidate.id, OWNER_ID, "sess-a0"
            )

        results = await asyncio.gather(approve(), approve(), return_exceptions=True)

        successes = [r for r in results if not isinstance(r, Exception)]
        failures = [r for r in results if isinstance(r, Exception)]
        assert len(successes) == 1, f"expected exactly one publish, got {results!r}"
        assert len(failures) == 1
        assert isinstance(failures[0], HTTPException)
        assert failures[0].status_code == 404

        async with factory() as s:
            count = (await s.execute(text("SELECT count(*) FROM evidences"))).scalar_one()
        assert count == 1

    @pytest.mark.asyncio
    async def test_postgresql_approval_locks_chunk_against_mutation(
        self, pg_world
    ) -> None:
        """The approval's FOR UPDATE on the chunk blocks a concurrent mutation.

        Reproduces the source-text race: between grounding validation and
        Evidence commit, a concurrent UPDATE of the chunk must be serialized
        behind the approval's row lock.
        """
        session = pg_world["session"]
        factory = pg_world["factory"]
        await build_world(session)
        await make_candidate(session)
        await session.commit()

        # T1 holds the chunk lock exactly as approve_and_publish_candidate does.
        async with factory() as t1:
            async with t1.begin():
                await t1.execute(
                    select(DocumentChunk)
                    .where(DocumentChunk.id == "chunk-a0")
                    .with_for_update()
                )

                # T2's mutation must be blocked while T1 holds the lock.
                async with factory() as t2:
                    await t2.execute(text("SET LOCAL lock_timeout='200ms'"))
                    with pytest.raises(DBAPIError):
                        await t2.execute(
                            text(
                                "UPDATE document_chunks SET content='tampered' "
                                "WHERE id='chunk-a0'"
                            )
                        )

    @pytest.mark.asyncio
    async def test_postgresql_approval_locks_version_against_withdrawal(
        self, pg_world
    ) -> None:
        """The approval's FOR UPDATE on the version blocks a concurrent withdrawal.

        Reproduces the withdrawn-version race: ``verify_and_resolve_source_ref``
        must lock the version row so a concurrent ``withdrawn_at`` update cannot
        slip between the check and the Evidence commit.
        """
        session = pg_world["session"]
        factory = pg_world["factory"]
        await build_world(session)
        await make_candidate(session)
        await session.commit()

        # T1 holds the version lock exactly as verify_and_resolve_source_ref does.
        async with factory() as t1:
            async with t1.begin():
                await t1.execute(
                    text(
                        "SELECT withdrawn_at FROM versions "
                        "WHERE id='ver-a0' AND is_deleted=false FOR UPDATE"
                    )
                )

                # T2's withdrawal must be blocked while T1 holds the lock.
                async with factory() as t2:
                    await t2.execute(text("SET LOCAL lock_timeout='200ms'"))
                    with pytest.raises(DBAPIError):
                        await t2.execute(
                            text(
                                "UPDATE versions SET withdrawn_at=now() "
                                "WHERE id='ver-a0'"
                            )
                        )

    @pytest.mark.asyncio
    async def test_postgresql_approval_fails_closed_on_soft_deleted_version(
        self, pg_world
    ) -> None:
        """Calling the approval service on a soft-deleted version → no publish."""
        session = pg_world["session"]
        factory = pg_world["factory"]
        world = await build_world(session)
        world["version"].is_deleted = True
        await session.flush()
        candidate = await make_candidate(session)
        await session.commit()

        with pytest.raises(RuntimeError, match="soft-deleted"):
            await CandidatePublishUnitOfWork(factory).publish(
                candidate.id, OWNER_ID, "sess-a0"
            )

        async with factory() as s:
            ev = (await s.execute(text("SELECT count(*) FROM evidences"))).scalar_one()
            cit = (await s.execute(text("SELECT count(*) FROM citations"))).scalar_one()
        assert ev == 0
        assert cit == 0


# ---------------------------------------------------------------------------
# Gates 11–12: withdrawn version & missing SourceRef rollback
# ---------------------------------------------------------------------------


class TestRollbackGuards:
    @pytest.mark.asyncio
    async def test_withdrawn_version_blocks_publish(
        self, db_session: AsyncSession
    ) -> None:
        world = await build_world(db_session)
        world["version"].withdrawn_at = datetime.now(UTC)
        await db_session.flush()
        candidate = await make_candidate(db_session)
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(RuntimeError, match="withdrawn"):
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )
        count = (
            await db_session.execute(text("SELECT count(*) FROM evidences"))
        ).scalar_one()
        assert count == 0

    @pytest.mark.asyncio
    async def test_soft_deleted_version_blocks_publish(
        self, db_session: AsyncSession
    ) -> None:
        """A soft-deleted Version must fail closed (no Evidence/Citation)."""
        world = await build_world(db_session)
        world["version"].is_deleted = True
        await db_session.flush()
        candidate = await make_candidate(db_session)
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(RuntimeError, match="soft-deleted"):
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )

        ev_count = (
            await db_session.execute(text("SELECT count(*) FROM evidences"))
        ).scalar_one()
        cit_count = (
            await db_session.execute(text("SELECT count(*) FROM citations"))
        ).scalar_one()
        assert ev_count == 0
        assert cit_count == 0

    @pytest.mark.asyncio
    async def test_missing_sourceref_rollback(self, db_session: AsyncSession) -> None:
        await build_world(db_session, with_source_ref=False)
        candidate = await make_candidate(db_session)
        reviewer = await _reviewer(db_session)
        await db_session.commit()

        with pytest.raises(RuntimeError, match="SourceRef"):
            await _publish(
                db_session, candidate.id, reviewer.id, "sess-a0"
            )
        await db_session.refresh(candidate)
        assert candidate.status == CandidateStatus.PENDING

        count = (
            await db_session.execute(text("SELECT count(*) FROM evidences"))
        ).scalar_one()
        assert count == 0


class TestAIMetadataChecks:
    @pytest.mark.asyncio
    async def test_ai_model_unknown_rejected_by_check(
        self, db_session: AsyncSession
    ) -> None:
        """The DB CHECK must reject ai_model='unknown' after migration."""
        await build_world(db_session)
        with pytest.raises(IntegrityError):
            await make_candidate(db_session, ai_model="unknown")
