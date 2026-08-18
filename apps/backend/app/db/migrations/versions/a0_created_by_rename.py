"""Phase A0 — rename candidate_extractions.created_by_user_id to created_by.

Aligns the field with HFB-DEV-0505 §7 (``created_by``). SQLite and PostgreSQL
both support ``ALTER TABLE ... RENAME COLUMN``, so this uses a direct rename
(no batch recreation).

Revision ID: a0_created_by_rename
Revises: a0_ai_metadata_fields
Create Date: 2026-08-17
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = "a0_created_by_rename"
down_revision: str | None = "a0_ai_metadata_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "candidate_extractions", "created_by_user_id", new_column_name="created_by"
    )
    op.drop_index(
        "ix_candidate_extractions_created_by_user_id",
        table_name="candidate_extractions",
    )
    op.create_index(
        "ix_candidate_extractions_created_by",
        "candidate_extractions",
        ["created_by"],
    )


def downgrade() -> None:
    op.alter_column(
        "candidate_extractions", "created_by", new_column_name="created_by_user_id"
    )
    op.drop_index(
        "ix_candidate_extractions_created_by", table_name="candidate_extractions"
    )
    op.create_index(
        "ix_candidate_extractions_created_by_user_id",
        "candidate_extractions",
        ["created_by_user_id"],
    )
