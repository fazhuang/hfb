"""
Unit tests for RAGService — full branch coverage.

Covers:
  - retrieve: custom entity_types, query expansion fallback, empty query handling
  - _enrich_result: all entity_type branches, unknown type, object not found
  - assemble_context: empty, skip-empty-content, author/version/translation blocks
  - _get_book_title: chapter_id path, version_id path, not-found at each level
  - _get_version_name / _get_person_name: found and not found
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from app.schemas.search import SearchResponse, SearchResultItem


def _make_item(entity_type: str, item_id: str = "id-1", title: str = "Test", score: float = 0.9) -> SearchResultItem:
    return SearchResultItem(
        id=item_id, entity_type=entity_type, title=title, snippet="...", score=score,
    )


def _make_response(items: list[SearchResultItem], total: int = 0, page: int = 1, limit: int = 20) -> SearchResponse:
    return SearchResponse(
        items=items,
        total=total or len(items),
        page=page,
        limit=limit,
        total_pages=1,
        query="test",
        entity_types=["passage", "book"],
    )


# =============================================================
# retrieve
# =============================================================


@pytest.mark.asyncio
class TestRetrieve:
    async def test_default_entity_types(self):
        """When entity_types is None, defaults to ['passage','book','version','person']."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        search_svc_mock = MagicMock()
        search_svc_mock.search = AsyncMock(return_value=_make_response([]))

        with (
            patch("app.services.rag_service.SearchService", return_value=search_svc_mock),
            patch("app.services.rag_service.build_academic_retrieval_query", return_value="expanded"),
        ):
            svc = RAGService(mock_session)
            result = await svc.retrieve("some question")
            assert isinstance(result, list)
            # Should have called search with all four default entity types
            call_args = search_svc_mock.search.call_args[0][0]
            assert sorted(call_args.entity_types) == sorted(["passage", "book", "version", "person"])

    async def test_custom_entity_types(self):
        """Custom entity_types are passed through to SearchService."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        search_svc_mock = MagicMock()
        search_svc_mock.search = AsyncMock(return_value=_make_response([]))

        with (
            patch("app.services.rag_service.SearchService", return_value=search_svc_mock),
            patch("app.services.rag_service.build_academic_retrieval_query", return_value="expanded"),
        ):
            svc = RAGService(mock_session)
            await svc.retrieve("query", entity_types=["passage", "person"])
            call_args = search_svc_mock.search.call_args[0][0]
            assert sorted(call_args.entity_types) == sorted(["passage", "person"])

    async def test_expanded_query_yields_results(self):
        """Expanded query hits results → those are used, original query never tried."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        search_svc_mock = MagicMock()
        passage_item = _make_item("passage", "p-1", "Passage Title")

        # Return items so that _enrich_result is called — we must mock it too
        search_svc_mock.search = AsyncMock(return_value=_make_response([passage_item]))

        with (
            patch("app.services.rag_service.SearchService", return_value=search_svc_mock),
            patch("app.services.rag_service.build_academic_retrieval_query", return_value="expanded keywords"),
            patch.object(
                RAGService, "_enrich_result",
                AsyncMock(return_value={"entity_type": "passage", "entity_id": "p-1", "title": "P", "score": 0.9, "content": "x"}),
            ),
        ):
            svc = RAGService(mock_session)
            result = await svc.retrieve("What is acupuncture?")
            assert len(result) == 1
            # build_academic_retrieval_query called with original query
            assert search_svc_mock.search.call_count == 1
            call_args = search_svc_mock.search.call_args[0][0]
            assert call_args.q == "expanded keywords"

    async def test_expanded_query_empty_fallback_to_original(self):
        """Expanded query returns no items → falls back to original query."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        search_svc_mock = MagicMock()
        passage_item = _make_item("passage", "p-2", "P2")

        # First call returns empty, second returns items
        search_svc_mock.search = AsyncMock(side_effect=[
            _make_response([]),      # expanded → empty
            _make_response([passage_item]),  # original → hit
        ])

        with (
            patch("app.services.rag_service.SearchService", return_value=search_svc_mock),
            patch("app.services.rag_service.build_academic_retrieval_query", return_value="expanded"),
            patch.object(
                RAGService, "_enrich_result",
                AsyncMock(return_value={"entity_type": "passage", "entity_id": "p-2", "title": "P2", "score": 0.9, "content": "y"}),
            ),
        ):
            svc = RAGService(mock_session)
            result = await svc.retrieve("acupuncture")
            assert len(result) == 1
            assert search_svc_mock.search.call_count == 2
            # Second call uses original query
            assert search_svc_mock.search.call_args[0][0].q == "acupuncture"

    async def test_expanded_empty_original_used(self):
        """When expanded_q is empty/whitespace, it is skipped and original query is tried."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        search_svc_mock = MagicMock()
        item = _make_item("book", "b-1", "Book")
        search_svc_mock.search = AsyncMock(return_value=_make_response([item]))

        with (
            patch("app.services.rag_service.SearchService", return_value=search_svc_mock),
            # expanded_q = "" → stripped to "" → continue; original="acupuncture" → searched
            patch("app.services.rag_service.build_academic_retrieval_query", return_value=""),
            patch.object(
                RAGService, "_enrich_result",
                AsyncMock(return_value={"entity_type": "book", "entity_id": "b-1", "title": "Book", "score": 0.9, "content": "z"}),
            ),
        ):
            svc = RAGService(mock_session)
            result = await svc.retrieve("acupuncture")
            assert len(result) == 1
            # Only one call: whitespace expanded skipped, original "acupuncture" used
            assert search_svc_mock.search.call_count == 1
            assert search_svc_mock.search.call_args[0][0].q == "acupuncture"

    async def test_whitespace_expanded_skipped_original_succeeds(self):
        """Expanded_q is whitespace-only → skipped, original non-empty query tried."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        search_svc_mock = MagicMock()
        item = _make_item("passage", "p-x", "Px")
        search_svc_mock.search = AsyncMock(return_value=_make_response([item]))

        with (
            patch("app.services.rag_service.SearchService", return_value=search_svc_mock),
            # expanded_q = "   " → stripped to "" → continue; original="针灸" → searched
            patch("app.services.rag_service.build_academic_retrieval_query", return_value="   "),
            patch.object(
                RAGService, "_enrich_result",
                AsyncMock(return_value={"entity_type": "passage", "entity_id": "p-x", "title": "Px", "score": 0.8, "content": "x"}),
            ),
        ):
            svc = RAGService(mock_session)
            result = await svc.retrieve("针灸")
            assert len(result) == 1
            assert search_svc_mock.search.call_count == 1
            assert search_svc_mock.search.call_args[0][0].q == "针灸"

    async def test_enrich_result_none_skipped(self):
        """When _enrich_result returns None, the chunk is skipped."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        search_svc_mock = MagicMock()
        search_svc_mock.search = AsyncMock(return_value=_make_response([
            _make_item("passage", "p-a", "A"), _make_item("passage", "p-b", "B"),
        ]))

        with (
            patch("app.services.rag_service.SearchService", return_value=search_svc_mock),
            patch("app.services.rag_service.build_academic_retrieval_query", return_value="kw"),
            patch.object(
                RAGService, "_enrich_result",
                AsyncMock(side_effect=[None, {"entity_type": "passage", "entity_id": "p-b", "title": "B", "score": 0.8, "content": "b"}]),
            ),
        ):
            svc = RAGService(mock_session)
            result = await svc.retrieve("kw")
            assert len(result) == 1
            assert result[0]["entity_id"] == "p-b"


