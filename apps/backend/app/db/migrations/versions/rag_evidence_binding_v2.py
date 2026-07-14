"""evidence-binding RAG v2: pdf_sha256 on documents, page-level provenance on document_chunks

Revision ID: rag_evidence_binding_v2
Revises: rag_evidence_binding_v1
Create Date: 2026-07-14
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "rag_evidence_binding_v2"
down_revision: Union[str, None] = "rag_evidence_binding_v1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- documents: pdf_sha256 ---
    with op.batch_alter_table("documents") as batch_op:
        batch_op.add_column(
            sa.Column(
                "pdf_sha256",
                sa.String(64),
                nullable=True,
                comment="原始 PDF blob 的 SHA-256 hash",
            )
        )
        batch_op.create_index("idx_documents_pdf_sha256", ["pdf_sha256"])

    # --- document_chunks: page-level provenance ---
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.add_column(
            sa.Column(
                "page_image_hash",
                sa.String(128),
                nullable=True,
                comment="页面区域截图或 OCR 文本的 hash (SHA-512/256 或感知 hash)",
            )
        )
        batch_op.add_column(
            sa.Column(
                "ocr_engine_version",
                sa.String(100),
                nullable=True,
                comment="OCR 引擎及参数标识，如 'paddleocr-v2.7_ch_PP-OCRv4'",
            )
        )
        batch_op.add_column(
            sa.Column(
                "match_method",
                sa.String(50),
                nullable=True,
                comment="引文匹配方法: exact | fuzzy | ocr_bounding_box",
            )
        )
        batch_op.add_column(
            sa.Column(
                "quote_bbox",
                sa.JSON(),
                nullable=True,
                comment="引文在页面上的边界框/偏移位置，如 {x0,y0,x1,y1,page} 或 {start,end}",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("document_chunks") as batch_op:
        batch_op.drop_column("quote_bbox")
        batch_op.drop_column("match_method")
        batch_op.drop_column("ocr_engine_version")
        batch_op.drop_column("page_image_hash")

    with op.batch_alter_table("documents") as batch_op:
        batch_op.drop_index("idx_documents_pdf_sha256")
        batch_op.drop_column("pdf_sha256")
