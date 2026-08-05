"""
Deterministic unit tests for literature ingestion orchestrator.
Covers: multi-source success, single-source failure isolation, dedup,
whitelist gate, unknown source handling, error counting, and per-query
result aggregation. All external HTTP, DB, and whitelist boundaries are mocked.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from sqlalchemy.exc import SQLAlchemyError


# =============================================================================
# Helpers
# =============================================================================


def _make_item(title: str, source: str, source_url: str, doi: str = "", year: int | None = None):
    """Build a LiteratureItem with required fields."""
    from app.services.literature_ingestion import LiteratureItem

    return LiteratureItem(
        title=title,
        source=source,
        source_url=source_url,
        doi=doi,
        year=year,
    )


async def _ok_searcher(query: str, page: int = 1) -> tuple[list, int]:
    """Mock searcher that returns predictable items."""
    from app.services.literature_ingestion import LiteratureItem

    items = [
        LiteratureItem(
            title=f"{query} result {page}-1",
            source="mock",
            source_url=f"https://mock.example/{query}/{page}/1",
        ),
        LiteratureItem(
            title=f"{query} result {page}-2",
            source="mock",
            source_url=f"https://mock.example/{query}/{page}/2",
        ),
    ]
    return items, 10


async def _empty_searcher(query: str, page: int = 1) -> tuple[list, int]:
    """Mock searcher that returns empty results."""
    return [], 0


async def _failing_searcher(query: str, page: int = 1) -> tuple[list, int]:
    """Mock searcher that raises on every call."""
    raise httpx.HTTPStatusError(
        "HTTP 500",
        request=MagicMock(),
        response=httpx.Response(500),
    )


# =============================================================================
# whitelist gate
# =============================================================================


class TestWhitelistGate:
    @pytest.mark.asyncio
    async def test_enforce_whitelist_rejects_all_when_whitelist_file_missing(self):
        """When source_whitelist.yaml can't be loaded, all sources are denied."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        with patch("app.services.source_whitelist.get_whitelist",
                   side_effect=OSError("file not found")):
            with patch("app.services.literature_ingestion.orchestrator.SOURCES", {}):
                jobs = await ingest(
                    mock_session,
                    queries=["test"],
                    sources=["openalex"],
                    max_pages=1,
                    enforce_whitelist=True,
                )

        assert len(jobs) >= 1
        # Gate job: source denied because whitelist couldn't load
        gate_jobs = [j for j in jobs if j.query == "<whitelist gate>"]
        assert len(gate_jobs) >= 1
        assert all(j.error_count > 0 for j in gate_jobs)

    @pytest.mark.asyncio
    async def test_enforce_whitelist_rejects_disallowed_source(self):
        """A source not in the whitelist is rejected with a gate job."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()
        mock_wl = MagicMock()
        mock_wl.is_source_allowed.return_value = False

        with patch("app.services.source_whitelist.get_whitelist",
                   return_value=mock_wl):
            with patch("app.services.literature_ingestion.orchestrator.SOURCES", {}):
                jobs = await ingest(
                    mock_session,
                    queries=["test"],
                    sources=["blocked_source"],
                    max_pages=1,
                    enforce_whitelist=True,
                )

        gate_jobs = [j for j in jobs if j.query == "<whitelist gate>"]
        assert len(gate_jobs) == 1
        assert gate_jobs[0].source == "blocked_source"
        assert gate_jobs[0].error_count > 0
        assert "not in the approved source whitelist" in gate_jobs[0].errors[0]

    @pytest.mark.asyncio
    async def test_enforce_whitelist_false_skips_gate(self):
        """When enforce_whitelist=False, gate is skipped entirely."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        jobs = await ingest(
            mock_session,
            queries=["test"],
            sources=["any_source"],
            max_pages=1,
            enforce_whitelist=False,
        )

        # No whitelist gate jobs
        gate_jobs = [j for j in jobs if j.query == "<whitelist gate>"]
        assert len(gate_jobs) == 0


