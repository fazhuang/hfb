"""Unit tests for CitationPersistenceService — deduplication, existing check, backfill."""

import json
from unittest.mock import AsyncMock, MagicMock, call, patch
from uuid import uuid4

import pytest

from app.services.citation_persistence import CitationPersistenceService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_citation(doc_id="doc-1", chunk_id="chunk-1", quote="test quote", **kwargs):
    """Build a mock citation with attributes for all getter lambdas."""
    c = MagicMock()
    c.document_id = doc_id
    c.chunk_id = chunk_id
    c.exact_quote = quote
    c.version_id = kwargs.get("version_id", "")
    c.passage_id = kwargs.get("passage_id", "")
    c.source_uri = kwargs.get("source_uri", "")
    c.evidence_id = kwargs.get("evidence_id", "")
    for k, v in kwargs.items():
        setattr(c, k, v)
    return c


# ---------------------------------------------------------------------------
# persist_academic_rag_citations — dedup + skip paths
# ---------------------------------------------------------------------------

class TestPersistAcademicRagCitations:

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero(self):
        """Line 133-134: empty citations => return 0."""
        session = AsyncMock()
        svc = CitationPersistenceService(session)
        count = await svc.persist_academic_rag_citations([], query="")
        assert count == 0

    @pytest.mark.asyncio
    async def test_deduplicate_by_doc_id_chunk_id(self):
        """Lines 139-148: duplicate (doc_id, chunk_id) pairs => unique only, returns 0."""
        session = AsyncMock()
        # _find_existing: return all as existing
        session.execute = AsyncMock(return_value=MagicMock())

        svc = CitationPersistenceService(session, creator_id=str(uuid4()))

        # Override _find_existing to return all keys
        with patch.object(svc, "_find_existing", AsyncMock()) as mock_find:
            mock_find.return_value = {
                ("doc-1", "chunk-1"),
                ("doc-2", "chunk-2"),
            }

            c1 = _make_citation(doc_id="doc-1", chunk_id="chunk-1")
            c2 = _make_citation(doc_id="doc-2", chunk_id="chunk-2")

            count = await svc.persist_academic_rag_citations([c1, c2], query="")
            # All already existed => 0 new ones
            assert count == 0

    @pytest.mark.asyncio
    async def test_all_already_persisted_returns_zero(self):
        """Lines 160-164: all new_citations already in existing_keys => return 0."""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())

        svc = CitationPersistenceService(session, creator_id=str(uuid4()))

        c1 = _make_citation(doc_id="doc-1", chunk_id="chunk-1")

        with patch.object(svc, "_find_existing", AsyncMock(return_value={("doc-1", "chunk-1")})):
            count = await svc.persist_academic_rag_citations([c1], query="")
            assert count == 0

    @pytest.mark.asyncio
    async def test_skip_citation_with_empty_doc_id(self):
        """Line 143: citation without doc_id => not added to unique set."""
        session = AsyncMock()
        session.execute = AsyncMock(return_value=MagicMock())

        svc = CitationPersistenceService(session, creator_id=str(uuid4()))

        c1 = _make_citation(doc_id="", chunk_id="chunk-1")  # empty doc_id

        with patch.object(svc, "_find_existing", AsyncMock(return_value=set())):
            count = await svc.persist_academic_rag_citations([c1], query="")
            assert count == 0

    @pytest.mark.asyncio
    async def test_successful_persist_creates_evidence_and_citation(self):
        """Lines 169-278: successful persistence path."""
        session = AsyncMock()
        session.execute = AsyncMock()

        # Mock _find_existing: nothing exists
        # Mock begin_nested
        mock_savepoint = AsyncMock()
        session.begin_nested = AsyncMock(return_value=mock_savepoint)

        # Mock _resolve_source_ref: returns a source_ref_id
        # Mock version check: no version_id => skip

        svc = CitationPersistenceService(session, creator_id=str(uuid4()))

        c = _make_citation(doc_id="doc-1", chunk_id="chunk-1", quote="test quote")

        with patch.object(svc, "_find_existing", AsyncMock(return_value=set())):
            with patch.object(svc, "_resolve_source_ref", AsyncMock(return_value="sr-1")):
                count = await svc.persist_academic_rag_citations([c], query="test query")
                assert count == 1

    @pytest.mark.asyncio
    async def test_version_withdrawal_rejects_citation(self):
        """Lines 211-224: withdrawn version raises RuntimeError."""
        session = AsyncMock()
        session.execute = AsyncMock()

        # Returns a row with withdrawn_at not null
        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("2024-01-01",)  # not None => withdrawn
        session.execute.return_value = mock_result

        mock_savepoint = AsyncMock()
        session.begin_nested = AsyncMock(return_value=mock_savepoint)

        svc = CitationPersistenceService(session, creator_id=str(uuid4()))
        c = _make_citation(
            doc_id="doc-1", chunk_id="chunk-1", quote="test quote",
            version_id="version-withdrawn",
        )

        with patch.object(svc, "_find_existing", AsyncMock(return_value=set())):
            with patch.object(svc, "_resolve_source_ref", AsyncMock(return_value="sr-1")):
                with pytest.raises(RuntimeError, match="withdrawn"):
                    await svc.persist_academic_rag_citations([c], query="")

    @pytest.mark.asyncio
    async def test_source_ref_not_found_raises(self):
        """Line 202-207: source_ref_id is None => RuntimeError."""
        session = AsyncMock()
        session.execute = AsyncMock()

        mock_savepoint = AsyncMock()
        session.begin_nested = AsyncMock(return_value=mock_savepoint)

        svc = CitationPersistenceService(session, creator_id=str(uuid4()))
        c = _make_citation(doc_id="doc-1", chunk_id="chunk-1", quote="test quote")

        with patch.object(svc, "_find_existing", AsyncMock(return_value=set())):
            with patch.object(svc, "_resolve_source_ref", AsyncMock(return_value=None)):
                with pytest.raises(RuntimeError, match="Cannot resolve SourceRef"):
                    await svc.persist_academic_rag_citations([c], query="")


