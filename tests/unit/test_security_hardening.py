"""Security hardening test suite (HFB-SEC-0702 / HFB-PS-1704).

Work packages WP-03A .. WP-03G:
  - Gateway auth for the three retrieval/ingest endpoints (401 / 403 / 200).
  - Disabled-user dual-token interception (access + refresh both 401).
  - Password-reset token lifecycle (old tokens voided, token_version bumps).
  - POST /users and PATCH /users/{id} privilege-escalation blocking.
  - Document/version withdraw permission grading (delete vs update).
  - Dual-dimension retrieval visibility matrix + repository injection.
  - Irreversible Alembic migration RBAC cleanup assertions.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid as _uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session_persistent  # noqa: F401

pytestmark = pytest.mark.anyio

BACKEND = Path(__file__).resolve().parent.parent.parent / "apps" / "backend"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_app(db: AsyncSession):
    """Build a full v1 API app bound to the given session via get_session override."""
    from app.api.v1 import router as v1_router
    from app.db.database import get_session
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(v1_router)

    async def _override_get_session():
        yield db

    app.dependency_overrides[get_session] = _override_get_session
    return app


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _request(app, method: str, path: str, **kwargs):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        return await c.request(method, path, **kwargs)


async def _ensure_permission(db: AsyncSession, resource: str, action: str):
    from app.models.user import Permission
    from sqlalchemy import select as sa

    perm = (
        await db.execute(
            sa(Permission).where(
                Permission.resource == resource,
                Permission.action == action,
            )
        )
    ).scalar_one_or_none()
    if perm is None:
        perm = Permission(id=str(_uuid.uuid4()), resource=resource, action=action)
        db.add(perm)
        await db.flush()
    return perm


async def _ensure_role(db: AsyncSession, name: str):
    from app.models.user import Role
    from sqlalchemy import select as sa

    role = (await db.execute(sa(Role).where(Role.name == name))).scalar_one_or_none()
    if role is None:
        role = Role(id=str(_uuid.uuid4()), name=name, description=f"Test {name}")
        db.add(role)
        await db.flush()
    return role


async def _grant(db: AsyncSession, role, perm) -> None:
    from app.models.user import role_permission as rp
    from sqlalchemy import and_
    from sqlalchemy import select as sa

    ex = (
        await db.execute(
            sa(rp).where(and_(rp.c.role_id == role.id, rp.c.permission_id == perm.id))
        )
    ).first()
    if ex is None:
        await db.execute(rp.insert().values(role_id=role.id, permission_id=perm.id))
        await db.flush()


async def _assign_role(db: AsyncSession, user, role) -> None:
    from app.models.user import user_role as ur
    from sqlalchemy import and_
    from sqlalchemy import select as sa

    ex = (
        await db.execute(
            sa(ur).where(and_(ur.c.user_id == user.id, ur.c.role_id == role.id))
        )
    ).first()
    if ex is None:
        await db.execute(ur.insert().values(user_id=user.id, role_id=role.id))
        await db.flush()


async def _create_user(
    db: AsyncSession,
    username: str,
    *,
    is_superuser: bool = False,
    is_active: bool = True,
    password: str = "TestPass123!",
):
    from app.models.user import User
    from app.services.auth_service import hash_password

    user = User(
        id=str(_uuid.uuid4()),
        username=username,
        email=f"{username}@test.com",
        hashed_password=hash_password(password),
        is_active=is_active,
        is_superuser=is_superuser,
    )
    db.add(user)
    await db.flush()
    return user


async def _grant_permissions(db: AsyncSession, user, perms: list[tuple[str, str]]):
    """Create a dedicated role granting `perms` [(resource, action), ...] to user."""
    role = await _ensure_role(db, f"{user.username}-role")
    for resource, action in perms:
        perm = await _ensure_permission(db, resource, action)
        await _grant(db, role, perm)
    await _assign_role(db, user, role)
    return role


# ---------------------------------------------------------------------------
# WP-03A — Gateway auth for search / chunks / ingest
# ---------------------------------------------------------------------------


class TestSearchGatewayAuth:
    @pytest.fixture
    async def gateway(self, db_session_persistent: AsyncSession):
        from app.services.auth_service import create_access_token

        db = db_session_persistent
        app = _build_app(db)

        authorized = await _create_user(db, "gw-authorized")
        await _grant_permissions(
            db, authorized, [("search", "read"), ("document", "create")]
        )

        noperm = await _create_user(db, "gw-noperm")

        return {
            "app": app,
            "token_auth": create_access_token(authorized.id),
            "token_noperm": create_access_token(noperm.id),
        }

    async def test_search_anonymous_401(self, gateway):
        r = await _request(gateway["app"], "POST", "/api/v1/search", json={"query": "x", "top_k": 5})
        assert r.status_code == 401, f"Expected 401, got {r.status_code}: {r.text}"

    async def test_search_no_permission_403(self, gateway):
        r = await _request(
            gateway["app"],
            "POST",
            "/api/v1/search",
            json={"query": "x", "top_k": 5},
            headers=_auth(gateway["token_noperm"]),
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    async def test_search_authorized_200(self, gateway):
        r = await _request(
            gateway["app"],
            "POST",
            "/api/v1/search",
            json={"query": "x", "top_k": 5},
            headers=_auth(gateway["token_auth"]),
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

    async def test_chunks_anonymous_401(self, gateway):
        r = await _request(
            gateway["app"], "POST", "/api/v1/search/chunks", json={"query": "x", "top_k": 5}
        )
        assert r.status_code == 401

    async def test_chunks_no_permission_403(self, gateway):
        r = await _request(
            gateway["app"],
            "POST",
            "/api/v1/search/chunks",
            json={"query": "x", "top_k": 5},
            headers=_auth(gateway["token_noperm"]),
        )
        assert r.status_code == 403

    async def test_chunks_authorized_200(self, gateway):
        r = await _request(
            gateway["app"],
            "POST",
            "/api/v1/search/chunks",
            json={"query": "x", "top_k": 5},
            headers=_auth(gateway["token_auth"]),
        )
        assert r.status_code == 200

    async def test_ingest_anonymous_401(self, gateway):
        r = await _request(
            gateway["app"],
            "POST",
            "/api/v1/search/ingest",
            json={
                "title": "安全测试",
                "text": "正文内容。",
                "copyright_status": "public_domain",
                "authorization_basis": "test fixture",
            },
        )
        assert r.status_code == 401

    async def test_ingest_no_permission_403(self, gateway):
        r = await _request(
            gateway["app"],
            "POST",
            "/api/v1/search/ingest",
            json={
                "title": "安全测试",
                "text": "正文内容。",
                "copyright_status": "public_domain",
                "authorization_basis": "test fixture",
            },
            headers=_auth(gateway["token_noperm"]),
        )
        assert r.status_code == 403

    async def test_ingest_authorized_200(self, gateway):
        r = await _request(
            gateway["app"],
            "POST",
            "/api/v1/search/ingest",
            json={
                "title": "安全测试",
                "text": "正文内容。",
                "copyright_status": "public_domain",
                "authorization_basis": "test fixture",
            },
            headers=_auth(gateway["token_auth"]),
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# WP-03B — Disabled user dual-token interception
# ---------------------------------------------------------------------------


class TestDisabledUserTokenBlock:
    async def test_disabled_user_access_and_refresh_rejected(
        self, db_session_persistent: AsyncSession
    ):
        from app.services.auth_service import create_access_token, create_refresh_token

        db = db_session_persistent
        app = _build_app(db)

        user = await _create_user(db, "disabled-user")
        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)

        user.is_active = False
        await db.flush()

        r = await _request(app, "GET", "/api/v1/auth/me", headers=_auth(access))
        assert r.status_code == 401, (
            f"Disabled user access token must be 401, got {r.status_code}"
        )

        r = await _request(
            app,
            "POST",
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh},
        )
        assert r.status_code == 401, (
            f"Disabled user refresh token must be 401, got {r.status_code}"
        )


# ---------------------------------------------------------------------------
# WP-03C — Password reset token lifecycle
# ---------------------------------------------------------------------------


class TestPasswordResetTokenLifecycle:
    async def test_reset_voids_old_tokens_and_new_credentials_work(
        self, db_session_persistent: AsyncSession
    ):
        from app.services.auth_service import AuthService, create_access_token, decode_token

        db = db_session_persistent
        app = _build_app(db)

        admin = await _create_user(db, "reset-admin", is_superuser=True)
        target = await _create_user(db, "reset-target", password="OldPass123!")

        auth_svc = AuthService(db)
        _u, old_access, old_refresh = await auth_svc.authenticate(
            "reset-target", "OldPass123!"
        )
        assert old_access and old_refresh

        admin_token = create_access_token(admin.id)

        # Admin resets the target's password.
        r = await _request(
            app,
            "PATCH",
            f"/api/v1/users/{target.id}",
            json={"password": "NewPass456!"},
            headers=_auth(admin_token),
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"

        # Old access token → 401.
        r = await _request(app, "GET", "/api/v1/auth/me", headers=_auth(old_access))
        assert r.status_code == 401

        # Old refresh token → 401.
        r = await _request(
            app,
            "POST",
            "/api/v1/auth/refresh",
            json={"refresh_token": old_refresh},
        )
        assert r.status_code == 401

        # New credentials work and carry token_version == 2.
        r = await _request(
            app,
            "POST",
            "/api/v1/auth/login",
            json={"username": "reset-target", "password": "NewPass456!"},
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
        data = r.json()["data"]
        new_access = data["access_token"]
        new_refresh = data["refresh_token"]

        assert decode_token(new_access)["token_version"] == 2
        assert decode_token(new_refresh)["token_version"] == 2

        r = await _request(app, "GET", "/api/v1/auth/me", headers=_auth(new_access))
        assert r.status_code == 200

        r = await _request(
            app,
            "POST",
            "/api/v1/auth/refresh",
            json={"refresh_token": new_refresh},
        )
        assert r.status_code == 200


# ---------------------------------------------------------------------------
# WP-03D — POST/PATCH privilege escalation blocking
# ---------------------------------------------------------------------------


class TestPrivilegeEscalationBlock:
    @pytest.fixture
    async def esc_app(self, db_session_persistent: AsyncSession):
        from app.services.auth_service import create_access_token

        db = db_session_persistent
        app = _build_app(db)

        admin = await _create_user(db, "esc-admin", is_superuser=True)
        attacker = await _create_user(db, "esc-attacker")
        victim = await _create_user(db, "esc-victim")
        await _grant_permissions(db, attacker, [("user", "create"), ("user", "update")])

        return {
            "app": app,
            "admin": admin,
            "attacker": attacker,
            "victim": victim,
            "admin_token": create_access_token(admin.id),
            "attacker_token": create_access_token(attacker.id),
        }

    async def test_non_superuser_cannot_create_superuser(self, esc_app):
        r = await _request(
            esc_app["app"],
            "POST",
            "/api/v1/users",
            json={
                "username": "new-super",
                "email": "new-super@test.com",
                "password": "TestPass123!",
                "is_superuser": True,
            },
            headers=_auth(esc_app["attacker_token"]),
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    async def test_non_superuser_cannot_assign_roles(self, esc_app):
        r = await _request(
            esc_app["app"],
            "POST",
            "/api/v1/users",
            json={
                "username": "new-roled",
                "email": "new-roled@test.com",
                "password": "TestPass123!",
                "role_ids": [str(_uuid.uuid4())],
            },
            headers=_auth(esc_app["attacker_token"]),
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    async def test_non_superuser_cannot_reset_others_password(self, esc_app):
        r = await _request(
            esc_app["app"],
            "PATCH",
            f"/api/v1/users/{esc_app['victim'].id}",
            json={"password": "Hacked123!"},
            headers=_auth(esc_app["attacker_token"]),
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    async def test_non_superuser_cannot_disable_account(self, esc_app):
        r = await _request(
            esc_app["app"],
            "PATCH",
            f"/api/v1/users/{esc_app['victim'].id}",
            json={"is_active": False},
            headers=_auth(esc_app["attacker_token"]),
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    async def test_non_superuser_cannot_promote_to_superuser(self, esc_app):
        r = await _request(
            esc_app["app"],
            "PATCH",
            f"/api/v1/users/{esc_app['victim'].id}",
            json={"is_superuser": True},
            headers=_auth(esc_app["attacker_token"]),
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    async def test_non_superuser_cannot_change_roles(self, esc_app):
        r = await _request(
            esc_app["app"],
            "PATCH",
            f"/api/v1/users/{esc_app['victim'].id}",
            json={"role_ids": [str(_uuid.uuid4())]},
            headers=_auth(esc_app["attacker_token"]),
        )
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.text}"

    async def test_non_superuser_can_update_display_name(self, esc_app):
        r = await _request(
            esc_app["app"],
            "PATCH",
            f"/api/v1/users/{esc_app['victim'].id}",
            json={"display_name": "Legit Name"},
            headers=_auth(esc_app["attacker_token"]),
        )
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# WP-03E — Withdraw permission grading
# ---------------------------------------------------------------------------


class TestWithdrawPermissionGrading:
    @pytest.fixture
    async def withdraw_app(self, db_session_persistent: AsyncSession):
        from app.models.book import Book
        from app.models.document import Document
        from app.models.version import Version
        from app.services.auth_service import create_access_token

        db = db_session_persistent
        app = _build_app(db)

        researcher = await _create_user(db, "wd-researcher")
        reviewer = await _create_user(db, "wd-reviewer")
        leader = await _create_user(db, "wd-leader")
        admin = await _create_user(db, "wd-admin", is_superuser=True)

        await _grant_permissions(db, researcher, [("document", "update")])
        await _grant_permissions(
            db, reviewer, [("document", "update"), ("document", "review")]
        )
        await _grant_permissions(
            db,
            leader,
            [("document", "update"), ("document", "delete"), ("version", "delete")],
        )

        doc1 = Document(id=str(_uuid.uuid4()), title="wd-doc-1", language="zh")
        doc2 = Document(id=str(_uuid.uuid4()), title="wd-doc-2", language="zh")
        book = Book(id=str(_uuid.uuid4()), title="wd-book")
        db.add_all([doc1, doc2, book])
        await db.flush()
        ver1 = Version(
            id=str(_uuid.uuid4()), book_id=book.id, version_name="wd-ver-1"
        )
        ver2 = Version(
            id=str(_uuid.uuid4()), book_id=book.id, version_name="wd-ver-2"
        )
        db.add_all([ver1, ver2])
        await db.flush()

        return {
            "app": app,
            "tokens": {
                "researcher": create_access_token(researcher.id),
                "reviewer": create_access_token(reviewer.id),
                "leader": create_access_token(leader.id),
                "admin": create_access_token(admin.id),
            },
            "doc1": doc1,
            "doc2": doc2,
            "ver1": ver1,
            "ver2": ver2,
        }

    async def test_document_withdraw_researcher_reviewer_403(self, withdraw_app):
        for role in ("researcher", "reviewer"):
            r = await _request(
                withdraw_app["app"],
                "POST",
                f"/api/v1/documents/{withdraw_app['doc1'].id}/withdraw",
                json={"reason": "test"},
                headers=_auth(withdraw_app["tokens"][role]),
            )
            assert r.status_code == 403, f"{role} must be 403, got {r.status_code}"

    async def test_document_withdraw_leader_admin_200(self, withdraw_app):
        r = await _request(
            withdraw_app["app"],
            "POST",
            f"/api/v1/documents/{withdraw_app['doc1'].id}/withdraw",
            json={"reason": "test"},
            headers=_auth(withdraw_app["tokens"]["leader"]),
        )
        assert r.status_code == 200, f"leader must be 200, got {r.status_code}: {r.text}"

        r = await _request(
            withdraw_app["app"],
            "POST",
            f"/api/v1/documents/{withdraw_app['doc2'].id}/withdraw",
            json={"reason": "test"},
            headers=_auth(withdraw_app["tokens"]["admin"]),
        )
        assert r.status_code == 200, f"admin must be 200, got {r.status_code}: {r.text}"

    async def test_version_withdraw_researcher_reviewer_403(self, withdraw_app):
        for role in ("researcher", "reviewer"):
            r = await _request(
                withdraw_app["app"],
                "POST",
                f"/api/v1/versions/{withdraw_app['ver1'].id}/withdraw",
                json={"reason": "test"},
                headers=_auth(withdraw_app["tokens"][role]),
            )
            assert r.status_code == 403, f"{role} must be 403, got {r.status_code}"

    async def test_version_withdraw_restore_leader_admin_200(self, withdraw_app):
        # Leader withdraws ver1
        r = await _request(
            withdraw_app["app"],
            "POST",
            f"/api/v1/versions/{withdraw_app['ver1'].id}/withdraw",
            json={"reason": "test"},
            headers=_auth(withdraw_app["tokens"]["leader"]),
        )
        assert r.status_code == 200, f"leader withdraw must be 200, got {r.status_code}: {r.text}"

        # Leader restores ver1
        r = await _request(
            withdraw_app["app"],
            "POST",
            f"/api/v1/versions/{withdraw_app['ver1'].id}/restore",
            headers=_auth(withdraw_app["tokens"]["leader"]),
        )
        assert r.status_code == 200, f"leader restore must be 200, got {r.status_code}: {r.text}"

        # Admin withdraws ver2
        r = await _request(
            withdraw_app["app"],
            "POST",
            f"/api/v1/versions/{withdraw_app['ver2'].id}/withdraw",
            json={"reason": "test"},
            headers=_auth(withdraw_app["tokens"]["admin"]),
        )
        assert r.status_code == 200, f"admin withdraw must be 200, got {r.status_code}: {r.text}"


# ---------------------------------------------------------------------------
# WP-03F — Dual-dimension visibility matrix + repository injection
# ---------------------------------------------------------------------------


class TestVisibilityMatrix:
    async def _seed_docs(self, db: AsyncSession):
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk
        from app.models.workspace import ResearchSession

        user_a = await _create_user(db, "matrix-a")
        user_b = await _create_user(db, "matrix-b")

        session_a = ResearchSession(
            id=str(_uuid.uuid4()), user_id=user_a.id, title="Session A"
        )
        session_b = ResearchSession(
            id=str(_uuid.uuid4()), user_id=user_b.id, title="Session B"
        )
        db.add_all([session_a, session_b])
        await db.flush()

        docs = {
            "doc1_public": Document(
                id=str(_uuid.uuid4()),
                title="doc1-public",
                uploaded_by=None,
                session_id=None,
                language="zh",
            ),
            "doc2_owner_a": Document(
                id=str(_uuid.uuid4()),
                title="doc2-owner-a",
                uploaded_by=user_a.id,
                session_id=None,
                language="zh",
            ),
            "doc3_session_a": Document(
                id=str(_uuid.uuid4()),
                title="doc3-session-a",
                uploaded_by=None,
                session_id=session_a.id,
                language="zh",
            ),
            "doc4_both_a": Document(
                id=str(_uuid.uuid4()),
                title="doc4-both-a",
                uploaded_by=user_a.id,
                session_id=session_a.id,
                language="zh",
            ),
            "doc5_mismatch": Document(
                id=str(_uuid.uuid4()),
                title="doc5-mismatch",
                uploaded_by=user_a.id,
                session_id=session_b.id,
                language="zh",
            ),
        }
        db.add_all(docs.values())
        await db.flush()

        for doc in docs.values():
            db.add(
                DocumentChunk(
                    id=str(_uuid.uuid4()),
                    document_id=doc.id,
                    chunk_index=0,
                    content="MATRIX_SENTINEL 内容",
                    token_count=10,
                )
            )
        await db.flush()

        return {
            "user_a": user_a,
            "user_b": user_b,
            "session_a": session_a,
            "session_b": session_b,
            "docs": docs,
        }

    async def test_service_layer_visibility_matrix(self, db_session_persistent: AsyncSession):
        from app.services.retrieval import RetrievalService

        db = db_session_persistent
        seeded = await self._seed_docs(db)
        docs = seeded["docs"]
        rsvc = RetrievalService(db)

        anon = await rsvc.search("MATRIX_SENTINEL", top_k=50, current_user=None)
        anon_ids = {r.document_id for r in anon.results}
        assert anon_ids == {docs["doc1_public"].id}, (
            f"Anonymous must only see public docs, got {anon_ids}"
        )

        user_a_res = await rsvc.search(
            "MATRIX_SENTINEL", top_k=50, current_user=seeded["user_a"].id
        )
        a_ids = {r.document_id for r in user_a_res.results}
        assert a_ids == {
            docs["doc1_public"].id,
            docs["doc2_owner_a"].id,
            docs["doc3_session_a"].id,
            docs["doc4_both_a"].id,
        }, f"User A visibility mismatch, got {a_ids}"

        user_b_res = await rsvc.search(
            "MATRIX_SENTINEL", top_k=50, current_user=seeded["user_b"].id
        )
        b_ids = {r.document_id for r in user_b_res.results}
        assert b_ids == {docs["doc1_public"].id}, (
            f"User B must only see public docs, got {b_ids}"
        )

    async def test_repository_session_injection_fails_closed(
        self, db_session_persistent: AsyncSession
    ):
        from app.repositories.document import DocumentRepository

        db = db_session_persistent
        seeded = await self._seed_docs(db)
        repo = DocumentRepository(db)

        # session_id=Session_B + user_id=User_A → A does not own session B → empty
        items, total = await repo.search_query(
            "", user_id=seeded["user_a"].id, session_id=seeded["session_b"].id, limit=100
        )
        assert total == 0 and items == [], (
            f"Cross-session injection must fail closed, got {total} rows"
        )

        # session_id=Session_A + user_id=None → anonymous session query → empty
        items, total = await repo.search_query(
            "", user_id=None, session_id=seeded["session_a"].id, limit=100
        )
        assert total == 0 and items == [], (
            f"Anonymous session query must fail closed, got {total} rows"
        )


# ---------------------------------------------------------------------------
# WP-03G — Irreversible migration RBAC cleanup
# ---------------------------------------------------------------------------


def _run_alembic(db_url: str, target: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=str(BACKEND),
        env=env,
        check=True,
        capture_output=True,
    )


class TestMigrationRBACCleanup:
    async def test_student_researcher_reviewer_lose_user_read(self):
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        try:
            # Bring the DB to just before the hardening migration, then seed
            # production-like RBAC rows so the DELETE has something to remove.
            _run_alembic(f"sqlite:///{db_path}", "source_admission_entries")

            conn = sqlite3.connect(db_path)
            roles = [
                "Student",
                "Researcher",
                "Reviewer",
                "Research Leader",
                "Academic Administrator",
                "Platform Administrator",
            ]
            role_ids: dict[str, str] = {}
            for i, name in enumerate(roles):
                rid = f"role-{i}"
                conn.execute(
                    "INSERT INTO roles (id, name, description, is_system, is_deleted) "
                    "VALUES (?, ?, ?, 0, 0)",
                    (rid, name, name),
                )
                role_ids[name] = rid
            conn.execute(
                "INSERT INTO permissions (id, resource, action, description, is_deleted) "
                "VALUES ('perm-user-read', 'user', 'read', 'read users', 0)"
            )
            for name in roles:
                conn.execute(
                    "INSERT INTO role_permission (role_id, permission_id) VALUES (?, 'perm-user-read')",
                    (role_ids[name],),
                )
            conn.commit()
            conn.close()

            # Run the hardening migration.
            _run_alembic(f"sqlite:///{db_path}", "rbac_cleanup_student_user_read")

            conn = sqlite3.connect(db_path)
            cols = [row[1] for row in conn.execute("PRAGMA table_info('users')")]
            assert "token_version" in cols, "users.token_version column missing"

            def _has_user_read(rid: str) -> bool:
                row = conn.execute(
                    "SELECT COUNT(*) FROM role_permission "
                    "WHERE role_id = ? AND permission_id = 'perm-user-read'",
                    (rid,),
                ).fetchone()
                return row[0] > 0

            for name in ("Student", "Researcher", "Reviewer"):
                assert not _has_user_read(role_ids[name]), (
                    f"{name} must lose user.read after migration"
                )
            for name in (
                "Research Leader",
                "Academic Administrator",
                "Platform Administrator",
            ):
                assert _has_user_read(role_ids[name]), (
                    f"{name} must keep user.read after migration"
                )
            conn.close()
        finally:
            os.unlink(db_path)
