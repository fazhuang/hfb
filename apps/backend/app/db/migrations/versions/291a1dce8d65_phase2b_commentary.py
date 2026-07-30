"""phase2b_commentary — Create commentaries table for 注疏链

Revision ID: 291a1dce8d65
Revises: d6575d7baf29
Create Date: 2026-07-05 16:01:11.097883
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = '291a1dce8d65'
down_revision: str | None = 'd6575d7baf29'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('commentaries',
        # BaseModel columns
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        # Commentary columns
        sa.Column('passage_id', sa.String(36), nullable=False, comment='所注段落 ID'),
        sa.Column('version_id', sa.String(36), nullable=True, comment='所注版本 ID（夹注可能无版本信息）'),
        sa.Column('author_id', sa.String(36), nullable=True, comment='注者 ID'),
        sa.Column('commentary_type', sa.String(30), nullable=False, comment='interlinear_gloss | end_of_passage | sub_commentary | commentary_work | critique'),
        sa.Column('layer', sa.String(20), nullable=False, comment='年代层: han, tang, song, ming, qing, modern'),
        sa.Column('content_text', sa.Text(), nullable=False, comment='注文内容'),
        sa.Column('target_position_start', sa.Integer(), nullable=True, comment='段落中起始字符偏移'),
        sa.Column('target_position_end', sa.Integer(), nullable=True, comment='段落中结束字符偏移'),
        sa.Column('parent_id', sa.String(36), nullable=True, comment='自引用 — 回应另一条注疏'),
        sa.Column('relation_type', sa.String(20), nullable=True, comment='supplements | refutes | expands | annotates | interprets'),
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "commentary_type IN ('interlinear_gloss', 'end_of_passage', "
            "'sub_commentary', 'commentary_work', 'critique')",
            name='ck_commentaries_type',
        ),
        sa.CheckConstraint(
            "layer IN ('han', 'tang', 'song', 'ming', 'qing', 'modern')",
            name='ck_commentaries_layer',
        ),
        sa.CheckConstraint(
            "relation_type IS NULL OR relation_type IN "
            "('supplements', 'refutes', 'expands', 'annotates', 'interprets')",
            name='ck_commentaries_relation',
        ),
        # Foreign keys
        sa.ForeignKeyConstraint(['passage_id'], ['passages.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['version_id'], ['versions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['author_id'], ['persons.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['parent_id'], ['commentaries.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_commentaries_passage_id'), 'commentaries', ['passage_id'], unique=False)
    op.create_index(op.f('ix_commentaries_parent_id'), 'commentaries', ['parent_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_commentaries_passage_id'), table_name='commentaries')
    op.drop_index(op.f('ix_commentaries_parent_id'), table_name='commentaries')
    op.drop_table('commentaries')