# ---------------------------------------------------------------------------
# _find_existing — note JSON parsing edge cases
# ---------------------------------------------------------------------------

class TestFindExisting:

    @pytest.mark.asyncio
    async def test_empty_chunk_ids_returns_empty_set(self):
        """Line 300-301: no chunk_ids in citations => return empty set."""
        session = AsyncMock()
        svc = CitationPersistenceService(session)

        result = await svc._find_existing(
            [], get_doc_id=lambda c: c.document_id, get_chunk_id=lambda c: c.chunk_id
        )
        assert result == set()

    @pytest.mark.asyncio
    async def test_note_with_non_json_skipped(self):
        """Line 320: json.JSONDecodeError => continue."""
        session = AsyncMock()
        session.execute = AsyncMock()

        # Return a row with target_id and non-JSON note
        mock_row = MagicMock()
        mock_row.__iter__.return_value = iter(["doc-1", "not valid json {broken"])
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([mock_row])
        session.execute.return_value = mock_result

        svc = CitationPersistenceService(session)

        c = _make_citation(doc_id="doc-1", chunk_id="chunk-1")
        result = await svc._find_existing(
            [c],
            get_doc_id=lambda c: c.document_id,
            get_chunk_id=lambda c: c.chunk_id,
        )
        # JSON parse failed, so nothing should be found
        assert result == set()

    @pytest.mark.asyncio
    async def test_valid_note_adds_to_existing(self):
        """Lines 312-319: valid note JSON => add to existing set."""
        session = AsyncMock()
        session.execute = AsyncMock()

        note = json.dumps({"chunk_id": "chunk-1"})
        row1 = MagicMock()

        def row_iter(self=None):
            return iter(["doc-1", note])

        row1.__iter__ = row_iter

        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([row1])
        session.execute.return_value = mock_result

        svc = CitationPersistenceService(session)

        c = _make_citation(doc_id="doc-1", chunk_id="chunk-1")
        result = await svc._find_existing(
            [c],
            get_doc_id=lambda c: c.document_id,
            get_chunk_id=lambda c: c.chunk_id,
        )
        assert ("doc-1", "chunk-1") in result

    @pytest.mark.asyncio
    async def test_null_note_skipped(self):
        """Line 313: note_str is None/falsy => continue."""
        session = AsyncMock()
        session.execute = AsyncMock()

        row1 = MagicMock()
        row1.__iter__.return_value = iter(["doc-1", None])
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([row1])
        session.execute.return_value = mock_result

        svc = CitationPersistenceService(session)

        c = _make_citation(doc_id="doc-1", chunk_id="chunk-1")
        result = await svc._find_existing(
            [c],
            get_doc_id=lambda c: c.document_id,
            get_chunk_id=lambda c: c.chunk_id,
        )
        assert result == set()

    @pytest.mark.asyncio
    async def test_note_without_chunk_id_key_skipped(self):
        """Lines 317-318: note JSON without chunk_id key."""
        session = AsyncMock()
        session.execute = AsyncMock()

        note = json.dumps({"something": "else"})  # no chunk_id key
        row1 = MagicMock()
        row1.__iter__.return_value = iter(["doc-1", note])
        mock_result = MagicMock()
        mock_result.__iter__.return_value = iter([row1])
        session.execute.return_value = mock_result

        svc = CitationPersistenceService(session)

        c = _make_citation(doc_id="doc-1", chunk_id="chunk-1")
        result = await svc._find_existing(
            [c],
            get_doc_id=lambda c: c.document_id,
            get_chunk_id=lambda c: c.chunk_id,
        )
        assert result == set()


