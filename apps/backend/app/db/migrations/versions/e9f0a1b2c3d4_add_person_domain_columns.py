"""add Person research-domain columns (domain_status, anchor_path,
research_relation_role, domain_relation_summary)

Revision ID: e9f0a1b2c3d4
Revises: d8e9f0a1b2c3
Create Date: 2026-08-13 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e9f0a1b2c3d4"
down_revision: str | None = "d8e9f0a1b2c3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("persons") as batch_op:
        batch_op.add_column(
            sa.Column(
                "domain_status",
                sa.String(50),
                nullable=False,
                server_default="pending",
                comment="研究域状态: pending/verified/excluded",
            ),
        )
        batch_op.add_column(
            sa.Column(
                "anchor_path",
                sa.Text(),
                nullable=True,
                comment="锚点回溯路径 JSON 序列",
            ),
        )
        batch_op.add_column(
            sa.Column(
                "research_relation_role",
                sa.String(100),
                nullable=True,
                comment=(
                    "研究域角色: huangfu_mi_self/master_predecessor/"
                    "friend_contemporary/annotator_editor/"
                    "transmission_scholar/modern_researcher"
                ),
            ),
        )
        batch_op.add_column(
            sa.Column(
                "domain_relation_summary",
                sa.Text(),
                nullable=True,
                comment="皇甫谧研究域关系摘要",
            ),
        )


def downgrade() -> None:
    with op.batch_alter_table("persons") as batch_op:
        batch_op.drop_column("domain_relation_summary")
        batch_op.drop_column("research_relation_role")
        batch_op.drop_column("anchor_path")
        batch_op.drop_column("domain_status")
