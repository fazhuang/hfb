"""phase2a_academic_edges_view

Creates the academic_edges SQL view that filters entity_relations to
academically citeable edges: evidence_level >= 2, evidence_status = 'verified',
is_deleted = 0, plus a computed confidence_score column.

Revision ID: d6575d7baf29
Revises: 452a2a7b5068
Create Date: 2026-07-05 15:22:36.033217
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers
revision: str = "d6575d7baf29"
down_revision: str | None = "452a2a7b5068"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VIEW_NAME = "academic_edges"
VIEW_SQL = """\
CREATE VIEW academic_edges AS
SELECT
    *,
    CASE evidence_level
        WHEN 2 THEN 0.65
        WHEN 3 THEN 0.85
        WHEN 4 THEN 0.98
        ELSE 0.0
    END AS confidence_score
FROM entity_relations
WHERE evidence_level >= 2
  AND evidence_status = 'verified'
  AND is_deleted = {is_deleted_false};
"""


def upgrade() -> None:
    conn = op.get_bind()
    # PostgreSQL needs boolean literal `false`; SQLite stores bool as int 0.
    is_deleted_false = "false" if conn.dialect.name == "postgresql" else "0"
    op.execute(VIEW_SQL.format(is_deleted_false=is_deleted_false))


def downgrade() -> None:
    op.execute(f"DROP VIEW IF EXISTS {VIEW_NAME};")
