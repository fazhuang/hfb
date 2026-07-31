"""fulltext compliance: Document + FulltextIngestionAudit (Context 21)

Revision ID: c21f1a2b3c4d
Revises: a4b5c6d7e8f9
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c21f1a2b3c4d"
down_revision: str | None = "a4b5c6d7e8f9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- documents table: new compliance columns ---
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "copyright_status",
                sa.String(50),
                nullable=False,
                server_default="unknown",
                comment="版权状态: public_domain|open_access|licensed|user_uploaded_with_permission|unknown|metadata_only|forbidden_fulltext|commercial_restricted|pirated",
            )
        )
        batch_op.add_column(
            sa.Column(
                "license_type",
                sa.String(100),
                nullable=True,
                comment="许可类型: CC-BY|CC-BY-NC|CC-BY-SA|CC0|custom",
            )
        )
        batch_op.add_column(
            sa.Column(
                "authorization_basis",
                sa.String(200),
                nullable=True,
                comment="授权依据 (license URL / agreement ref / basis statement)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "review_status",
                sa.String(50),
                nullable=False,
                server_default="pending_review",
                comment="审核状态: pending_review|under_review|approved|rejected",
            )
        )
        batch_op.add_column(
            sa.Column(
                "reviewed_by",
                sa.String(36),
                nullable=True,
                comment="审核人 user ID",
            )
        )
        batch_op.add_column(
            sa.Column(
                "reviewed_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="审核时间",
            )
        )
        batch_op.add_column(
            sa.Column(
                "rag_enabled",
                sa.Boolean(),
                nullable=False,
                server_default="false",
                comment="是否允许进入 RAG",
            )
        )
        batch_op.add_column(
            sa.Column(
                "content_checksum",
                sa.String(64),
                nullable=True,
                comment="全文 SHA-256 checksum",
            )
        )
        batch_op.add_column(
            sa.Column(
                "source_name",
                sa.String(200),
                nullable=True,
                comment="摄入来源名称",
            )
        )
        batch_op.add_column(
            sa.Column(
                "withdrawn_at",
                sa.DateTime(timezone=True),
                nullable=True,
                comment="撤回时间",
            )
        )
        batch_op.add_column(
            sa.Column(
                "withdraw_reason",
                sa.Text(),
                nullable=True,
                comment="撤回原因",
            )
        )

    # --- fulltext_ingestion_audit table ---
    op.create_table(
        "fulltext_ingestion_audit",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "action",
            sa.String(50),
            nullable=False,
            comment="fulltext_ingest | reject | skip | withdraw | chunk_delete | rag_disabled",
        ),
        sa.Column(
            "status",
            sa.String(50),
            nullable=False,
            server_default="success",
            comment="success | skipped | rejected | withdrawn",
        ),
        sa.Column("source_url", sa.String(2000), nullable=True, comment="来源 URL"),
        sa.Column("source_name", sa.String(200), nullable=True, comment="摄入来源名称"),
        sa.Column("copyright_status", sa.String(50), nullable=True, comment="版权状态"),
        sa.Column(
            "authorization_basis", sa.String(200), nullable=True, comment="授权依据"
        ),
        sa.Column("license_type", sa.String(100), nullable=True, comment="许可类型"),
        sa.Column("review_status", sa.String(50), nullable=True, comment="审核状态"),
        sa.Column(
            "reviewed_by", sa.String(36), nullable=True, comment="审核人 user ID"
        ),
        sa.Column(
            "reviewed_at", sa.DateTime(timezone=True), nullable=True, comment="审核时间"
        ),
        sa.Column(
            "checksum",
            sa.String(64),
            nullable=True,
            comment="SHA-256 of full-text content",
        ),
        sa.Column(
            "result_entity_type", sa.String(50), nullable=True, comment="结果实体类型"
        ),
        sa.Column(
            "result_entity_id", sa.String(36), nullable=True, comment="结果实体 ID"
        ),
        sa.Column("reject_reason", sa.Text(), nullable=True, comment="拒绝/跳过原因"),
        sa.Column("skipped_reason", sa.Text(), nullable=True, comment="跳过原因"),
        sa.Column("actor_id", sa.String(36), nullable=True, comment="操作人 user ID"),
        sa.Column("details", sa.JSON(), nullable=True, comment="自由格式上下文"),
    )


def downgrade() -> None:
    op.drop_table("fulltext_ingestion_audit")
    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_column("withdraw_reason")
        batch_op.drop_column("withdrawn_at")
        batch_op.drop_column("source_name")
        batch_op.drop_column("content_checksum")
        batch_op.drop_column("rag_enabled")
        batch_op.drop_column("reviewed_at")
        batch_op.drop_column("reviewed_by")
        batch_op.drop_column("review_status")
        batch_op.drop_column("authorization_basis")
        batch_op.drop_column("license_type")
        batch_op.drop_column("copyright_status")
