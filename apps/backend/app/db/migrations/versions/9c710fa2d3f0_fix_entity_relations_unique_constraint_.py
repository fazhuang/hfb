"""fix entity_relations unique constraint to active-only

Revision ID: 9c710fa2d3f0
Revises: e7f8a9b0c1d2
Create Date: 2026-07-02 03:17:35.777921

Sprint 3 P0-6: Replace the global unique index with a partial unique index
that only enforces uniqueness among active (is_deleted=false) rows.
This allows soft-deleted relations to coexist with re-created ones.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "9c710fa2d3f0"
down_revision: str | None = "e7f8a9b0c1d2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop the old global unique index
    op.drop_index("ix_entity_relations_dedup", table_name="entity_relations")

    # 2. Create a new partial unique index that only covers active rows.
    # SQLite does not support partial indexes natively with the ORM, so
    # we use raw SQL and branch on the backend dialect.
    # PostgreSQL: CREATE UNIQUE INDEX ... WHERE is_deleted = false
    # SQLite: CREATE UNIQUE INDEX ... WHERE is_deleted = 0

    conn = op.get_bind()
    dialect_name = conn.dialect.name

    if dialect_name == "postgresql":
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX ix_entity_relations_active_dedup "
                "ON entity_relations (source_entity_type, source_entity_id, "
                "target_entity_type, target_entity_id, relation_type) "
                "WHERE is_deleted = false"
            )
        )
    else:
        # SQLite and others — use WHERE is_deleted = 0 (SQLite stores bool as int)
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX ix_entity_relations_active_dedup "
                "ON entity_relations (source_entity_type, source_entity_id, "
                "target_entity_type, target_entity_id, relation_type) "
                "WHERE is_deleted = 0"
            )
        )


def downgrade() -> None:
    # Drop the partial index
    op.drop_index("ix_entity_relations_active_dedup", table_name="entity_relations")

    # Restore the old global index
    op.create_index(
        "ix_entity_relations_dedup",
        "entity_relations",
        [
            "source_entity_type",
            "source_entity_id",
            "target_entity_type",
            "target_entity_id",
            "relation_type",
        ],
        unique=True,
    )
