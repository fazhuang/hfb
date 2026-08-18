"""Phase A0 — HTTP approve route integration (real route + auth context).

Verifies the transaction boundary the reviewer flagged: in a real request the
auth/permission checks run on the request's shared session (autobegin), and the
publish must still succeed on a fresh session without ``InvalidRequestError``.
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

from app.db.base import Base
from app.models.candidate_extraction import CandidateExtraction, CandidateStatus
from app.models.user import Permission, Role
from app.models.user import role_permission as rp_table
from app.models.user import user_role as ur_table
from app.services.auth_service import create_access_token

from main import app as fastapi_app

import app.db.database as db_mod
from app.db.database import get_session

# Reuse the builders from the pipeline test.
from tests.unit.test_phase_a0_candidate_pipeline import (
    CANON,
    build_world,
    make_candidate,
)

GOLD_PATH = Path(__file__).resolve().parent.parent / "fixtures" / "gold_benchmark_v03.json"
GOLD = json.loads(GOLD_PATH.read_text(encoding="utf-8"))

REVIEWER_ID = "http-reviewer"


@pytest_asyncio.fixture
async def http_factory(tmp_path):
    """A file-backed SQLite engine shared by the auth and publish sessions."""
    db_path = tmp_path / "a0_http.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _grant_permission(
    session: AsyncSession, user_id: str, resource: str, action: str
) -> None:
    """Grant a single permission to an existing (non-superuser) user."""
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
    """Point the request-scoped session at the shared file DB.

    ``get_current_user`` and ``get_auth_service`` are left untouched so the
    route exercises genuine JWT validation and a real ``AuthService`` bound to
    the overridden ``get_session``. The publish factory is monkeypatched by
    each test to the same DB.
    """
    async def override_get_session():
        async with factory() as s:
            yield s

    fastapi_app.dependency_overrides[get_session] = override_get_session


def _cleanup_overrides() -> None:
    fastapi_app.dependency_overrides.clear()


class TestHTTPApproveRoute:
    @pytest.mark.asyncio
    async def test_approve_publishes_through_real_auth(
        self, http_factory, monkeypatch
    ) -> None:
        """Reviewer with extraction:approve → 200, one Evidence row."""
        async with http_factory() as session:
            world = await build_world(session, owner_id=REVIEWER_ID)
            world["owner"].is_superuser = False  # force real RBAC path
            await _grant_permission(session, REVIEWER_ID, "extraction", "approve")
            candidate = await make_candidate(session, creator_id=REVIEWER_ID)
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_app_overrides(http_factory)
        token = create_access_token(REVIEWER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/extractions/{candidate.id}/approve",
                    json={"session_id": "sess-a0"},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 200, resp.text
            assert resp.json()["success"] is True
        finally:
            _cleanup_overrides()
            monkeypatch.undo()

        async with http_factory() as session:
            count = (
                await session.execute(text("SELECT count(*) FROM evidences"))
            ).scalar_one()
        assert count == 1

    @pytest.mark.asyncio
    async def test_approve_without_permission_returns_403(
        self, http_factory, monkeypatch
    ) -> None:
        """A user without extraction:approve → 403."""
        async with http_factory() as session:
            world = await build_world(session, owner_id=REVIEWER_ID)
            world["owner"].is_superuser = False
            candidate = await make_candidate(session, creator_id=REVIEWER_ID)
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_app_overrides(http_factory)
        token = create_access_token(REVIEWER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/extractions/{candidate.id}/approve",
                    json={"session_id": "sess-a0"},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 403, resp.text
        finally:
            _cleanup_overrides()
            monkeypatch.undo()

    @pytest.mark.asyncio
    async def test_approve_drift_returns_409(self, http_factory, monkeypatch) -> None:
        """Grounded candidate whose chunk drifted → 409 with committed drift."""
        async with http_factory() as session:
            world = await build_world(session, owner_id=REVIEWER_ID)
            world["owner"].is_superuser = False
            await _grant_permission(session, REVIEWER_ID, "extraction", "approve")
            candidate = await make_candidate(session, creator_id=REVIEWER_ID)
            world["chunk"].content = CANON + "（篡改）"
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_app_overrides(http_factory)
        token = create_access_token(REVIEWER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post(
                    f"/api/v1/extractions/{candidate.id}/approve",
                    json={"session_id": "sess-a0"},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 409, resp.text
            assert "GROUNDING_DRIFT" in resp.json()["message"]
        finally:
            _cleanup_overrides()
            monkeypatch.undo()

        # Drift was committed despite the 409.
        async with http_factory() as session:
            cand = await session.get(CandidateExtraction, candidate.id)
            assert cand.status == CandidateStatus.DRIFT_INVALID
