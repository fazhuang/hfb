"""Phase A0 standards — required indexes + unique constraints.

Adds the HFB-DEV-0505 §15 required indexes (version_id/status) and enforces the
Metadata 1:1 contract (unique metadata_id on candidate_extractions, unique
(entity_type, entity_id) on metadata).

Revision ID: phase_a0_standards_indexes
Revises: phase_a0_standards_metadata
Create Date: 2026-08-17
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = "phase_a0_standards_indexes"
down_revision: str | None = "phase_a0_standards_metadata"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_candidate_extractions_version_id",
        "candidate_extractions",
        ["version_id"],
    )
    op.create_index(
        "ix_candidate_extractions_status",
        "candidate_extractions",
        ["status"],
    )
    op.create_index(
        "ix_candidate_extractions_metadata_id",
        "candidate_extractions",
        ["metadata_id"],
        unique=True,
    )
    op.create_index(
        "uq_metadata_entity",
        "metadata",
        ["entity_type", "entity_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_metadata_entity", table_name="metadata")
    op.drop_index("ix_candidate_extractions_metadata_id", table_name="candidate_extractions")
    op.drop_index("ix_candidate_extractions_status", table_name="candidate_extractions")
    op.drop_index("ix_candidate_extractions_version_id", table_name="candidate_extractions")
