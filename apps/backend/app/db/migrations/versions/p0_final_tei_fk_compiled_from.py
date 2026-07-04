"""P0-3/5/6 final: compiled_from ontology + TEI ForeignKeys + server_default fix

Revision ID: p0_final_tei_fk_compiled_from
Revises: p0p4p5p6_evidence_tei_ontology
Create Date: 2026-07-04

Changes:
  P0-3: compiled_from relation type added to ontology CHECK
  P0-5: real FK constraints on text_sentences, text_tokens, textual_variants
         plus unique constraints on (passage_id, order), (sentence_id, order)
         plus CHECK on verification_status and variant_type
         plus offset CHECK (end_offset >= start_offset)
  P0-6: server_default fixed to use sa.text("'unverified'") — no extra quotes
"""

from typing import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "p0_final_tei_fk_compiled_from"
down_revision: str | None = "p0p4p5p6_evidence_tei_ontology"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VALID_ENTITY_TYPES = (
    "person", "book", "version", "passage", "text",
    "herb", "prescription", "meridian", "symptom",
)
VALID_RELATION_TYPES = (
    "authored", "compiled", "compiled_from", "commented_on", "cited_in",
    "studied", "compared", "referenced", "related_to",
    "contains", "treats", "corresponds_to",
)
VALID_EVIDENCE_STATUS = ("unverified", "verified", "rejected")
VALID_VARIANT_TYPES = ("substitution", "addition", "deletion", "transposition")


def upgrade() -> None:
    # ---- P0-3: Drop old relation_type CHECK, add new one with compiled_from ----
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.drop_constraint("ck_entity_relations_relation_type")
        batch_op.create_check_constraint(
            "ck_entity_relations_relation_type",
            f"relation_type IN {str(VALID_RELATION_TYPES)}",
        )

    # ---- P0-6: Fix server_default for evidence_status ----
    # SQLite stores '''unverified''' when server_default="'unverified'" is passed as string.
    # We must ALTER the column to fix this. In batch mode we recreate the table.
    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.alter_column(
            "evidence_status",
            existing_type=sa.String(20),
            existing_nullable=False,
            server_default=sa.text("'unverified'"),
        )

    with op.batch_alter_table("textual_variants") as batch_op:
        batch_op.alter_column(
            "verification_status",
            existing_type=sa.String(20),
            existing_nullable=False,
            server_default=sa.text("'unverified'"),
        )

    # ---- P0-5: TEI ForeignKeys ----
    # SQLite batch mode: recreate tables with FK constraints

    # text_sentences: FK to passages
    # Drop old index first since it gets recreated
    with op.batch_alter_table("text_sentences") as batch_op:
        batch_op.create_foreign_key(
            "fk_text_sentences_passage",
            "passages", ["passage_id"], ["id"],
            ondelete="CASCADE",
        )
        # Unique: passage_id + order
        batch_op.create_unique_constraint(
            "uq_text_sentences_passage_order",
            ["passage_id", "order"],
        )

    # text_tokens: FK to text_sentences
    with op.batch_alter_table("text_tokens") as batch_op:
        batch_op.create_foreign_key(
            "fk_text_tokens_sentence",
            "text_sentences", ["sentence_id"], ["id"],
            ondelete="CASCADE",
        )
        batch_op.create_unique_constraint(
            "uq_text_tokens_sentence_order",
            ["sentence_id", "order"],
        )
        # offset check
        batch_op.create_check_constraint(
            "ck_text_tokens_offsets",
            "end_offset IS NULL OR start_offset IS NULL OR end_offset >= start_offset",
        )

    # textual_variants: FKs to versions, passages, text_sentences
    with op.batch_alter_table("textual_variants") as batch_op:
        batch_op.create_foreign_key(
            "fk_textual_variants_source_version",
            "versions", ["source_version_id"], ["id"],
        )
        batch_op.create_foreign_key(
            "fk_textual_variants_target_version",
            "versions", ["target_version_id"], ["id"],
        )
        batch_op.create_foreign_key(
            "fk_textual_variants_source_passage",
            "passages", ["source_passage_id"], ["id"],
        )
        batch_op.create_foreign_key(
            "fk_textual_variants_target_passage",
            "passages", ["target_passage_id"], ["id"],
        )
        batch_op.create_foreign_key(
            "fk_textual_variants_source_sentence",
            "text_sentences", ["source_sentence_id"], ["id"],
        )
        batch_op.create_foreign_key(
            "fk_textual_variants_target_sentence",
            "text_sentences", ["target_sentence_id"], ["id"],
        )
        batch_op.create_check_constraint(
            "ck_textual_variants_verification_status",
            f"verification_status IN {str(VALID_EVIDENCE_STATUS)}",
        )
        batch_op.create_check_constraint(
            "ck_textual_variants_variant_type",
            f"variant_type IS NULL OR variant_type IN {str(VALID_VARIANT_TYPES)}",
        )

    # Fix any existing '''unverified''' values in entity_relations
    op.execute(
        "UPDATE entity_relations SET evidence_status = 'unverified' "
        "WHERE evidence_status = '''unverified'''"
    )
    op.execute(
        "UPDATE textual_variants SET verification_status = 'unverified' "
        "WHERE verification_status = '''unverified'''"
    )


def downgrade() -> None:
    # Fix bad values again if downgrading
    op.execute(
        "UPDATE entity_relations SET evidence_status = 'unverified' "
        "WHERE evidence_status = '''unverified'''"
    )
    op.execute(
        "UPDATE textual_variants SET verification_status = 'unverified' "
        "WHERE verification_status = '''unverified'''"
    )

    with op.batch_alter_table("textual_variants") as batch_op:
        batch_op.drop_constraint("ck_textual_variants_variant_type")
        batch_op.drop_constraint("ck_textual_variants_verification_status")
        batch_op.drop_constraint("fk_textual_variants_target_sentence")
        batch_op.drop_constraint("fk_textual_variants_source_sentence")
        batch_op.drop_constraint("fk_textual_variants_target_passage")
        batch_op.drop_constraint("fk_textual_variants_source_passage")
        batch_op.drop_constraint("fk_textual_variants_target_version")
        batch_op.drop_constraint("fk_textual_variants_source_version")

    with op.batch_alter_table("text_tokens") as batch_op:
        batch_op.drop_constraint("ck_text_tokens_offsets")
        batch_op.drop_constraint("uq_text_tokens_sentence_order")
        batch_op.drop_constraint("fk_text_tokens_sentence")

    with op.batch_alter_table("text_sentences") as batch_op:
        batch_op.drop_constraint("uq_text_sentences_passage_order")
        batch_op.drop_constraint("fk_text_sentences_passage")

    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.alter_column(
            "evidence_status",
            existing_type=sa.String(20),
            existing_nullable=False,
            server_default="'unverified'",
        )

    with op.batch_alter_table("textual_variants") as batch_op:
        batch_op.alter_column(
            "verification_status",
            existing_type=sa.String(20),
            existing_nullable=False,
            server_default="'unverified'",
        )

    with op.batch_alter_table("entity_relations") as batch_op:
        batch_op.drop_constraint("ck_entity_relations_relation_type")
        batch_op.create_check_constraint(
            "ck_entity_relations_relation_type",
            f"relation_type IN {str(('authored', 'compiled', 'commented_on', 'cited_in', 'studied', 'compared', 'referenced', 'related_to', 'contains', 'treats', 'corresponds_to'))}",
        )
