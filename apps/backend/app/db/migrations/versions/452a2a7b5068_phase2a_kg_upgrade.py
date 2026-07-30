"""Phase 2a: knowledge graph upgrade — evidence_level + syndrome + indicates

Adds evidence_level column to entity_relations with a CHECK constraint.
Adds 'syndrome' to entity type CHECK constraints (source/target/tcm).
Adds 'indicates' to relation type CHECK constraint.

Revision ID: 452a2a7b5068
Revises: p0_1_verified_by_fk
Create Date: 2026-07-05 02:15:44.740636
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "452a2a7b5068"
down_revision: str | None = "p0_1_verified_by_fk"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Add evidence_level column + update constraints on entity_relations
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.add_column(
            sa.Column("evidence_level", sa.Integer(), nullable=False, server_default="0")
        )

        # Drop old CHECK constraints (named constraints from p0p4p5p6 migration)
        batch_op.drop_constraint("ck_entity_relations_source_type", type_="check")
        batch_op.drop_constraint("ck_entity_relations_target_type", type_="check")
        batch_op.drop_constraint("ck_entity_relations_relation_type", type_="check")

        # Recreate with 'syndrome' and 'indicates' added
        batch_op.create_check_constraint(
            "ck_entity_relations_source_type",
            "source_entity_type IN ('person','book','version','passage',"
            "'text','herb','prescription','meridian','symptom','syndrome')",
        )
        batch_op.create_check_constraint(
            "ck_entity_relations_target_type",
            "target_entity_type IN ('person','book','version','passage',"
            "'text','herb','prescription','meridian','symptom','syndrome')",
        )
        batch_op.create_check_constraint(
            "ck_entity_relations_relation_type",
            "relation_type IN ('authored','compiled','compiled_from',"
            "'commented_on','cited_in','studied','compared','referenced',"
            "'related_to','contains','treats','corresponds_to','indicates')",
        )
        batch_op.create_check_constraint(
            "ck_entity_relations_level",
            "evidence_level IN (0, 1, 2, 3, 4)",
        )

    # 2. Update tcm_entities CHECK constraint to include 'syndrome'
    with op.batch_alter_table("tcm_entities") as batch_op:
        batch_op.drop_constraint("ck_tcm_entities_entity_type", type_="check")
        batch_op.create_check_constraint(
            "ck_tcm_entities_entity_type",
            "entity_type IN ('person','book','version','passage',"
            "'text','herb','prescription','meridian','symptom','syndrome')",
        )


def downgrade() -> None:
    # 1. Revert tcm_entities constraint (remove 'syndrome')
    with op.batch_alter_table("tcm_entities") as batch_op:
        batch_op.drop_constraint("ck_tcm_entities_entity_type", type_="check")
        batch_op.create_check_constraint(
            "ck_tcm_entities_entity_type",
            "entity_type IN ('person','book','version','passage',"
            "'text','herb','prescription','meridian','symptom')",
        )

    # 2. Revert entity_relations constraints + drop evidence_level
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.drop_constraint("ck_entity_relations_level", type_="check")
        batch_op.drop_constraint("ck_entity_relations_relation_type", type_="check")
        batch_op.drop_constraint("ck_entity_relations_target_type", type_="check")
        batch_op.drop_constraint("ck_entity_relations_source_type", type_="check")

        # Restore old constraints (without 'syndrome'/'indicates')
        batch_op.create_check_constraint(
            "ck_entity_relations_source_type",
            "source_entity_type IN ('person','book','version','passage',"
            "'text','herb','prescription','meridian','symptom')",
        )
        batch_op.create_check_constraint(
            "ck_entity_relations_target_type",
            "target_entity_type IN ('person','book','version','passage',"
            "'text','herb','prescription','meridian','symptom')",
        )
        batch_op.create_check_constraint(
            "ck_entity_relations_relation_type",
            "relation_type IN ('authored','compiled','compiled_from',"
            "'commented_on','cited_in','studied','compared','referenced',"
            "'related_to','contains','treats','corresponds_to')",
        )

        batch_op.drop_column("evidence_level")
