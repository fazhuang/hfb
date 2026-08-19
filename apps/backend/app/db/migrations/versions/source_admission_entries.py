"""Source admission entries table (HFB-DAT-0306 §3 online checklist).

Revision ID: source_admission_entries
Revises: a0_core_metadata_fields
Create Date: 2026-08-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "source_admission_entries"
down_revision: str | None = "a0_core_metadata_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "source_admission_entries",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("entry_key", sa.String(20), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("source_uri", sa.String(2000), nullable=False),
        sa.Column("authorization_basis", sa.String(500), nullable=False),
        sa.Column("version_label", sa.String(500), nullable=False),
        sa.Column("import_scope", sa.String(500), nullable=False),
        sa.Column("binding_plan", sa.Text(), nullable=False),
        sa.Column("risk_note", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="submitted",
        ),
        sa.Column("submitted_by", sa.String(36), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reviewed_by", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["submitted_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_sae_entry_key", "source_admission_entries", ["entry_key"], unique=True
    )
    op.create_index("idx_sae_status", "source_admission_entries", ["status"])


def downgrade() -> None:
    op.drop_index("idx_sae_status", table_name="source_admission_entries")
    op.drop_index("idx_sae_entry_key", table_name="source_admission_entries")
    op.drop_table("source_admission_entries")
