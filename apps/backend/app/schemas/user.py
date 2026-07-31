"""
Auth-related Pydantic schemas — login, register, token, user CRUD.
"""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Auth — Login / Register / Token
# ------------------------------------------------------------------


class LoginRequest(BaseModel):
    """Login credentials."""

    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=200)


class RegisterRequest(BaseModel):
    """Self-registration payload."""

    username: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=200)
    display_name: str | None = Field(default=None, max_length=200)


class TokenResponse(BaseModel):
    """JWT token pair returned on successful login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")


class RefreshRequest(BaseModel):
    """Refresh an expired access token."""

    refresh_token: str


# ------------------------------------------------------------------
# User — Read / Create / Update
# ------------------------------------------------------------------


class UserBase(BaseModel):
    """Fields shared across user schemas."""

    username: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    display_name: str | None = Field(default=None, max_length=200)
    affiliation: str | None = Field(default=None, max_length=500)
    is_active: bool = True
    is_superuser: bool = False


class UserCreate(UserBase):
    """Create a new user (admin only)."""

    password: str = Field(..., min_length=8, max_length=200)
    role_ids: list[UUID] = Field(
        default_factory=list, description="Initial role assignments"
    )


class UserUpdate(BaseModel):
    """Partial update for a user."""

    email: EmailStr | None = None
    display_name: str | None = Field(default=None, max_length=200)
    affiliation: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None
    is_superuser: bool | None = None
    password: str | None = Field(default=None, min_length=8, max_length=200)
    role_ids: list[UUID] | None = None


class UserBrief(BaseModel):
    """Minimal user representation for list views."""

    id: UUID
    username: str
    display_name: str | None
    affiliation: str | None
    is_active: bool
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserResponse(UserBase):
    """Full user representation returned by the API."""

    id: UUID
    created_at: datetime | None = None
    updated_at: datetime | None = None
    roles: list[RoleBrief] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @field_validator("roles", mode="before")
    @classmethod
    def _safe_roles(cls, v: object) -> list[object]:
        """Suppress lazy-load errors in test environments."""
        try:
            if (
                v is not None
                and hasattr(v, "__iter__")
                and not isinstance(v, (str, bytes))
            ):
                return list(v)  # type: ignore[arg-type]
        except (AttributeError, TypeError, RuntimeError):
            logger.debug("Failed to iterate roles in field validator", exc_info=True)
        return []


# ------------------------------------------------------------------
# Role / Permission
# ------------------------------------------------------------------


class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = Field(default=None)


class RoleCreate(RoleBase):
    permission_ids: list[UUID] = Field(default_factory=list)


class RoleBrief(BaseModel):
    id: UUID
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class RoleResponse(RoleBase):
    id: UUID
    is_system: bool
    created_at: datetime | None = None
    permissions: list[PermissionBrief] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class PermissionBrief(BaseModel):
    id: UUID
    resource: str
    action: str
    description: str | None = None

    model_config = {"from_attributes": True}
