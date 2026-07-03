"""
Authentication & authorization service.

Handles JWT token creation/verification, password hashing, login,
and RBAC permission checks.

Per:
  HFB-SEC-0702 Security Standard Ch.3-6
  HFB-PS-1704 Permission & Workspace Ch.3-5
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.user import User, Role, Permission
from app.repositories.user import UserRepository, RoleRepository, PermissionRepository


# ------------------------------------------------------------------
# Password hashing
# ------------------------------------------------------------------

def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ------------------------------------------------------------------
# JWT
# ------------------------------------------------------------------

def _jwt_secret() -> str:
    """Return the JWT secret, ensuring minimum key length for HMAC."""
    raw = settings.JWT_SECRET_KEY if settings.JWT_SECRET_KEY != "change-me-to-a-random-secret-key" else settings.SECRET_KEY
    if len(raw) < 32:
        # Pad to minimum 32 bytes for HMAC-SHA256 (RFC 7518 §3.2)
        raw = raw.ljust(32, "0")
    return raw


def _jwt_algorithm() -> str:
    return getattr(settings, "JWT_ALGORITHM", None) or "HS256"


def _jwt_expiry() -> int:
    return getattr(settings, "JWT_ACCESS_TOKEN_EXPIRE_MINUTES", None) or 60


def create_access_token(user_id: str, extra_claims: dict[str, Any] | None = None) -> str:
    """Create a signed JWT access token."""
    import uuid as _uuid

    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(minutes=_jwt_expiry()),
        "type": "access",
        "jti": str(_uuid.uuid4()),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived refresh token."""
    import uuid as _uuid

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(days=7),
        "type": "refresh",
        "jti": str(_uuid.uuid4()),
    }
    return jwt.encode(payload, _jwt_secret(), algorithm=_jwt_algorithm())


def decode_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token. Raises jwt.PyJWTError on failure."""
    return jwt.decode(token, _jwt_secret(), algorithms=[_jwt_algorithm()])


# ------------------------------------------------------------------
# Auth Service
# ------------------------------------------------------------------

class AuthService:
    """Authentication and authorization business logic."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.role_repo = RoleRepository(session)
        self.perm_repo = PermissionRepository(session)

    # ----- Login / Register -----

    async def authenticate(self, username: str, password: str) -> tuple[User | None, str | None, str | None]:
        """Validate credentials and return (user, access_token, refresh_token) or (None, None, None)."""
        user = await self.user_repo.get_by_username(username)
        if user is None or not user.is_active:
            return None, None, None
        if not verify_password(password, user.hashed_password):
            return None, None, None

        access = create_access_token(user.id)
        refresh = create_refresh_token(user.id)
        return user, access, refresh

    async def register(self, username: str, email: str, password: str, display_name: str | None = None) -> User:
        """Register a new user with default 'Researcher' role."""
        existing_user = await self.user_repo.get_by_username(username)
        if existing_user:
            raise ValueError("Username already taken")
        existing_email = await self.user_repo.get_by_email(email)
        if existing_email:
            raise ValueError("Email already registered")

        user = await self.user_repo.create(
            username=username,
            email=email,
            hashed_password=hash_password(password),
            display_name=display_name,
        )

        # Assign default Researcher role if it exists
        default_role = await self.role_repo.get_by_name("Researcher")

        # A fresh database must use the canonical RBAC definition. A second
        # reduced matrix here caused first-run users to miss valid resources.
        if default_role is None:
            from app.db.seed_rbac import seed_rbac

            await seed_rbac(self.session)
            default_role = await self.role_repo.get_by_name("Researcher")
        if default_role:
            from app.models.user import user_role
            from sqlalchemy import select as sa_select, and_
            existing = await self.session.execute(
                sa_select(user_role).where(
                    and_(user_role.c.user_id == user.id, user_role.c.role_id == default_role.id)
                )
            )
            if existing.first() is None:
                await self.session.execute(
                    user_role.insert().values(user_id=user.id, role_id=default_role.id)
                )
            await self.session.flush()

        return user

    def refresh_access_token(self, refresh_token: str) -> tuple[str, str] | None:
        """Issue a new token pair from a valid refresh token. Returns (access, refresh) or None."""
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                return None
            user_id = payload["sub"]
            return create_access_token(user_id), create_refresh_token(user_id)
        except jwt.PyJWTError:
            return None

    def get_current_user_id(self, token: str) -> str | None:
        """Extract the user ID from an access token. Returns None if invalid."""
        try:
            payload = decode_token(token)
            if payload.get("type") != "access":
                return None
            return payload["sub"]
        except jwt.PyJWTError:
            return None

    # ----- RBAC -----

    async def get_user_permissions(self, user_id: UUID | str) -> set[str]:
        """Return the set of permission codes ('resource.action') for a user.

        Uses explicit JOIN queries instead of lazy-loaded relationships to avoid
        MissingGreenlet errors in test environments (pexpect/ASGI transport).
        """
        from sqlalchemy import select as sa_select
        from app.models.user import user_role, role_permission
        user_exists = await self.user_repo.get_by_id(user_id)
        if user_exists is None:
            return set()

        stmt = (
            sa_select(Permission.resource, Permission.action)
            .select_from(User)
            .join(user_role, User.id == user_role.c.user_id)
            .join(Role, user_role.c.role_id == Role.id)
            .join(role_permission, Role.id == role_permission.c.role_id)
            .join(Permission, role_permission.c.permission_id == Permission.id)
            .where(User.id == str(user_id))
        )
        result = await self.session.execute(stmt)
        return {f"{row[0]}.{row[1]}" for row in result.all()}

    async def has_permission(self, user_id: UUID | str, resource: str, action: str) -> bool:
        """Check whether a user has a specific permission. Superuser bypasses RBAC."""
        user = await self.user_repo.get_by_id(user_id)
        if user is not None and user.is_superuser:
            return True
        code = f"{resource}.{action}"
        codes = await self.get_user_permissions(user_id)
        return code in codes

    async def has_any_permission(self, user_id: UUID | str, *permissions: tuple[str, str]) -> bool:
        """Check whether a user has any of the given (resource, action) tuples."""
        codes = await self.get_user_permissions(user_id)
        for resource, action in permissions:
            if f"{resource}.{action}" in codes:
                return True
        return False
