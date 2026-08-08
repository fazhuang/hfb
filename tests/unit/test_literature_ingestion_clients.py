"""
Deterministic unit tests for literature ingestion API clients.
Covers: request construction, response parsing, error handling, timeout,
OA detection, and fallback branches. All external HTTP is mocked via
httpx.AsyncClient injection — no real network requests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

# =============================================================================
# Helpers
# =============================================================================


def _json_response(data: dict, status: int = 200) -> MagicMock:
    """Build a mock httpx response with .json() and .raise_for_status()."""
    resp = MagicMock()
    resp.json.return_value = data
    resp.status_code = status
    if status >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status}",
            request=MagicMock(),
            response=httpx.Response(status),
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# =============================================================================
# core_client
# =============================================================================


class TestCoreClient:
    @pytest.mark.asyncio
    async def test_search_parses_valid_response(self):
        from app.services.literature_ingestion.core_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "totalHits": 2,
                "results": [
                    {
                        "id": "123",
                        "title": "Study on Acupuncture",
                        "authors": [{"name": "Li Si"}, {"name": "Wang Wu"}],
                        "yearPublished": 2020,
                        "abstract": "An important study.",
                        "subjects": ["acupuncture", "TCM"],
                        "doi": "10.1000/test.1",
                        "publisher": "Journal of TCM",
                        "downloadUrl": "https://api.core.ac.uk/v3/download/123/pdf",
                        "language": {"code": "en"},
                    },
                    {
                        "id": "456",
                        "title": "Huangfu Mi Research",
                        "authors": [],
                        "yearPublished": 2019,
                        "abstract": "",
                        "subjects": [],
                        "doi": "",
                        "publisher": "",
                        "language": {"code": "zh"},
                    },
                ],
            }
        )

        items, total = await search("acupuncture", http_client=mock_client)

        assert total == 2
        assert len(items) == 2
        assert items[0].title == "Study on Acupuncture"
        assert items[0].source == "core"
        assert items[0].source_url == "https://core.ac.uk/works/123"
        assert items[0].authors == "Li Si, Wang Wu"
        assert items[0].year == 2020
        assert items[0].doi == "10.1000/test.1"
        assert items[0].is_open_access is True
        assert items[0].language == "en"
        assert items[1].title == "Huangfu Mi Research"
        assert items[1].is_open_access is False
        assert items[1].language == "zh"
        assert items[1].keywords == ""

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        from app.services.literature_ingestion.core_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response({"totalHits": 0, "results": []})

        items, total = await search("nonexistent", http_client=mock_client)

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_search_non_2xx_raises(self):
        from app.services.literature_ingestion.core_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response({}, status=500)

        with pytest.raises(httpx.HTTPStatusError):
            await search("test", http_client=mock_client)

    @pytest.mark.asyncio
    async def test_search_connect_error_raises(self):
        from app.services.literature_ingestion.core_client import search

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        with pytest.raises(httpx.ConnectError):
            await search("test", http_client=mock_client)

    @pytest.mark.asyncio
    async def test_search_null_result_fields_defaulted(self):
        """Missing optional fields (authors, doi, downloadUrl) default safely."""
        from app.services.literature_ingestion.core_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "totalHits": 1,
                "results": [
                    {
                        "id": "999",
                        "title": "Minimal Paper",
                        "yearPublished": None,
                        "abstract": "",
                        "publisher": "",
                        "language": "en",  # string not dict — edge case
                    }
                ],
            }
        )

        items, total = await search("minimal", http_client=mock_client)
        assert len(items) == 1
        assert items[0].title == "Minimal Paper"
        assert items[0].authors == ""
        assert items[0].doi == ""
        assert items[0].is_open_access is False
        assert items[0].language == "en"

    @pytest.mark.asyncio
    async def test_search_builds_correct_url_and_params(self):
        """Verify the request URL and parameters are correctly constructed."""
        from app.services.literature_ingestion.core_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response({"totalHits": 0, "results": []})

        await search("Huangfu Mi", page=2, per_page=5, http_client=mock_client)

        call_args = mock_client.get.call_args
        url = call_args[0][0]
        params = call_args[1]["params"]

        assert "api.core.ac.uk/v3/search/works" in url
        assert params["q"] == "Huangfu Mi"
        assert params["limit"] == "5"
        assert params["offset"] == "5"  # (page-1)*per_page = (2-1)*5

    @pytest.mark.asyncio
    async def test_search_without_passed_client_creates_own(self):
        """When no http_client is passed, the function creates its own and closes it."""
        from app.services.literature_ingestion.core_client import search

        with patch(
            "app.services.literature_ingestion.core_client._http_client"
        ) as mock_factory:
            mock_client = AsyncMock()
            mock_client.get.return_value = _json_response(
                {"totalHits": 0, "results": []}
            )
            mock_factory.return_value = mock_client

            items, total = await search("test")

            assert total == 0
            mock_factory.assert_called_once()
            mock_client.aclose.assert_called_once()


# =============================================================================
# crossref_client
# =============================================================================


class TestCrossrefClient:
    @pytest.mark.asyncio
    async def test_search_parses_valid_response(self):
        from app.services.literature_ingestion.crossref_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "message": {
                    "total-results": 1,
                    "items": [
                        {
                            "DOI": "10.1000/cr.test",
                            "title": ["Crossref Test Paper"],
                            "author": [
                                {"given": "Si", "family": "Li"},
                                {"given": "Wu", "family": "Wang"},
                            ],
                            "published-print": {"date-parts": [[2021, 3, 15]]},
                            "abstract": "<jats:p>An abstract with</jats:p><jats:p>structured content.</jats:p>",
                            "subject": ["Medicine", "History"],
                            "container-title": ["Journal of Medical History"],
                            "license": [
                                {"URL": "http://creativecommons.org/licenses/by/4.0/"}
                            ],
                            "language": "en",
                            "URL": "https://example.com/fallback",
                        }
                    ],
                }
            }
        )

        items, total = await search("test", http_client=mock_client)

        assert total == 1
        assert len(items) == 1
        assert items[0].title == "Crossref Test Paper"
        assert items[0].source == "crossref"
        assert items[0].source_url == "https://doi.org/10.1000/cr.test"
        assert items[0].authors == "Si Li, Wu Wang"
        assert items[0].year == 2021
        assert items[0].doi == "10.1000/cr.test"
        assert items[0].journal == "Journal of Medical History"
        assert items[0].is_open_access is True  # creativecommons license
        assert "jats:p" not in items[0].abstract  # HTML tags stripped
        assert "structured" in items[0].abstract  # text content preserved
        assert items[0].language == "en"

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        from app.services.literature_ingestion.crossref_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {"message": {"total-results": 0, "items": []}}
        )

        items, total = await search("nonexistent", http_client=mock_client)
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_search_non_2xx_raises(self):
        from app.services.literature_ingestion.crossref_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response({}, status=503)

        with pytest.raises(httpx.HTTPStatusError):
            await search("test", http_client=mock_client)

    @pytest.mark.asyncio
    async def test_search_connect_error_raises(self):
        from app.services.literature_ingestion.crossref_client import search

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("timeout")

        with pytest.raises(httpx.ConnectError):
            await search("test", http_client=mock_client)

    @pytest.mark.asyncio
    async def test_no_doi_uses_url_fallback(self):
        """When DOI is empty, source_url falls back to the URL field."""
        from app.services.literature_ingestion.crossref_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "message": {
                    "total-results": 1,
                    "items": [
                        {
                            "title": ["No DOI Paper"],
                            "URL": "https://example.com/no-doi",
                            "author": [],
                            "abstract": "",
                            "language": "en",
                        }
                    ],
                }
            }
        )

        items, total = await search("test", http_client=mock_client)
        assert len(items) == 1
        assert items[0].source_url == "https://example.com/no-doi"

    @pytest.mark.asyncio
    async def test_open_access_detection_via_cc_by(self):
        """_check_crossref_oa returns True for CC-BY license URL."""
        from app.services.literature_ingestion.crossref_client import _check_crossref_oa

        work = {"license": [{"URL": "http://creativecommons.org/licenses/by/4.0/"}]}
        assert _check_crossref_oa(work) is True

    @pytest.mark.asyncio
    async def test_open_access_detection_via_open_access_tag(self):
        """_check_crossref_oa returns True for 'open-access' in license URL."""
        from app.services.literature_ingestion.crossref_client import _check_crossref_oa

        work = {"license": [{"URL": "https://publisher.com/open-access"}]}
        assert _check_crossref_oa(work) is True

    @pytest.mark.asyncio
    async def test_open_access_detection_no_license(self):
        """_check_crossref_oa returns False when no OA license found."""
        from app.services.literature_ingestion.crossref_client import _check_crossref_oa

        work = {"license": [{"URL": "https://publisher.com/all-rights-reserved"}]}
        assert _check_crossref_oa(work) is False

    @pytest.mark.asyncio
    async def test_open_access_detection_empty_license(self):
        """_check_crossref_oa returns False when license list is empty."""
        from app.services.literature_ingestion.crossref_client import _check_crossref_oa

        work = {"license": []}
        assert _check_crossref_oa(work) is False

    @pytest.mark.asyncio
    async def test_first_abstract_strips_html_tags(self):
        """_first_abstract removes HTML tags from abstract text."""
        from app.services.literature_ingestion.crossref_client import _first_abstract

        work = {"abstract": "<jats:p>Main finding.</jats:p><jats:p>Secondary.</jats:p>"}
        result = _first_abstract(work)
        assert "<jats:p>" not in result
        assert "Main finding." in result
        assert "Secondary." in result

    @pytest.mark.asyncio
    async def test_first_abstract_empty(self):
        from app.services.literature_ingestion.crossref_client import _first_abstract

        assert _first_abstract({}) == ""
        assert _first_abstract({"abstract": ""}) == ""

    @pytest.mark.asyncio
    async def test_year_from_created_date(self):
        """When published-print is missing, falls back to created date."""
        from app.services.literature_ingestion.crossref_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "message": {
                    "total-results": 1,
                    "items": [
                        {
                            "title": ["Fallback Year Paper"],
                            "URL": "https://example.com/fallback",
                            "created": {"date-parts": [[2019, 6, 1]]},
                            "author": [],
                            "abstract": "",
                            "language": "en",
                        }
                    ],
                }
            }
        )

        items, total = await search("test", http_client=mock_client)
        assert items[0].year == 2019


# =============================================================================
# internet_archive_client
# =============================================================================


class TestInternetArchiveClient:
    @pytest.mark.asyncio
    async def test_search_parses_valid_response(self):
        from app.services.literature_ingestion.internet_archive_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "response": {
                    "numFound": 1,
                    "docs": [
                        {
                            "identifier": "test-item-001",
                            "title": "Classic Chinese Medicine Text",
                            "creator": ["Author One", "Author Two"],
                            "year": "1923",
                            "description": ["A scanned ancient text."],
                            "subject": ["Medicine, Chinese Traditional"],
                            "language": "zh",
                            "doi": "10.1000/ia.test",
                            "licenseurl": "http://creativecommons.org/publicdomain/zero/1.0/",
                        }
                    ],
                }
            }
        )

        items, total = await search("Chinese medicine", http_client=mock_client)

        assert total == 1
        assert len(items) == 1
        assert items[0].title == "Classic Chinese Medicine Text"
        assert items[0].source == "internet_archive"
        assert items[0].source_url == "https://archive.org/details/test-item-001"
        assert items[0].authors == "Author One, Author Two"
        assert items[0].year == 1923
        assert items[0].doi == "10.1000/ia.test"
        assert items[0].is_open_access is True
        assert items[0].language == "zh"

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        from app.services.literature_ingestion.internet_archive_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {"response": {"numFound": 0, "docs": []}}
        )

        items, total = await search("nonexistent", http_client=mock_client)
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_search_non_2xx_raises(self):
        from app.services.literature_ingestion.internet_archive_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response({}, status=429)

        with pytest.raises(httpx.HTTPStatusError):
            await search("test", http_client=mock_client)

    @pytest.mark.asyncio
    async def test_search_connect_error_raises(self):
        from app.services.literature_ingestion.internet_archive_client import search

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("DNS failure")

        with pytest.raises(httpx.ConnectError):
            await search("test", http_client=mock_client)

    @pytest.mark.asyncio
    async def test_no_identifier_produces_empty_source_url(self):
        """When identifier is missing, source_url is empty; item skipped by try_create."""
        from app.services.literature_ingestion.internet_archive_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "response": {
                    "numFound": 1,
                    "docs": [
                        {
                            "title": "No ID Item",
                            "creator": [],
                            "description": [],
                            "language": "en",
                        }
                    ],
                }
            }
        )

        items, total = await search("test", http_client=mock_client)
        assert total == 1
        assert len(items) == 0  # source_url empty → try_create returns None

    @pytest.mark.asyncio
    async def test_extract_doi_from_doi_field(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _extract_doi,
        )

        assert _extract_doi({"doi": "10.1234/foo"}) == "10.1234/foo"

    @pytest.mark.asyncio
    async def test_extract_doi_from_identifier_list(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _extract_doi,
        )

        doc = {"identifier": ["not-a-doi", "10.5678/from-list"]}
        assert _extract_doi(doc) == "10.5678/from-list"

    @pytest.mark.asyncio
    async def test_extract_doi_no_match(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _extract_doi,
        )

        assert _extract_doi({}) == ""
        assert _extract_doi({"doi": "not-a-doi-prefix"}) == ""

    @pytest.mark.asyncio
    async def test_is_ia_oa_defaults_true(self):
        """Internet Archive texts are OA by default."""
        from app.services.literature_ingestion.internet_archive_client import _is_ia_oa

        # No licenseurl — still OA (IA texts are public domain by nature)
        assert _is_ia_oa({}) is True
        assert _is_ia_oa({"licenseurl": "https://example.com/all-rights"}) is True

    @pytest.mark.asyncio
    async def test_is_ia_oa_cc_license(self):
        from app.services.literature_ingestion.internet_archive_client import _is_ia_oa

        assert (
            _is_ia_oa({"licenseurl": "http://creativecommons.org/licenses/by/4.0/"})
            is True
        )
        assert (
            _is_ia_oa(
                {"licenseurl": "http://creativecommons.org/publicdomain/zero/1.0/"}
            )
            is True
        )
        assert _is_ia_oa({"licenseurl": "https://example.com/cc0-waiver"}) is True

    @pytest.mark.asyncio
    async def test_first_lang_string(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _first_lang,
        )

        assert _first_lang({"language": "eng"}) == "eng"
        assert _first_lang({"language": "zh-Hans"}) == "zh-Ha"

    @pytest.mark.asyncio
    async def test_first_lang_list(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _first_lang,
        )

        assert _first_lang({"language": ["eng", "fra"]}) == "eng"

    @pytest.mark.asyncio
    async def test_first_lang_missing(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _first_lang,
        )

        assert _first_lang({}) == "en"

    @pytest.mark.asyncio
    async def test_join_creators_string(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _join_creators,
        )

        assert _join_creators("Single Author") == "Single Author"

    @pytest.mark.asyncio
    async def test_join_creators_list(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _join_creators,
        )

        assert _join_creators(["A", "B"]) == "A, B"

    @pytest.mark.asyncio
    async def test_join_creators_none(self):
        from app.services.literature_ingestion.internet_archive_client import (
            _join_creators,
        )

        assert _join_creators(None) == ""


# =============================================================================
# openalex_client
# =============================================================================


class TestOpenAlexClient:
    @pytest.mark.asyncio
    async def test_search_parses_valid_response(self):
        from app.services.literature_ingestion.openalex_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "meta": {"count": 1},
                "results": [
                    {
                        "id": "https://openalex.org/W12345",
                        "title": "Acupuncture Mechanisms",
                        "authorships": [
                            {"author": {"display_name": "Li Si"}},
                            {"author": {"display_name": "Wang Wu"}},
                        ],
                        "publication_year": 2022,
                        "abstract_inverted_index": {
                            "This": [0],
                            "study": [1],
                            "examines": [2],
                            "pain": [3],
                        },
                        "concepts": [
                            {"display_name": "Medicine"},
                            {"display_name": "Acupuncture"},
                        ],
                        "doi": "https://doi.org/10.1000/oa.test",
                        "primary_location": {
                            "source": {"display_name": "Pain Research Journal"}
                        },
                        "open_access": {"is_oa": True},
                        "language": "en",
                    }
                ],
            }
        )

        items, total = await search("acupuncture", http_client=mock_client)

        assert total == 1
        assert len(items) == 1
        assert items[0].title == "Acupuncture Mechanisms"
        assert items[0].source == "openalex"
        assert items[0].source_url == "https://openalex.org/W12345"
        assert items[0].authors == "Li Si, Wang Wu"
        assert items[0].year == 2022
        assert items[0].doi == "10.1000/oa.test"  # strip https://doi.org/ prefix
        assert items[0].journal == "Pain Research Journal"
        assert items[0].is_open_access is True
        assert items[0].language == "en"

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        from app.services.literature_ingestion.openalex_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {"meta": {"count": 0}, "results": []}
        )

        items, total = await search("nonexistent", http_client=mock_client)
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_search_non_403_raises_immediately(self):
        """Non-403 errors (e.g. 500) should raise without retry."""
        from app.services.literature_ingestion.openalex_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response({}, status=500)

        with pytest.raises(httpx.HTTPStatusError):
            await search("test", http_client=mock_client)

        # No retries — only one call
        assert mock_client.get.call_count == 1

    @pytest.mark.asyncio
    async def test_search_403_retries_then_raises(self):
        """403 should trigger retries with exponential backoff, then raise."""
        from app.services.literature_ingestion.openalex_client import search

        mock_client = AsyncMock()
        # All 3 attempts return 403
        mock_client.get.return_value = _json_response({}, status=403)

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(httpx.HTTPStatusError):
                await search("test", http_client=mock_client)

        assert mock_client.get.call_count == 3  # _RETRIES = 3
        assert mock_sleep.call_count == 2  # sleep on attempts 0 and 1
        # Exponential backoff: 3.0 * 1, 3.0 * 2
        assert mock_sleep.call_args_list[0][0][0] == 3.0
        assert mock_sleep.call_args_list[1][0][0] == 6.0

    @pytest.mark.asyncio
    async def test_search_403_succeeds_on_retry(self):
        """403 on first attempt, success on second — should return results."""
        from app.services.literature_ingestion.openalex_client import search

        mock_client = AsyncMock()
        # First call: 403, second call: 200 with valid data
        mock_client.get.side_effect = [
            _json_response({}, status=403),
            _json_response(
                {
                    "meta": {"count": 1},
                    "results": [
                        {
                            "id": "https://openalex.org/W999",
                            "title": "Retry Success Paper",
                            "authorships": [],
                            "abstract_inverted_index": {},
                            "open_access": {"is_oa": False},
                            "language": "en",
                        }
                    ],
                }
            ),
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            items, total = await search("test", http_client=mock_client)

        assert total == 1
        assert items[0].title == "Retry Success Paper"

    @pytest.mark.asyncio
    async def test_search_connect_error_retries(self):
        """ConnectError should trigger retries then raise after exhaustion."""
        from app.services.literature_ingestion.openalex_client import search

        mock_client = AsyncMock()
        mock_client.get.side_effect = httpx.ConnectError("DNS failure")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with pytest.raises(httpx.ConnectError):
                await search("test", http_client=mock_client)

        assert mock_client.get.call_count == 3
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_search_connect_error_succeeds_on_retry(self):
        """ConnectError on attempt 0, success on attempt 1."""
        from app.services.literature_ingestion.openalex_client import search

        mock_client = AsyncMock()
        mock_client.get.side_effect = [
            httpx.ConnectError("timeout"),
            _json_response(
                {
                    "meta": {"count": 1},
                    "results": [
                        {
                            "id": "https://openalex.org/W888",
                            "title": "Recovered Paper",
                            "authorships": [],
                            "abstract_inverted_index": {},
                            "open_access": {"is_oa": False},
                            "language": "en",
                        }
                    ],
                }
            ),
        ]

        with patch("asyncio.sleep", new_callable=AsyncMock):
            items, total = await search("test", http_client=mock_client)

        assert len(items) == 1

    @pytest.mark.asyncio
    async def test_first_str_reconstructs_abstract(self):
        from app.services.literature_ingestion.openalex_client import _first_str

        inverted = {"This": [0], "is": [1], "a": [2], "test": [3]}
        result = _first_str(inverted)
        assert result == "This is a test"

    @pytest.mark.asyncio
    async def test_first_str_empty(self):
        from app.services.literature_ingestion.openalex_client import _first_str

        assert _first_str({}) == ""

    @pytest.mark.asyncio
    async def test_host_venue_name_from_primary_location(self):
        from app.services.literature_ingestion.openalex_client import _host_venue_name

        work = {
            "primary_location": {"source": {"display_name": "Nature"}},
        }
        assert _host_venue_name(work) == "Nature"

    @pytest.mark.asyncio
    async def test_host_venue_name_from_locations_dict(self):
        from app.services.literature_ingestion.openalex_client import _host_venue_name

        work = {
            "locations": {"source": {"display_name": "Science"}},
        }
        assert _host_venue_name(work) == "Science"

    @pytest.mark.asyncio
    async def test_host_venue_name_from_locations_list(self):
        from app.services.literature_ingestion.openalex_client import _host_venue_name

        work = {
            "locations": [
                {"source": {"display_name": "Cell"}},
            ],
        }
        assert _host_venue_name(work) == "Cell"

    @pytest.mark.asyncio
    async def test_host_venue_name_empty(self):
        from app.services.literature_ingestion.openalex_client import _host_venue_name

        assert _host_venue_name({}) == ""


# =============================================================================
# pubmed_client
# =============================================================================


class TestPubMedClient:
    @pytest.mark.asyncio
    async def test_search_europe_pmc_success(self):
        """Primary path: Europe PMC returns valid JSON."""
        from app.services.literature_ingestion.pubmed_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {
                "resultList": {
                    "hitCount": 1,
                    "result": [
                        {
                            "id": "12345",
                            "title": "Huangfu Mi and the Jiayi Jing",
                            "authorString": "Zhang S, Liu W",
                            "pubYear": "2018",
                            "abstractText": "A study on the earliest acupuncture classic.",
                            "keywordList": {"keyword": ["Acupuncture", "History"]},
                            "doi": "10.1000/pm.test",
                            "journalTitle": "Chinese Medicine Journal",
                            "language": "en",
                            "isOpenAccess": "Y",
                        }
                    ],
                }
            }
        )

        items, total = await search("Huangfu Mi", http_client=mock_client)

        assert total == 1
        assert len(items) == 1
        assert items[0].title == "Huangfu Mi and the Jiayi Jing"
        assert items[0].source == "pubmed"
        assert items[0].source_url == "https://europepmc.org/article/MED/12345"
        assert items[0].authors == "Zhang S, Liu W"
        assert items[0].year == 2018
        assert items[0].doi == "10.1000/pm.test"
        assert items[0].journal == "Chinese Medicine Journal"
        assert items[0].is_open_access is True
        assert items[0].keywords == "Acupuncture, History"

    @pytest.mark.asyncio
    async def test_search_europe_pmc_empty(self):
        from app.services.literature_ingestion.pubmed_client import search

        mock_client = AsyncMock()
        mock_client.get.return_value = _json_response(
            {"resultList": {"hitCount": 0, "result": []}}
        )

        items, total = await search("nonexistent", http_client=mock_client)
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_search_falls_back_to_pubmed_on_europe_pmc_error(self):
        """When Europe PMC raises HTTP error, falls back to PubMed E-utilities."""
        from app.services.literature_ingestion.pubmed_client import search

        mock_client = AsyncMock()

        # Europe PMC returns 500 → triggers fallback
        # PubMed ESearch returns valid JSON → EFetch returns XML
        epmc_resp = _json_response({}, status=500)

        esearch_resp = MagicMock()
        esearch_resp.json.return_value = {
            "esearchresult": {"idlist": ["12345"], "count": "1"}
        }
        esearch_resp.raise_for_status.return_value = None

        efetch_resp = MagicMock()
        efetch_resp.text = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN"
        "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation Status="MEDLINE" Owner="NLM">
              <PMID Version="1">12345</PMID>
              <Article PubModel="Print">
                <ArticleTitle>Huangfu Mi Biography</ArticleTitle>
                <Abstract>
                  <AbstractText>Early life of the acupuncture master.</AbstractText>
                </Abstract>
                <AuthorList CompleteYN="Y">
                  <Author ValidYN="Y">
                    <LastName>Li</LastName>
                    <ForeName>Wei</ForeName>
                  </Author>
                </AuthorList>
                <Journal>
                  <Title>Med Hist</Title>
                  <JournalIssue CitedMedium="Print">
                    <PubDate>
                      <Year>2015</Year>
                    </PubDate>
                  </JournalIssue>
                </Journal>
                <ELocationID EIdType="doi" ValidYN="Y">10.1000/pm.fallback</ELocationID>
              </Article>
              <KeywordList Owner="NLM">
                <Keyword MajorTopicYN="N">Acupuncture</Keyword>
                <Keyword MajorTopicYN="N">History of Medicine</Keyword>
              </KeywordList>
            </MedlineCitation>
          </PubmedArticle>
        </PubmedArticleSet>"""
        efetch_resp.raise_for_status.return_value = None

        mock_client.get.side_effect = [epmc_resp, esearch_resp, efetch_resp]

        items, total = await search("Huangfu Mi", http_client=mock_client)

        assert total == 1
        assert len(items) == 1
        assert items[0].title == "Huangfu Mi Biography"
        assert items[0].source == "pubmed"
        assert items[0].source_url == "https://pubmed.ncbi.nlm.nih.gov/12345/"
        assert items[0].authors == "Wei Li"
        assert items[0].year == 2015
        assert items[0].doi == "10.1000/pm.fallback"
        assert items[0].journal == "Med Hist"
        assert items[0].is_open_access is False  # PubMed doesn't tag OA
        assert "Acupuncture" in items[0].keywords

    @pytest.mark.asyncio
    async def test_search_falls_back_to_pubmed_on_json_decode_error(self):
        """Corrupt Europe PMC JSON triggers PubMed fallback."""
        import json

        from app.services.literature_ingestion.pubmed_client import search

        mock_client = AsyncMock()

        # Europe PMC returns malformed JSON → ValueError triggers fallback
        bad_resp = MagicMock()
        bad_resp.json.side_effect = json.JSONDecodeError("malformed", "", 0)
        bad_resp.raise_for_status.return_value = None

        # PubMed returns empty results
        esearch_resp = MagicMock()
        esearch_resp.json.return_value = {"esearchresult": {"idlist": [], "count": "0"}}
        esearch_resp.raise_for_status.return_value = None

        mock_client.get.side_effect = [bad_resp, esearch_resp]

        items, total = await search("test", http_client=mock_client)
        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_epmc_open_access_via_is_open_access(self):
        from app.services.literature_ingestion.pubmed_client import _check_epmc_oa

        assert _check_epmc_oa({"isOpenAccess": "Y"}) is True
        assert _check_epmc_oa({"isOpenAccess": "N"}) is False

    @pytest.mark.asyncio
    async def test_epmc_open_access_via_bool(self):
        from app.services.literature_ingestion.pubmed_client import _check_epmc_oa

        assert _check_epmc_oa({"openAccess": True}) is True
        assert _check_epmc_oa({"openAccess": False}) is False
        assert _check_epmc_oa({}) is False

    @pytest.mark.asyncio
    async def test_parse_pubmed_xml_without_doi(self):
        """XML without ELocationID/DOI should produce item with empty doi."""
        from app.services.literature_ingestion.pubmed_client import _parse_pubmed_xml

        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <!DOCTYPE PubmedArticleSet PUBLIC "-//NLM//DTD PubMedArticle, 1st January 2024//EN"
        "https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_240101.dtd">
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID>99999</PMID>
              <Article>
                <ArticleTitle>Minimal Paper</ArticleTitle>
                <AuthorList CompleteYN="Y">
                  <Author ValidYN="Y">
                    <LastName>Chen</LastName>
                    <ForeName>X</ForeName>
                  </Author>
                </AuthorList>
                <Journal>
                  <Title>Test Journal</Title>
                  <JournalIssue>
                    <PubDate><Year>2020</Year></PubDate>
                  </JournalIssue>
                </Journal>
              </Article>
            </MedlineCitation>
          </PubmedArticle>
        </PubmedArticleSet>"""

        items = _parse_pubmed_xml(xml)
        assert len(items) == 1
        assert items[0].title == "Minimal Paper"
        assert items[0].doi == ""
        assert items[0].authors == "X Chen"
        assert items[0].year == 2020


# =============================================================================
# crossref first_abstract edge cases
# =============================================================================


class TestCrossrefFirstAbstract:
    def test_truncated_at_1000_chars(self):
        from app.services.literature_ingestion.crossref_client import _first_abstract

        long_text = "x" * 2000
        result = _first_abstract({"abstract": long_text})
        assert len(result) <= 1000
