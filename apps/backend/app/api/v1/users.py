"""
User management API — admin CRUD for users and roles.

GET    /api/v1/users
POST   /api/v1/users
GET    /api/v1/users/{id}
PATCH  /api/v1/users/{id}
DELETE /api/v1/users/{id}

GET    /api/v1/roles
POST   /api/v1/roles
GET    /api/v1/roles/{id}
DELETE /api/v1/roles/{id}
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.repositories.user import RoleRepository, UserRepository
from app.schemas.user import (
    RoleBrief,
    RoleCreate,
    RoleResponse,
    UserBrief,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import hash_password
from app.utils.response import api_response

router = APIRouter(tags=["Users & Roles"])


# ------------------------------------------------------------------
# Users
# ------------------------------------------------------------------

_user_create_guard = require_permission("user", "create")
_user_read_guard = require_permission("user", "read")
_user_update_guard = require_permission("user", "update")
_user_delete_guard = require_permission("user", "delete")


@router.get(
    "/users",
    response_model=dict,
    dependencies=[Depends(_user_read_guard)],
)
async def list_users(
    session: Annotated[AsyncSession, Depends(get_session)],
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user_id: Annotated[str, Depends(get_current_user)] = "",
) -> dict:
    """List all users (admin)."""
    repo = UserRepository(session)
    items, total = await repo.get_all(page=page, limit=limit)
    users = [UserBrief.model_validate(u).model_dump(mode="json") for u in items]
    return api_response(data={"items": users, "total": total})


@router.post(
    "/users",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(_user_create_guard)],
)
async def create_user(
    body: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user_id: Annotated[str, Depends(get_current_user)] = "",
) -> dict:
    """Create a new user (admin).

    Privilege-escalation guard: only superusers may create a superuser
    account or assign roles directly.
    """
    repo = UserRepository(session)
    role_repo = RoleRepository(session)

    caller = await repo.get_by_id(current_user_id)
    caller_is_superuser = caller is not None and caller.is_superuser
    if body.is_superuser and not caller_is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can create superuser accounts",
        )
    if body.role_ids and not caller_is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can assign roles",
        )

    existing = await repo.get_by_username(body.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username already taken"
        )

    existing = await repo.get_by_email(str(body.email))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        )

    user = await repo.create(
        username=body.username,
        email=str(body.email),
        hashed_password=hash_password(body.password),
        display_name=body.display_name,
        affiliation=body.affiliation,
        is_active=body.is_active,
        is_superuser=body.is_superuser,
    )

    if body.role_ids:
        for rid in body.role_ids:
            role = await role_repo.get_by_id(rid)
            if role:
                user.roles.append(role)
        await session.flush()

    return api_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        message="User created",
    )


@router.get(
    "/users/{user_id}",
    response_model=dict,
    dependencies=[Depends(_user_read_guard)],
)
async def get_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Get a single user by ID."""
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return api_response(data=UserResponse.model_validate(user).model_dump(mode="json"))


@router.patch(
    "/users/{user_id}",
    response_model=dict,
    dependencies=[Depends(_user_update_guard)],
)
async def update_user(
    user_id: UUID,
    body: UserUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user_id: Annotated[str, Depends(get_current_user)] = "",
) -> dict:
    """Partially update a user.

    Account-takeover guard: only superusers may modify is_superuser,
    role_ids, is_active, or reset another user's password. A successful
    password change or account disable increments token_version to void
    every in-flight access and refresh token immediately.
    """
    repo = UserRepository(session)
    user = await repo.get_by_id(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    caller = await repo.get_by_id(current_user_id)
    caller_is_superuser = caller is not None and caller.is_superuser

    if body.is_superuser is not None and not caller_is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can modify the is_superuser flag",
        )
    if body.role_ids is not None and not caller_is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can modify role assignments",
        )
    if body.is_active is not None and not caller_is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can modify account status",
        )
    if body.password and not caller_is_superuser and str(user_id) != current_user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can reset other users' passwords",
        )

    password_changed = bool(body.password)
    active_changed = body.is_active is not None

    updates = body.model_dump(exclude_unset=True, exclude={"role_ids", "password"})
    for key, value in updates.items():
        if hasattr(user, key):
            setattr(user, key, value)
    if body.password:
        user.hashed_password = hash_password(body.password)  # type: ignore[attr-defined]
    if body.role_ids is not None:
        role_repo = RoleRepository(session)
        user.roles.clear()  # type: ignore[attr-defined]
        for rid in body.role_ids:
            role = await role_repo.get_by_id(rid)
            if role:
                user.roles.append(role)  # type: ignore[attr-defined]

    # Token lifecycle: password reset or account disable atomically voids
    # all previously issued tokens by bumping token_version.
    if password_changed or active_changed:
        user.token_version = (user.token_version or 1) + 1

    await session.flush()

    return api_response(
        data=UserResponse.model_validate(user).model_dump(mode="json"),
        message="User updated",
    )


@router.delete(
    "/users/{user_id}",
    response_model=dict,
    dependencies=[Depends(_user_delete_guard)],
)
async def delete_user(
    user_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Soft-delete a user."""
    repo = UserRepository(session)
    ok = await repo.soft_delete(user_id)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return api_response(data=None, message="User deleted")


# ------------------------------------------------------------------
# Roles
# ------------------------------------------------------------------


@router.get(
    "/roles",
    response_model=dict,
    dependencies=[Depends(require_permission("user", "read"))],
)
async def list_roles(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """List all roles."""
    repo = RoleRepository(session)
    items, _ = await repo.get_all(page=1, limit=100)
    roles = [RoleBrief.model_validate(r).model_dump(mode="json") for r in items]
    return api_response(data={"items": roles})


@router.post(
    "/roles",
    response_model=dict,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("user", "create"))],
)
async def create_role(
    body: RoleCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Create a new role with optional permission assignments."""
    from app.repositories.user import PermissionRepository

    role_repo = RoleRepository(session)
    perm_repo = PermissionRepository(session)

    existing = await role_repo.get_by_name(body.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Role name already exists"
        )

    role = await role_repo.create(name=body.name, description=body.description)
    for pid in body.permission_ids:
        perm = await perm_repo.get_by_id(pid)
        if perm:
            role.permissions.append(perm)
    await session.flush()

    return api_response(
        data=RoleResponse.model_validate(role).model_dump(mode="json"),
        message="Role created",
    )


@router.delete(
    "/roles/{role_id}",
    response_model=dict,
    dependencies=[Depends(require_permission("user", "delete"))],
)
async def delete_role(
    role_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Soft-delete a role. System roles cannot be deleted."""
    repo = RoleRepository(session)
    role = await repo.get_by_id(role_id)
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be deleted",
        )
    await repo.soft_delete(role_id)
    return api_response(data=None, message="Role deleted")
