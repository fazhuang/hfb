"""
User, Role, Permission — RBAC domain models.

HFB-PS-1704 Permission & Workspace
HFB-SEC-0702 Security Standard Chapter 4-5
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, ForeignKey, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, BaseModel

# ------------------------------------------------------------------
# Association tables (many-to-many)
# ------------------------------------------------------------------

user_role = Table(
    "user_role",
    Base.metadata,
    Column(
        "user_id",
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "role_id",
        String(36),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

role_permission = Table(
    "role_permission",
    Base.metadata,
    Column(
        "role_id",
        String(36),
        ForeignKey("roles.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "permission_id",
        String(36),
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


# ------------------------------------------------------------------
# User
# ------------------------------------------------------------------


class User(BaseModel):
    """Platform user — identity and credentials only.

    Roles are assigned via the user_role association table.
    """

    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True, comment="用户名"
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True, comment="邮箱"
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="bcrypt 哈希密码"
    )
    display_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="显示名称"
    )
    affiliation: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="所属机构"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, comment="是否激活"
    )
    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="超级管理员",
    )

    # Relationships
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary=user_role,
        lazy="selectin",
        back_populates="users",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} username={self.username!r}>"


# ------------------------------------------------------------------
# Role
# ------------------------------------------------------------------


class Role(BaseModel):
    """Named role grouping permissions.

    Per 1704 Ch.3: Platform Administrator, Academic Administrator,
    Research Leader, Researcher, Reviewer, Student, Visitor.
    """

    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, comment="角色名称"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="角色描述"
    )
    is_system: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="系统内置角色(不可删除)",
    )

    # Relationships
    users: Mapped[list[User]] = relationship(
        "User",
        secondary=user_role,
        lazy="selectin",
        back_populates="roles",
    )
    permissions: Mapped[list[Permission]] = relationship(
        "Permission",
        secondary=role_permission,
        lazy="selectin",
        back_populates="roles",
    )

    def __repr__(self) -> str:
        return f"<Role id={self.id} name={self.name!r}>"


# ------------------------------------------------------------------
# Permission
# ------------------------------------------------------------------


class Permission(BaseModel):
    """Granular permission — resource + action.

    Per 1704 Ch.5: Version, Book, Passage, Person, Evidence,
    Citation, Research, Workspace, Project, Dataset ×
    Create, Read, Update, Delete, Export, Publish, Review, Approve.
    """

    __tablename__ = "permissions"

    resource: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="资源类型"
    )
    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="操作 (create, read, update, delete, export, publish, review, approve)",
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="权限描述"
    )

    # Relationships
    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary=role_permission,
        lazy="selectin",
        back_populates="permissions",
    )

    @property
    def code(self) -> str:
        """Canonical permission code: resource.action."""
        return f"{self.resource}.{self.action}"

    def __repr__(self) -> str:
        return f"<Permission resource={self.resource!r} action={self.action!r}>"
