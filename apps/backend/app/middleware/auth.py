"""
JWT authentication & RBAC authorization dependencies for FastAPI.

Per HFB-SEC-0702 Ch.6: all endpoints must validate JWT + RBAC.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.services.auth_service import AuthService


async def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AuthService:
    """Dependency: yield an AuthService bound to the request's DB session."""
    return AuthService(session)


def _extract_token(request: Request) -> str | None:
    """Extract Bearer token from Authorization header or cookie."""
    auth_header = request.headers.get("Authorization") or request.headers.get(
        "authorization"
    )
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header.removeprefix("Bearer ").strip()

    # Fallback: cookie
    cookie_token = request.cookies.get("access_token")
    if cookie_token:
        return cookie_token

    return None


async def get_current_user(
    request: Request,
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    """Dependency: validate JWT and return the current user_id.

    Returns a 401 if the token is missing or invalid.
    """
    token = _extract_token(request)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = await auth_svc.verify_access_token(token)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


def require_permission(resource: str, action: str):
    """Factory: FastAPI dependency that checks a single permission.

    Usage:
        @router.get("/admin/users", dependencies=[Depends(require_permission("user", "read"))])
    """

    async def checker(
        user_id: Annotated[str, Depends(get_current_user)],
        auth_svc: Annotated[AuthService, Depends(get_auth_service)],
    ) -> None:
        allowed = await auth_svc.has_permission(user_id, resource, action)
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {resource}.{action}",
            )

    return checker


def require_any_permission(*permissions: tuple[str, str]):
    """Factory: require at least one of several permissions."""

    async def checker(
        user_id: Annotated[str, Depends(get_current_user)],
        auth_svc: Annotated[AuthService, Depends(get_auth_service)],
    ) -> None:
        allowed = await auth_svc.has_any_permission(user_id, *permissions)
        if not allowed:
            required = ", ".join(f"{r}.{a}" for r, a in permissions)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: any of [{required}] required",
            )

    return checker


class OptionalUser:
    """Dependency: extracts the current user_id if a valid token is present, otherwise None.

    Use for endpoints that behave differently for authenticated vs anonymous users.
    """

    def __init__(self) -> None:
        pass

    async def __call__(
        self,
        request: Request,
        auth_svc: Annotated[AuthService, Depends(get_auth_service)],
    ) -> str | None:
        token = _extract_token(request)
        if token is None:
            return None
        return auth_svc.get_current_user_id(token)


async def get_current_admin_user(
    user_id: Annotated[str, Depends(get_current_user)],
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> str:
    """Dependency: validate JWT and verify that current user is an admin or superuser."""
    user = await auth_svc.user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    if user.is_superuser:
        return user_id

    has_review = await auth_svc.has_permission(user_id, "document", "review")
    has_user = await auth_svc.has_permission(user_id, "user", "update")
    if not (has_review or has_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privilege required",
        )
    return user_id


def requires_admin():
    """Dependency factory for requiring admin privilege."""
    return Depends(get_current_admin_user)

