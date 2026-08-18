"""Phase A0 standards — candidate-specific 1:1 metadata + remaining FK indexes.

Replaces the generic ``metadata`` table with ``candidate_extraction_metadata``
(a real 1:1 FK from metadata → candidate_extractions), migrating all linked
metadata rows first, then dropping the redundant ``candidate_extractions.metadata_id``
column, and adding the missing FK indexes.

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
    # 1. Create the new candidate-specific 1:1 metadata table.
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

    # 2. Migrate every metadata row linked to a candidate (via the old
    #    candidate_extractions.metadata_id FK). Preserve id/payload/timestamps.
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO candidate_extraction_metadata
                (candidate_id, payload, status, version, created_by, updated_by,
                 id, created_at, updated_at, deleted_at, is_deleted)
            SELECT c.id, m.payload, 'active', 1, NULL, NULL,
                   m.id, m.created_at, m.updated_at, m.deleted_at, m.is_deleted
            FROM candidate_extractions c
            JOIN metadata m ON c.metadata_id = m.id
            """
        )
    )

    # 3. Integrity check: migrated count must equal the number of linked rows,
    #    AND the old table must have no unlinked/orphan rows (fail-closed on
    #    silent data loss).
    expected = bind.execute(
        sa.text(
            "SELECT count(*) FROM candidate_extractions WHERE metadata_id IS NOT NULL"
        )
    ).scalar()
    actual = bind.execute(
        sa.text("SELECT count(*) FROM candidate_extraction_metadata")
    ).scalar()
    if expected != actual:
        raise RuntimeError(
            f"metadata migration integrity check failed: "
            f"expected {expected} rows, migrated {actual}"
        )

    old_total = bind.execute(sa.text("SELECT count(*) FROM metadata")).scalar()
    if old_total != actual:
        raise RuntimeError(
            f"metadata migration would silently drop {old_total - actual} "
            f"unlinked metadata row(s); aborting (fail-closed). "
            f"Provide an explicit migration target for non-candidate metadata."
        )

    # 4. Drop the redundant metadata_id column + old generic table.
    op.drop_index(
        "ix_candidate_extractions_metadata_id", table_name="candidate_extractions"
    )
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.drop_constraint(
            "fk_candidate_extractions_metadata", type_="foreignkey"
        )
        batch_op.drop_column("metadata_id")
    op.drop_index("uq_metadata_entity", table_name="metadata")
    op.drop_index("ix_metadata_entity_id", table_name="metadata")
    op.drop_table("metadata")

    # 5. Remaining FK indexes (HFB-DEV-0505 §15).
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
    # Reverse backfill: restore the generic metadata table + metadata_id column,
    # copying candidate_extraction_metadata back into metadata.
    for idx in (
        "ix_candidate_extractions_updated_by",
        "ix_candidate_extractions_published_evidence_id",
        "ix_candidate_extractions_reviewed_by_user_id",
        "ix_candidate_extractions_created_by_user_id",
    ):
        op.drop_index(idx, table_name="candidate_extractions")

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

    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO metadata
                (id, entity_type, entity_id, payload, created_at, updated_at,
                 deleted_at, is_deleted)
            SELECT id, 'candidate_extraction', candidate_id, payload,
                   created_at, updated_at, deleted_at, is_deleted
            FROM candidate_extraction_metadata
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE candidate_extractions
            SET metadata_id = (
                SELECT id FROM candidate_extraction_metadata
                WHERE candidate_id = candidate_extractions.id
            )
            WHERE EXISTS (
                SELECT 1 FROM candidate_extraction_metadata
                WHERE candidate_id = candidate_extractions.id
            )
            """
        )
    )

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
