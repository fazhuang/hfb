"""add tcm_entities table

Revision ID: a1b2c3d4e5f6
Revises: f8a9b0c1d2e3
Create Date: 2026-07-04

This migration creates the generic tcm_entities table for ontology types
that don't have dedicated ORM models (herb, prescription, meridian, symptom).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "f8a9b0c1d2e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "tcm_entities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("entity_type", sa.String(50), nullable=False, index=True),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("name_zh", sa.String(300), nullable=True),
        sa.Column("properties", sa.JSON, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("external_ref", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("ix_tcm_entities_type_name", "tcm_entities", ["entity_type", "name"])


def downgrade() -> None:
    op.drop_index("ix_tcm_entities_type_name")
    op.drop_table("tcm_entities")
