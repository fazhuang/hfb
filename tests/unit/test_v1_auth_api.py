"""
Tests for app/api/v1/auth.py -- login, register, refresh, me routes.
Covers uncovered lines: 38-57 (_user_to_dict), 77-86 (login 401),
104-114 (register success), 126-134 (refresh 401), 150-157 (me 404).

Uses httpx.ASGITransport + dependency_overrides (TestClient blocked by httpx2).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.anyio


# ---------------------------------------------------------------------------
# Helpers -- fake ORM-like User
# ---------------------------------------------------------------------------

# Valid UUIDs for FakeUser.id so UserResponse.model_validate doesn't choke.
_U1 = "f1b68b1d-9262-4f91-baf4-9032bf188f38"
_U2 = "1f8a54dc-e02f-484f-9497-beacf7fa2222"
_U3 = "5a013799-5289-4aa1-b500-6ed3fcc80776"
_U4 = "ffd4b5c4-fa63-4342-bc1d-a2ae6a323e05"
_U5 = "4c0a008b-8a52-4712-aecf-39d634c3f7b4"
_UR = "a8646473-ef79-4b31-9a85-ebdf7eb37ef7"
_UC = "b0000000-0000-0000-0000-000000000001"
_UG = "b0000000-0000-0000-0000-000000000002"

# Valid UUIDs for role ids (RoleBrief.id is UUID)
_R1 = "c0000000-0000-0000-0000-000000000001"
_RA = "c0000000-0000-0000-0000-000000000002"


class _FakeUser:
    """Fake User for _user_to_dict testing. Supports getattr pattern."""

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class _FakeRole:
    def __init__(self, id=_R1, name="Researcher", description="default"):
        self.id = id
        self.name = name
        self.description = description


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def _make_auth_app(**svc_kwargs):
    """Build a FastAPI app with the auth router and overridden AuthService."""
    from fastapi import FastAPI
    from app.api.v1.auth import router as auth_router
    from app.middleware.auth import get_auth_service

    app = FastAPI(debug=False)
    app.include_router(auth_router)

    svc = MagicMock()

    if "authenticate_result" in svc_kwargs:
        svc.authenticate = AsyncMock(return_value=svc_kwargs["authenticate_result"])
    if "register_result" in svc_kwargs:
        res = svc_kwargs["register_result"]
        if isinstance(res, Exception):
            svc.register = AsyncMock(side_effect=res)
        else:
            svc.register = AsyncMock(return_value=res)
    if "refresh_result" in svc_kwargs:
        svc.refresh_access_token = MagicMock(return_value=svc_kwargs["refresh_result"])

    async def _fake_get_auth_service():
        return svc

    app.dependency_overrides[get_auth_service] = _fake_get_auth_service

    return app, svc


async def _get(app, path):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def _post(app, path, json):
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.post(path, json=json)


# ---------------------------------------------------------------------------
# LOGIN -- POST /api/v1/auth/login
# ---------------------------------------------------------------------------


class TestLogin:
    """Lines 76-95. Uncovered: 77-86 (401), 38-57 (_user_to_dict)."""

    async def test_login_success(self):
        """Line 77-95: successful login returns tokens + user dict."""
        fake_user = _FakeUser(
            id=_U1,
            username="researcher",
            email="r@test.com",
            display_name="Test",
            affiliation=None,
            is_active=True,
            is_superuser=False,
            roles=[_FakeRole()],
            created_at="2026-01-01T00:00:00",
            updated_at="2026-01-01T00:00:00",
        )
        app, svc = _make_auth_app(
            authenticate_result=(fake_user, "access-abc", "refresh-xyz"),
        )

        resp = await _post(app, "/auth/login", json={
            "username": "researcher",
            "password": "secure-password",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["access_token"] == "access-abc"
        assert data["data"]["refresh_token"] == "refresh-xyz"
        assert data["data"]["token_type"] == "bearer"
        assert "user" in data["data"]
        assert data["data"]["user"]["username"] == "researcher"

    async def test_login_invalid_credentials(self):
        """Lines 77-86: authenticate returns (None, None, None) -> 401."""
        app, svc = _make_auth_app(
            authenticate_result=(None, None, None),
        )

        resp = await _post(app, "/auth/login", json={
            "username": "bad",
            "password": "bad",
        })

        assert resp.status_code == 401
        data = resp.json()
        assert "Invalid username or password" in data.get("detail", "")

    async def test_login_user_to_dict_with_roles(self):
        """Lines 38-57: _user_to_dict handles roles iteration correctly."""
        fake_user = _FakeUser(
            id=_U2,
            username="admin",
            email="admin@test.com",
            display_name=None,
            affiliation=None,
            is_active=True,
            is_superuser=True,
            roles=[_FakeRole(_RA, "Admin", "Full access")],
            created_at=None,
            updated_at=None,
        )
        app, svc = _make_auth_app(
            authenticate_result=(fake_user, "access-2", "refresh-2"),
        )

        resp = await _post(app, "/auth/login", json={
            "username": "admin",
            "password": "admin123",
        })

        assert resp.status_code == 200
        user_data = resp.json()["data"]["user"]
        assert user_data["is_superuser"] is True
        assert len(user_data["roles"]) == 1
        assert user_data["roles"][0]["name"] == "Admin"
        assert user_data["roles"][0]["description"] == "Full access"

    async def test_login_user_to_dict_roles_none(self):
        """Line 40-41: raw_roles is None -> empty list."""
        fake_user = _FakeUser(
            id=_U3,
            username="noroles",
            email="nr@test.com",
            display_name="NR",
            affiliation=None,
            is_active=True,
            is_superuser=False,
            roles=None,
            created_at=None,
            updated_at=None,
        )
        app, svc = _make_auth_app(
            authenticate_result=(fake_user, "access-3", "refresh-3"),
        )

        resp = await _post(app, "/auth/login", json={
            "username": "noroles",
            "password": "nr-pass-123",
        })

        assert resp.status_code == 200
        user_data = resp.json()["data"]["user"]
        assert user_data["roles"] == []

    async def test_login_user_to_dict_roles_string(self):
        """Lines 43-44: roles is a string -> not iterable -> empty list."""
        fake_user = _FakeUser(
            id=_U4,
            username="strroles",
            email="sr@test.com",
            display_name="SR",
            affiliation=None,
            is_active=True,
            is_superuser=False,
            roles="not-an-iterable",
            created_at=None,
            updated_at=None,
        )
        app, svc = _make_auth_app(
            authenticate_result=(fake_user, "access-4", "refresh-4"),
        )

        resp = await _post(app, "/auth/login", json={
            "username": "strroles",
            "password": "sr-pass-123",
        })

        assert resp.status_code == 200
        user_data = resp.json()["data"]["user"]
        assert user_data["roles"] == []

    async def test_login_user_to_dict_roles_triggers_exception_safe(self):
        """Lines 54-55: AttributeError during role iteration -> empty roles."""
        class _BadRoleIter:
            def __iter__(self):
                raise AttributeError("lazy-load failure")
            def __len__(self):
                return 0

        fake_user = _FakeUser(
            id=_U5,
            username="badroles",
            email="br@test.com",
            display_name="BR",
            affiliation=None,
            is_active=True,
            is_superuser=False,
            roles=_BadRoleIter(),
            created_at=None,
            updated_at=None,
        )
        app, svc = _make_auth_app(
            authenticate_result=(fake_user, "access-5", "refresh-5"),
        )

        resp = await _post(app, "/auth/login", json={
            "username": "badroles",
            "password": "br-pass-123",
        })

        assert resp.status_code == 200
        user_data = resp.json()["data"]["user"]
        assert isinstance(user_data["roles"], list)

    async def test_login_respects_inactive_user(self):
        """authenticate returns None when user is inactive -> 401."""
        app, svc = _make_auth_app(
            authenticate_result=(None, None, None),
        )

        resp = await _post(app, "/auth/login", json={
            "username": "inactive-user",
            "password": "some-pass",
        })

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# REGISTER -- POST /api/v1/auth/register
# ---------------------------------------------------------------------------


class TestRegister:
    """Lines 98-117. Uncovered: 104-114 (register success)."""

    async def test_register_success(self):
        """Lines 104-114: register returns 201 with user dict."""
        fake_user = _FakeUser(
            id=_UR,
            username="newuser",
            email="new@test.com",
            display_name="New User",
            affiliation=None,
            is_active=True,
            is_superuser=False,
            roles=[],
            created_at=None,
            updated_at=None,
        )
        app, svc = _make_auth_app(register_result=fake_user)

        resp = await _post(app, "/auth/register", json={
            "username": "newuser",
            "email": "new@test.com",
            "password": "newuser-password",
            "display_name": "New User",
        })

        assert resp.status_code == 201
        data = resp.json()
        assert data["success"] is True
        assert data["message"] == "Registration successful"
        assert data["data"]["username"] == "newuser"
        assert "password" not in data["data"]

    async def test_register_duplicate_username(self):
        """Line 111-112: ValueError -> 409."""
        app, svc = _make_auth_app(
            register_result=ValueError("Username already taken"),
        )

        resp = await _post(app, "/auth/register", json={
            "username": "dup",
            "email": "dup@test.com",
            "password": "dup-pass-123",
        })

        assert resp.status_code == 409
        data = resp.json()
        assert "Username already taken" in data.get("detail", "")

    async def test_register_duplicate_email(self):
        """ValueError for email -> 409."""
        app, svc = _make_auth_app(
            register_result=ValueError("Email already registered"),
        )

        resp = await _post(app, "/auth/register", json={
            "username": "u2",
            "email": "dup-email@test.com",
            "password": "pass-123456",
        })

        assert resp.status_code == 409
        data = resp.json()
        assert "Email already registered" in data.get("detail", "")


# ---------------------------------------------------------------------------
# REFRESH -- POST /api/v1/auth/refresh
# ---------------------------------------------------------------------------


class TestRefresh:
    """Lines 120-141. Uncovered: 126-134 (refresh 401)."""

    async def test_refresh_success(self):
        """Valid refresh token."""
        app, svc = _make_auth_app(
            refresh_result=("new-access", "new-refresh"),
        )

        resp = await _post(app, "/auth/refresh", json={
            "refresh_token": "valid-refresh-token",
        })

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["access_token"] == "new-access"
        assert data["data"]["refresh_token"] == "new-refresh"
        assert data["data"]["token_type"] == "bearer"

    async def test_refresh_invalid_token(self):
        """Lines 126-134: refresh_access_token returns None -> 401."""
        app, svc = _make_auth_app(refresh_result=None)

        resp = await _post(app, "/auth/refresh", json={
            "refresh_token": "expired-token",
        })

        assert resp.status_code == 401
        data = resp.json()
        assert "Invalid or expired refresh token" in data.get("detail", "")

    async def test_refresh_malformed_token(self):
        """Also 401: None for malformed JWT."""
        app, svc = _make_auth_app(refresh_result=None)

        resp = await _post(app, "/auth/refresh", json={
            "refresh_token": "not.a.jwt",
        })

        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# ME -- GET /api/v1/auth/me
# ---------------------------------------------------------------------------


class TestMe:
    """Lines 144-160. Uncovered: 150-157 (me 404)."""

    async def test_me_success(self):
        """Happy path: authenticated user found."""
        fake_user = _FakeUser(
            id=_UC,
            username="current",
            email="current@test.com",
            display_name="Current",
            affiliation=None,
            is_active=True,
            is_superuser=False,
            roles=[],
            created_at=None,
            updated_at=None,
        )
        user_repo_mock = MagicMock()
        user_repo_mock.get_by_id = AsyncMock(return_value=fake_user)

        app = _make_me_only_app("current-user", user_repo_mock)

        resp = await _get(app, "/auth/me")

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["username"] == "current"

    async def test_me_user_not_found(self):
        """Lines 150-157: user not found -> 404."""
        user_repo_mock = MagicMock()
        user_repo_mock.get_by_id = AsyncMock(return_value=None)

        app = _make_me_only_app("ghost-user", user_repo_mock)

        resp = await _get(app, "/auth/me")

        assert resp.status_code == 404
        data = resp.json()
        assert "User not found" in data.get("detail", "")

    async def test_me_requires_authentication(self):
        """No dependency override for get_current_user -> 401."""
        from fastapi import FastAPI
        from app.api.v1.auth import router as auth_router

        app = FastAPI(debug=False)
        app.include_router(auth_router)

        resp = await _get(app, "/auth/me")

        assert resp.status_code == 401


def _make_me_only_app(user_id: str, user_repo_mock: MagicMock):
    """Build an app with auth router, overridden get_current_user + UserRepository."""
    from fastapi import FastAPI
    from app.api.v1.auth import router as auth_router
    from app.middleware.auth import get_current_user
    from app.db.database import get_session

    app = FastAPI(debug=False)
    app.include_router(auth_router)

    async def _fake_user() -> str:
        return user_id

    async def _fake_session():
        return MagicMock()

    app.dependency_overrides[get_current_user] = _fake_user
    app.dependency_overrides[get_session] = _fake_session

    import app.api.v1.auth as auth_module
    auth_module.UserRepository = MagicMock(return_value=user_repo_mock)

    return app