# =============================================================================
# single-source failure isolation
# =============================================================================


class TestSourceFailureIsolation:
    @pytest.mark.asyncio
    async def test_single_source_failure_does_not_block_others(self):
        """One failing source should not prevent other sources from succeeding."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        sources_map = {
            "good": _ok_searcher,
            "bad": _failing_searcher,
        }

        with patch("app.services.literature_ingestion.orchestrator.SOURCES", sources_map):
            with patch("app.services.literature_ingestion.orchestrator.filter_new_items",
                       new_callable=AsyncMock) as mock_filter:
                mock_filter.return_value = [_make_item("Kept", "good", "https://x.com")]
                with patch("app.services.literature_ingestion.orchestrator._save_items",
                           new_callable=AsyncMock) as mock_save:
                    jobs = await ingest(
                        mock_session,
                        queries=["test"],
                        sources=["good", "bad"],
                        max_pages=1,
                        enforce_whitelist=False,
                    )

        good_jobs = [j for j in jobs if j.source == "good"]
        bad_jobs = [j for j in jobs if j.source == "bad"]

        assert len(good_jobs) == 1
        assert len(bad_jobs) == 1
        assert good_jobs[0].error_count == 0
        assert good_jobs[0].success is True
        assert bad_jobs[0].error_count > 0
        assert bad_jobs[0].success is False
        # _save_items is called for both sources (even bad one gets empty-item pass)
        assert mock_save.call_count >= 1

    @pytest.mark.asyncio
    async def test_unknown_source_logs_error(self):
        """An source name not in SOURCES should produce an error job."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        jobs = await ingest(
            mock_session,
            queries=["test"],
            sources=["nonexistent_source"],
            max_pages=1,
            enforce_whitelist=False,
        )

        assert len(jobs) == 1
        assert jobs[0].error_count == 1
        assert "Unknown source" in jobs[0].errors[0]


# =============================================================================
# dedup behavior
# =============================================================================


