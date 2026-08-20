"""Add users.token_version and revoke user.read from Student/Researcher/Reviewer (Irreversible).

Revision ID: rbac_cleanup_student_user_read
Revises: source_admission_entries
Create Date: 2026-08-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "rbac_cleanup_student_user_read"
down_revision: str | None = "source_admission_entries"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    op.add_column(
        "users",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="令牌版本号",
        ),
    )
    # Revoke user.read from Student / Researcher / Reviewer — these roles
    # must never enumerate or inspect other user accounts.
    conn.execute(
        sa.text(
            """
            DELETE FROM role_permission
            WHERE permission_id IN (
                SELECT id FROM permissions WHERE resource = 'user' AND action = 'read'
            )
            AND role_id IN (
                SELECT id FROM roles WHERE name IN ('Student', 'Researcher', 'Reviewer')
            )
            """
        )
    )


def downgrade() -> None:
    raise RuntimeError(
        "Irreversible security migration: re-granting user.read to "
        "Student/Researcher/Reviewer is forbidden for data privacy compliance."
    )
