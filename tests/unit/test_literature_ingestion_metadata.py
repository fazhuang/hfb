"""
Test literature metadata ingestion — client behavior and result normalization.
"""

from __future__ import annotations

from app.services.literature_ingestion import LiteratureItem

# ---------------------------------------------------------------------------
# LiteratureItem normalization
# ---------------------------------------------------------------------------

class TestLiteratureItem:
    def test_dedup_key_uses_doi_when_present(self):
        item = LiteratureItem(
            title="Test Paper",
            source="openalex",
            source_url="https://example.com",
            doi="10.1234/foo.bar",
            year=2023,
        )
        assert item.dedup_key() == "doi:10.1234/foo.bar"

    def test_dedup_key_falls_back_to_title_year(self):
        item = LiteratureItem(
            title="A-B Classic of Acupuncture",
            source="crossref",
            source_url="https://example.com",
            year=2020,
        )
        assert item.dedup_key() == "title:a-b classic of acupuncture|2020"

    def test_dedup_key_no_year(self):
        item = LiteratureItem(
            title="Zhenjiu Jiayi Jing",
            source="pubmed",
            source_url="https://example.com",
        )
        assert item.dedup_key() == "title:zhenjiu jiayi jing|"

    def test_title_normalization_trims_whitespace(self):
        item = LiteratureItem(
            title="  Huangfu Mi  ",
            source="core",
            source_url="https://example.com",
            year=1999,
        )
        assert item.dedup_key() == "title:huangfu mi|1999"

    def test_source_url_always_recorded(self):
        item = LiteratureItem(
            title="Test",
            source="internet_archive",
            source_url="https://archive.org/details/test",
        )
        assert item.source_url == "https://archive.org/details/test"

    def test_keywords_defaults_to_empty_string(self):
        item = LiteratureItem(
            title="Test",
            source="openalex",
            source_url="https://example.com",
        )
        assert item.keywords == ""

    def test_is_open_access_defaults_to_false(self):
        item = LiteratureItem(
            title="Test",
            source="openalex",
            source_url="https://example.com",
        )
        assert item.is_open_access is False


# ---------------------------------------------------------------------------
# IngestionJob state machine
# ---------------------------------------------------------------------------

class TestIngestionJob:
    def test_success_when_no_errors(self):
        from app.services.literature_ingestion import IngestionJob

        job = IngestionJob(source="openalex", query="Huangfu Mi")
        job.start()
        job.total_found = 5
        job.new_added = 3
        job.duplicates_skipped = 2
        job.finish()
        assert job.success is True
        assert job.started_at != ""
        assert job.finished_at != ""

    def test_failure_when_errors_present(self):
        from app.services.literature_ingestion import IngestionJob

        job = IngestionJob(source="core", query="甲乙经")
        job.start()
        job.error_count = 2
        job.errors.append("Connection timeout")
        job.finish()
        assert job.success is False
        assert job.error_count == 2

    def test_partial_failure_not_marked_success(self):
        from app.services.literature_ingestion import IngestionJob

        job = IngestionJob(source="pubmed", query="皇甫谧")
        job.start()
        job.total_found = 10
        job.new_added = 8
        job.error_count = 1
        job.finish()
        assert job.success is False
        assert job.new_added == 8
