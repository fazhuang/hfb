"""add institution

Revision ID: a1b2c3d4e5f6
Revises: 221e630d3f7b
Create Date: 2026-06-30 18:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '221e630d3f7b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'institutions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(300), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('location', sa.String(300), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "type IN ('research', 'university', 'archive', 'institution')",
            name='ck_institutions_type',
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'archived', 'deleted')",
            name='ck_institutions_status',
        ),
    )
    op.create_index('idx_institutions_name', 'institutions', ['name'])
    op.create_index('idx_institutions_type', 'institutions', ['type'])


def downgrade() -> None:
    op.drop_table('institutions')