# ---------------------------------------------------------------------------
# _resolve_source_ref
# ---------------------------------------------------------------------------

class TestResolveSourceRef:

    @pytest.mark.asyncio
    async def test_url_match_returns_source_ref_id(self):
        """Lines 346-355: match by URL."""
        session = AsyncMock()
        session.execute = AsyncMock()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = ("sr-url-1",)
        session.execute.return_value = mock_result

        svc = CitationPersistenceService(session)
        result = await svc._resolve_source_ref(
            source_uri="https://ctext.org/foo",
            doc_id="doc-1",
        )
        assert result == "sr-url-1"

    @pytest.mark.asyncio
    async def test_page_location_fallback_returns_source_ref_id(self):
        """Lines 358-367: fallback to page_location match when source_uri is falsy."""
        session = AsyncMock()
        session.execute = AsyncMock()

        # Only one execute call: page_location lookup (URL skipped since empty)
        mock_result_found = MagicMock()
        mock_result_found.fetchone.return_value = ("sr-page-1",)
        session.execute.return_value = mock_result_found

        svc = CitationPersistenceService(session)
        result = await svc._resolve_source_ref(
            source_uri="",  # empty URL is falsy → skip URL branch
            doc_id="doc-1",
        )
        assert result == "sr-page-1"

    @pytest.mark.asyncio
    async def test_no_match_returns_none(self):
        """Line 371: no source_ref found => return None."""
        session = AsyncMock()
        session.execute = AsyncMock()

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        session.execute.return_value = mock_result

        svc = CitationPersistenceService(session)
        result = await svc._resolve_source_ref(
            source_uri="",
            doc_id="",
        )
        assert result is None


# ---------------------------------------------------------------------------
# persist_evidence_rag_citations
# ---------------------------------------------------------------------------

class TestPersistEvidenceRagCitations:

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero(self):
        session = AsyncMock()
        svc = CitationPersistenceService(session)
        count = await svc.persist_evidence_rag_citations([], query="")
        assert count == 0

    @pytest.mark.asyncio
    async def test_uses_quote_from_source_url_attrs(self):
        """Evidence citations use c.quote and c.source_url."""
        session = AsyncMock()
        session.execute = AsyncMock()

        mock_savepoint = AsyncMock()
        session.begin_nested = AsyncMock(return_value=mock_savepoint)

        svc = CitationPersistenceService(session, creator_id=str(uuid4()))

        c = MagicMock()
        c.document_id = "doc-1"
        c.chunk_id = "chunk-1"
        c.quote = "evidence quote"
        c.source_url = "https://ctext.org/foo"

        with patch.object(svc, "_find_existing", AsyncMock(return_value=set())):
            with patch.object(svc, "_resolve_source_ref", AsyncMock(return_value="sr-1")):
                count = await svc.persist_evidence_rag_citations([c], query="")
                assert count == 1


# ---------------------------------------------------------------------------
# backfill_missing_source_refs
# ---------------------------------------------------------------------------

