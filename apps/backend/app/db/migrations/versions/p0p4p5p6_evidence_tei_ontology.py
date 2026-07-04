"""P0-4/5/6: evidence provenance + TEI hierarchy + ontology DB constraints

Revision ID: p0p4p5p6_evidence_tei_ontology
Revises: a1b2c3d4e5f7
Create Date: 2026-07-04

Changes:
  P0-4: entity_relations evidence provenance + claim + verification fields
  P0-5: text_sentences, text_tokens, textual_variants tables
  P0-6: ontology CHECK constraints on entity_relations + tcm_entities
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p0p4p5p6_evidence_tei_ontology"
down_revision: str | None = "a1b2c3d4e5f7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Canonical ontology entity types for CHECK constraints
VALID_ENTITY_TYPES = (
    "person", "book", "version", "passage", "text",
    "herb", "prescription", "meridian", "symptom",
)
VALID_RELATION_TYPES = (
    "authored", "compiled", "commented_on", "cited_in",
    "studied", "compared", "referenced", "related_to",
    "contains", "treats", "corresponds_to",
)
VALID_EVIDENCE_STATUS = ("unverified", "verified", "rejected")


def upgrade() -> None:
    # ---- P0-4: entity_relations evidence provenance + claim + verification ----
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.add_column(sa.Column("evidence_version_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("evidence_passage_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("evidence_source_uri", sa.String(500), nullable=True))
        batch_op.add_column(
            sa.Column(
                "evidence_status",
                sa.String(20),
                nullable=False,
                server_default="'unverified'",
            )
        )
        batch_op.add_column(sa.Column("claim_text", sa.Text, nullable=True))
        batch_op.add_column(sa.Column("verified_by", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True))

    # ---- P0-6: ontology CHECK constraints ----
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.create_check_constraint(
            "ck_entity_relations_source_type",
            f"source_entity_type IN {str(VALID_ENTITY_TYPES)}",
        )
        batch_op.create_check_constraint(
            "ck_entity_relations_target_type",
            f"target_entity_type IN {str(VALID_ENTITY_TYPES)}",
        )
        batch_op.create_check_constraint(
            "ck_entity_relations_relation_type",
            f"relation_type IN {str(VALID_RELATION_TYPES)}",
        )
        batch_op.create_check_constraint(
            "ck_entity_relations_evidence_status",
            f"evidence_status IN {str(VALID_EVIDENCE_STATUS)}",
        )

    with op.batch_alter_table("tcm_entities") as batch_op:
        batch_op.create_check_constraint(
            "ck_tcm_entities_entity_type",
            f"entity_type IN {str(VALID_ENTITY_TYPES)}",
        )

    # ---- P0-5: TEI hierarchy tables ----

    op.create_table(
        "text_sentences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("passage_id", sa.String(36), nullable=False),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("xml_id", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("ix_text_sentences_passage_order", "text_sentences", ["passage_id", "order"])

    op.create_table(
        "text_tokens",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sentence_id", sa.String(36), nullable=False),
        sa.Column("order", sa.Integer, nullable=False),
        sa.Column("text", sa.String(50), nullable=False),
        sa.Column("lemma", sa.String(50), nullable=True),
        sa.Column("pos", sa.String(20), nullable=True),
        sa.Column("start_offset", sa.Integer, nullable=True),
        sa.Column("end_offset", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index("ix_text_tokens_sentence_order", "text_tokens", ["sentence_id", "order"])

    op.create_table(
        "textual_variants",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_version_id", sa.String(36), nullable=False),
        sa.Column("target_version_id", sa.String(36), nullable=False),
        sa.Column("source_passage_id", sa.String(36), nullable=True),
        sa.Column("target_passage_id", sa.String(36), nullable=True),
        sa.Column("source_sentence_id", sa.String(36), nullable=True),
        sa.Column("target_sentence_id", sa.String(36), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("lemma", sa.String(200), nullable=True),
        sa.Column("reading", sa.Text, nullable=False),
        sa.Column("variant_type", sa.String(50), nullable=True),
        sa.Column("apparatus", sa.Text, nullable=True),
        sa.Column("verification_status", sa.String(20), nullable=False, server_default="'unverified'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
    )
    op.create_index(
        "ix_textual_variants_versions",
        "textual_variants",
        ["source_version_id", "target_version_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_textual_variants_versions")
    op.drop_table("textual_variants")
    op.drop_index("ix_text_tokens_sentence_order")
    op.drop_table("text_tokens")
    op.drop_index("ix_text_sentences_passage_order")
    op.drop_table("text_sentences")

    with op.batch_alter_table("tcm_entities") as batch_op:
        batch_op.drop_constraint("ck_tcm_entities_entity_type")

    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.drop_constraint("ck_entity_relations_evidence_status")
        batch_op.drop_constraint("ck_entity_relations_relation_type")
        batch_op.drop_constraint("ck_entity_relations_target_type")
        batch_op.drop_constraint("ck_entity_relations_source_type")
        batch_op.drop_column("verified_at")
        batch_op.drop_column("verified_by")
        batch_op.drop_column("claim_text")
        batch_op.drop_column("evidence_status")
        batch_op.drop_column("evidence_source_uri")
        batch_op.drop_column("evidence_passage_id")
        batch_op.drop_column("evidence_version_id")