# =============================================================
# _enrich_result
# =============================================================


@pytest.mark.asyncio
class TestEnrichResult:
    async def test_unknown_entity_type_returns_none(self):
        """ENTITY_CONFIG missing the entity_type → None."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()  # not used

        item = _make_item("nonexistent_type", "x-1", "X")
        result = await svc._enrich_result(item)
        assert result is None

    async def test_object_not_found_returns_none(self):
        """Entity type is known but DB row missing → None."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        # Simulate execute → scalar_one_or_none returns None
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        item = _make_item("passage", "p-gone", "Gone")
        result = await svc._enrich_result(item)
        assert result is None

    # --- passage ---

    async def test_enrich_passage_with_version(self):
        """Passage entity with content, translation, notes, and version_id."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        # Mock the execute for passage fetch
        mock_passage = MagicMock()
        mock_passage.content_text = "凡刺之道"
        mock_passage.translation = "The way of needling"
        mock_passage.notes = "Important note"
        mock_passage.order = 3
        mock_passage.version_id = "v-42"

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_passage
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        # Patch _get_book_title and _get_version_name
        with (
            patch.object(svc, "_get_book_title", AsyncMock(return_value="针灸甲乙经")),
            patch.object(svc, "_get_version_name", AsyncMock(return_value="明嘉靖刻本")),
        ):
            item = _make_item("passage", "p-1", "凡刺之道...")
            result = await svc._enrich_result(item)

        assert result is not None
        assert result["entity_type"] == "passage"
        assert result["content"] == "凡刺之道"
        assert result["translation"] == "The way of needling"
        assert result["notes"] == "Important note"
        assert result["version"] == "明嘉靖刻本"
        assert "针灸甲乙经" in result["citation"]

    async def test_enrich_passage_no_version(self):
        """Passage without version_id → no version key."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_passage = MagicMock()
        mock_passage.content_text = "经脉者"
        mock_passage.translation = None
        mock_passage.notes = None
        mock_passage.order = 1
        mock_passage.version_id = None

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_passage
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        with patch.object(svc, "_get_book_title", AsyncMock(return_value="灵枢")):
            item = _make_item("passage", "p-2", "经脉...")
            result = await svc._enrich_result(item)

        assert result is not None
        assert result["entity_type"] == "passage"
        assert "version" not in result

    async def test_enrich_passage_version_not_found(self):
        """Passage has version_id but _get_version_name returns None → no version key."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_passage = MagicMock()
        mock_passage.content_text = "text"
        mock_passage.translation = None
        mock_passage.notes = None
        mock_passage.order = 0
        mock_passage.version_id = "v-missing"

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_passage
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        with (
            patch.object(svc, "_get_book_title", AsyncMock(return_value="Book")),
            patch.object(svc, "_get_version_name", AsyncMock(return_value=None)),
        ):
            item = _make_item("passage", "p-3", "T")
            result = await svc._enrich_result(item)

        assert result is not None
        assert "version" not in result

    # --- book ---

    async def test_enrich_book_with_author(self):
        """Book entity with author_id → author name attached."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_book = MagicMock()
        mock_book.abstract = "针灸经典"
        mock_book.title = "针灸甲乙经"
        mock_book.dynasty = "晋"
        mock_book.author_id = "per-1"

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_book
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        with patch.object(svc, "_get_person_name", AsyncMock(return_value="皇甫谧")):
            item = _make_item("book", "b-1", "针灸甲乙经")
            result = await svc._enrich_result(item)

        assert result is not None
        assert result["entity_type"] == "book"
        assert result["content"] == "针灸经典"
        assert result["author"] == "皇甫谧"
        assert "针灸甲乙经" in result["citation"]
        assert "晋" in result["citation"]

    async def test_enrich_book_no_author(self):
        """Book without author_id → no author key."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_book = MagicMock()
        mock_book.abstract = "摘要"
        mock_book.title = "无名书"
        mock_book.dynasty = "唐"
        mock_book.author_id = None

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_book
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        item = _make_item("book", "b-2", "无名书")
        result = await svc._enrich_result(item)

        assert result is not None
        assert result["entity_type"] == "book"
        assert "author" not in result

    async def test_enrich_book_author_not_found(self):
        """Book has author_id but _get_person_name returns None → no author key."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_book = MagicMock()
        mock_book.abstract = "text"
        mock_book.title = "Book"
        mock_book.dynasty = "汉"
        mock_book.author_id = "per-gone"

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_book
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        with patch.object(svc, "_get_person_name", AsyncMock(return_value=None)):
            item = _make_item("book", "b-3", "Book")
            result = await svc._enrich_result(item)

        assert result is not None
        assert "author" not in result

    # --- person ---

    async def test_enrich_person(self):
        """Person entity → biography, citation, notable_works."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_person = MagicMock()
        mock_person.biography = "西晋医学家"
        mock_person.name = "皇甫谧"
        mock_person.dynasty = "晋"
        mock_person.notable_works = "针灸甲乙经"

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_person
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        item = _make_item("person", "per-1", "皇甫谧")
        result = await svc._enrich_result(item)

        assert result is not None
        assert result["entity_type"] == "person"
        assert result["content"] == "西晋医学家"
        assert result["notable_works"] == "针灸甲乙经"
        assert "皇甫谧" in result["citation"]
        assert "晋" in result["citation"]

    # --- version ---

    async def test_enrich_version(self):
        """Version entity → description, citation, repository."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_version = MagicMock()
        mock_version.description = "明嘉靖年间刻本，藏于中国中医科学院"
        mock_version.version_name = "明嘉靖刻本"
        mock_version.era = "明"
        mock_version.repository = "中国中医科学院"

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_version
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        item = _make_item("version", "v-1", "明嘉靖刻本")
        result = await svc._enrich_result(item)

        assert result is not None
        assert result["entity_type"] == "version"
        assert result["content"] == "明嘉靖年间刻本，藏于中国中医科学院"
        assert result["repository"] == "中国中医科学院"
        assert "明嘉靖刻本" in result["citation"]
        assert "明" in result["citation"]

    async def test_enrich_other_entity_type_bare_chunk(self):
        """Entity type in ENTITY_CONFIG but not passage/book/person/version → bare chunk with title/score only."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        # "document" is in ENTITY_CONFIG but has no specific _enrich_result branch
        mock_doc = MagicMock()
        mock_doc.title = "Some Document"
        mock_doc.dynasty = "唐"

        mock_exec_result = MagicMock()
        mock_exec_result.scalar_one_or_none.return_value = mock_doc
        mock_session.execute = AsyncMock(return_value=mock_exec_result)

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        item = _make_item("document", "doc-1", "Some Document")
        result = await svc._enrich_result(item)

        assert result is not None
        assert result["entity_type"] == "document"
        assert result["entity_id"] == "doc-1"
        assert result["title"] == "Some Document"
        # No content/citation/version/author — bare chunk
        assert "content" not in result
        assert "citation" not in result


# =============================================================
# assemble_context
# =============================================================


@pytest.mark.asyncio
class TestAssembleContext:
    async def test_empty_chunks_returns_empty_string(self):
        """retrieve returns no chunks → empty string."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        search_svc_mock = MagicMock()
        search_svc_mock.search = AsyncMock(return_value=_make_response([]))

        with (
            patch("app.services.rag_service.SearchService", return_value=search_svc_mock),
            patch("app.services.rag_service.build_academic_retrieval_query", return_value="q"),
        ):
            svc = RAGService(mock_session)
            result = await svc.assemble_context("test query")
            assert result == ""

    async def test_chunk_without_content_skipped(self):
        """Chunk where content is empty/None → skipped entirely."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        # Mock retrieve to return chunks, one with no content
        chunks = [
            {"entity_type": "passage", "citation": "《书》", "content": "", "entity_id": "p-1", "title": "T1", "score": 0.9},
            {"entity_type": "book", "citation": "《易》", "content": "valid content", "entity_id": "b-1", "title": "T2", "score": 0.8},
            {"entity_type": "passage", "citation": "《礼》", "content": None, "entity_id": "p-2", "title": "T3", "score": 0.7},
        ]

        with patch.object(svc, "retrieve", AsyncMock(return_value=chunks)):
            result = await svc.assemble_context("q")
            # Only the book with content "valid content" appears
            assert "valid content" in result
            # Empty and None content chunks are excluded
            assert result.count("[") == 1  # one block only

    async def test_single_passage_with_translation(self):
        """Passage chunk with translation → includes modern translation line."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        chunks = [{
            "entity_type": "passage",
            "citation": "《灵枢》#1",
            "content": "凡刺之道，必通十二经络之所终始。",
            "translation": "The way of needling requires understanding the twelve meridians.",
            "entity_id": "p-1",
            "title": "...",
            "score": 0.95,
        }]

        with patch.object(svc, "retrieve", AsyncMock(return_value=chunks)):
            result = await svc.assemble_context("针灸")
            assert "[1] (passage) 《灵枢》#1" in result
            assert "现代汉语:" in result
            assert "The way of needling" in result

    async def test_book_with_author_block(self):
        """Book chunk with author → includes author line."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        chunks = [{
            "entity_type": "book",
            "citation": "《针灸甲乙经》(晋)",
            "content": "晋代皇甫谧编纂的针灸学专著。",
            "author": "皇甫谧",
            "entity_id": "b-1",
            "title": "针灸甲乙经",
            "score": 0.9,
        }]

        with patch.object(svc, "retrieve", AsyncMock(return_value=chunks)):
            result = await svc.assemble_context("甲乙经")
            assert "[1] (book) 《针灸甲乙经》(晋)" in result
            assert "作者: 皇甫谧" in result

    async def test_chunk_with_version_line(self):
        """Chunk with version → includes version line."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        chunks = [{
            "entity_type": "passage",
            "citation": "《灵枢》#2",
            "content": "经脉者，所以行血气而营阴阳。",
            "version": "明赵府居敬堂刊本",
            "entity_id": "p-2",
            "title": "...",
            "score": 0.92,
        }]

        with patch.object(svc, "retrieve", AsyncMock(return_value=chunks)):
            result = await svc.assemble_context("经脉")
            assert "版本: 明赵府居敬堂刊本" in result

    async def test_multiple_chunks_join_with_double_newline(self):
        """Multiple valid chunks → joined by \\n\\n."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        chunks = [
            {"entity_type": "passage", "citation": "《甲》#1", "content": "第一条。", "entity_id": "p-1", "title": "A", "score": 0.9},
            {"entity_type": "passage", "citation": "《乙》#5", "content": "第二条。", "entity_id": "p-2", "title": "B", "score": 0.8},
        ]

        with patch.object(svc, "retrieve", AsyncMock(return_value=chunks)):
            result = await svc.assemble_context("q")
            assert "\n\n" in result
            assert "[1]" in result
            assert "[2]" in result

    async def test_content_truncated_at_500(self):
        """Content longer than 500 chars is truncated."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        long_content = "文" * 600
        chunks = [{
            "entity_type": "passage",
            "citation": "《书》#9",
            "content": long_content,
            "entity_id": "p-long",
            "title": "L",
            "score": 0.7,
        }]

        with patch.object(svc, "retrieve", AsyncMock(return_value=chunks)):
            result = await svc.assemble_context("q")
            # Only first 500 chars should appear
            assert len(long_content[:500]) in [len(s) for s in result.split("\n") if "文" in s]
            assert long_content not in result  # full 600 not present

    async def test_translation_truncated_at_300(self):
        """Translation longer than 300 chars is truncated."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        long_translation = "T" * 500
        chunks = [{
            "entity_type": "passage",
            "citation": "《书》#9",
            "content": "正文",
            "translation": long_translation,
            "entity_id": "p-tr",
            "title": "Tr",
            "score": 0.7,
        }]

        with patch.object(svc, "retrieve", AsyncMock(return_value=chunks)):
            result = await svc.assemble_context("q")
            assert long_translation[:300] in result
            assert long_translation not in result  # full 500 not present


# =============================================================
# _get_book_title
# =============================================================


@pytest.mark.asyncio
class TestGetBookTitle:
    async def test_via_chapter_id(self):
        """Passage has chapter_id → fetch Chapter → fetch Book."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        # First call: fetch Chapter
        mock_chapter = MagicMock()
        mock_chapter.book_id = "book-1"

        # Second call: fetch Book
        mock_book = MagicMock()
        mock_book.title = "针灸甲乙经"

        mock_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_chapter)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_book)),
        ])

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        mock_passage = MagicMock()
        mock_passage.chapter_id = "ch-1"
        mock_passage.version_id = None

        result = await svc._get_book_title(mock_passage)
        assert result == "针灸甲乙经"

    async def test_via_chapter_id_chapter_not_found(self):
        """Chapter not found → '未知'."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        mock_passage = MagicMock()
        mock_passage.chapter_id = "ch-missing"
        mock_passage.version_id = None

        result = await svc._get_book_title(mock_passage)
        assert result == "未知"

    async def test_via_chapter_id_book_not_found(self):
        """Chapter found but Book not found → '未知'."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_chapter = MagicMock()
        mock_chapter.book_id = "book-gone"

        mock_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_chapter)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ])

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        mock_passage = MagicMock()
        mock_passage.chapter_id = "ch-1"
        mock_passage.version_id = None

        result = await svc._get_book_title(mock_passage)
        assert result == "未知"

    async def test_via_version_id(self):
        """No chapter_id → fetch Version → fetch Book."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_version = MagicMock()
        mock_version.book_id = "book-2"

        mock_book = MagicMock()
        mock_book.title = "黄帝内经"

        mock_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_version)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_book)),
        ])

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        mock_passage = MagicMock()
        mock_passage.chapter_id = None
        mock_passage.version_id = "v-9"

        result = await svc._get_book_title(mock_passage)
        assert result == "黄帝内经"

    async def test_via_version_id_version_not_found(self):
        """No chapter_id, version not found → '未知'."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        mock_passage = MagicMock()
        mock_passage.chapter_id = None
        mock_passage.version_id = "v-missing"

        result = await svc._get_book_title(mock_passage)
        assert result == "未知"

    async def test_via_version_id_book_not_found(self):
        """No chapter_id, version found but book not found → '未知'."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_version = MagicMock()
        mock_version.book_id = "book-gone"

        mock_session.execute = AsyncMock(side_effect=[
            MagicMock(scalar_one_or_none=MagicMock(return_value=mock_version)),
            MagicMock(scalar_one_or_none=MagicMock(return_value=None)),
        ])

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        mock_passage = MagicMock()
        mock_passage.chapter_id = None
        mock_passage.version_id = "v-1"

        result = await svc._get_book_title(mock_passage)
        assert result == "未知"

    async def test_no_chapter_no_version(self):
        """Neither chapter_id nor version_id → '未知'."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        mock_passage = MagicMock()
        mock_passage.chapter_id = None
        mock_passage.version_id = None

        result = await svc._get_book_title(mock_passage)
        assert result == "未知"
        mock_session.execute.assert_not_called()


# =============================================================
# _get_version_name
# =============================================================


@pytest.mark.asyncio
class TestGetVersionName:
    async def test_version_found(self):
        """Version exists → return version_name."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_version = MagicMock()
        mock_version.version_name = "宋刊本"

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_version))
        )

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        result = await svc._get_version_name("v-1")
        assert result == "宋刊本"

    async def test_version_not_found(self):
        """Version does not exist → return None."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        result = await svc._get_version_name("v-missing")
        assert result is None


# =============================================================
# _get_person_name
# =============================================================


@pytest.mark.asyncio
class TestGetPersonName:
    async def test_person_found(self):
        """Person exists → return name."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_person = MagicMock()
        mock_person.name = "张仲景"

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=mock_person))
        )

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        result = await svc._get_person_name("per-1")
        assert result == "张仲景"

    async def test_person_not_found(self):
        """Person does not exist → return None."""
        from app.services.rag_service import RAGService

        mock_session = AsyncMock()

        mock_session.execute = AsyncMock(
            return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
        )

        svc = RAGService(mock_session)
        svc.search_svc = MagicMock()

        result = await svc._get_person_name("per-gone")
        assert result is None
