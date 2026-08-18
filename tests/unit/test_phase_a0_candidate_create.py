"""Phase A0 — candidate create UoW + HTTP route tests.

Verifies the fail-closed create path: a candidate is buffered as PENDING only
when ownership (session → chunk → document) and grounding anchors all validate;
otherwise it is rejected before entering the review queue.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.exceptions import NotFoundException, ValidationException
from app.db import audit_triggers
from app.db.base import Base
from app.db.candidate_create_uow import CandidateCreateUnitOfWork
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.models.user import Permission, Role
from app.models.user import role_permission as rp_table
from app.models.user import user_role as ur_table
from app.schemas.candidate import CreateCandidateRequest
from app.services.auth_service import create_access_token

from main import app as fastapi_app

import app.db.database as db_mod
from app.db.database import get_session

# Reuse builders + gold baseline from the pipeline test.
from tests.unit.test_phase_a0_candidate_pipeline import (
    CANON_SHA,
    DEFAULT_PAYLOAD,
    END_CHAR,
    EXACT,
    OWNER_ID,
    SR_URL,
    START_CHAR,
    build_world,
)

# Reuse the SQLite session fixture (conftest_db is not auto-discovered).
from tests.conftest_db import db_session  # noqa: F401

GOLD_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "gold_benchmark_v03.json"
GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

REVIEWER_ID = "http-create-reviewer"


def _make_request(**overrides: object) -> CreateCandidateRequest:
    """Build a valid create request grounded on the gold baseline."""
    data: dict[str, object] = {
        "session_id": "sess-a0",
        "chunk_id": "chunk-a0",
        "version_id": "ver-a0",
        "expected_chunk_sha256": CANON_SHA,
        "expected_nfc_sha256": CANON_SHA,
        "start_char": START_CHAR,
        "end_char": END_CHAR,
        "exact_text": EXACT,
        "extracted_payload": DEFAULT_PAYLOAD,
        "input_snapshot": {"source_uri": SR_URL},
        "extractor_name": "test-extractor",
        "ai_model": "test-model",
        "ai_version": "1.0.0",
        "prompt_version": "p1",
        "processing_time": 0.01,
        "confidence": 0.99,
    }
    data.update(overrides)
    return CreateCandidateRequest.model_validate(data)


def _make_create_uow(session: AsyncSession) -> CandidateCreateUnitOfWork:
    factory = async_sessionmaker(
        session.bind, class_=AsyncSession, expire_on_commit=False
    )
    return CandidateCreateUnitOfWork(factory)


async def _count_candidates(session: AsyncSession) -> int:
    return (
        await session.execute(text("SELECT count(*) FROM candidate_extractions"))
    ).scalar_one()


# ---------------------------------------------------------------------------
# UoW tests
# ---------------------------------------------------------------------------


class TestCandidateCreateUow:
    @pytest.mark.asyncio
    async def test_create_valid_candidate_buffers_pending(self, db_session) -> None:
        await build_world(db_session)
        await db_session.commit()

        created = await _make_create_uow(db_session).create(
            _make_request(), OWNER_ID
        )

        assert created.status == CandidateStatus.PENDING
        assert created.id

        async with db_session as session:
            assert await _count_candidates(session) == 1
            audit = (
                await session.execute(
                    text(
                        "SELECT action FROM candidate_audit_logs "
                        "WHERE candidate_id = :cid"
                    ),
                    {"cid": created.id},
                )
            ).scalar_one()
            assert audit == "created"

    @pytest.mark.asyncio
    async def test_create_grounding_mismatch_rejected(self, db_session) -> None:
        await build_world(db_session)
        await db_session.commit()

        req = _make_request(expected_chunk_sha256="0" * 64)

        with pytest.raises(ValidationException) as exc_info:
            await _make_create_uow(db_session).create(req, OWNER_ID)
        assert exc_info.value.status_code == 422

        async with db_session as session:
            assert await _count_candidates(session) == 0

    @pytest.mark.asyncio
    async def test_create_exact_text_span_mismatch_rejected(self, db_session) -> None:
        await build_world(db_session)
        await db_session.commit()

        req = _make_request(end_char=END_CHAR - 1)  # truncates the span

        with pytest.raises(ValidationException):
            await _make_create_uow(db_session).create(req, OWNER_ID)

        async with db_session as session:
            assert await _count_candidates(session) == 0

    @pytest.mark.asyncio
    async def test_create_cross_session_404(self, db_session) -> None:
        await build_world(db_session)
        await db_session.commit()

        req = _make_request(session_id="other-session")

        with pytest.raises(NotFoundException) as exc_info:
            await _make_create_uow(db_session).create(req, OWNER_ID)
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_create_version_mismatch_422(self, db_session) -> None:
        await build_world(db_session)
        await db_session.commit()

        req = _make_request(version_id="ver-other")

        with pytest.raises(ValidationException):
            await _make_create_uow(db_session).create(req, OWNER_ID)

    @pytest.mark.asyncio
    async def test_create_chunk_without_passage_422(self, db_session) -> None:
        world = await build_world(db_session)
        world["chunk"].passage_id = None
        await db_session.commit()

        with pytest.raises(ValidationException):
            await _make_create_uow(db_session).create(_make_request(), OWNER_ID)


# ---------------------------------------------------------------------------
# HTTP route tests
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def http_factory(tmp_path):
    """A file-backed SQLite engine shared by the auth and create sessions."""
    db_path = tmp_path / "a0_create_http.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await audit_triggers.install_audit_log_triggers(conn)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _grant_permission(
    session: AsyncSession, user_id: str, resource: str, action: str
) -> None:
    role = Role(
        id=f"role-{user_id}-{resource}-{action}",
        name=f"Role-{user_id}-{resource}-{action}",
        is_system=True,
    )
    session.add(role)
    await session.flush()
    await session.execute(ur_table.insert().values(user_id=user_id, role_id=role.id))
    perm = Permission(
        id=f"perm-{user_id}-{resource}-{action}", resource=resource, action=action
    )
    session.add(perm)
    await session.flush()
    await session.execute(
        rp_table.insert().values(role_id=role.id, permission_id=perm.id)
    )
    await session.flush()


def _setup_app_overrides(factory) -> None:
    async def override_get_session():
        async with factory() as s:
            yield s

    fastapi_app.dependency_overrides[get_session] = override_get_session


def _cleanup_overrides() -> None:
    fastapi_app.dependency_overrides.clear()


class TestHTTPCreateRoute:
    @pytest.mark.asyncio
    async def test_create_through_http_returns_201(
        self, http_factory, monkeypatch
    ) -> None:
        async with http_factory() as session:
            world = await build_world(session, owner_id=REVIEWER_ID)
            world["owner"].is_superuser = False
            await _grant_permission(session, REVIEWER_ID, "extraction", "create")
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_app_overrides(http_factory)
        token = create_access_token(REVIEWER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/extractions",
                    json=_make_request().model_dump(mode="json"),
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 201, resp.text
            body = resp.json()
            assert body["success"] is True
            assert body["data"]["candidate_id"]
        finally:
            _cleanup_overrides()
            monkeypatch.undo()

        async with http_factory() as session:
            assert await _count_candidates(session) == 1

    @pytest.mark.asyncio
    async def test_create_without_permission_returns_403(
        self, http_factory, monkeypatch
    ) -> None:
        async with http_factory() as session:
            world = await build_world(session, owner_id=REVIEWER_ID)
            world["owner"].is_superuser = False
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_app_overrides(http_factory)
        token = create_access_token(REVIEWER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/extractions",
                    json=_make_request().model_dump(mode="json"),
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 403, resp.text
        finally:
            _cleanup_overrides()
            monkeypatch.undo()

    @pytest.mark.asyncio
    async def test_create_grounding_mismatch_returns_422(
        self, http_factory, monkeypatch
    ) -> None:
        async with http_factory() as session:
            world = await build_world(session, owner_id=REVIEWER_ID)
            world["owner"].is_superuser = False
            await _grant_permission(session, REVIEWER_ID, "extraction", "create")
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_app_overrides(http_factory)
        token = create_access_token(REVIEWER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                bad = _make_request(expected_chunk_sha256="0" * 64)
                resp = await client.post(
                    "/api/v1/extractions",
                    json=bad.model_dump(mode="json"),
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 422, resp.text
        finally:
            _cleanup_overrides()
            monkeypatch.undo()

    @pytest.mark.asyncio
    async def test_list_candidates_returns_buffered(
        self, http_factory, monkeypatch
    ) -> None:
        async with http_factory() as session:
            world = await build_world(session, owner_id=REVIEWER_ID)
            world["owner"].is_superuser = False
            await _grant_permission(session, REVIEWER_ID, "extraction", "create")
            await _grant_permission(session, REVIEWER_ID, "extraction", "read")
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_app_overrides(http_factory)
        token = create_access_token(REVIEWER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    "/api/v1/extractions",
                    json=_make_request().model_dump(mode="json"),
                    headers={"Authorization": f"Bearer {token}"},
                )
                assert resp.status_code == 201, resp.text

                listing = await client.get(
                    "/api/v1/extractions?status=pending",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert listing.status_code == 200, listing.text
            body = listing.json()
            assert body["total"] == 1
            assert body["items"][0]["status"] == "pending"
        finally:
            _cleanup_overrides()
            monkeypatch.undo()


class TestCandidateReject:
    @pytest.mark.asyncio
    async def test_reject_uow_marks_rejected_with_audit(self, db_session) -> None:
        from app.db.candidate_publish_uow import CandidatePublishUnitOfWork
        from tests.unit.test_phase_a0_candidate_pipeline import make_candidate

        await build_world(db_session)
        candidate = await make_candidate(db_session, creator_id=OWNER_ID)
        await db_session.commit()

        factory = async_sessionmaker(
            db_session.bind, class_=AsyncSession, expire_on_commit=False
        )
        await CandidatePublishUnitOfWork(factory).reject(
            candidate.id, OWNER_ID, "sess-a0", "证据描述与原文不符"
        )

        async with factory() as session:
            cand = await session.get(CandidateExtraction, candidate.id)
            assert cand.status == CandidateStatus.REJECTED
            assert cand.rejection_reason == "证据描述与原文不符"
            assert cand.reviewed_by_user_id == OWNER_ID
            audit = (
                await session.execute(
                    text(
                        "SELECT action FROM candidate_audit_logs "
                        "WHERE candidate_id = :cid"
                    ),
                    {"cid": candidate.id},
                )
            ).scalar_one()
            assert audit == "rejected"

    @pytest.mark.asyncio
    async def test_reject_cross_session_404(self, db_session) -> None:
        from app.db.candidate_publish_uow import CandidatePublishUnitOfWork
        from tests.unit.test_phase_a0_candidate_pipeline import make_candidate

        await build_world(db_session)
        candidate = await make_candidate(db_session, creator_id=OWNER_ID)
        await db_session.commit()

        factory = async_sessionmaker(
            db_session.bind, class_=AsyncSession, expire_on_commit=False
        )
        with pytest.raises(NotFoundException):
            await CandidatePublishUnitOfWork(factory).reject(
                candidate.id, OWNER_ID, "other-session", "nope"
            )
