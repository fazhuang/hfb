"""Phase A0 standards — Metadata table + candidate_extractions.metadata_id FK.

Revision ID: phase_a0_standards_metadata
Revises: phase_a0_standards_common_fields
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "phase_a0_standards_metadata"
down_revision: str | None = "phase_a0_standards_common_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "metadata",
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_metadata_entity_id", "metadata", ["entity_id"])

    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.create_foreign_key(
            "fk_candidate_extractions_metadata",
            "metadata",
            ["metadata_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.drop_constraint(
            "fk_candidate_extractions_metadata", type_="foreignkey"
        )

    op.drop_index("ix_metadata_entity_id", table_name="metadata")
    op.drop_table("metadata")
