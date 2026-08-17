"""Phase A0 standards — CandidateExtraction common fields + audit-log evidence FK.

Adds the HFB-DEV-0505 §7 common business-table fields (version/updated_by/
metadata_id) to ``candidate_extractions`` and the missing FK on
``candidate_audit_logs.published_evidence_id``.

Revision ID: phase_a0_standards_common_fields
Revises: phase_a0_candidate_extraction
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = "phase_a0_standards_common_fields"
down_revision: str | None = "phase_a0_candidate_extraction"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.add_column(
            sa.Column(
                "version",
                sa.Integer(),
                nullable=False,
                server_default="1",
                comment="模型修订版本号 (乐观并发控制)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_by",
                sa.String(36),
                nullable=True,
                comment="最后修改人 user ID",
            )
        )
        batch_op.add_column(
            sa.Column(
                "metadata_id",
                sa.String(36),
                nullable=True,
                comment="关联元数据记录 ID (Metadata 表落地后建立 FK)",
            )
        )
        batch_op.create_foreign_key(
            "fk_candidate_extractions_updated_by",
            "users",
            ["updated_by"],
            ["id"],
            ondelete="SET NULL",
        )

    with op.batch_alter_table("candidate_audit_logs") as batch_op:
        batch_op.create_foreign_key(
            "fk_candidate_audit_logs_published_evidence",
            "evidences",
            ["published_evidence_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("candidate_audit_logs") as batch_op:
        batch_op.drop_constraint(
            "fk_candidate_audit_logs_published_evidence", type_="foreignkey"
        )

    with op.batch_alter_table("candidate_extractions") as batch_op:
        batch_op.drop_constraint(
            "fk_candidate_extractions_updated_by", type_="foreignkey"
        )
        batch_op.drop_column("metadata_id")
        batch_op.drop_column("updated_by")
        batch_op.drop_column("version")
