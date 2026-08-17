"""add entity_relations.domain_status

Revision ID: f1a2b3c4d5e6
Revises: e9f0a1b2c3d4
Create Date: 2026-08-13 13:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: str | None = "e9f0a1b2c3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.add_column(
            sa.Column(
                "domain_status",
                sa.String(50),
                nullable=False,
                server_default="pending",
                comment="研究域状态: pending/verified/excluded",
            ),
        )


def downgrade() -> None:
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.drop_column("domain_status")
