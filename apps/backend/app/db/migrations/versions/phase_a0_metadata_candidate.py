"""Phase A0 standards — candidate-specific 1:1 metadata + remaining FK indexes.

Replaces the generic ``metadata`` table with ``candidate_extraction_metadata``
(a real 1:1 FK from metadata → candidate_extractions), drops the redundant
``candidate_extractions.metadata_id`` column, and adds the missing FK indexes.

Revision ID: phase_a0_metadata_candidate
Revises: phase_a0_standards_indexes
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "phase_a0_metadata_candidate"
down_revision: str | None = "phase_a0_standards_indexes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop the redundant candidate_extractions.metadata_id column + its FK and
    # unique index (ownership now lives on the metadata side).
    op.drop_index(
        "ix_candidate_extractions_metadata_id", table_name="candidate_extractions"
    )
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.drop_constraint(
            "fk_candidate_extractions_metadata", type_="foreignkey"
        )
        batch_op.drop_column("metadata_id")

    # Drop the old generic metadata table.
    op.drop_index("uq_metadata_entity", table_name="metadata")
    op.drop_index("ix_metadata_entity_id", table_name="metadata")
    op.drop_table("metadata")

    # Create the candidate-specific 1:1 metadata table (real FK, no polymorphic
    # entity_type/entity_id strings).
    op.create_table(
        "candidate_extraction_metadata",
        sa.Column("candidate_id", sa.String(36), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(50), server_default="active", nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_by", sa.String(36), nullable=True),
        sa.Column("updated_by", sa.String(36), nullable=True),
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
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_extractions.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_extraction_metadata_candidate_id",
        "candidate_extraction_metadata",
        ["candidate_id"],
        unique=True,
    )
    op.create_index(
        "ix_candidate_extraction_metadata_created_by",
        "candidate_extraction_metadata",
        ["created_by"],
    )
    op.create_index(
        "ix_candidate_extraction_metadata_updated_by",
        "candidate_extraction_metadata",
        ["updated_by"],
    )

    # Remaining FK indexes (HFB-DEV-0505 §15).
    op.create_index(
        "ix_candidate_extractions_created_by_user_id",
        "candidate_extractions",
        ["created_by_user_id"],
    )
    op.create_index(
        "ix_candidate_extractions_reviewed_by_user_id",
        "candidate_extractions",
        ["reviewed_by_user_id"],
    )
    op.create_index(
        "ix_candidate_extractions_published_evidence_id",
        "candidate_extractions",
        ["published_evidence_id"],
    )
    op.create_index(
        "ix_candidate_extractions_updated_by",
        "candidate_extractions",
        ["updated_by"],
    )


def downgrade() -> None:
    for idx in (
        "ix_candidate_extractions_updated_by",
        "ix_candidate_extractions_published_evidence_id",
        "ix_candidate_extractions_reviewed_by_user_id",
        "ix_candidate_extractions_created_by_user_id",
    ):
        op.drop_index(idx, table_name="candidate_extractions")

    op.drop_index(
        "ix_candidate_extraction_metadata_updated_by",
        table_name="candidate_extraction_metadata",
    )
    op.drop_index(
        "ix_candidate_extraction_metadata_created_by",
        table_name="candidate_extraction_metadata",
    )
    op.drop_index(
        "ix_candidate_extraction_metadata_candidate_id",
        table_name="candidate_extraction_metadata",
    )
    op.drop_table("candidate_extraction_metadata")

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
    op.create_index(
        "uq_metadata_entity", "metadata", ["entity_type", "entity_id"], unique=True
    )

    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.add_column(
            sa.Column("metadata_id", sa.String(36), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_candidate_extractions_metadata",
            "metadata",
            ["metadata_id"],
            ["id"],
            ondelete="SET NULL",
        )
    op.create_index(
        "ix_candidate_extractions_metadata_id",
        "candidate_extractions",
        ["metadata_id"],
        unique=True,
    )
