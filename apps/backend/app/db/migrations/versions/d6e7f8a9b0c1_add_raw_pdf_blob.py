"""add raw_pdf_blob column to documents

Revision ID: d6e7f8a9b0c1
Revises: c5d6e7f8a9b0
Create Date: 2026-06-30 23:45:00.000000
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers
revision: str = 'd6e7f8a9b0c1'
down_revision: str | None = 'c5d6e7f8a9b0'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        'documents',
        sa.Column('raw_pdf_blob', sa.LargeBinary(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('documents', 'raw_pdf_blob')
