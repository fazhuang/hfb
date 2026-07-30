"""add evidence columns to entity_relations

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-07-02

Sprint 3 P0: Adds structured corpus evidence columns to entity_relations.
  - evidence_document_id: source document for the evidence quote
  - evidence_chunk_id: exact chunk containing the evidence
  - evidence_quote: exact contiguous substring from chunk.content
  - evidence_citation: formatted citation [document_id:chunk_id]
Also adds a dedup index.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e7f8a9b0c1d2"
down_revision: str | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "entity_relations",
        sa.Column(
            "evidence_document_id",
            sa.String(36),
            nullable=True,
            comment="证据来源 document ID",
        ),
    )
    op.add_column(
        "entity_relations",
        sa.Column(
            "evidence_chunk_id",
            sa.String(36),
            nullable=True,
            comment="证据来源 chunk ID",
        ),
    )
    op.add_column(
        "entity_relations",
        sa.Column(
            "evidence_quote",
            sa.Text(),
            nullable=True,
            comment="chunk 中的确切引用文本",
        ),
    )
    op.add_column(
        "entity_relations",
        sa.Column(
            "evidence_citation",
            sa.String(200),
            nullable=True,
            comment="格式化引用 [document_id:chunk_id]",
        ),
    )
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


def downgrade() -> None:
    op.drop_index("ix_entity_relations_dedup", table_name="entity_relations")
    op.drop_column("entity_relations", "evidence_citation")
    op.drop_column("entity_relations", "evidence_quote")
    op.drop_column("entity_relations", "evidence_chunk_id")
    op.drop_column("entity_relations", "evidence_document_id")
