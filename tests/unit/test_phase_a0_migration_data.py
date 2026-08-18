"""Phase A0 migration data-preservation tests.

Verifies that ``phase_a0_metadata_candidate`` migrates real ``metadata`` rows
into ``candidate_extraction_metadata`` without losing content, count, or the
candidate association — on both SQLite and PostgreSQL.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent.parent / "apps" / "backend"

OLD_REVISION = "phase_a0_standards_indexes"


def _run_alembic(db_url: str, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["DATABASE_URL"] = db_url
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )


_CANDIDATE_INSERT = """
INSERT INTO candidate_extractions
    (id, session_id, created_by_user_id, chunk_id, version_id,
     expected_chunk_sha256, expected_nfc_sha256, unicode_normalization,
     start_char, end_char, exact_text, input_snapshot, extracted_payload,
     extractor_name, confidence, metadata_id)
VALUES
    ('mig-cand-1', 'mig-session', 'mig-user', 'mig-chunk', 'mig-version',
     'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
     'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb',
     'NFC', 0, 5, 'hello', '{}', '{}', 'test-extractor', 0.9, 'mig-meta-1')
"""


def _verify_preserved(conn) -> None:
    """Assert the migrated metadata content/count/association are intact."""
    rows = conn.execute(
        "SELECT candidate_id, payload FROM candidate_extraction_metadata"
    ).fetchall()
    assert len(rows) == 1, f"expected 1 migrated metadata row, got {len(rows)}"
    assert rows[0][0] == "mig-cand-1"
    payload = rows[0][1]
    assert "preserve-me" in payload
    assert json.loads(payload)["note"] == "preserve-me"

    cols = {r[1] for r in conn.execute("PRAGMA table_info(candidate_extractions)")}
    assert "metadata_id" not in cols, "metadata_id column should be dropped"


# ---------------------------------------------------------------------------
# SQLite
# ---------------------------------------------------------------------------


def test_sqlite_migration_preserves_metadata_data(tmp_path) -> None:
    import sqlite3

    db_path = str(tmp_path / "mig.db")
    db_url = f"sqlite:///{db_path}"

    # Upgrade to the OLD schema (generic metadata + metadata_id).
    r = _run_alembic(db_url, "upgrade", OLD_REVISION)
    assert r.returncode == 0, r.stderr

    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO metadata (id, entity_type, entity_id, payload) "
        "VALUES ('mig-meta-1', 'candidate_extraction', 'mig-cand-1', "
        "'{\"note\": \"preserve-me\"}')"
    )
    conn.execute(_CANDIDATE_INSERT)
    conn.commit()
    conn.close()

    # Upgrade to head (runs phase_a0_metadata_candidate).
    r = _run_alembic(db_url, "upgrade", "head")
    assert r.returncode == 0, r.stderr

    conn = sqlite3.connect(db_path)
    _verify_preserved(conn)
    conn.close()


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------


def _pg_urls() -> tuple[str, str]:
    """Return (sync psycopg2 URL, async URL for alembic)."""
    from app.core.config import settings

    db = os.environ.get("POSTGRES_TEST_DB", "hfb_test")
    base = f"{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db}"
    return f"postgresql://{base}", f"postgresql+asyncpg://{base}"


def test_postgresql_migration_preserves_metadata_data() -> None:
    import psycopg2

    sync_url, async_url = _pg_urls()

    try:
        conn = psycopg2.connect(sync_url)
    except psycopg2.OperationalError as exc:
        pytest.skip(f"PostgreSQL unavailable: {exc}")

    # Reset the test schema to empty, then upgrade to the OLD schema.
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")
    conn.close()

    r = _run_alembic(async_url, "upgrade", OLD_REVISION)
    assert r.returncode == 0, r.stderr

    with psycopg2.connect(sync_url) as conn:
        with conn.cursor() as cur:
            # Minimal FK chain.
            cur.execute(
                "INSERT INTO users (id, username, email, hashed_password) "
                "VALUES ('mig-user', 'mig-user', 'mig@test.com', 'x')"
            )
            cur.execute("INSERT INTO books (id, title) VALUES ('mig-book', 't')")
            cur.execute(
                "INSERT INTO versions (id, book_id, version_name) "
                "VALUES ('mig-version', 'mig-book', 'v1')"
            )
            cur.execute(
                "INSERT INTO chapters (id, book_id, title, \"order\") "
                "VALUES ('mig-chapter', 'mig-book', 'c1', 0)"
            )
            cur.execute(
                "INSERT INTO passages (id, chapter_id, version_id, content_text, \"order\") "
                "VALUES ('mig-passage', 'mig-chapter', 'mig-version', 't', 0)"
            )
            cur.execute(
                "INSERT INTO documents (id, title, language) "
                "VALUES ('mig-doc', 't', 'zh')"
            )
            cur.execute(
                "INSERT INTO document_chunks (id, document_id, passage_id, chunk_index, content) "
                "VALUES ('mig-chunk', 'mig-doc', 'mig-passage', 0, 'hello')"
            )
            cur.execute(
                "INSERT INTO research_sessions (id, user_id, title) "
                "VALUES ('mig-session', 'mig-user', 't')"
            )
            cur.execute(
                "INSERT INTO metadata (id, entity_type, entity_id, payload) "
                "VALUES ('mig-meta-1', 'candidate_extraction', 'mig-cand-1', "
                "'{\"note\": \"preserve-me\"}')"
            )
            cur.execute(_CANDIDATE_INSERT)
        conn.commit()

    r = _run_alembic(async_url, "upgrade", "head")
    assert r.returncode == 0, r.stderr

    with psycopg2.connect(sync_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT candidate_id, payload::text FROM candidate_extraction_metadata"
            )
            rows = cur.fetchall()
            assert len(rows) == 1, f"expected 1 migrated row, got {len(rows)}"
            assert rows[0][0] == "mig-cand-1"
            assert "preserve-me" in rows[0][1]

            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='candidate_extractions' AND column_name='metadata_id'"
            )
            assert cur.fetchall() == [], "metadata_id column should be dropped"
