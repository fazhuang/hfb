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

    # Upgrade through the AI-fields migration, backfill real AI metadata, then
    # finish to head so a0_ai_metadata_required does not fail-closed.
    r = _run_alembic(db_url, "upgrade", "a0_ai_metadata_fields")
    assert r.returncode == 0, r.stderr
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE candidate_extractions SET ai_model='real-model', "
        "ai_version='1.0.0', prompt_version='1.0.0', processing_time=0.5 "
        "WHERE ai_model='unknown' OR ai_version IS NULL "
        "OR prompt_version IS NULL OR processing_time IS NULL"
    )
    conn.commit()
    conn.close()

    r = _run_alembic(db_url, "upgrade", "head")
    assert r.returncode == 0, r.stderr

    conn = sqlite3.connect(db_path)
    _verify_preserved(conn)
    conn.close()


def test_sqlite_migration_fails_on_orphan_metadata(tmp_path) -> None:
    """Unlinked/orphan old metadata must fail-closed and leave the table intact."""
    import sqlite3

    db_path = str(tmp_path / "orphan.db")
    db_url = f"sqlite:///{db_path}"

    r = _run_alembic(db_url, "upgrade", OLD_REVISION)
    assert r.returncode == 0, r.stderr

    conn = sqlite3.connect(db_path)
    # An orphan metadata row not referenced by any candidate.
    conn.execute(
        "INSERT INTO metadata (id, entity_type, entity_id, payload) "
        "VALUES ('orphan-meta', 'other_entity', 'other-1', '{}')"
    )
    conn.commit()
    conn.close()

    r = _run_alembic(db_url, "upgrade", "head")
    assert r.returncode != 0, "upgrade must fail on orphan metadata"
    combined = (r.stderr or "") + (r.stdout or "")
    assert "unlinked" in combined, f"expected fail-closed message, got: {combined}"

    # Old table unchanged: the orphan row is still present.
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT id FROM metadata").fetchall()
    assert [r_[0] for r_ in rows] == ["orphan-meta"]
    conn.close()


# ---------------------------------------------------------------------------
# PostgreSQL
# ---------------------------------------------------------------------------


def _pg_urls() -> tuple[str, str]:
    """Return (sync psycopg2 URL, async URL for alembic)."""
    from app.core.config import settings

    db = os.environ.get("POSTGRES_TEST_DB", "hfb_test")
    base = (
        f"{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db}"
    )
    return f"postgresql://{base}", f"postgresql+asyncpg://{base}"


def test_postgresql_migration_preserves_metadata_data() -> None:
    import psycopg2

    sync_url, async_url = _pg_urls()

    try:
        conn = psycopg2.connect(sync_url)
    except psycopg2.OperationalError as exc:
        pytest.fail(f"PostgreSQL migration test requires a database: {exc}")

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

    # Upgrade through the AI-fields migration, backfill real AI metadata, then
    # finish to head so a0_ai_metadata_required does not fail-closed.
    r = _run_alembic(async_url, "upgrade", "a0_ai_metadata_fields")
    assert r.returncode == 0, r.stderr
    with psycopg2.connect(sync_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE candidate_extractions SET ai_model='real-model', "
                "ai_version='1.0.0', prompt_version='1.0.0', processing_time=0.5 "
                "WHERE ai_model='unknown' OR ai_version IS NULL "
                "OR prompt_version IS NULL OR processing_time IS NULL"
            )
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


def test_postgresql_disabled_trigger_fails_startup(monkeypatch) -> None:
    """A disabled audit trigger must fail-closed at PostgreSQL startup."""
    import asyncio

    import psycopg2
    from sqlalchemy.ext.asyncio import create_async_engine

    sync_url, async_url = _pg_urls()

    try:
        conn = psycopg2.connect(sync_url)
    except psycopg2.OperationalError as exc:  # noqa: BLE001
        pytest.fail(f"PostgreSQL migration test requires a database: {exc}")

    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")
    conn.close()

    r = _run_alembic(async_url, "upgrade", "head")
    assert r.returncode == 0, r.stderr

    with psycopg2.connect(sync_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "ALTER TABLE candidate_audit_logs "
                "DISABLE TRIGGER trg_audit_log_immutable"
            )
        conn.commit()

    import app.db.database as db_mod

    engine = create_async_engine(async_url)
    monkeypatch.setattr(db_mod, "_db_url", async_url)
    monkeypatch.setattr(db_mod, "engine", engine)

    async def _run_startup() -> None:
        with pytest.raises(RuntimeError, match="append-only trigger"):
            await db_mod.init_database()

    try:
        asyncio.run(_run_startup())
    finally:
        asyncio.run(engine.dispose())


