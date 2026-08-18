"""Phase A0 — make AI metadata fields required (NOT NULL, no placeholder).

Fails closed rather than fabricating source facts: if any row has a placeholder
``ai_model`` or NULL/blank ``ai_version``/``prompt_version``/``processing_time``,
the migration raises and refuses to proceed. Only when all rows carry real values
are the NOT NULL constraints enforced and the ``unknown`` server_default dropped.

Backfill procedure for a deployed database with legacy candidates: before
upgrading past ``a0_ai_metadata_fields``, an operator must run a controlled,
auditable ``UPDATE`` that sets real ``ai_model``/``ai_version``/``prompt_version``/
``processing_time`` values sourced from the extractor run log (no fabricated
placeholders). This migration then verifies that backfill is complete.

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
    bind = op.get_bind()
    missing = bind.execute(
        sa.text(
            "SELECT count(*) FROM candidate_extractions "
            "WHERE ai_model IS NULL OR length(trim(ai_model)) = 0 "
            "OR lower(trim(ai_model)) = 'unknown' "
            "OR ai_version IS NULL OR length(trim(ai_version)) = 0 "
            "OR prompt_version IS NULL OR length(trim(prompt_version)) = 0 "
            "OR processing_time IS NULL"
        )
    ).scalar()
    if missing:
        raise RuntimeError(
            f"{missing} candidate_extraction row(s) lack real AI metadata "
            f"(ai_model/ai_version/prompt_version/processing_time). "
            f"Provide an auditable backfill source before migrating; "
            f"refusing to fabricate source facts."
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
        batch_op.create_check_constraint(
            "ck_candidate_ai_metadata",
            "length(trim(ai_model)) > 0 AND length(trim(ai_version)) > 0 "
            "AND length(trim(prompt_version)) > 0 AND processing_time >= 0 "
            "AND lower(trim(ai_model)) <> 'unknown'",
        )


def downgrade() -> None:
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.drop_constraint(
            "ck_candidate_ai_metadata", type_="check"
        )
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
