"""add institution name non-blank check constraint

Revision ID: b3c4d5e6f7a8
Revises: a1b2c3d4e5f6
Create Date: 2026-06-30 23:00:00.000000
"""
from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = 'b3c4d5e6f7a8'
down_revision: str | None = 'a1b2c3d4e5f6'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table('institutions') as batch_op:
        batch_op.create_check_constraint(
            "ck_institutions_name_not_blank",
            "length(trim(name)) > 0",
        )


def downgrade() -> None:
    with op.batch_alter_table('institutions') as batch_op:
        batch_op.drop_constraint("ck_institutions_name_not_blank")