def _insert_fk_chain(cur) -> None:
    """Insert the minimal FK chain required by candidate_extractions."""
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
        "INSERT INTO documents (id, title, language) VALUES ('mig-doc', 't', 'zh')"
    )
    cur.execute(
        "INSERT INTO document_chunks (id, document_id, passage_id, chunk_index, content) "
        "VALUES ('mig-chunk', 'mig-doc', 'mig-passage', 0, 'hello')"
    )
    cur.execute(
        "INSERT INTO research_sessions (id, user_id, title) "
        "VALUES ('mig-session', 'mig-user', 't')"
    )


def _illegal_candidate_insert(
    cand_id: str,
    ai_model: str,
    ai_version: str,
    prompt_version: str,
    processing_time_sql: str,
) -> str:
    sha = "a" * 64
    return (
        "INSERT INTO candidate_extractions "
        "(id, session_id, created_by, chunk_id, version_id, "
        "expected_chunk_sha256, expected_nfc_sha256, unicode_normalization, "
        "start_char, end_char, exact_text, input_snapshot, extracted_payload, "
        "extractor_name, ai_model, ai_version, prompt_version, processing_time, "
        "confidence) VALUES "
        "('{cand_id}', 'mig-session', 'mig-user', 'mig-chunk', 'mig-version', "
        "'{sha}', '{sha}', 'NFC', 0, 5, 'hello', '{{}}', '{{}}', 'test', "
        "'{ai_model}', '{ai_version}', '{prompt_version}', {processing_time_sql}, 0.9)"
    ).format(
        cand_id=cand_id,
        sha=sha,
        ai_model=ai_model,
        ai_version=ai_version,
        prompt_version=prompt_version,
        processing_time_sql=processing_time_sql,
    )


def test_sqlite_illegal_ai_metadata_rejected(tmp_path) -> None:
    """The migrated SQLite schema must reject unknown/blank/negative AI metadata."""
    import sqlite3

    db_path = str(tmp_path / "illegal.db")
    db_url = f"sqlite:///{db_path}"

    r = _run_alembic(db_url, "upgrade", "head")
    assert r.returncode == 0, r.stderr

    conn = sqlite3.connect(db_path)
    try:
        _insert_fk_chain(conn.cursor())
        conn.commit()
        cur = conn.cursor()
        cases = [
            ("cand-unknown", "unknown", "1.0.0", "1.0.0", "0.5"),
            ("cand-blank", "   ", "1.0.0", "1.0.0", "0.5"),
            ("cand-neg", "real-model", "1.0.0", "1.0.0", "-1.0"),
        ]
        for cand_id, model, ver, pver, pt in cases:
            with pytest.raises(sqlite3.IntegrityError):
                cur.execute(_illegal_candidate_insert(cand_id, model, ver, pver, pt))

        # NaN is stored as NULL by SQLite (NOT NULL violation); Infinity/-Infinity
        # are stored as IEEE 754 and rejected by the finite-range CHECK.
        for tag, val in [("nan", float("nan")), ("inf", float("inf")), ("-inf", float("-inf"))]:
            with pytest.raises(sqlite3.IntegrityError):
                cur.execute(
                    _illegal_candidate_insert_bound(
                        f"cand-{tag}", "real-model", "1.0.0", "1.0.0"
                    ),
                    (val,),
                )
    finally:
        conn.close()


