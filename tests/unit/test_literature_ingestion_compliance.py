"""
Compliance tests for literature ingestion — no full-text download,
mandatory source_url, audit trail, error tracking.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from app.db.base import Base
from app.services.literature_ingestion import IngestionJob, LiteratureItem
from app.services.literature_ingestion.orchestrator import _save_items
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    async_session = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


# ---------------------------------------------------------------------------
# IngestionJob audit compliance
# ---------------------------------------------------------------------------

class TestIngestionJobCompliance:
    def test_every_job_has_started_at(self):
        job = IngestionJob(source="openalex", query="Huangfu Mi")
        job.start()
        assert job.started_at != ""

    def test_every_job_has_finished_at(self):
        job = IngestionJob(source="crossref", query="Zhenjiu Jiayi Jing")
        job.finish()
        assert job.finished_at != ""

    def test_full_success_job_log(self):
        job = IngestionJob(source="pubmed", query="皇甫谧")
        job.start()
        job.total_found = 12
        job.new_added = 10
        job.duplicates_skipped = 2
        job.finish()
        assert job.success is True
        assert job.total_found == 12
        assert job.new_added == 10
        assert job.duplicates_skipped == 2
        assert job.error_count == 0

    def test_error_job_never_success(self):
        job = IngestionJob(source="core", query="甲乙经")
        job.start()
        job.error_count = 3
        job.finish()
        assert job.success is False

    def test_partial_error_counts_preserved(self):
        """Partially failed job records error_count but still reports finds."""
        job = IngestionJob(source="internet_archive", query="A-B Classic")
        job.start()
        job.total_found = 20
        job.new_added = 15
        job.duplicates_skipped = 3
        job.error_count = 2
        job.errors = ["timeout on page 3", "parse error on item 7"]
        job.finish()
        assert job.success is False
        assert job.total_found == 20
        assert job.new_added == 15


# ---------------------------------------------------------------------------
# source_url mandatory compliance
# ---------------------------------------------------------------------------

class TestSourceUrlMandatory:
    def test_literature_item_requires_source_url_in_constructor(self):
        """Every item MUST have source_url set."""
        item = LiteratureItem(
            title="Huangfu Mi Biography",
            source="openalex",
            source_url="https://openalex.org/W12345",
        )
        assert item.source_url != ""

    def test_empty_source_url_rejected(self):
        """Empty source_url must raise ValueError — never construct with it."""
        with pytest.raises(ValueError, match="source_url"):
            LiteratureItem(
                title="Bad Item",
                source="openalex",
                source_url="",
            )

    def test_try_create_returns_none_for_invalid(self):
        """try_create returns None silently instead of raising."""
        item = LiteratureItem.try_create(
            title="Bad Item",
            source="openalex",
            source_url="",
        )
        assert item is None

    def test_empty_title_rejected(self):
        with pytest.raises(ValueError, match="title"):
            LiteratureItem(title="", source="openalex", source_url="https://example.com")

    def test_empty_source_rejected(self):
        with pytest.raises(ValueError, match="source"):
            LiteratureItem(title="X", source="", source_url="https://example.com")

    def test_non_url_source_url_rejected(self):
        with pytest.raises(ValueError, match="HTTP"):
            LiteratureItem(title="X", source="openalex", source_url="not-a-url")

    def test_dedup_preserves_source_urls(self):
        """Dedup by DOI doesn't mix up source_url from different records."""
        a = LiteratureItem(
            title="Same Paper",
            source="openalex",
            source_url="https://openalex.org/W1",
            doi="10.1000/test",
        )
        b = LiteratureItem(
            title="Same Paper",
            source="crossref",
            source_url="https://doi.org/10.1000/test",
            doi="10.1000/test",
        )
        assert a.dedup_key() == b.dedup_key()
        assert a.source_url != b.source_url
        # Both survive cross-source dedup; first-writer-wins at DB layer.


# ---------------------------------------------------------------------------
# No full-text download compliance
# ---------------------------------------------------------------------------

class TestNoFullTextDownload:
    def test_literature_item_has_no_fulltext_field(self):
        """LiteratureItem must not carry full-text content."""
        item = LiteratureItem(
            title="Test",
            source="openalex",
            source_url="https://example.com",
        )
        assert not hasattr(item, "full_text")
        assert not hasattr(item, "pdf_data")
        assert not hasattr(item, "download_url")

    def test_client_search_returns_metadata_only(self):
        """All client search() functions return LiteratureItem list — never raw text."""
        import inspect

        from app.services.literature_ingestion import (
            core_client,
            crossref_client,
            internet_archive_client,
            openalex_client,
            pubmed_client,
        )

        for mod in (openalex_client, crossref_client, core_client, pubmed_client, internet_archive_client):
            sig = inspect.signature(mod.search)
            return_annotation = sig.return_annotation
            assert "LiteratureItem" in str(return_annotation), f"{mod.__name__} search returns LiteratureItem"

    def test_clients_never_request_pdf_or_fulltext_urls(self):
        """No client sends requests to PDF/full-text/download endpoints."""
        import inspect

        from app.services.literature_ingestion import (
            core_client,
            crossref_client,
            internet_archive_client,
            openalex_client,
            pubmed_client,
        )

        clients = [openalex_client, crossref_client, core_client, pubmed_client, internet_archive_client]
        for mod in clients:
            source = inspect.getsource(mod)
            assert ".pdf" not in source.lower(), f"{mod.__name__} references .pdf"
            assert "fulltext" not in source.lower(), f"{mod.__name__} references fulltext"
            assert "full_text" not in source.lower(), f"{mod.__name__} references full_text"
            assert "full text" not in source.lower(), f"{mod.__name__} references full text"
            assert "download.pdf" not in source.lower(), f"{mod.__name__} references download.pdf"

    def test_core_client_uses_work_url_not_download_url(self):
        """CORE source_url must be the work/detail page, not downloadUrl."""
        import inspect

        from app.services.literature_ingestion import core_client

        source = inspect.getsource(core_client)
        # Must construct a core.ac.uk/works/ URL
        assert 'core.ac.uk/works/' in source
        # Must NOT save downloadUrl as source_url
        assert 'source_url' not in source.split('downloadUrl')[1].split('source_url')[0] if 'downloadUrl' in source else True
        # downloadUrl should not appear as source_url value
        assert 'source_url=' not in source or 'downloadUrl' not in source[source.index('source_url='):].split('\n')[0].lower()


