"""
Academic credibility — Version formal source + withdraw support

Revision ID: p2t1_formal_source
Revises: rag_evidence_binding_v2
Create Date: 2026-07-15
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "p2t1_formal_source"
down_revision: str | None = "rag_evidence_binding_v2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add withdrawn_at and withdraw_reason to versions
    with op.batch_alter_table("versions") as batch_op:
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
        batch_op.add_column(
            sa.Column(
                "is_formal_source",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="是否为正式学术可引用来源",
            )
        )
        batch_op.add_column(
            sa.Column(
                "rights_statement",
                sa.String(500),
                nullable=True,
                comment="权利/授权依据",
            )
        )
        batch_op.add_column(
            sa.Column(
                "persistent_identifier",
                sa.String(500),
                nullable=True,
                comment="稳定可核验标识",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("versions") as batch_op:
        batch_op.drop_column("persistent_identifier")
        batch_op.drop_column("rights_statement")
        batch_op.drop_column("is_formal_source")
        batch_op.drop_column("withdraw_reason")
        batch_op.drop_column("withdrawn_at")
