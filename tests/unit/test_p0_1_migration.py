"""P0-1: Migration tests — verified_by FK constraint.

Tests:
  - Fresh DB via Alembic has FK on entity_relations.verified_by -> users.id
  - Illegal reviewer ID is rejected by FK constraint
"""

import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent.parent / "apps" / "backend"


def _run_upgrade(db_url: str, target: str = "head") -> None:
    """Run alembic upgrade in a subprocess to avoid asyncio conflicts."""
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", target],
        cwd=str(BACKEND),
        env=env,
        check=True,
        capture_output=True,
    )


@pytest.mark.asyncio
async def test_verified_by_fk_in_fresh_db() -> None:
    """Create fresh SQLite DB via Alembic, verify FK on verified_by."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    try:
        _run_upgrade(f"sqlite:///{db_path}")

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")
        rows = conn.execute("PRAGMA foreign_key_list('entity_relations')").fetchall()

        fk_found = [
            r
            for r in rows
            if r[2] == "users" and r[3] == "verified_by" and r[4] == "id"
        ]
        assert len(fk_found) == 1, (
            f"Expected FK verified_by->users.id, got foreign_key_list: {rows}"
        )
        assert fk_found[0][6] == "SET NULL", (
            f"Expected ON DELETE SET NULL, got: {fk_found[0][6]}"
        )
        conn.close()
    finally:
        os.unlink(db_path)


@pytest.mark.asyncio
async def test_illegal_verified_by_rejected_by_fk() -> None:
    """Inserting a relation with verified_by pointing to nonexistent user must fail."""
    db_fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(db_fd)
    try:
        _run_upgrade(f"sqlite:///{db_path}")

        conn = sqlite3.connect(db_path)
        conn.execute("PRAGMA foreign_keys=ON")

        # Insert a valid user first
        conn.execute(
            "INSERT INTO users (id, username, email, hashed_password, is_active, is_superuser) "
            "VALUES ('valid-reviewer', 'reviewer', 'r@test.com', 'x', 1, 0)"
        )
        conn.commit()

        # Valid reviewer should work
        conn.execute(
            "INSERT INTO entity_relations "
            "(id, source_entity_type, source_entity_id, target_entity_type, "
            "target_entity_id, relation_type, evidence_document_id, "
            "evidence_chunk_id, evidence_quote, evidence_citation, "
            "evidence_status, verified_by) "
            "VALUES ('rel-valid', 'person', 'p1', 'book', 'b1', 'compiled', "
            "'d1', 'c1', 'quote', 'cit', 'verified', 'valid-reviewer')"
        )
        conn.commit()

        # Nonexistent user must be rejected by FK
        with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY"):
            conn.execute(
                "INSERT INTO entity_relations "
                "(id, source_entity_type, source_entity_id, target_entity_type, "
                "target_entity_id, relation_type, evidence_document_id, "
                "evidence_chunk_id, evidence_quote, evidence_citation, "
                "evidence_status, verified_by) "
                "VALUES ('rel-illegal', 'person', 'p2', 'book', 'b2', 'compiled', "
                "'d2', 'c2', 'quote', 'cit', 'verified', 'nonexistent-user')"
            )
            conn.commit()

        conn.close()
    finally:
        os.unlink(db_path)
