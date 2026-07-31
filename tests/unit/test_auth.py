"""
Tests for auth service — password hashing, JWT, login, permissions.
"""

import pytest
from app.repositories.user import PermissionRepository, RoleRepository, UserRepository
from app.services.auth_service import (
    AuthService,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


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
        """Each hash call produces a unique salt → different output."""
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

        tokens = svc.refresh_access_token(refresh)
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

        # Using access token as refresh → should fail
        result = svc.refresh_access_token(access)
        assert result is None

    @pytest.mark.asyncio
    async def test_rbac_permissions(self, db_session: AsyncSession):
        """Test that RBAC permission checking works."""
        svc = AuthService(db_session)

        # Create permissions
        perm_repo = PermissionRepository(db_session)
        p_read = await perm_repo.create(resource="person", action="read")
        await perm_repo.create(resource="person", action="write")

        # Create role with read permission — use explicit association table insert
        role_repo = RoleRepository(db_session)
        role = await role_repo.create(name="TestRole")

        # Insert into role_permission table directly to avoid lazy-load on SQLite
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

        # Insert into user_role table directly
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
