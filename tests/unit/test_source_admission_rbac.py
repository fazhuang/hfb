"""Source-admission RBAC tightening tests (HFB-DAT-0306 governance).

Verifies:
  - seed_rbac canonical matrix: fill (create) is Research-Leader-only;
    review is Steering-Committee-only; Researcher/Reviewer are read-only.
  - The irreversible migration revokes stale grants and installs the
    Steering Committee role on existing databases.
"""

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import uuid as _uuid_mod
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest_db import db_session_persistent  # noqa: F401

pytestmark = pytest.mark.anyio

BACKEND = Path(__file__).resolve().parent.parent.parent / "apps" / "backend"

_SA = "source_admission."


async def _sa_matrix(db: AsyncSession) -> dict[str, set[str]]:
    """Return {role_name: {source_admission codes}} from the live DB."""
    from app.models.user import Permission, Role, role_permission
    from sqlalchemy import select as sa

    await db.flush()
    rows = (
        await db.execute(
            sa(Role.name, Permission.resource, Permission.action)
            .select_from(Role)
            .join(role_permission, Role.id == role_permission.c.role_id)
            .join(Permission, role_permission.c.permission_id == Permission.id)
            .where(Permission.resource == "source_admission")
        )
    ).all()
    mapping: dict[str, set[str]] = {}
    for rname, res, act in rows:
        mapping.setdefault(rname, set()).add(f"{res}.{act}")
    return mapping


class TestSourceAdmissionRbacMatrix:
    async def test_seed_rbac_canonical_matrix(self, db_session_persistent: AsyncSession):
        from app.db.seed_rbac import seed_rbac

        db = db_session_persistent
        await seed_rbac(db)
        m = await _sa_matrix(db)

        # Researcher / Reviewer: read-only (no create, no review).
        for role in ("Researcher", "Reviewer"):
            assert f"{_SA}read" in m[role], f"{role} must keep read"
            assert f"{_SA}create" not in m[role], f"{role} must lose create"
            assert f"{_SA}review" not in m[role], f"{role} must lose review"

        # Research Leader: fill (create), but not review.
        assert f"{_SA}create" in m["Research Leader"]
        assert f"{_SA}review" not in m["Research Leader"]

        # Steering Committee: review + read, but not fill.
        assert f"{_SA}read" in m["Steering Committee"]
        assert f"{_SA}review" in m["Steering Committee"]
        assert f"{_SA}create" not in m["Steering Committee"]

        # Academic Administrator inherits fill, but not review.
        assert f"{_SA}create" in m["Academic Administrator"]
        assert f"{_SA}review" not in m["Academic Administrator"]


def _run_alembic(db_url: str, target: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=str(BACKEND),
        env=env,
        check=True,
        capture_output=True,
    )


