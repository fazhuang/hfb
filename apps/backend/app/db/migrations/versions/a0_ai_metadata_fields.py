"""Phase A0 — AI metadata fields (HFB-DAT-0303 §8).

Adds ai_model/ai_version/prompt_version/processing_time to candidate_extractions
and makes candidate_extraction_metadata.payload NOT NULL.

Revision ID: a0_ai_metadata_fields
Revises: a0_audit_insert_trigger
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "a0_ai_metadata_fields"
down_revision: str | None = "a0_audit_insert_trigger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "ai_model",
                sa.String(200),
                nullable=False,
                server_default="unknown",
                comment="AI 模型名称 (规则抽取则填 extractor 标识)",
            )
        )
        batch_op.add_column(
            sa.Column("ai_version", sa.String(100), nullable=True, comment="AI 模型版本")
        )
        batch_op.add_column(
            sa.Column(
                "prompt_version", sa.String(100), nullable=True, comment="Prompt 版本"
            )
        )
        batch_op.add_column(
            sa.Column(
                "processing_time",
                sa.Float(),
                nullable=True,
                comment="处理耗时 (秒)",
            )
        )

    # Backfill NULL payloads, then enforce NOT NULL.
    op.execute(
        "UPDATE candidate_extraction_metadata SET payload = '{}' WHERE payload IS NULL"
    )
    with op.batch_alter_table("candidate_extraction_metadata") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.JSON(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("candidate_extraction_metadata") as batch_op:
        batch_op.alter_column("payload", existing_type=sa.JSON(), nullable=True)

    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.drop_column("processing_time")
        batch_op.drop_column("prompt_version")
        batch_op.drop_column("ai_version")
        batch_op.drop_column("ai_model")