class TestBackfillMissingSourceRefs:

    @pytest.mark.asyncio
    async def test_empty_orphans_returns_zero(self):
        """Line 403: no orphan Evidence rows => return 0."""
        session = AsyncMock()
        session.execute = AsyncMock()

        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        session.execute.return_value = mock_result

        svc = CitationPersistenceService(session)
        result = await svc.backfill_missing_source_refs()
        assert result == 0

    @pytest.mark.asyncio
    async def test_passage_derived_source_ref_found(self):
        """Lines 414-432: Strategy 1 — passage → version → source_url."""
        session = AsyncMock()
        session.execute = AsyncMock()

        # First query: find orphans — returns one
        orphan_result = MagicMock()
        orphan = {
            "evidence_id": "ev-1",
            "source_passage_id": "passage-1",
            "doc_id": None,
        }
        orphan_result.mappings.return_value.all.return_value = [orphan]

        # Second query: passage → version → source_url match — returns sr_id
        sr_result = MagicMock()
        sr_result.fetchone.return_value = ("sr-passage-1",)

        # Third query: UPDATE
        update_result = MagicMock()

        session.execute.side_effect = [orphan_result, sr_result, update_result]

        svc = CitationPersistenceService(session)
        result = await svc.backfill_missing_source_refs()
        assert result == 1

    @pytest.mark.asyncio
    async def test_doc_id_fallback_for_source_ref(self):
        """Lines 435-446: Strategy 2 — doc_id → page_location match."""
        session = AsyncMock()
        session.execute = AsyncMock()

        orphan_result = MagicMock()
        orphan = {
            "evidence_id": "ev-2",
            "source_passage_id": None,  # No passage
            "doc_id": "doc-1",
        }
        orphan_result.mappings.return_value.all.return_value = [orphan]

        # First SR query (Strategy 1): not executed since passage_id is None
        # Second SR query (Strategy 2): doc_id → page_location — returns sr_id
        sr_result = MagicMock()
        sr_result.fetchone.return_value = ("sr-doc-1",)

        # UPDATE
        update_result = MagicMock()

        session.execute.side_effect = [orphan_result, sr_result, update_result]

        svc = CitationPersistenceService(session)
        result = await svc.backfill_missing_source_refs()
        assert result == 1

    @pytest.mark.asyncio
    async def test_last_resort_any_source_ref(self):
        """Lines 448-459: Strategy 3 — pick any SourceRef."""
        session = AsyncMock()
        session.execute = AsyncMock()

        orphan_result = MagicMock()
        orphan = {
            "evidence_id": "ev-3",
            "source_passage_id": None,
            "doc_id": None,
        }
        orphan_result.mappings.return_value.all.return_value = [orphan]

        # Strategy 1: skipped (no passage_id)
        # Strategy 2: skipped (no doc_id)
        # Strategy 3: any source_ref — returns sr_id
        sr_result = MagicMock()
        sr_result.fetchone.return_value = ("sr-any-1",)

        # UPDATE
        update_result = MagicMock()

        session.execute.side_effect = [orphan_result, sr_result, update_result]

        svc = CitationPersistenceService(session)
        result = await svc.backfill_missing_source_refs()
        assert result == 1

    @pytest.mark.asyncio
    async def test_no_source_ref_found_skips_update(self):
        """Lines 461->406: no source_ref_id => skip update, loop continues."""
        session = AsyncMock()
        session.execute = AsyncMock()

        orphan_result = MagicMock()
        orphan = {
            "evidence_id": "ev-4",
            "source_passage_id": None,
            "doc_id": None,
        }
        orphan_result.mappings.return_value.all.return_value = [orphan]

        # Strategy 3: any source_ref — returns None
        sr_result = MagicMock()
        sr_result.fetchone.return_value = None

        # No UPDATE should be called
        session.execute.side_effect = [orphan_result, sr_result]

        svc = CitationPersistenceService(session)
        result = await svc.backfill_missing_source_refs()
        assert result == 0


# ---------------------------------------------------------------------------
# _truncate
# ---------------------------------------------------------------------------

class TestTruncate:

    def test_short_string_unchanged(self):
        result = CitationPersistenceService._truncate("hello", 10)
        assert result == "hello"

    def test_long_string_truncated_with_ellipsis(self):
        result = CitationPersistenceService._truncate("hello world", 8)
        assert result == "hello..."

    def test_empty_string_returns_empty(self):
        result = CitationPersistenceService._truncate("", 10)
        assert result == ""

    def test_none_returns_empty(self):
        result = CitationPersistenceService._truncate(None, 10)
        assert result == ""

    def test_exact_length_no_ellipsis(self):
        result = CitationPersistenceService._truncate("1234567890", 10)
        assert result == "1234567890"


# ---------------------------------------------------------------------------
# persist_academic_citations
# ---------------------------------------------------------------------------

class TestPersistAcademicCitations:

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero(self):
        session = AsyncMock()
        svc = CitationPersistenceService(session)
        count = await svc.persist_academic_citations([], query="")
        assert count == 0

    @pytest.mark.asyncio
    async def test_uses_text_for_quote(self):
        session = AsyncMock()
        session.execute = AsyncMock()

        mock_savepoint = AsyncMock()
        session.begin_nested = AsyncMock(return_value=mock_savepoint)

        svc = CitationPersistenceService(session, creator_id=str(uuid4()))

        c = MagicMock()
        c.document_id = "doc-1"
        c.chunk_id = "chunk-1"
        c.text = "academic citation text"

        with patch.object(svc, "_find_existing", AsyncMock(return_value=set())):
            with patch.object(svc, "_resolve_source_ref", AsyncMock(return_value="sr-1")):
                count = await svc.persist_academic_citations([c], query="")
                assert count == 1
