"""Tighten source_admission RBAC and add the Steering Committee review role.

Governance alignment (HFB-DAT-0306):
  - Filling the admission checklist (source_admission.create) is restricted to
    the Research Leader (and senior roles that inherit it).
  - Reviewing/approving (source_admission.review) is moved to a dedicated
    "Steering Committee" role instead of being scattered across Reviewer /
    Research Leader / Academic Administrator.

Revision ID: tighten_source_admission_rbac
Revises: rbac_cleanup_student_user_read
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "tighten_source_admission_rbac"
down_revision: str | None = "rbac_cleanup_student_user_read"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()

    # Revoke source_admission.create from Researcher and Reviewer — filling is
    # now a Research-Leader-only governance action.
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permission
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE resource = 'source_admission' AND action = 'create'
            )
            AND role_id IN (
                SELECT id FROM roles WHERE name IN ('Researcher', 'Reviewer')
            )
            """
        )
    )

    # Revoke source_admission.review from Reviewer / Research Leader /
    # Academic Administrator — review moves to the Steering Committee.
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permission
            WHERE permission_id IN (
                SELECT id FROM permissions
                WHERE resource = 'source_admission' AND action = 'review'
            )
            AND role_id IN (
                SELECT id FROM roles
                WHERE name IN ('Reviewer', 'Research Leader', 'Academic Administrator')
            )
            """
        )
    )

    # Insert the Steering Committee role (governance review body).
    # The id must be a valid UUID (roles.id is a String(36) UUID and the API
    # schemas validate it as a UUID).
    conn.execute(
        sa.text(
            """
            INSERT INTO roles (id, name, description, is_system)
            SELECT 'a96dd15c-124b-435b-9b1c-e5fc6b82709f', 'Steering Committee',
                   '指导委员会 — 审核来源准入与语料解冻治理决策', TRUE
            WHERE NOT EXISTS (
                SELECT 1 FROM roles WHERE name = 'Steering Committee'
            )
            """
        )
    )

    # Grant the Steering Committee read + review on source_admission.
    # Idempotent: skip links that already exist (e.g. a Steering role that was
    # manually created and pre-linked before this migration ran).
    conn.execute(
        sa.text(
            """
            INSERT INTO role_permission (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r, permissions p
            WHERE r.name = 'Steering Committee'
              AND p.resource = 'source_admission'
              AND p.action IN ('read', 'review')
              AND NOT EXISTS (
                  SELECT 1 FROM role_permission rp
                  WHERE rp.role_id = r.id AND rp.permission_id = p.id
              )
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "Irreversible governance migration: source_admission RBAC tightening "
        "(Research-Leader-only create + Steering-Committee review) cannot be "
        "auto-reverted."
    )
