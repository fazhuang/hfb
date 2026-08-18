"""Phase A0 — CandidateExtraction core metadata fields (HFB-DAT-0303 §3).

Revision ID: a0_core_metadata_fields
Revises: a0_ai_metadata_required
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "a0_core_metadata_fields"
down_revision: str | None = "a0_ai_metadata_required"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "resource_type",
                sa.String(50),
                nullable=False,
                server_default="candidate_extraction",
            )
        )
        batch_op.add_column(
            sa.Column("title", sa.String(500), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("language", sa.String(20), nullable=False, server_default="zh")
        )
        batch_op.add_column(
            sa.Column("abstract", sa.Text(), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("keywords", sa.String(500), nullable=False, server_default="")
        )
        batch_op.add_column(
            sa.Column("description", sa.Text(), nullable=False, server_default="")
        )


def downgrade() -> None:
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.drop_column("description")
        batch_op.drop_column("keywords")
        batch_op.drop_column("abstract")
        batch_op.drop_column("language")
        batch_op.drop_column("title")
        batch_op.drop_column("resource_type")
