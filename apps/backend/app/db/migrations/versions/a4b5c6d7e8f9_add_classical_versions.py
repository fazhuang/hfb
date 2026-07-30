"""add_classical_versions — Classical edition catalogue table

Revision ID: a4b5c6d7e8f9
Revises: p0_final_tei_fk_compiled_from
Create Date: 2026-07-10
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = 'a4b5c6d7e8f9'
down_revision: str | None = 'a3a194fc4f8d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table('classical_versions',
        # BaseModel columns
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
        # ClassicalVersion columns
        sa.Column('work_title', sa.String(500), nullable=False, comment='著作名称'),
        sa.Column('version_name', sa.String(300), nullable=False, comment='版本名称'),
        sa.Column('dynasty', sa.String(100), nullable=True, comment='朝代'),
        sa.Column('edition_type', sa.String(100), nullable=True, comment='版本类型'),
        sa.Column('volume_count', sa.Integer(), nullable=True, comment='卷数'),
        sa.Column('repository', sa.String(500), nullable=True, comment='收藏机构'),
        sa.Column('source_url', sa.String(2000), nullable=True, comment='来源链接'),
        sa.Column('image_url', sa.String(2000), nullable=True, comment='书影链接'),
        sa.Column('public_domain_status', sa.String(50), nullable=False, server_default='unknown', comment='公共领域状态'),
        sa.Column('ocr_text_available', sa.Boolean(), nullable=False, server_default='false', comment='是否有 OCR 文本'),
        sa.Column('citation_note', sa.Text(), nullable=True, comment='引用说明'),
        sa.Column('academic_note', sa.Text(), nullable=True, comment='学术备注'),
        sa.Column('review_status', sa.String(50), nullable=False, server_default='pending_review', comment='审核状态'),
        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint(
            "public_domain_status IN ('confirmed_public_domain', 'copyright_claimed', 'unknown', 'not_applicable')",
            name='ck_classical_versions_pd_status',
        ),
        sa.CheckConstraint(
            "review_status IN ('pending_review', 'under_review', 'approved', 'rejected')",
            name='ck_classical_versions_review_status',
        ),
    )
    op.create_index('ix_classical_versions_work_title', 'classical_versions', ['work_title'])
    op.create_index('ix_classical_versions_review_status', 'classical_versions', ['review_status'])
    op.create_index('ix_classical_versions_is_deleted', 'classical_versions', ['is_deleted'])


def downgrade() -> None:
    op.drop_index('ix_classical_versions_is_deleted', table_name='classical_versions')
    op.drop_index('ix_classical_versions_review_status', table_name='classical_versions')
    op.drop_index('ix_classical_versions_work_title', table_name='classical_versions')
    op.drop_table('classical_versions')