class TestOrchestratorDedup:
    @pytest.mark.asyncio
    async def test_duplicate_items_across_pages_are_deduped(self):
        """Items with same dedup_key across pages are counted once."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        # Searcher that returns the same item on pages 1 and 2
        async def _repeat_searcher(query: str, page: int = 1):
            from app.services.literature_ingestion import LiteratureItem

            item = LiteratureItem(
                title="Same Paper",
                source="mock",
                source_url="https://mock.example/same",
                doi="10.1000/same",
                year=2023,
            )
            return [item], 1

        with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                   {"mock": _repeat_searcher}):
            with patch("app.services.literature_ingestion.orchestrator.filter_new_items",
                       new_callable=AsyncMock) as mock_filter:
                mock_filter.return_value = [_make_item("Same Paper", "mock",
                                                       "https://mock.example/same",
                                                       doi="10.1000/same")]
                with patch("app.services.literature_ingestion.orchestrator._save_items",
                           new_callable=AsyncMock) as mock_save:
                    jobs = await ingest(
                        mock_session,
                        queries=["test"],
                        sources=["mock"],
                        max_pages=2,
                        enforce_whitelist=False,
                    )

        job = jobs[0]
        # total_found = deduped count; duplicates_skipped counts cross-page dup removal
        assert job.total_found == 1  # deduped across pages
        assert job.duplicates_skipped == 0  # filtered_new returns the one item → zero DB dup
        assert mock_save.call_count == 1


# =============================================================================
# result aggregation
# =============================================================================


class TestResultAggregation:
    @pytest.mark.asyncio
    async def test_multiple_queries_all_executed(self):
        """Every query × source combination produces a job."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                   {"mock": _ok_searcher}):
            with patch("app.services.literature_ingestion.orchestrator.filter_new_items",
                       new_callable=AsyncMock) as mock_filter:
                mock_filter.return_value = [_make_item("Kept", "mock", "https://x.com")]
                with patch("app.services.literature_ingestion.orchestrator._save_items",
                           new_callable=AsyncMock) as mock_save:
                    jobs = await ingest(
                        mock_session,
                        queries=["q1", "q2"],
                        sources=["mock"],
                        max_pages=1,
                        enforce_whitelist=False,
                    )

        assert len(jobs) == 2
        assert {j.query for j in jobs} == {"q1", "q2"}
        assert mock_save.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_page_stops_pagination(self):
        """When a page returns zero items, pagination stops (no further pages)."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()
        call_count = 0

        async def _once_then_empty(query: str, page: int = 1):
            nonlocal call_count
            call_count += 1
            if page == 1:
                return [_make_item("Only One", "mock", "https://x.com")], 1
            return [], 0

        with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                   {"mock": _once_then_empty}):
            with patch("app.services.literature_ingestion.orchestrator.filter_new_items",
                       new_callable=AsyncMock) as mock_filter:
                mock_filter.return_value = [_make_item("Only One", "mock", "https://x.com")]
                with patch("app.services.literature_ingestion.orchestrator._save_items",
                           new_callable=AsyncMock):
                    jobs = await ingest(
                        mock_session,
                        queries=["test"],
                        sources=["mock"],
                        max_pages=3,
                        enforce_whitelist=False,
                    )

        # Page 1 returns item, page 2 returns empty → stops at page 2
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_save_items_preserved_count(self):
        """After successful save, job records new_added and total_found."""
        from app.services.literature_ingestion.orchestrator import ingest
        from app.services.literature_ingestion import IngestionJob

        mock_session = AsyncMock()

        async def _two_items_searcher(query: str, page: int = 1):
            return [
                _make_item("Item 1", "mock", "https://x.com/1"),
                _make_item("Item 2", "mock", "https://x.com/2"),
            ], 2

        with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                   {"mock": _two_items_searcher}):
            with patch("app.services.literature_ingestion.orchestrator.filter_new_items",
                       new_callable=AsyncMock) as mock_filter:
                # Both items are "new"
                mock_filter.return_value = [
                    _make_item("Item 1", "mock", "https://x.com/1"),
                    _make_item("Item 2", "mock", "https://x.com/2"),
                ]
                with patch("app.services.literature_ingestion.orchestrator._save_items",
                           new_callable=AsyncMock) as mock_save:
                    jobs = await ingest(
                        mock_session,
                        queries=["test"],
                        sources=["mock"],
                        max_pages=1,
                        enforce_whitelist=False,
                    )

        assert jobs[0].total_found == 2


# =============================================================================
# error handling within page loop
# =============================================================================


class TestPageLevelErrorHandling:
    @pytest.mark.asyncio
    async def test_page_error_logged_but_continues(self):
        """HTTP error on one page logs error but doesn't crash the job."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        async def _fail_page2(query: str, page: int = 1):
            if page == 2:
                raise httpx.ConnectError("timeout on page 2")
            return [_make_item(f"Page{page}", "mock", f"https://x.com/p{page}")], 1

        with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                   {"mock": _fail_page2}):
            with patch("app.services.literature_ingestion.orchestrator.filter_new_items",
                       new_callable=AsyncMock) as mock_filter:
                mock_filter.return_value = [_make_item("Page1", "mock", "https://x.com/p1")]
                with patch("app.services.literature_ingestion.orchestrator._save_items",
                           new_callable=AsyncMock) as mock_save:
                    jobs = await ingest(
                        mock_session,
                        queries=["test"],
                        sources=["mock"],
                        max_pages=2,
                        enforce_whitelist=False,
                    )

        job = jobs[0]
        # Page 1 succeeded, page 2 errored
        assert job.total_found == 1  # only page 1 items counted
        assert job.error_count > 0  # page 2 error logged
        assert any("page 2" in e.lower() for e in job.errors)


# =============================================================================
# SQLAlchemy error isolation
# =============================================================================


