"""
Auth API routes — login, register, refresh, me.

POST /api/v1/auth/login
POST /api/v1/auth/register
POST /api/v1/auth/refresh
GET  /api/v1/auth/me
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_session
from app.middleware.auth import get_auth_service, get_current_user
from app.repositories.user import UserRepository
from app.schemas.user import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    UserResponse,
)
from app.services.auth_service import AuthService
from app.utils.response import api_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


def _user_to_dict(user: object) -> dict:
    """Safe User→dict conversion that avoids lazy-load issues."""
    roles = []
    try:
        raw_roles = getattr(user, "roles", None)
        if (
            raw_roles is not None
            and hasattr(raw_roles, "__iter__")
            and not isinstance(raw_roles, (str, bytes))
        ):
            for r in raw_roles:
                roles.append(
                    {
                        "id": getattr(r, "id", ""),
                        "name": getattr(r, "name", ""),
                        "description": getattr(r, "description", None),
                    }
                )
    except (AttributeError, TypeError, RuntimeError):
        logger.debug("Error iterating user roles", exc_info=True)

    return {
        "id": getattr(user, "id", ""),
        "username": getattr(user, "username", ""),
        "email": getattr(user, "email", ""),
        "display_name": getattr(user, "display_name", None),
        "affiliation": getattr(user, "affiliation", None),
        "is_active": getattr(user, "is_active", True),
        "is_superuser": getattr(user, "is_superuser", False),
        "roles": roles,
        "created_at": getattr(user, "created_at", None),
        "updated_at": getattr(user, "updated_at", None),
    }


@router.post("/login", response_model=dict, status_code=status.HTTP_200_OK)
async def login(
    body: LoginRequest,
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    """Authenticate with username and password. Returns JWT token pair."""
    user, access_token, refresh_token = await auth_svc.authenticate(
        body.username, body.password
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    return api_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": UserResponse.model_validate(user).model_dump(mode="json"),
        },
        message="Login successful",
    )


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    """Register a new user account."""
    try:
        user = await auth_svc.register(
            username=body.username,
            email=str(body.email),
            password=body.password,
            display_name=body.display_name,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    return api_response(
        data=_user_to_dict(user),
        message="Registration successful",
    )


@router.post("/refresh", response_model=dict, status_code=status.HTTP_200_OK)
async def refresh(
    body: RefreshRequest,
    auth_svc: Annotated[AuthService, Depends(get_auth_service)],
) -> dict:
    """Issue a new token pair using a valid refresh token."""
    tokens = auth_svc.refresh_access_token(body.refresh_token)
    if tokens is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    access_token, refresh_token = tokens
    return api_response(
        data={
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        },
        message="Token refreshed",
    )


@router.get("/me", response_model=dict, status_code=status.HTTP_200_OK)
async def me(
    user_id: Annotated[str, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Return the current authenticated user's profile."""
    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return api_response(
        data=_user_to_dict(user),
        message="ok",
    )