def _illegal_candidate_insert_bound(
    cand_id: str, ai_model: str, ai_version: str, prompt_version: str
) -> str:
    sha = "a" * 64
    return (
        "INSERT INTO candidate_extractions "
        "(id, session_id, created_by, chunk_id, version_id, "
        "expected_chunk_sha256, expected_nfc_sha256, unicode_normalization, "
        "start_char, end_char, exact_text, input_snapshot, extracted_payload, "
        "extractor_name, ai_model, ai_version, prompt_version, processing_time, "
        "confidence) VALUES "
        f"('{cand_id}', 'mig-session', 'mig-user', 'mig-chunk', 'mig-version', "
        f"'{sha}', '{sha}', 'NFC', 0, 5, 'hello', '{{}}', '{{}}', 'test', "
        f"'{ai_model}', '{ai_version}', '{prompt_version}', ?, 0.9)"
    )


def test_postgresql_illegal_ai_metadata_rejected() -> None:
    """The migrated PostgreSQL schema must reject unknown/blank/negative AI metadata."""
    import psycopg2

    sync_url, async_url = _pg_urls()

    try:
        conn = psycopg2.connect(sync_url)
    except psycopg2.OperationalError as exc:
        pytest.fail(f"PostgreSQL migration test requires a database: {exc}")

    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")
    conn.close()

    r = _run_alembic(async_url, "upgrade", "head")
    assert r.returncode == 0, r.stderr

    with psycopg2.connect(sync_url) as conn:
        _insert_fk_chain(conn.cursor())
        conn.commit()
        cur = conn.cursor()
        cases = [
            ("cand-unknown", "unknown", "1.0.0", "1.0.0", "0.5"),
            ("cand-blank", "   ", "1.0.0", "1.0.0", "0.5"),
            ("cand-neg", "real-model", "1.0.0", "1.0.0", "-1.0"),
            ("cand-nan", "real-model", "1.0.0", "1.0.0", "'NaN'::float8"),
            ("cand-inf", "real-model", "1.0.0", "1.0.0", "'Infinity'::float8"),
            ("cand--inf", "real-model", "1.0.0", "1.0.0", "'-Infinity'::float8"),
        ]
        for cand_id, model, ver, pver, pt in cases:
            with pytest.raises(psycopg2.errors.CheckViolation):
                cur.execute(_illegal_candidate_insert(cand_id, model, ver, pver, pt))
            conn.rollback()  # reset the aborted transaction after each violation


def test_sqlite_phase_a0_rollback_and_reupgrade(tmp_path) -> None:
    """Migration rollback gate: upgrade → downgrade (all Phase A0) → re-upgrade.

    Phase A0 rollback is exercised up to `source_admission_entries` — the
    revision immediately before the irreversible security migration
    `rbac_cleanup_student_user_read` (whose downgrade intentionally raises).
    """
    db_path = str(tmp_path / "rollback.db")
    db_url = f"sqlite:///{db_path}"

    r = _run_alembic(db_url, "upgrade", "source_admission_entries")
    assert r.returncode == 0, r.stderr

    # Roll back every Phase A0 migration (down to the pre-Phase-A0 head).
    r = _run_alembic(db_url, "downgrade", "f1a2b3c4d5e6")
    assert r.returncode == 0, r.stderr

    r = _run_alembic(db_url, "upgrade", "source_admission_entries")
    assert r.returncode == 0, r.stderr


def test_postgresql_phase_a0_rollback_and_reupgrade() -> None:
    """PostgreSQL migration rollback gate: upgrade → downgrade → re-upgrade."""
    import psycopg2

    sync_url, async_url = _pg_urls()

    try:
        conn = psycopg2.connect(sync_url)
    except psycopg2.OperationalError as exc:
        pytest.fail(f"PostgreSQL migration test requires a database: {exc}")

    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("DROP SCHEMA public CASCADE")
        cur.execute("CREATE SCHEMA public")
    conn.close()

    r = _run_alembic(async_url, "upgrade", "source_admission_entries")
    assert r.returncode == 0, r.stderr

    r = _run_alembic(async_url, "downgrade", "f1a2b3c4d5e6")
    assert r.returncode == 0, r.stderr

    r = _run_alembic(async_url, "upgrade", "source_admission_entries")
    assert r.returncode == 0, r.stderr