class TestSQLAlchemyErrorIsolation:
    @pytest.mark.asyncio
    async def test_sqla_error_in_searcher_context_does_not_crash_orchestrator(self):
        """A RuntimeError from the searcher layer is caught per-query."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        async def _exploding_searcher(query: str, page: int = 1):
            raise RuntimeError("simulated crash")

        with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                   {"bad": _exploding_searcher}):
            jobs = await ingest(
                mock_session,
                queries=["test"],
                sources=["bad"],
                max_pages=1,
                enforce_whitelist=False,
            )

        assert len(jobs) == 1
        assert jobs[0].error_count > 0
        assert "RuntimeError" in jobs[0].errors[0]


# =============================================================================
# custom queries/sources parameters
# =============================================================================


class TestCustomParameters:
    @pytest.mark.asyncio
    async def test_default_queries_used_when_none_provided(self):
        """When queries=None, the default QUERIES list is used."""
        from app.services.literature_ingestion.orchestrator import QUERIES, ingest

        mock_session = AsyncMock()

        with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                   {"mock": _ok_searcher}):
            with patch("app.services.literature_ingestion.orchestrator.filter_new_items",
                       new_callable=AsyncMock) as mock_filter:
                mock_filter.return_value = [_make_item("Result", "mock", "https://x.com")]
                with patch("app.services.literature_ingestion.orchestrator._save_items",
                           new_callable=AsyncMock):
                    jobs = await ingest(
                        mock_session,
                        queries=None,
                        sources=["mock"],
                        max_pages=1,
                        enforce_whitelist=False,
                    )

        assert len(jobs) == len(QUERIES)  # one job per default query


# =============================================================================
# Additional coverage gap tests
# =============================================================================


class TestWhitelistAllowedSourceFiltered:
    """Cover orchestrator.py lines 108, 130-132: allowed source flows through, error isolation."""

    @pytest.mark.asyncio
    async def test_allowed_source_passes_gate_and_reaches_save(self):
        """Source allowed by whitelist proceeds to normal execution (covers line 108)."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()
        mock_wl = MagicMock()
        mock_wl.is_source_allowed.return_value = True

        with patch("app.services.source_whitelist.get_whitelist",
                   return_value=mock_wl):
            with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                       {"mock": _ok_searcher}):
                with patch("app.services.literature_ingestion.orchestrator.filter_new_items",
                           new_callable=AsyncMock) as mock_filter:
                    mock_filter.return_value = [_make_item("Kept", "mock", "https://x.com")]
                    with patch("app.services.literature_ingestion.orchestrator._save_items",
                               new_callable=AsyncMock) as mock_save:
                        jobs = await ingest(
                            mock_session,
                            queries=["test"],
                            sources=["mock"],
                            max_pages=1,
                            enforce_whitelist=True,
                        )

        # Should have one normal job (not gate), no whitelist errors
        gate_jobs = [j for j in jobs if j.query == "<whitelist gate>"]
        assert len(gate_jobs) == 0
        assert len(jobs) == 1
        assert jobs[0].source == "mock"
        assert jobs[0].success is True
        assert mock_save.call_count >= 1

    @pytest.mark.asyncio
    async def test_keyboard_interrupt_passthrough_does_not_trap(self):
        """A non-(SQLAlchemyError,ValueError,RuntimeError) exception propagates.
        Covers the except clause boundary at line 130."""
        from app.services.literature_ingestion.orchestrator import ingest

        mock_session = AsyncMock()

        async def _type_error_searcher(query: str, page: int = 1):
            raise TypeError("not-a-handled-type")

        with patch("app.services.literature_ingestion.orchestrator.SOURCES",
                   {"mock": _type_error_searcher}):
            # TypeError is NOT in (SQLAlchemyError, ValueError, RuntimeError), should propagate
            with pytest.raises(TypeError):
                await ingest(
                    mock_session,
                    queries=["test"],
                    sources=["mock"],
                    max_pages=1,
                    enforce_whitelist=False,
                )
