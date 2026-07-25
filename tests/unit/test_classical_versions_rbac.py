"""
RBAC tests for ClassicalVersion — route-level authorization with dependency overrides.

Verifies:
  - user with only create perm cannot PATCH (needs update perm)
  - user with update perm can PATCH
  - non-superuser cannot DELETE
  - superuser DELETE is soft-delete
  - anonymous gets 401
  - soft-delete enforcement at service level
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from main import app as fastapi_app
from app.services.auth_service import create_access_token
from app.models.classical_version import ClassicalVersion

from tests.conftest_db import db_session  # noqa: F401

pytestmark = pytest.mark.anyio


# ============================================================
# Dependency overrides (same pattern as test_p0_2_http_verify.py)
# ============================================================


def _setup_overrides(session: AsyncSession, token: str | None = None) -> None:
    from app.db.database import get_session
    from app.middleware import auth as auth_mod
    from app.services.auth_service import AuthService

    async def override_get_session():
        yield session

    fastapi_app.dependency_overrides[get_session] = override_get_session

    if token is not None:
        async def override_get_current_user(request=None):
            from app.services.auth_service import decode_token
            payload = decode_token(token)
            return payload["sub"]

        async def override_get_auth_service():
            svc = AuthService(session)

            class _A:
                def __init__(self):
                    self.session = session

                async def has_permission(self, uid, r, a):
                    return await svc.has_permission(uid, r, a)

                async def has_any_permission(self, uid, *p):
                    return await svc.has_any_permission(uid, *p)

            return _A()

        fastapi_app.dependency_overrides[auth_mod.get_current_user] = override_get_current_user
        fastapi_app.dependency_overrides[auth_mod.get_auth_service] = override_get_auth_service


def _cleanup_overrides() -> None:
    fastapi_app.dependency_overrides.clear()


# ============================================================
# Helpers
# ============================================================


def _token(user_id: str) -> dict:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


async def _seed_user(
    session: AsyncSession,
    user_id: str,
    username: str,
    permission_codes: list[str],
    is_superuser: bool = False,
):
    from app.models.user import User, Role, Permission
    from app.models.user import user_role, role_permission

    user = User(
        id=user_id,
        username=username,
        email=f"{username}@test.com",
        hashed_password="pw",
        is_active=True,
        is_superuser=is_superuser,
    )
    session.add(user)
    role = Role(id=f"role-{username}", name=username, description=f"Test {username}")
    session.add(role)
    await session.flush()
    await session.execute(user_role.insert().values(user_id=user_id, role_id=role.id))
    for code in permission_codes:
        resource, action = code.split(".", 1)
        perm = Permission(
            id=f"perm-{code}-{username}",
            resource=resource,
            action=action,
            description=code,
        )
        session.add(perm)
        await session.flush()
        await session.execute(
            role_permission.insert().values(role_id=role.id, permission_id=perm.id)
        )
    await session.flush()


async def _seed_cv(session, title="针灸甲乙经", vname="宋刻本", source="https://example.com/song"):
    from app.api.v1.classical_versions import ClassicalVersionService
    from app.schemas.classical_version import ClassicalVersionCreate

    svc = ClassicalVersionService(session)
    obj = await svc.create(ClassicalVersionCreate(
        work_title=title,
        version_name=vname,
        source_url=source,
        public_domain_status="unknown",
    ))
    return obj.id


# ============================================================
# Route-level RBAC tests
# ============================================================


class TestClassicalVersionRouteRBAC:
    async def test_user_with_create_only_cannot_patch(self, db_session):
        cvid = await _seed_cv(db_session)
        uid = "create-only-99"
        await _seed_user(db_session, uid, uid, [
            "classical_version.read",
            "classical_version.create",
        ])
        jwt_str = create_access_token(uid)
        headers = {"Authorization": f"Bearer {jwt_str}"}

        _setup_overrides(db_session, jwt_str)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"/api/v1/admin/classical-versions/{cvid}",
                    headers=headers,
                    json={"review_status": "approved"},
                )
                assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        finally:
            _cleanup_overrides()

    async def test_user_with_update_perm_can_patch(self, db_session):
        cvid = await _seed_cv(db_session)
        uid = "updater-99"
        await _seed_user(db_session, uid, uid, [
            "classical_version.read",
            "classical_version.update",
        ])
        jwt_str = create_access_token(uid)
        headers = {"Authorization": f"Bearer {jwt_str}"}

        _setup_overrides(db_session, jwt_str)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    f"/api/v1/admin/classical-versions/{cvid}",
                    headers=headers,
                    json={"review_status": "approved"},
                )
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                assert response.json()["data"]["review_status"] == "approved"
        finally:
            _cleanup_overrides()

    async def test_non_superuser_cannot_delete(self, db_session):
        cvid = await _seed_cv(db_session)
        uid = "no-su-del-99"
        await _seed_user(db_session, uid, uid, [
            "classical_version.read",
            "classical_version.delete",
        ], is_superuser=False)
        jwt_str = create_access_token(uid)
        headers = {"Authorization": f"Bearer {jwt_str}"}

        _setup_overrides(db_session, jwt_str)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(
                    f"/api/v1/admin/classical-versions/{cvid}",
                    headers=headers,
                )
                assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
        finally:
            _cleanup_overrides()

    async def test_superuser_delete_is_soft(self, db_session):
        cvid = await _seed_cv(db_session)
        uid = "su-del-99"
        await _seed_user(db_session, uid, uid, [], is_superuser=True)
        jwt_str = create_access_token(uid)
        headers = {"Authorization": f"Bearer {jwt_str}"}

        _setup_overrides(db_session, jwt_str)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(
                    f"/api/v1/admin/classical-versions/{cvid}",
                    headers=headers,
                )
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        finally:
            _cleanup_overrides()

        # Row still exists in DB
        stmt = select(ClassicalVersion).where(ClassicalVersion.id == cvid)
        result = await db_session.execute(stmt)
        row = result.scalar_one_or_none()
        assert row is not None, "row must still exist after soft-delete"
        assert row.is_deleted is True
        assert row.deleted_at is not None

    async def test_anonymous_list_401(self, db_session):
        _setup_overrides(db_session, token=None)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/api/v1/classical-versions")
                assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        finally:
            _cleanup_overrides()

    async def test_anonymous_delete_401(self, db_session):
        _setup_overrides(db_session, token=None)
        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.delete(
                    "/api/v1/admin/classical-versions/00000000-0000-0000-0000-000000000000",
                )
                assert response.status_code == 401, f"Expected 401, got {response.status_code}"
        finally:
            _cleanup_overrides()


# ============================================================
# Service-level RBAC + soft-delete (no ASGI needed)
# ============================================================


class TestClassicalVersionServiceRBAC:
    async def test_superuser_bypasses_all_checks(self, db_session):
        from app.services.auth_service import AuthService

        await _seed_user(db_session, "su-svc-1", "su-svc-1", [], is_superuser=True)
        svc = AuthService(db_session)
        assert await svc.has_permission("su-svc-1", "classical_version", "read") is True
        assert await svc.has_permission("su-svc-1", "classical_version", "create") is True
        assert await svc.has_permission("su-svc-1", "classical_version", "update") is True
        assert await svc.has_permission("su-svc-1", "classical_version", "delete") is True

    async def test_visitor_read_only(self, db_session):
        from app.services.auth_service import AuthService

        await _seed_user(db_session, "visitor-svc-1", "visitor-svc-1", [
            "classical_version.read",
        ])
        svc = AuthService(db_session)
        assert await svc.has_permission("visitor-svc-1", "classical_version", "read") is True
        assert await svc.has_permission("visitor-svc-1", "classical_version", "create") is False
        assert await svc.has_permission("visitor-svc-1", "classical_version", "update") is False
        assert await svc.has_permission("visitor-svc-1", "classical_version", "delete") is False

    async def test_no_permissions_without_seed(self, db_session):
        from app.services.auth_service import AuthService

        svc = AuthService(db_session)
        assert await svc.has_permission("nonexistent-user", "classical_version", "read") is False


class TestClassicalVersionSoftDelete:
    """Soft-delete enforcement at service level."""

    async def test_deleted_not_in_list(self, db_session):
        from app.api.v1.classical_versions import ClassicalVersionService
        from app.schemas.classical_version import ClassicalVersionCreate

        svc = ClassicalVersionService(db_session)
        obj = await svc.create(ClassicalVersionCreate(
            work_title="测试",
            version_name="v1",
            source_url="https://example.com/test",
            public_domain_status="unknown",
        ))
        await svc.soft_delete(obj.id)
        items, total = await svc.list()
        assert total == 0

    async def test_deleted_not_found_by_id(self, db_session):
        from app.api.v1.classical_versions import ClassicalVersionService
        from app.schemas.classical_version import ClassicalVersionCreate

        svc = ClassicalVersionService(db_session)
        obj = await svc.create(ClassicalVersionCreate(
            work_title="测试",
            version_name="v2",
            source_url="https://example.com/test2",
            public_domain_status="unknown",
        ))
        await svc.soft_delete(obj.id)
        assert await svc.get_by_id(obj.id) is None