class TestSourceAdmissionRbacMigration:
    async def test_migration_tightens_and_installs_steering(self):
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        try:
            # Bring the DB to just before the tightening migration.
            _run_alembic(f"sqlite:///{db_path}", "rbac_cleanup_student_user_read")

            conn = sqlite3.connect(db_path)
            # Seed the OLD matrix: permissions + roles + links.
            conn.execute(
                "INSERT INTO permissions (id, resource, action, description, is_deleted) VALUES "
                "('p-sa-read', 'source_admission', 'read', 'read', 0),"
                "('p-sa-create', 'source_admission', 'create', 'create', 0),"
                "('p-sa-review', 'source_admission', 'review', 'review', 0)"
            )
            roles = {
                "Researcher": "role-researcher",
                "Reviewer": "role-reviewer",
                "Research Leader": "role-leader",
                "Academic Administrator": "role-academic",
            }
            for name, rid in roles.items():
                conn.execute(
                    "INSERT INTO roles (id, name, description, is_system, is_deleted) "
                    "VALUES (?, ?, ?, 0, 0)",
                    (rid, name, name),
                )
            # Researcher: read + create (old). Others: read + create + review.
            conn.execute(
                "INSERT INTO role_permission (role_id, permission_id) VALUES "
                "('role-researcher','p-sa-read'),('role-researcher','p-sa-create'),"
                "('role-reviewer','p-sa-read'),('role-reviewer','p-sa-create'),('role-reviewer','p-sa-review'),"
                "('role-leader','p-sa-read'),('role-leader','p-sa-create'),('role-leader','p-sa-review'),"
                "('role-academic','p-sa-read'),('role-academic','p-sa-create'),('role-academic','p-sa-review')"
            )
            conn.commit()
            conn.close()

            # Run the tightening migration.
            _run_alembic(f"sqlite:///{db_path}", "tighten_source_admission_rbac")

            conn = sqlite3.connect(db_path)

            def _grants(rid: str) -> set[str]:
                rows = conn.execute(
                    "SELECT permission_id FROM role_permission WHERE role_id = ?",
                    (rid,),
                ).fetchall()
                return {r[0] for r in rows}

            # Researcher: create revoked, read kept.
            assert _grants("role-researcher") == {"p-sa-read"}
            # Reviewer: create + review revoked, read kept.
            assert _grants("role-reviewer") == {"p-sa-read"}
            # Leader: review revoked, create + read kept.
            assert _grants("role-leader") == {"p-sa-read", "p-sa-create"}
            # Academic Administrator: review revoked, create + read kept.
            assert _grants("role-academic") == {"p-sa-read", "p-sa-create"}

            # Steering Committee role installed with read + review.
            steering = conn.execute(
                "SELECT id FROM roles WHERE name = 'Steering Committee'"
            ).fetchone()
            assert steering is not None, "Steering Committee role missing"
            steering_id = steering[0]
            # Role id must be a valid UUID — the API schemas validate it as UUID.
            _uuid_mod.UUID(steering_id)
            assert _grants(steering_id) == {"p-sa-read", "p-sa-review"}

            conn.close()
        finally:
            os.unlink(db_path)

    async def test_migration_idempotent_when_steering_preexists(self):
        """A pre-existing Steering role (with read/review links) must not break
        the migration with a primary-key violation."""
        db_fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(db_fd)
        try:
            _run_alembic(f"sqlite:///{db_path}", "rbac_cleanup_student_user_read")

            conn = sqlite3.connect(db_path)
            conn.execute(
                "INSERT INTO permissions (id, resource, action, description, is_deleted) VALUES "
                "('p-sa-read', 'source_admission', 'read', 'read', 0),"
                "('p-sa-create', 'source_admission', 'create', 'create', 0),"
                "('p-sa-review', 'source_admission', 'review', 'review', 0)"
            )
            roles = {
                "Researcher": "role-researcher",
                "Reviewer": "role-reviewer",
                "Research Leader": "role-leader",
                "Academic Administrator": "role-academic",
                "Steering Committee": "role-steering-pre",  # pre-existing, custom id
            }
            for name, rid in roles.items():
                conn.execute(
                    "INSERT INTO roles (id, name, description, is_system, is_deleted) "
                    "VALUES (?, ?, ?, 0, 0)",
                    (rid, name, name),
                )
            conn.execute(
                "INSERT INTO role_permission (role_id, permission_id) VALUES "
                "('role-researcher','p-sa-read'),('role-researcher','p-sa-create'),"
                "('role-reviewer','p-sa-read'),('role-reviewer','p-sa-create'),('role-reviewer','p-sa-review'),"
                "('role-leader','p-sa-read'),('role-leader','p-sa-create'),('role-leader','p-sa-review'),"
                "('role-academic','p-sa-read'),('role-academic','p-sa-create'),('role-academic','p-sa-review'),"
                "('role-steering-pre','p-sa-read'),('role-steering-pre','p-sa-review')"
            )
            conn.commit()
            conn.close()

            # Must NOT raise a primary-key violation.
            _run_alembic(f"sqlite:///{db_path}", "tighten_source_admission_rbac")

            conn = sqlite3.connect(db_path)

            def _grants(rid: str) -> set[str]:
                return {
                    r[0]
                    for r in conn.execute(
                        "SELECT permission_id FROM role_permission WHERE role_id = ?",
                        (rid,),
                    ).fetchall()
                }

            assert _grants("role-researcher") == {"p-sa-read"}
            assert _grants("role-reviewer") == {"p-sa-read"}
            assert _grants("role-leader") == {"p-sa-read", "p-sa-create"}
            assert _grants("role-academic") == {"p-sa-read", "p-sa-create"}
            # Pre-existing Steering keeps its grants; no duplicate rows.
            assert _grants("role-steering-pre") == {"p-sa-read", "p-sa-review"}

            count = conn.execute(
                "SELECT COUNT(*) FROM roles WHERE name = 'Steering Committee'"
            ).fetchone()[0]
            assert count == 1, "A second Steering Committee role must not be created"
            conn.close()
        finally:
            os.unlink(db_path)
