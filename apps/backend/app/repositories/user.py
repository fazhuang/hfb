"""
User repository — data access for users, roles, permissions.
"""
from __future__ import annotations


from sqlalchemy import select

from app.models.user import User, Role, Permission
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for User entities."""

    model = User

    async def get_by_username(self, username: str) -> User | None:
        """Fetch a non-deleted user by username."""
        stmt = select(User).where(
            User.username == username,
            User.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a non-deleted user by email."""
        stmt = select(User).where(
            User.email == email,
            User.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class RoleRepository(BaseRepository[Role]):
    """Repository for Role entities."""

    model = Role

    async def get_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(
            Role.name == name,
            Role.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class PermissionRepository(BaseRepository[Permission]):
    """Repository for Permission entities."""

    model = Permission

    async def get_by_code(self, resource: str, action: str) -> Permission | None:
        stmt = select(Permission).where(
            Permission.resource == resource,
            Permission.action == action,
            Permission.is_deleted.is_(False),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_permissions(self) -> list[Permission]:
        stmt = select(Permission).where(Permission.is_deleted.is_(False))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
