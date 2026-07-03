"""
Seed data for RBAC — default roles, permissions, and admin user.

Per 1704 Ch.3 — seven platform roles.
Per 1704 Ch.5 — resource × action permissions.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import (
    User,
    Role,
    Permission,
    role_permission,
    user_role,
)
from app.services.auth_service import hash_password

# ============================================================
# Default Permissions — resource × action
# ============================================================

_RESOURCES = [
    "person",
    "book",
    "version",
    "chapter",
    "passage",
    "paper",
    "document",
    "image",
    "user",
    "evidence",
    "citation",
    "research",
    "workspace",
    "project",
    "graph",
    "search",
    "ai",
    "dashboard",
]

_ACTIONS = [
    "create",
    "read",
    "update",
    "delete",
    "export",
]

# Admin-only actions
_ADMIN_ACTIONS = [
    "publish",
    "review",
    "approve",
]

SEED_PERMISSIONS: list[dict] = []
for resource in _RESOURCES:
    for action in _ACTIONS + _ADMIN_ACTIONS:
        SEED_PERMISSIONS.append({"resource": resource, "action": action})

# ============================================================
# Default Roles
# ============================================================

SEED_ROLES = [
    {
        "name": "Platform Administrator",
        "description": "平台管理员 — 拥有全部权限",
        "is_system": True,
    },
    {
        "name": "Academic Administrator",
        "description": "学术管理员 — 管理学术资源与审核",
        "is_system": True,
    },
    {
        "name": "Research Leader",
        "description": "项目负责人 — 管理课题组与研究项目",
        "is_system": False,
    },
    {
        "name": "Researcher",
        "description": "研究人员 — 创建和编辑研究内容",
        "is_system": False,
    },
    {
        "name": "Reviewer",
        "description": "学术审核人 — 审核研究内容",
        "is_system": False,
    },
    {
        "name": "Student",
        "description": "学生 — 浏览与学习",
        "is_system": False,
    },
    {
        "name": "Visitor",
        "description": "游客 — 仅公开内容浏览",
        "is_system": True,
    },
]

# ============================================================
# Role → Permissions mapping (by permission code "resource.action")
# ============================================================

_VISITOR_READS = [
    "person.read",
    "book.read",
    "version.read",
    "passage.read",
    "paper.read",
    "graph.read",
    "search.read",
    "dashboard.read",
]

_STUDENT_PERMS = _VISITOR_READS + [
    "workspace.read",
    "ai.read",
]

_RESEARCHER_PERMS = _STUDENT_PERMS + [
    "person.create", "person.update",
    "book.create", "book.update",
    "version.create", "version.update",
    "chapter.create", "chapter.update",
    "passage.create", "passage.update",
    "paper.create", "paper.update",
    "evidence.create", "evidence.read", "evidence.update",
    "citation.create", "citation.read", "citation.update",
    "research.create", "research.read", "research.update", "research.delete", "research.export",
    "workspace.create", "workspace.update",
    "project.create", "project.read", "project.update",
    "person.export", "book.export", "chapter.export", "passage.export",
]

_REVIEWER_PERMS = _RESEARCHER_PERMS + [
    "person.review", "book.review", "version.review", "chapter.review", "passage.review",
    "evidence.review", "citation.review", "research.review",
    "person.approve", "book.approve", "version.approve",
    "research.approve",
]

_LEADER_PERMS = _REVIEWER_PERMS + [
    "person.publish", "book.publish", "version.publish", "chapter.publish", "passage.publish",
    "evidence.publish", "citation.publish",
    "research.publish",
    "person.delete", "book.delete", "version.delete", "chapter.delete", "passage.delete", "paper.delete",
    "evidence.delete", "citation.delete",
    "workspace.delete",
    "project.delete",
    "project.publish",
]

_ACADEMIC_ADMIN_PERMS = _LEADER_PERMS + [
    "person.approve", "book.approve", "evidence.approve", "citation.approve",
    "person.review", "book.review", "evidence.review", "citation.review",
]

# Platform Admin gets ALL permissions (resolved dynamically after permission seed)


def _resolve_role_permission_codes() -> dict[str, list[str]]:
    """Return {role_name: [permission_code, ...]} for seeding."""
    return {
        "Visitor": _VISITOR_READS,
        "Student": _STUDENT_PERMS,
        "Researcher": _RESEARCHER_PERMS,
        "Reviewer": _REVIEWER_PERMS,
        "Research Leader": _LEADER_PERMS,
        "Academic Administrator": _ACADEMIC_ADMIN_PERMS,
        # "Platform Administrator" resolved at seed time → all permissions
    }


# ============================================================
# Default Admin User
# ============================================================

SEED_ADMIN_USER = {
    "username": "admin",
    "email": "admin@huangfumi.org",
    "password": "admin123",  # MUST be changed on first login
    "display_name": "平台管理员",
    "affiliation": "皇甫谧数字人文平台",
}


# ============================================================
# Seed function
# ============================================================

async def seed_rbac(session: AsyncSession) -> dict[str, int]:
    """Insert RBAC seed data — permissions, roles, admin user.

    Returns counts of inserted records.
    """
    counts: dict[str, int] = {}

    # ---- Permissions ----
    perm_count = 0
    perm_objects: dict[str, Permission] = {}  # code → Permission
    for data in SEED_PERMISSIONS:
        code = f"{data['resource']}.{data['action']}"
        existing = await session.execute(
            select(Permission).where(
                Permission.resource == data["resource"],
                Permission.action == data["action"],
            )
        )
        perm = existing.scalar_one_or_none()
        if perm is None:
            perm = Permission(**data)
            session.add(perm)
            perm_objects[code] = perm
            perm_count += 1
        else:
            perm_objects[code] = perm
    counts["permissions"] = perm_count

    # ---- Roles ----
    role_count = 0
    role_objects: dict[str, Role] = {}  # name → Role
    role_perm_map = _resolve_role_permission_codes()

    for data in SEED_ROLES:
        existing = await session.execute(
            select(Role).where(Role.name == data["name"])
        )
        role = existing.scalar_one_or_none()
        if role is None:
            role = Role(**data)
            session.add(role)
            role_count += 1
        role_objects[data["name"]] = role

    await session.flush()

    # Assign permissions to roles
    for role_name, role in role_objects.items():
        existing_links = await session.execute(
            select(role_permission.c.permission_id).where(
                role_permission.c.role_id == role.id
            )
        )
        existing_permission_ids = set(existing_links.scalars().all())
        if role_name == "Platform Administrator":
            permissions = perm_objects.values()
        else:
            permissions = (
                perm_objects[code]
                for code in role_perm_map.get(role_name, [])
                if code in perm_objects
            )

        new_links: list[dict[str, str]] = []
        planned_permission_ids = set(existing_permission_ids)
        for perm in permissions:
            if perm.id in planned_permission_ids:
                continue
            new_links.append(
                {"role_id": role.id, "permission_id": perm.id}
            )
            planned_permission_ids.add(perm.id)
        if new_links:
            await session.execute(role_permission.insert(), new_links)

    await session.flush()
    counts["roles"] = role_count

    # ---- Admin User ----
    user_count = 0
    existing_admin = await session.execute(
        select(User).where(User.username == SEED_ADMIN_USER["username"])
    )
    if existing_admin.scalar_one_or_none() is None:
        admin = User(
            username=SEED_ADMIN_USER["username"],
            email=SEED_ADMIN_USER["email"],
            hashed_password=hash_password(SEED_ADMIN_USER["password"]),
            display_name=SEED_ADMIN_USER["display_name"],
            affiliation=SEED_ADMIN_USER["affiliation"],
            is_superuser=True,
        )
        session.add(admin)
        await session.flush()

        # Attach Platform Administrator role
        admin_role = role_objects.get("Platform Administrator")
        if admin_role:
            await session.execute(
                user_role.insert().values(
                    user_id=admin.id,
                    role_id=admin_role.id,
                )
            )

        user_count += 1
    counts["users"] = user_count

    await session.flush()
    return counts
