"""Append-only DDL triggers for ``candidate_audit_logs`` (Phase A0).

Both dialects enforce the same invariant:

* ``INSERT`` is allowed only with a non-NULL ``candidate_id`` (no orphan logs).
* ``DELETE`` is always forbidden.
* ``UPDATE`` is allowed **only** for the single sanctioned transition where
  ``candidate_id`` goes from non-NULL to NULL, and every other column remains
  byte-for-byte identical.

The SQLite variant uses the ``IS`` null-safe operator; the PostgreSQL variant
uses ``IS NOT DISTINCT FROM``. This module is the single source of truth shared
by the Alembic migration and the unit tests, so the two can never drift apart.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

# ---------------------------------------------------------------------------
# PostgreSQL (PL/pgSQL)
# ---------------------------------------------------------------------------

PG_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION block_audit_log_changes() RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        IF NEW.candidate_id IS NULL THEN
            RAISE EXCEPTION 'CandidateAuditLog requires a candidate_id on INSERT';
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
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

PG_TRIGGER_SQL = """
CREATE TRIGGER trg_audit_log_immutable
BEFORE INSERT OR UPDATE OR DELETE ON candidate_audit_logs
FOR EACH ROW EXECUTE FUNCTION block_audit_log_changes();
"""

PG_DROP_TRIGGER_SQL = "DROP TRIGGER IF EXISTS trg_audit_log_immutable ON candidate_audit_logs;"
PG_DROP_FUNCTION_SQL = "DROP FUNCTION IF EXISTS block_audit_log_changes();"

# ---------------------------------------------------------------------------
# SQLite (IS null-safe comparison)
# ---------------------------------------------------------------------------

SQLITE_NO_DELETE_SQL = """
CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_delete
BEFORE DELETE ON candidate_audit_logs
BEGIN
    SELECT RAISE(ABORT, 'CandidateAuditLog is append-only: DELETE forbidden');
END;
"""

SQLITE_NO_ORPHAN_INSERT_SQL = """
CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_orphan_insert
BEFORE INSERT ON candidate_audit_logs
WHEN NEW.candidate_id IS NULL
BEGIN
    SELECT RAISE(ABORT, 'CandidateAuditLog requires a candidate_id on INSERT');
END;
"""

SQLITE_NO_UPDATE_SQL = """
CREATE TRIGGER IF NOT EXISTS trg_audit_log_no_update
BEFORE UPDATE ON candidate_audit_logs
WHEN NOT (
    OLD.candidate_id IS NOT NULL AND NEW.candidate_id IS NULL
    AND NEW.id IS OLD.id
    AND NEW.action IS OLD.action
    AND NEW.operator_id IS OLD.operator_id
    AND NEW.input_snapshot IS OLD.input_snapshot
    AND NEW.pre_payload IS OLD.pre_payload
    AND NEW.post_payload IS OLD.post_payload
    AND NEW.published_evidence_id IS OLD.published_evidence_id
    AND NEW.created_at = OLD.created_at
)
BEGIN
    SELECT RAISE(ABORT, 'CandidateAuditLog is append-only: UPDATE forbidden');
END;
"""

SQLITE_DROP_TRIGGERS_SQL = """
DROP TRIGGER IF EXISTS trg_audit_log_no_delete;
DROP TRIGGER IF EXISTS trg_audit_log_no_update;
DROP TRIGGER IF EXISTS trg_audit_log_no_orphan_insert;
"""


def dialect_name(bind: Any) -> str:
    """Return the backend dialect name from a connection or engine."""
    return bind.dialect.name if hasattr(bind, "dialect") else bind.engine.dialect.name


async def install_audit_log_triggers(conn: AsyncConnection) -> None:
    """Install the audit-log triggers for the connection's dialect.

    ``conn`` is an async SQLAlchemy ``Connection``.
    """
    name = dialect_name(conn)
    if name == "postgresql":
        await conn.execute(text(PG_FUNCTION_SQL))
        await conn.execute(text(PG_TRIGGER_SQL))
    elif name == "sqlite":
        await conn.execute(text(SQLITE_NO_DELETE_SQL))
        await conn.execute(text(SQLITE_NO_UPDATE_SQL))
        await conn.execute(text(SQLITE_NO_ORPHAN_INSERT_SQL))
    else:
        raise NotImplementedError(f"audit triggers unsupported for dialect {name!r}")


async def drop_audit_log_triggers(conn: AsyncConnection) -> None:
    """Drop the audit-log triggers for the connection's dialect (idempotent)."""
    name = dialect_name(conn)
    if name == "postgresql":
        await conn.execute(text(PG_DROP_TRIGGER_SQL))
        await conn.execute(text(PG_DROP_FUNCTION_SQL))
    elif name == "sqlite":
        await conn.execute(text(SQLITE_DROP_TRIGGERS_SQL))