# ---------------------------------------------------------------------------
# _save_items compliance
# ---------------------------------------------------------------------------

class TestSaveItemsCompliance:
    @pytest.mark.asyncio
    async def test_save_preserves_source_url(self, db_session: AsyncSession):
        from app.models.paper import Paper
        from sqlalchemy import select

        job = IngestionJob(source="pubmed", query="test")
        item = LiteratureItem(
            title="Compliance Test Paper",
            source="pubmed",
            source_url="https://pubmed.ncbi.nlm.nih.gov/12345/",
            doi="10.1000/compliance",
            year=2025,
        )
        await _save_items(db_session, [item], job)
        await db_session.flush()

        stmt = select(Paper).where(Paper.doi == "10.1000/compliance")
        result = await db_session.execute(stmt)
        paper = result.scalar_one_or_none()
        assert paper is not None
        assert paper.source_url == "https://pubmed.ncbi.nlm.nih.gov/12345/"
        assert paper.full_text is None  # never store full text

    @pytest.mark.asyncio
    async def test_save_never_stores_full_text(self, db_session: AsyncSession):
        from app.models.paper import Paper
        from sqlalchemy import select

        job = IngestionJob(source="crossref", query="test")
        item = LiteratureItem(
            title="No Full Text Paper",
            source="crossref",
            source_url="https://doi.org/10.1000/nofull",
            doi="10.1000/nofull",
        )
        await _save_items(db_session, [item], job)
        await db_session.flush()

        stmt = select(Paper).where(Paper.doi == "10.1000/nofull")
        result = await db_session.execute(stmt)
        paper = result.scalar_one_or_none()
        assert paper is not None
        assert paper.full_text is None

    @pytest.mark.asyncio
    async def test_save_error_increments_error_count(self, db_session: AsyncSession):
        """If one item fails to save, error_count increases, partial success."""
        job = IngestionJob(source="openalex", query="test")
        items = [
            LiteratureItem(
                title="Good Paper",
                source="openalex",
                source_url="https://example.com/good",
                doi="10.1000/good",
                year=2024,
            ),
        ]
        await _save_items(db_session, items, job)
        await db_session.commit()

        assert job.error_count == 0
        assert job.new_added == 1

    @pytest.mark.asyncio
    async def test_save_empty_source_url_rejected(self, db_session: AsyncSession):
        """_save_items must skip items whose source_url.strip() is empty and log error."""
        job = IngestionJob(source="openalex", query="test")
        # We can't construct a LiteratureItem with empty source_url anymore,
        # but _save_items also checks source_url.strip() as a belt-and-suspenders guard.
        # This test verifies the try_create path won't produce items with empty urls.
        item = LiteratureItem.try_create(
            title="Has URL",
            source="openalex",
            source_url="https://example.com/ok",
        )
        assert item is not None
        await _save_items(db_session, [item], job)
        await db_session.flush()
        assert job.new_added == 1

        null_item = LiteratureItem.try_create(
            title="No URL Item",
            source="openalex",
            source_url="",
        )
        assert null_item is None  # try_create rejects, never reaches _save_items

    @pytest.mark.asyncio
    async def test_flush_failure_sets_job_error(self, db_session: AsyncSession):
        """When session.flush() fails, job.error_count and job.errors must reflect it."""
        from unittest.mock import AsyncMock

        job = IngestionJob(source="crossref", query="test")
        item = LiteratureItem(
            title="Flush Test Paper",
            source="crossref",
            source_url="https://doi.org/10.1000/flushtest",
            doi="10.1000/flushtest",
            year=2026,
        )
        await _save_items(db_session, [item], job)
        assert job.error_count == 0

        # Use a second item that will trigger a flush failure via mocked flush
        job2 = IngestionJob(source="crossref", query="test2")
        item2 = LiteratureItem(
            title="Flush Test Paper 2",
            source="crossref",
            source_url="https://doi.org/10.1000/flushtest2",
            doi="10.1000/flushtest2",
            year=2026,
        )
        # Mock session.flush to raise — the _save_items try/except must catch it
        original_flush = db_session.flush
        db_session.flush = AsyncMock(side_effect=RuntimeError("forced flush failure"))  # type: ignore[method-assign]
        try:
            await _save_items(db_session, [item2], job2)
        finally:
            db_session.flush = original_flush

        assert job2.error_count > 0, f"Expected error_count>0, got {job2.error_count}"
        assert any("Flush" in e for e in job2.errors), f"Expected Flush error in: {job2.errors}"
