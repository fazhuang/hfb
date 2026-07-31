"""evidence-binding RAG: DocumentChunk + paragraph_index, page_number, ocr_confidence

Revision ID: rag_evidence_binding_v1
Revises: c21f1a2b3c4d
Create Date: 2026-07-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "rag_evidence_binding_v1"
down_revision: str | None = "c21f1a2b3c4d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "page_number",
                sa.Integer(),
                nullable=True,
                comment="源文档页码 (1-based)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "paragraph_index",
                sa.Integer(),
                nullable=True,
                comment="源文档段落索引 (0-based)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "ocr_confidence",
                sa.Float(),
                nullable=True,
                comment="OCR 可信度 0.0-1.0，NULL 表示非 OCR 文本",
            )
        )
        batch_op.add_column(
            sa.Column(
                "evidence_weight",
                sa.String(20),
                nullable=False,
                server_default=sa.text("'primary'"),
                comment="证据权重: primary | reference",
            )
        )
        batch_op.add_column(
            sa.Column(
                "citation_format",
                sa.String(200),
                nullable=True,
                comment="引文格式模板，如 '《{title}》p.{page_number} par.{paragraph_index}'",
            )
        )

    # Index on (document_id, page_number) for page-range queries
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.create_index("idx_chunks_doc_page", ["document_id", "page_number"])


def downgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.drop_index("idx_chunks_doc_page")
        batch_op.drop_column("citation_format")
        batch_op.drop_column("evidence_weight")
        batch_op.drop_column("ocr_confidence")
        batch_op.drop_column("paragraph_index")
        batch_op.drop_column("page_number")
