"""add session_id to documents for cross-project isolation (SQLite-safe)

Revision ID: d8e9f0a1b2c3
Revises: p2t1_formal_source
Create Date: 2026-07-20 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d8e9f0a1b2c3"
down_revision: str | None = "p2t1_formal_source"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "session_id",
                sa.String(36),
                nullable=True,
                comment="所属研究项目/会话 ID — NULL = 公共/系统文献，不归属特定项目",
            ),
        )
        batch_op.create_index("idx_documents_session_id", ["session_id"])


def downgrade() -> None:
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("idx_documents_session_id")
        batch_op.drop_column("session_id")
