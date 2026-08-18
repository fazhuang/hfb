"""Phase A0 — make AI metadata fields required (NOT NULL, no placeholder).

Backfills placeholder values, then enforces NOT NULL on ai_model/ai_version/
prompt_version/processing_time and drops the 'unknown' server_default.

Revision ID: a0_ai_metadata_required
Revises: a0_created_by_rename
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "a0_ai_metadata_required"
down_revision: str | None = "a0_created_by_rename"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        "UPDATE candidate_extractions SET ai_model='rule-based-extractor' "
        "WHERE ai_model='unknown' OR ai_model IS NULL"
    )
    op.execute(
        "UPDATE candidate_extractions SET ai_version='1.0.0' WHERE ai_version IS NULL"
    )
    op.execute(
        "UPDATE candidate_extractions SET prompt_version='1.0.0' "
        "WHERE prompt_version IS NULL"
    )
    op.execute(
        "UPDATE candidate_extractions SET processing_time=0.0 "
        "WHERE processing_time IS NULL"
    )

    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.alter_column(
            "ai_model",
            existing_type=sa.String(200),
            nullable=False,
            server_default=None,
        )
        batch_op.alter_column(
            "ai_version", existing_type=sa.String(100), nullable=False
        )
        batch_op.alter_column(
            "prompt_version", existing_type=sa.String(100), nullable=False
        )
        batch_op.alter_column(
            "processing_time", existing_type=sa.Float(), nullable=False
        )


def downgrade() -> None:
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.alter_column(
            "processing_time", existing_type=sa.Float(), nullable=True
        )
        batch_op.alter_column(
            "prompt_version", existing_type=sa.String(100), nullable=True
        )
        batch_op.alter_column(
            "ai_version", existing_type=sa.String(100), nullable=True
        )
        batch_op.alter_column(
            "ai_model",
            existing_type=sa.String(200),
            nullable=False,
            server_default="unknown",
        )
