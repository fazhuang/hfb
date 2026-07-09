"""add_academic_and_version_criticism_models

Revision ID: a3a194fc4f8d
Revises: 291a1dce8d65
Create Date: 2026-07-10 01:05:25.937956
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision: str = 'a3a194fc4f8d'
down_revision: Union[str, None] = '291a1dce8d65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('academic_entities',
    sa.Column('name', sa.String(length=100), nullable=False, comment='实体名称'),
    sa.Column('entity_type', sa.Enum('ACUPOINT', 'MERIDIAN', 'DISEASE', 'PERSON', 'TECHNIQUE', name='academicentitytype'), nullable=False, comment='实体类型'),
    sa.Column('description', sa.Text(), nullable=True, comment='定义与说明'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_academic_entities_name'), 'academic_entities', ['name'], unique=True)
    op.create_table('source_refs',
    sa.Column('title', sa.String(length=500), nullable=False, comment='物理书名/文献名/论文名'),
    sa.Column('author', sa.String(length=200), nullable=True, comment='作者/编校者'),
    sa.Column('edition_info', sa.String(length=500), nullable=True, comment='版本信息/出版社/刊刻年代'),
    sa.Column('page_location', sa.String(length=200), nullable=True, comment='文献内的定位：卷/页/行/栏'),
    sa.Column('url', sa.String(length=1000), nullable=True, comment='数字化链接/古籍库链接'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('academic_relations',
    sa.Column('source_entity_id', sa.String(length=36), nullable=False, comment='源实体ID'),
    sa.Column('target_entity_id', sa.String(length=36), nullable=False, comment='靶实体ID'),
    sa.Column('relation_type', sa.String(length=100), nullable=False, comment="关系类型，如 'TREAT' (主治), 'LOCATE_AT' (定位)"),
    sa.Column('description', sa.Text(), nullable=True, comment='命题关系阐述'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['source_entity_id'], ['academic_entities.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['target_entity_id'], ['academic_entities.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('relation_confidences',
    sa.Column('relation_id', sa.String(length=36), nullable=False, comment='关联的学术命题'),
    sa.Column('calculated_score', sa.Float(), nullable=False, comment='计算得到的可信度评分 (0.00-1.00)'),
    sa.Column('logic_checked', sa.Boolean(), nullable=False, comment='是否通过医学知识逻辑校验（无明显悖论）'),
    sa.Column('calculation_log', sa.Text(), nullable=True, comment='可信度计算的来源因子权重明细'),
    sa.Column('last_calculated_at', sa.DateTime(timezone=True), nullable=False, comment='最后计算更新时间'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['relation_id'], ['academic_relations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('relation_id')
    )
    op.create_table('evidences',
    sa.Column('description', sa.Text(), nullable=False, comment='证据内容概述/考证逻辑'),
    sa.Column('evidence_level', sa.Enum('LEVEL_1', 'LEVEL_2', 'LEVEL_3', 'LEVEL_4', name='evidencelevel'), nullable=False, comment='学术证据力等级'),
    sa.Column('source_ref_id', sa.String(length=36), nullable=True, comment='关联的物理文献来源'),
    sa.Column('source_passage_id', sa.String(length=36), nullable=True, comment='关联的系统内数字文献段落'),
    sa.Column('creator_id', sa.String(length=36), nullable=True, comment='创建录入人'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['creator_id'], ['users.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_passage_id'], ['passages.id'], ondelete='SET NULL'),
    sa.ForeignKeyConstraint(['source_ref_id'], ['source_refs.id'], ondelete='RESTRICT'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('sentences',
    sa.Column('passage_id', sa.String(length=36), nullable=False, comment='所属段落 ID'),
    sa.Column('content_text', sa.Text(), nullable=False, comment='句子内容'),
    sa.Column('order', sa.Integer(), nullable=False, comment='句子在段落内的序号'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['passage_id'], ['passages.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_sentences_passage_id'), 'sentences', ['passage_id'], unique=False)
    op.create_table('citations',
    sa.Column('target_type', sa.String(length=50), nullable=False, comment='被引用的系统对象类型 (Variant/AcademicRelation/Passage)'),
    sa.Column('target_id', sa.String(length=36), nullable=False, comment='被引用的对象UUID'),
    sa.Column('evidence_id', sa.String(length=36), nullable=False, comment='支撑证据ID'),
    sa.Column('quote_text', sa.Text(), nullable=True, comment='引用时的佐证原文'),
    sa.Column('note', sa.Text(), nullable=True, comment='引用时的考证评注'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidences.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_citation_target', 'citations', ['target_type', 'target_id'], unique=False)
    op.create_table('relation_evidences',
    sa.Column('relation_id', sa.String(length=36), nullable=False),
    sa.Column('evidence_id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['evidence_id'], ['evidences.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['relation_id'], ['academic_relations.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('relation_id', 'evidence_id')
    )
    op.create_table('tokens',
    sa.Column('sentence_id', sa.String(length=36), nullable=False, comment='所属断句 ID'),
    sa.Column('char_text', sa.String(length=50), nullable=False, comment='单个汉字或核心词'),
    sa.Column('position', sa.Integer(), nullable=False, comment='字/词在句中的绝对位置索引'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['sentence_id'], ['sentences.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_token_lookup', 'tokens', ['sentence_id', 'position'], unique=False)
    op.create_table('variants',
    sa.Column('base_token_id', sa.String(length=36), nullable=False, comment='基准版本的Token ID'),
    sa.Column('compare_token_id', sa.String(length=36), nullable=True, comment='比对版本的Token ID'),
    sa.Column('variant_type', sa.Enum('SUBSTITUTION', 'OMISSION', 'INSERTION', 'TRANSPOSITION', 'CORRUPTION', name='varianttype'), nullable=False, comment='异文类型'),
    sa.Column('description', sa.Text(), nullable=True, comment='校勘记/校勘说明'),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('is_deleted', sa.Boolean(), server_default='false', nullable=False),
    sa.ForeignKeyConstraint(['base_token_id'], ['tokens.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['compare_token_id'], ['tokens.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_variants_base_token_id'), 'variants', ['base_token_id'], unique=False)
    op.create_index(op.f('ix_variants_compare_token_id'), 'variants', ['compare_token_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_variants_compare_token_id'), table_name='variants')
    op.drop_index(op.f('ix_variants_base_token_id'), table_name='variants')
    op.drop_table('variants')
    op.drop_index('idx_token_lookup', table_name='tokens')
    op.drop_table('tokens')
    op.drop_table('relation_evidences')
    op.drop_index('idx_citation_target', table_name='citations')
    op.drop_table('citations')
    op.drop_index(op.f('ix_sentences_passage_id'), table_name='sentences')
    op.drop_table('sentences')
    op.drop_table('evidences')
    op.drop_table('relation_confidences')
    op.drop_table('academic_relations')
    op.drop_table('source_refs')
    op.drop_index(op.f('ix_academic_entities_name'), table_name='academic_entities')
    op.drop_table('academic_entities')
