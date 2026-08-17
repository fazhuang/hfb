"""Phase A0 — candidate extraction buffer + append-only audit log + DDL triggers.

Creates ``candidate_extractions`` and ``candidate_audit_logs``, adds
``page_image_hash_alg`` to ``document_chunks``, and installs the native
append-only triggers for the active backend dialect (PL/pgSQL on PostgreSQL,
``IS`` null-safe RAISE on SQLite).

Revision ID: phase_a0_candidate_extraction
Revises: f1a2b3c4d5e6
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

from app.db import audit_triggers

# revision identifiers
revision: str = "phase_a0_candidate_extraction"
down_revision: str | None = "f1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Postgres json lacks an equality operator; the append-only trigger compares
# these columns with IS NOT DISTINCT FROM, so they must be jsonb on Postgres.
_AUDIT_JSON = sa.JSON().with_variant(JSONB(), "postgresql")

_CANDIDATE_STATUS_CHECK = sa.CheckConstraint(
    "status IN ('pending', 'approved', 'rejected', 'modified', 'drift_invalid')",
    name="candidate_status",
)


def upgrade() -> None:
    # --- candidate_extractions ---
    op.create_table(
        "candidate_extractions",
        sa.Column("session_id", sa.String(36), nullable=False),
        sa.Column("created_by_user_id", sa.String(36), nullable=False),
        sa.Column("chunk_id", sa.String(36), nullable=False),
        sa.Column("version_id", sa.String(36), nullable=False),
        sa.Column("expected_chunk_sha256", sa.String(64), nullable=False),
        sa.Column("expected_nfc_sha256", sa.String(64), nullable=False),
        sa.Column("unicode_normalization", sa.String(10), nullable=False),
        sa.Column("start_char", sa.Integer(), nullable=False),
        sa.Column("end_char", sa.Integer(), nullable=False),
        sa.Column("exact_text", sa.Text(), nullable=False),
        sa.Column("input_snapshot", sa.JSON(), nullable=False),
        sa.Column("page_image_hash", sa.String(64), nullable=True),
        sa.Column(
            "page_image_hash_alg",
            sa.String(20),
            sa.CheckConstraint(
                "page_image_hash_alg IN ('sha256', 'sha512', 'phash')",
                name="ck_candidate_page_image_hash_alg",
            ),
            server_default="sha256",
            nullable=False,
        ),
        sa.Column(
            "extraction_type", sa.String(50), server_default="proposed_evidence", nullable=False
        ),
        sa.Column("extracted_payload", sa.JSON(), nullable=False),
        sa.Column("extractor_name", sa.String(100), nullable=False),
        sa.Column("prompt_hash", sa.String(64), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("reviewed_by_user_id", sa.String(36), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("published_evidence_id", sa.String(36), nullable=True),
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
            ["session_id"], ["research_sessions.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"], ["users.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["chunk_id"], ["document_chunks.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["version_id"], ["versions.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["reviewed_by_user_id"], ["users.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["published_evidence_id"], ["evidences.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        _CANDIDATE_STATUS_CHECK,
    )
    op.create_index(
        "ix_candidate_extractions_session_id",
        "candidate_extractions",
        ["session_id"],
    )
    op.create_index(
        "ix_candidate_extractions_chunk_id",
        "candidate_extractions",
        ["chunk_id"],
    )

    # --- candidate_audit_logs ---
    op.create_table(
        "candidate_audit_logs",
        sa.Column("id", sa.String(36), nullable=False),
        sa.Column("candidate_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("operator_id", sa.String(36), nullable=False),
        sa.Column("input_snapshot", _AUDIT_JSON, nullable=True),
        sa.Column("pre_payload", _AUDIT_JSON, nullable=True),
        sa.Column("post_payload", _AUDIT_JSON, nullable=True),
        sa.Column("published_evidence_id", sa.String(36), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_extractions.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["operator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_candidate_audit_logs_candidate_id",
        "candidate_audit_logs",
        ["candidate_id"],
    )

    # --- document_chunks: page_image_hash_alg ---
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "page_image_hash_alg",
                sa.String(20),
                sa.CheckConstraint(
                    "page_image_hash_alg IN ('sha256', 'sha512', 'phash')",
                    name="ck_chunk_page_image_hash_alg",
                ),
                server_default="sha256",
                nullable=False,
                comment="page_image_hash 的算法: sha256 | sha512 | phash",
            )
        )

    # --- native append-only triggers ---
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(audit_triggers.PG_FUNCTION_SQL)
        op.execute(audit_triggers.PG_TRIGGER_SQL)
    elif bind.dialect.name == "sqlite":
        op.execute(audit_triggers.SQLITE_NO_DELETE_SQL)
        op.execute(audit_triggers.SQLITE_NO_UPDATE_SQL)


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(audit_triggers.PG_DROP_TRIGGER_SQL)
        op.execute(audit_triggers.PG_DROP_FUNCTION_SQL)
    elif bind.dialect.name == "sqlite":
        op.execute(audit_triggers.SQLITE_DROP_TRIGGERS_SQL)

    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.drop_column("page_image_hash_alg")

    op.drop_index("ix_candidate_audit_logs_candidate_id", table_name="candidate_audit_logs")
    op.drop_table("candidate_audit_logs")
    op.drop_index("ix_candidate_extractions_chunk_id", table_name="candidate_extractions")
    op.drop_index("ix_candidate_extractions_session_id", table_name="candidate_extractions")
    op.drop_table("candidate_extractions")
