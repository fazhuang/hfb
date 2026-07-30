"""P0-1: Fix verified_by column — VARCHAR(36) + FK to users.id ON DELETE SET NULL

Revision ID: p0_1_verified_by_fk
Revises: p0_final_tei_fk_compiled_from
Create Date: 2026-07-04

Changes:
  - Alter verified_by from VARCHAR(100) (no FK) to VARCHAR(36) with FK → users.id
  - Clean illegal data: verified_by referencing nonexistent users → NULL + unverified
  - Downgrade: drop FK, restore VARCHAR(100) without FK
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "p0_1_verified_by_fk"
down_revision: str | None = "p0_final_tei_fk_compiled_from"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Clean illegal data: verified_by that doesn't reference a real user
    conn = op.get_bind()

    # Find relations with verified_by that doesn't match any user.id
    result = conn.execute(
        text(
            "SELECT id FROM entity_relations "
            "WHERE verified_by IS NOT NULL "
            "AND verified_by NOT IN (SELECT id FROM users)"
        )
    )
    orphan_ids = [row[0] for row in result.fetchall()]

    if orphan_ids:
        # Reset these to unverified state
        placeholders = ",".join([f":id_{i}" for i in range(len(orphan_ids))])
        params = {f"id_{i}": oid for i, oid in enumerate(orphan_ids)}
        conn.execute(
            text(
                f"UPDATE entity_relations "
                f"SET verified_by = NULL, verified_at = NULL, "
                f"evidence_status = 'unverified' "
                f"WHERE id IN ({placeholders})"
            ),
            params,
        )

    # 2. Handle verified_by = '' (empty string) — treat as NULL
    conn.execute(
        text(
            "UPDATE entity_relations "
            "SET verified_by = NULL, verified_at = NULL, "
            "evidence_status = 'unverified' "
            "WHERE verified_by = ''"
        )
    )

    # 3. SQLite batch migration: rebuild column as VARCHAR(36) + FK
    with op.batch_alter_table("entity_relations") as batch_op:
        # Drop existing FK if any (in case of partial prior migration)
        # SQLite batch mode recreates the table, so we just redefine the column
        batch_op.alter_column(
            "verified_by",
            existing_type=sa.String(100),
            type_=sa.String(36),
            nullable=True,
            existing_nullable=True,
        )
        batch_op.create_foreign_key(
            "fk_entity_relations_verified_by_users",
            "users",
            ["verified_by"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.drop_constraint(
            "fk_entity_relations_verified_by_users",
            type_="foreignkey",
        )
        batch_op.alter_column(
            "verified_by",
            existing_type=sa.String(36),
            type_=sa.String(100),
            nullable=True,
            existing_nullable=True,
        )
