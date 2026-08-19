"""Source admission API — online 0306 checklist + review flow tests."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.models.user import Permission, Role, User
from app.models.user import role_permission as rp_table
from app.models.user import user_role as ur_table
from app.services.auth_service import create_access_token

from main import app as fastapi_app

import app.db.database as db_mod
from app.db.database import get_session

RESEARCHER_ID = "sa-researcher"
REVIEWER_ID = "sa-reviewer"


@pytest_asyncio.fixture
async def http_factory(tmp_path):
    db_path = tmp_path / "sa.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def _seed_user(session: AsyncSession, user_id: str, username: str) -> None:
    session.add(
        User(
            id=user_id,
            username=username,
            email=f"{username}@test.com",
            hashed_password="x",
            is_active=True,
            is_superuser=False,
        )
    )
    await session.flush()


async def _grant(
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


def _setup_overrides(factory) -> None:
    async def override_get_session():
        async with factory() as s:
            yield s

    fastapi_app.dependency_overrides[get_session] = override_get_session


def _cleanup() -> None:
    fastapi_app.dependency_overrides.clear()


def _valid_payload() -> dict:
    return {
        "source_uri": "https://example.org/source/1",
        "authorization_basis": "公有领域（作者逝世超过 100 年）",
        "version_label": "明万历刊本，行款 10 行 20 字",
        "import_scope": "选篇（共 10 条）",
        "binding_plan": "SourceRef(url=…) → Evidence(<待创建>) → Citation(<待创建>)，计划 10 条",
        "risk_note": "避讳改字，标注版本来源",
    }


class TestSourceAdmissionAPI:
    @pytest.mark.asyncio
    async def test_list_returns_13_empty_rows(self, http_factory, monkeypatch) -> None:
        async with http_factory() as session:
            await _seed_user(session, RESEARCHER_ID, "researcher")
            await _grant(session, RESEARCHER_ID, "source_admission", "read")
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_overrides(http_factory)
        token = create_access_token(RESEARCHER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.get(
                    "/api/v1/source-admissions",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 200, resp.text
            body = resp.json()
            assert len(body["items"]) == 13
            assert body["summary"]["total_rows"] == 13
            assert body["summary"]["filled"] == 0
            assert body["items"][0]["entry_key"] == "CV-01"
            assert body["items"][0]["status"] == "empty"
        finally:
            _cleanup()
            monkeypatch.undo()

    @pytest.mark.asyncio
    async def test_upsert_submits_row(self, http_factory, monkeypatch) -> None:
        async with http_factory() as session:
            await _seed_user(session, RESEARCHER_ID, "researcher")
            await _grant(session, RESEARCHER_ID, "source_admission", "create")
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_overrides(http_factory)
        token = create_access_token(RESEARCHER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put(
                    "/api/v1/source-admissions/CV-01",
                    json=_valid_payload(),
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 200, resp.text
            assert resp.json()["data"]["status"] == "submitted"
        finally:
            _cleanup()
            monkeypatch.undo()

    @pytest.mark.asyncio
    async def test_upsert_invalid_key_422(self, http_factory, monkeypatch) -> None:
        async with http_factory() as session:
            await _seed_user(session, RESEARCHER_ID, "researcher")
            await _grant(session, RESEARCHER_ID, "source_admission", "create")
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_overrides(http_factory)
        token = create_access_token(RESEARCHER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.put(
                    "/api/v1/source-admissions/XX-99",
                    json=_valid_payload(),
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 422, resp.text
        finally:
            _cleanup()
            monkeypatch.undo()

    @pytest.mark.asyncio
    async def test_review_approve_flow(self, http_factory, monkeypatch) -> None:
        async with http_factory() as session:
            await _seed_user(session, RESEARCHER_ID, "researcher")
            await _seed_user(session, REVIEWER_ID, "reviewer")
            await _grant(session, RESEARCHER_ID, "source_admission", "create")
            await _grant(session, REVIEWER_ID, "source_admission", "review")
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_overrides(http_factory)
        researcher_token = create_access_token(RESEARCHER_ID)
        reviewer_token = create_access_token(REVIEWER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.put(
                    "/api/v1/source-admissions/CV-01",
                    json=_valid_payload(),
                    headers={"Authorization": f"Bearer {researcher_token}"},
                )
                resp = await client.post(
                    "/api/v1/source-admissions/CV-01/review",
                    json={"decision": "approve", "note": "OK"},
                    headers={"Authorization": f"Bearer {reviewer_token}"},
                )
            assert resp.status_code == 200, resp.text
            assert resp.json()["status"] == "approved"
        finally:
            _cleanup()
            monkeypatch.undo()

    @pytest.mark.asyncio
    async def test_review_without_permission_403(
        self, http_factory, monkeypatch
    ) -> None:
        async with http_factory() as session:
            await _seed_user(session, RESEARCHER_ID, "researcher")
            await _grant(session, RESEARCHER_ID, "source_admission", "create")
            await session.commit()

        monkeypatch.setattr(db_mod, "async_session_factory", http_factory)
        _setup_overrides(http_factory)
        token = create_access_token(RESEARCHER_ID)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                await client.put(
                    "/api/v1/source-admissions/CV-01",
                    json=_valid_payload(),
                    headers={"Authorization": f"Bearer {token}"},
                )
                resp = await client.post(
                    "/api/v1/source-admissions/CV-01/review",
                    json={"decision": "approve"},
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert resp.status_code == 403, resp.text
        finally:
            _cleanup()
            monkeypatch.undo()
