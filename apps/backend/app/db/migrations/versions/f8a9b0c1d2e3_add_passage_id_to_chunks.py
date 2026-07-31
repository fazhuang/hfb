"""add passage_id FK to document_chunks (SQLite-safe)

Revision ID: f8a9b0c1d2e3
Revises: 525e27e38f88
Create Date: 2026-07-02 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f8a9b0c1d2e3"
down_revision: str | None = "525e27e38f88"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "passage_id",
                sa.String(36),
                nullable=True,
                comment="Linked passage for lineage resolution (chunk → passage → citation)",
            ),
        )
        batch_op.create_foreign_key(
            "fk_chunks_passage",
            "passages",
            ["passage_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("idx_chunks_passage", ["passage_id"])


def downgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.drop_index("idx_chunks_passage")
        batch_op.drop_column("passage_id")
