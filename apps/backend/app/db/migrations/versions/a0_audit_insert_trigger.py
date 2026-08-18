"""Phase A0 — forbid orphan audit-log inserts (candidate_id NULL on INSERT).

Revision ID: a0_audit_insert_trigger
Revises: phase_a0_metadata_candidate
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from app.db import audit_triggers

# revision identifiers
revision: str = "a0_audit_insert_trigger"
down_revision: str | None = "phase_a0_metadata_candidate"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Pre-INSERT-constraint PG DDL (for downgrade).
_PG_FUNCTION_WITHOUT_INSERT = """
CREATE OR REPLACE FUNCTION block_audit_log_changes() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'CandidateAuditLog is append-only: DELETE forbidden';
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.candidate_id IS NOT NULL AND NEW.candidate_id IS NULL
           AND NEW.id = OLD.id
           AND NEW.action = OLD.action
           AND NEW.operator_id = OLD.operator_id
           AND NEW.input_snapshot IS NOT DISTINCT FROM OLD.input_snapshot
           AND NEW.pre_payload IS NOT DISTINCT FROM OLD.pre_payload
           AND NEW.post_payload IS NOT DISTINCT FROM OLD.post_payload
           AND NEW.published_evidence_id IS NOT DISTINCT FROM OLD.published_evidence_id
           AND NEW.created_at = OLD.created_at THEN
            RETURN NEW;
        END IF;
        RAISE EXCEPTION 'CandidateAuditLog is append-only: UPDATE forbidden';
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;
"""

_PG_TRIGGER_WITHOUT_INSERT = """
CREATE TRIGGER trg_audit_log_immutable
BEFORE UPDATE OR DELETE ON candidate_audit_logs
FOR EACH ROW EXECUTE FUNCTION block_audit_log_changes();
"""


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(audit_triggers.PG_DROP_TRIGGER_SQL))
        op.execute(sa.text(audit_triggers.PG_FUNCTION_SQL))
        op.execute(sa.text(audit_triggers.PG_TRIGGER_SQL))
    elif bind.dialect.name == "sqlite":
        op.execute(sa.text(audit_triggers.SQLITE_NO_ORPHAN_INSERT_SQL))


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(audit_triggers.PG_DROP_TRIGGER_SQL))
        op.execute(sa.text(_PG_FUNCTION_WITHOUT_INSERT))
        op.execute(sa.text(_PG_TRIGGER_WITHOUT_INSERT))
    elif bind.dialect.name == "sqlite":
        op.execute(sa.text("DROP TRIGGER IF EXISTS trg_audit_log_no_orphan_insert"))
