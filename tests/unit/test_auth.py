"""
Tests for auth service — password hashing, JWT, login, permissions,
and auth middleware (_extract_token, get_current_user, require_permission,
require_any_permission, OptionalUser).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from app.middleware.auth import (
    OptionalUser,
    _extract_token,
    get_current_user,
    require_any_permission,
    require_permission,
)
from app.repositories.user import PermissionRepository, RoleRepository, UserRepository
from app.services.auth_service import (
    AuthService,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from fastapi import Depends, FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401

pytestmark = pytest.mark.anyio


class TestPasswordHashing:
    """Test bcrypt password utilities."""

    def test_hash_and_verify(self):
        hashed = hash_password("secret123")
        assert hashed != "secret123"
        assert verify_password("secret123", hashed)

    def test_verify_wrong_password(self):
        hashed = hash_password("secret123")
        assert not verify_password("wrong", hashed)

    def test_hash_is_deterministic_for_same_input(self):
        """Each hash call produces a unique salt -> different output."""
        h1 = hash_password("secret123")
        h2 = hash_password("secret123")
        assert h1 != h2
        assert verify_password("secret123", h1)
        assert verify_password("secret123", h2)


class TestJWT:
    """Test JWT token creation and verification."""

    def test_create_and_decode_access_token(self):
        token = create_access_token("user-1")
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "access"
        assert "exp" in payload
        assert "iat" in payload

    def test_create_and_decode_refresh_token(self):
        token = create_refresh_token("user-1")
        payload = decode_token(token)
        assert payload["sub"] == "user-1"
        assert payload["type"] == "refresh"

    def test_decode_invalid_token(self):
        import jwt as pyjwt

        with pytest.raises(pyjwt.PyJWTError):
            decode_token("not.a.valid.token")


class TestAuthService:
    """Test AuthService with in-memory SQLite."""

    @pytest.mark.asyncio
    async def test_register_and_authenticate(self, db_session: AsyncSession):
        svc = AuthService(db_session)

        # Register
        user = await svc.register("researcher1", "r1@test.com", "pass123", "测试")
        assert user.username == "researcher1"
        assert user.display_name == "测试"

        # Authenticate
        u, access, refresh = await svc.authenticate("researcher1", "pass123")
        assert u is not None
        assert u.id == user.id
        assert access is not None
        assert refresh is not None

        # Wrong password
        u, a, r = await svc.authenticate("researcher1", "wrongpassword")
        assert u is None

        # Wrong username
        u, _a, _r = await svc.authenticate("nonexistent", "pass123")
        assert u is None

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, db_session: AsyncSession):
        svc = AuthService(db_session)
        await svc.register("dup", "dup1@test.com", "pass123")
        with pytest.raises(ValueError, match="Username already taken"):
            await svc.register("dup", "dup2@test.com", "pass123")

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, db_session: AsyncSession):
        svc = AuthService(db_session)
        await svc.register("u1", "same@test.com", "pass123")
        with pytest.raises(ValueError, match="Email already registered"):
            await svc.register("u2", "same@test.com", "pass123")

    @pytest.mark.asyncio
    async def test_refresh_token_flow(self, db_session: AsyncSession):
        svc = AuthService(db_session)
        await svc.register("rtest", "rtest@test.com", "pass123")

        _u, access, refresh = await svc.authenticate("rtest", "pass123")
        assert refresh is not None

        tokens = await svc.refresh_access_token(refresh)
        assert tokens is not None
        new_access, _new_refresh = tokens
        assert new_access != access
        payload = decode_token(new_access)
        assert payload["type"] == "access"

    @pytest.mark.asyncio
    async def test_refresh_rejects_access_token(self, db_session: AsyncSession):
        svc = AuthService(db_session)
        await svc.register("rtest2", "rtest2@test.com", "pass123")
        _u, access, _refresh = await svc.authenticate("rtest2", "pass123")

        # Using access token as refresh -> should fail
        result = await svc.refresh_access_token(access)
        assert result is None

    @pytest.mark.asyncio
    async def test_rbac_permissions(self, db_session: AsyncSession):
        """Test that RBAC permission checking works."""
        svc = AuthService(db_session)

        # Create permissions
        perm_repo = PermissionRepository(db_session)
        p_read = await perm_repo.create(resource="person", action="read")
        await perm_repo.create(resource="person", action="write")

        # Create role with read permission
        role_repo = RoleRepository(db_session)
        role = await role_repo.create(name="TestRole")

        from app.models.user import role_permission

        await db_session.execute(
            role_permission.insert().values(role_id=role.id, permission_id=p_read.id)
        )
        await db_session.flush()

        # Create user with role
        user_repo = UserRepository(db_session)
        user = await user_repo.create(
            username="rbac_test",
            email="rbac@test.com",
            hashed_password=hash_password("test"),
        )

        from app.models.user import user_role

        await db_session.execute(
            user_role.insert().values(user_id=user.id, role_id=role.id)
        )
        await db_session.flush()

        # Reload user with eager-loaded roles+permissions
        from app.models.user import User
        from sqlalchemy import select as sa_select

        stmt = sa_select(User).where(User.id == user.id)
        result = await db_session.execute(stmt)
        user_fresh = result.scalar_one()

        # Check permissions
        assert await svc.has_permission(user_fresh.id, "person", "read") is True
        assert await svc.has_permission(user_fresh.id, "person", "write") is False

        # has_any_permission
        assert (
            await svc.has_any_permission(
                user_fresh.id, ("person", "read"), ("person", "write")
            )
            is True
        )
        assert (
            await svc.has_any_permission(
                user_fresh.id, ("book", "read"), ("book", "write")
            )
            is False
        )


# ============================================================
# AUTH MIDDLEWARE -- _extract_token, get_current_user,
# require_permission, require_any_permission, OptionalUser
# ============================================================


class TestExtractToken:
    """Coverage for _extract_token lines 25-38."""

    async def test_extracts_bearer_header(self):
        """Lines 27-31: Bearer token via Authorization header (Starlette's
        Headers.get is case-insensitive, so either get('Authorization')
        or get('authorization') resolves correctly)."""
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer my-access-token")],
        }
        request = Request(scope)
        token = _extract_token(request)
        assert token == "my-access-token"

    async def test_extracts_cookie_fallback(self):
        """Line 34-36: fallback to access_token cookie."""
        scope = {
            "type": "http",
            "headers": [],
        }
        request = Request(scope)
        request._cookies = {"access_token": "cookie-token-value"}
        token = _extract_token(request)
        assert token == "cookie-token-value"

    async def test_returns_none_when_no_token(self):
        """Line 38: returns None when no token anywhere."""
        scope = {
            "type": "http",
            "headers": [],
        }
        request = Request(scope)
        request._cookies = {}
        token = _extract_token(request)
        assert token is None

    async def test_non_bearer_header_ignored(self):
        """Authorization header without Bearer prefix is ignored."""
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Basic dXNlcjpwYXNz")],
        }
        request = Request(scope)
        request._cookies = {}
        token = _extract_token(request)
        assert token is None


class TestGetCurrentUser:
    """Coverage for get_current_user, specifically line 58 (invalid token)."""

    async def test_invalid_token_returns_401_via_http(self):
        """Line 58: get_current_user_id returns None -> 401.

        Test via a real FastAPI request (ASGITransport).
        """
        from app.middleware.auth import get_auth_service as auth_svc_dep

        app = FastAPI(debug=False)

        async def _fake_svc():
            svc = MagicMock()
            svc.verify_access_token = AsyncMock(return_value=None)
            return svc

        app.dependency_overrides[auth_svc_dep] = _fake_svc

        @app.get("/me")
        async def me_endpoint(
            user_id: str = Depends(get_current_user),
        ) -> dict:
            return {"user_id": user_id}

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/me", headers={"Authorization": "Bearer bad-token"}
            )

        assert resp.status_code == 401
        data = resp.json()
        assert "Invalid or expired token" in data.get("detail", "")

    async def test_missing_token_returns_401_via_http(self):
        """Line 50-55: no token -> 401 'Authentication required'."""
        from app.middleware.auth import get_auth_service as auth_svc_dep

        app = FastAPI(debug=False)

        async def _fake_svc():
            return MagicMock()

        app.dependency_overrides[auth_svc_dep] = _fake_svc

        @app.get("/me")
        async def me_endpoint(
            user_id: str = Depends(get_current_user),
        ) -> dict:
            return {"user_id": user_id}

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/me")

        assert resp.status_code == 401
        data = resp.json()
        assert "Authentication required" in data.get("detail", "")


class TestRequirePermission:
    """Coverage for require_permission factory -- line 95, 112."""

    async def test_permission_granted_passes(self):
        """Happy path: user has the permission."""
        from app.middleware.auth import (
            get_auth_service as auth_svc_dep,
        )
        from app.middleware.auth import (
            get_current_user as gcu_dep,
        )

        app = FastAPI(debug=False)

        svc = MagicMock()
        svc.has_permission = AsyncMock(return_value=True)

        async def _fake_user():
            return "test-user"

        async def _fake_svc():
            return svc

        app.dependency_overrides[gcu_dep] = _fake_user
        app.dependency_overrides[auth_svc_dep] = _fake_svc

        check = require_permission("books", "read")

        @app.get("/books", dependencies=[Depends(check)])
        async def list_books():
            return {"books": []}

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/books")
        assert resp.status_code == 200

    async def test_permission_denied_returns_403(self):
        """Line 79-81 (via require_permission): denied -> 403."""
        from app.middleware.auth import (
            get_auth_service as auth_svc_dep,
        )
        from app.middleware.auth import (
            get_current_user as gcu_dep,
        )

        app = FastAPI(debug=False)

        svc = MagicMock()
        svc.has_permission = AsyncMock(return_value=False)

        async def _fake_user():
            return "test-user"

        async def _fake_svc():
            return svc

        app.dependency_overrides[gcu_dep] = _fake_user
        app.dependency_overrides[auth_svc_dep] = _fake_svc

        check = require_permission("admin", "manage")

        @app.get("/admin", dependencies=[Depends(check)])
        async def admin_endpoint():
            return {"ok": True}

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin")
        assert resp.status_code == 403
        data = resp.json()
        assert "admin.manage" in data.get("detail", "")


class TestRequireAnyPermission:
    """Coverage for require_any_permission -- lines 95-97, 119-122."""

    async def test_any_permission_granted_passes(self):
        """Line 119-122: user has at least one match."""
        from app.middleware.auth import (
            get_auth_service as auth_svc_dep,
        )
        from app.middleware.auth import (
            get_current_user as gcu_dep,
        )

        app = FastAPI(debug=False)

        svc = MagicMock()
        svc.has_any_permission = AsyncMock(return_value=True)

        async def _fake_user():
            return "test-user"

        async def _fake_svc():
            return svc

        app.dependency_overrides[gcu_dep] = _fake_user
        app.dependency_overrides[auth_svc_dep] = _fake_svc

        check = require_any_permission(("books", "read"), ("books", "write"))

        @app.get("/books-any", dependencies=[Depends(check)])
        async def list_books_any():
            return {"books": []}

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/books-any")
        assert resp.status_code == 200

    async def test_any_permission_denied_returns_403(self):
        """Lines 95-97: no permission matched -> 403 with formatted detail."""
        from app.middleware.auth import (
            get_auth_service as auth_svc_dep,
        )
        from app.middleware.auth import (
            get_current_user as gcu_dep,
        )

        app = FastAPI(debug=False)

        svc = MagicMock()
        svc.has_any_permission = AsyncMock(return_value=False)

        async def _fake_user():
            return "test-user"

        async def _fake_svc():
            return svc

        app.dependency_overrides[gcu_dep] = _fake_user
        app.dependency_overrides[auth_svc_dep] = _fake_svc

        check = require_any_permission(("admin", "manage"), ("admin", "delete"))

        @app.get("/admin-any", dependencies=[Depends(check)])
        async def admin_any():
            return {"ok": True}

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/admin-any")
        assert resp.status_code == 403
        data = resp.json()
        assert "admin.manage" in data.get("detail", "")
        assert "admin.delete" in data.get("detail", "")
        assert "any of" in data.get("detail", "")


class TestOptionalUser:
    """Coverage for OptionalUser -- lines 112, 119-122."""

    async def test_returns_user_id_when_token_valid(self):
        """Line 122: valid token returns user_id via __call__."""
        from app.middleware.auth import OptionalUser as OU

        optional = OU()
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer good-token")],
        }
        request = Request(scope)

        svc = MagicMock()
        svc.get_current_user_id = MagicMock(return_value="user-456")

        result = await optional.__call__(request, svc)
        assert result == "user-456"
        svc.get_current_user_id.assert_called_once_with("good-token")

    async def test_returns_none_when_no_token(self):
        """Lines 119-121: no token -> returns None, svc not called."""
        from app.middleware.auth import OptionalUser as OU

        optional = OU()
        scope = {
            "type": "http",
            "headers": [],
        }
        request = Request(scope)
        request._cookies = {}

        svc = MagicMock()
        result = await optional.__call__(request, svc)
        assert result is None
        svc.get_current_user_id.assert_not_called()

    async def test_returns_none_when_token_invalid(self):
        """Line 122: token present but get_current_user_id returns None."""
        from app.middleware.auth import OptionalUser as OU

        optional = OU()
        scope = {
            "type": "http",
            "headers": [(b"authorization", b"Bearer expired-token")],
        }
        request = Request(scope)

        svc = MagicMock()
        svc.get_current_user_id = MagicMock(return_value=None)
        result = await optional.__call__(request, svc)
        assert result is None

    async def test_init_accepts_no_args(self):
        """Line 112: OptionalUser.__init__ with no args."""
        ou = OptionalUser()
        assert ou is not None  # pylint: disable=no-member
