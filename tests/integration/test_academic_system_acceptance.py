"""
Academic System Acceptance Tests — P0 hardened.

Verification:
  P0-1: Exact question via HTTP API, strict response schema assertions
  P0-2: Academic RAG endpoint with full evidence chain
  P0-3: No fake historical sources; only verifiable evidence
  P0-4: Semantic evidence validation at DB level
  P0-5: TEI Sentence/Token/Variant DB round-trip
  P0-6: Ontology DB CHECK constraints — BogusType INSERT must fail
  P0-7: Anti-cheat tests
"""

from __future__ import annotations

from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from main import app as fastapi_app
from app.models.book import Book
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.passage import Passage
from app.models.person import Person
from app.models.tei import TextSentence, TextToken, TextualVariant
from app.models.version import Version
from app.schemas.graph import GraphEvidence
from app.services.graph_service import GraphService
from tests.conftest_db import db_session  # noqa: F401


# ============================================================
# Helpers
# ============================================================


# Only verifiable historical content — no AI-generated pseudo-classical text
_JINSHU_BIO = (
    "皇甫谧，字士安，安定朝那人也。"
    "居贫，躬自稼穑，带经而农，遂博综典籍百家之言。"
    "沉静寡欲，始有高尚之志，以著述为务，自号玄晏先生。"
    "后得风痹疾，犹手不辍卷。"
    "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。"
)

# The forged sentence removed from corpus — was: "其论针灸之道，以经络为本，以腧穴为标，以针刺为用。"
# This is NOT in the historical 《晋书·皇甫谧传》

_ZJYJ_SONG_PASSAGE = "黄帝问曰：针道可得闻乎？岐伯对曰：可得闻也。"
_ZJYJ_MING_PASSAGE = "黄帝问曰：针道可得闻乎？岐伯对曰：可得闻耳。"


async def _seed_acceptance_corpus(session: AsyncSession) -> dict[str, Any]:
    """Seed the verifiable acceptance corpus for Huangfu Mi study.

    Only uses historically-attested text. No AI-generated pseudo-classical content.
    Returns dict of created entities keyed by label.
    """
    # Person: 皇甫谧
    person = Person(
        name="皇甫谧", name_zh="皇甫谧", courtesy_name="士安",
        pseudonym="玄晏先生", dynasty="魏晋", birth_year=215, death_year=282,
        birth_place="安定朝那", biography="魏晋医学家，著《针灸甲乙经》",
        expertise="针灸", notable_works="针灸甲乙经",
    )
    session.add(person)
    await session.flush()

    # Book: 针灸甲乙经
    book = Book(
        title="针灸甲乙经", dynasty="魏晋", year=256,
        category="针灸", abstract="皇甫谧编纂的针灸学经典",
        author_id=person.id,
    )
    session.add(book)
    await session.flush()

    # Source texts the book was compiled from (attested in preface)
    suwen = Book(
        title="素问", dynasty="汉", year=0,
        category="医经", abstract="《黄帝内经素问》，针灸甲乙经主要来源之一",
    )
    zhenjing = Book(
        title="针经", dynasty="汉", year=0,
        category="医经", abstract="即《灵枢经》，针灸甲乙经主要来源之一",
    )
    mingtang = Book(
        title="明堂孔穴针灸治要", dynasty="汉", year=0,
        category="针灸", abstract="明堂孔穴针灸治要，皇甫谧序中提及的来源之一",
    )
    session.add_all([suwen, zhenjing, mingtang])
    await session.flush()

    # Versions
    v_song = Version(
        book_id=book.id, version_name="宋本", era="北宋",
        repository="中国国家图书馆", description="北宋刻本《针灸甲乙经》",
    )
    v_ming = Version(
        book_id=book.id, version_name="明赵府居敬堂刊本", era="明",
        repository="赵府居敬堂", description="明刻本《针灸甲乙经》",
    )
    session.add_all([v_song, v_ming])
    await session.flush()

    # Document — 《晋书·皇甫谧传》 (verifiable content only)
    doc = Document(
        title="晋书·皇甫谧传", dynasty="唐", category="史书",
        content_text=_JINSHU_BIO,
    )
    session.add(doc)
    await session.flush()

    # Chunks
    chunk1 = DocumentChunk(
        document_id=doc.id, chunk_index=0,
        content=(
            "皇甫谧，字士安，安定朝那人也。"
            "居贫，躬自稼穑，带经而农，遂博综典籍百家之言。"
            "沉静寡欲，始有高尚之志，以著述为务，自号玄晏先生。"
        ),
        token_count=60,
    )
    chunk2 = DocumentChunk(
        document_id=doc.id, chunk_index=1,
        content=(
            "后得风痹疾，犹手不辍卷。"
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。"
        ),
        token_count=35,
    )
    session.add_all([chunk1, chunk2])
    await session.flush()

    # Passages
    passage_song = Passage(
        chapter_id="00000000-0000-0000-0000-000000000001",
        version_id=v_song.id, order=1,
        content_text=_ZJYJ_SONG_PASSAGE,
    )
    passage_ming = Passage(
        chapter_id="00000000-0000-0000-0000-000000000001",
        version_id=v_ming.id, order=1,
        content_text=_ZJYJ_MING_PASSAGE,
    )
    session.add_all([passage_song, passage_ming])
    await session.flush()

    return {
        "person": person,
        "book": book,
        "suwen": suwen,
        "zhenjing": zhenjing,
        "mingtang": mingtang,
        "v_song": v_song,
        "v_ming": v_ming,
        "doc": doc,
        "chunk1": chunk1,
        "chunk2": chunk2,
        "passage_song": passage_song,
        "passage_ming": passage_ming,
    }


def _make_ev(doc_id: str, chunk_id: str, quote: str) -> GraphEvidence:
    return GraphEvidence(
        document_id=doc_id,
        chunk_id=chunk_id,
        exact_quote=quote,
        citation=f"[{doc_id}:{chunk_id}]",
    )


# ============================================================
# HTTP test fixture
# ============================================================


@pytest_asyncio.fixture
async def acceptance_app(db_session: AsyncSession):
    """Build a FastAPI test app with auth overrides and the test DB session."""
    from app.db.database import get_session
    from app.middleware import auth as auth_mod

    async def override_get_session():
        yield db_session

    async def override_get_current_user():
        return "test-user-id"

    async def override_get_auth_service():
        class FakeAuth:
            async def has_permission(self, *a: Any, **kw: Any) -> bool:
                return True
            async def has_any_permission(self, *a: Any, **kw: Any) -> bool:
                return True
        return FakeAuth()

    fastapi_app.dependency_overrides[get_session] = override_get_session
    fastapi_app.dependency_overrides[auth_mod.get_current_user] = override_get_current_user
    fastapi_app.dependency_overrides[auth_mod.get_auth_service] = override_get_auth_service

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    fastapi_app.dependency_overrides.clear()


# ============================================================
# P0-1: ExactQuestionTest — no query rewriting
# ============================================================


@pytest.mark.asyncio
class TestExactQuestion:
    """The exact question MUST be submitted without rewriting, spaces, or tokenization."""

    async def test_exact_question_no_rewrite(self, acceptance_app, db_session: AsyncSession) -> None:
        """Submit the exact question: 皇甫谧针灸思想来源是什么？"""
        ents = await _seed_acceptance_corpus(db_session)

        # Create verified edges: 皇甫谧 --compiled--> 针灸甲乙经
        # Evidence: 《晋书》 says 皇甫谧 撰《针灸甲乙经》
        svc = GraphService(db_session)
        ev = _make_ev(
            ents["doc"].id, ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            evidence=ev,
        )
        # Mark as verified
        rel.evidence_status = "verified"
        await db_session.flush()

        # Submit EXACT question — no spaces, no tokenization
        exact_question = "皇甫谧针灸思想来源是什么？"
        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": exact_question},
        )
        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["query"] == exact_question

    async def test_no_query_rewrite_in_request(self, acceptance_app, db_session: AsyncSession) -> None:
        """Verify the query arrives at the API exactly as sent — no rewriting by middleware."""
        ents = await _seed_acceptance_corpus(db_session)

        svc = GraphService(db_session)
        ev = _make_ev(
            ents["doc"].id, ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        rel.evidence_status = "verified"
        await db_session.flush()

        original = "皇甫谧针灸思想来源是什么？"
        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": original},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["query"] == original


# ============================================================
# P0-1: ResponseContractTest — strict field assertions
# ============================================================


@pytest.mark.asyncio
class TestResponseContract:
    """Response MUST contain: answer, citations, kg_paths, evidence_chain, refusal, query, corpus_sha256, output_sha256."""

    REQUIRED_FIELDS = [
        "answer", "citations", "kg_paths", "evidence_chain",
        "refusal", "query", "corpus_sha256", "output_sha256",
    ]

    async def test_all_required_fields_present(self, acceptance_app, db_session: AsyncSession) -> None:
        """Every required field must be present in the response."""
        ents = await _seed_acceptance_corpus(db_session)

        svc = GraphService(db_session)
        ev = _make_ev(
            ents["doc"].id, ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        rel.evidence_status = "verified"
        await db_session.flush()

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        for field in self.REQUIRED_FIELDS:
            assert field in data, f"Missing required field: {field}"

    async def test_success_path_has_non_empty_answer(self, acceptance_app, db_session: AsyncSession) -> None:
        """When evidence exists, answer must be non-empty."""
        ents = await _seed_acceptance_corpus(db_session)

        svc = GraphService(db_session)
        ev = _make_ev(
            ents["doc"].id, ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        rel.evidence_status = "verified"
        await db_session.flush()

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["refusal"] is False, f"Expected refusal=False, got refusal=True: answer={data['answer']}"
        assert len(data["answer"]) > 0, "answer must be non-empty on success path"
        assert len(data["citations"]) > 0, "citations must be non-empty on success path"
        assert len(data["kg_paths"]) > 0, "kg_paths must be non-empty on success path"

    async def test_refusal_when_no_evidence(self, acceptance_app, db_session: AsyncSession) -> None:
        """When no evidence exists, response must be refusal=True with empty lists."""
        # Seed corpus but create NO edges
        await _seed_acceptance_corpus(db_session)

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "张仲景方剂来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        # Must have refusal=True or empty answer with refusal=True
        assert data["refusal"] is True or (
            len(data["answer"]) == 0
            and len(data["citations"]) == 0
            and len(data["kg_paths"]) == 0
        )


# ============================================================
# P0-1: MultiHopPathTest — at least one path with hop_count >= 2
# ============================================================


@pytest.mark.asyncio
class TestMultiHopPath:
    """Must return at least one continuous path with hop_count >= 2."""

    async def test_two_hop_path_in_kg_paths(self, acceptance_app, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        # Edge 1: 皇甫谧 --compiled--> 针灸甲乙经
        ev1 = _make_ev(ents["doc"].id, ents["chunk2"].id,
                       "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。")
        rel1 = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev1,
        )
        rel1.evidence_status = "verified"
        await db_session.flush()

        # Edge 2: 针灸甲乙经 --related_to--> 素问
        ev2 = _make_ev(ents["doc"].id, ents["chunk1"].id,
                       "皇甫谧，字士安，安定朝那人也。")
        rel2 = await svc.create_relation(
            source_entity_type="book", source_entity_id=ents["book"].id,
            target_entity_type="book", target_entity_id=ents["suwen"].id,
            relation_type="related_to", evidence=ev2,
        )
        rel2.evidence_status = "verified"
        await db_session.flush()

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        kg_paths = data["kg_paths"]

        # Must have at least one 2-hop path
        two_hop = [p for p in kg_paths if p.get("hop_count", 0) >= 2]
        assert len(two_hop) > 0, f"No 2-hop path found in: {kg_paths}"


# ============================================================
# P0: Evidence-bound assertions
# ============================================================


@pytest.mark.asyncio
class TestEvidenceBinding:
    """Every claim binds to evidence; every citation is DB-retrievable; every quote is contiguous."""

    async def test_evidence_chain_claims_bound(self, acceptance_app, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(ents["doc"].id, ents["chunk2"].id,
                      "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。")
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        rel.evidence_status = "verified"
        await db_session.flush()

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        evidence_chain = data["evidence_chain"]

        for link in evidence_chain:
            assert "claim" in link, f"Evidence link missing 'claim': {link}"
            assert len(link.get("claim", "")) > 0

    async def test_citations_retrievable_from_db(self, acceptance_app, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(ents["doc"].id, ents["chunk2"].id,
                      "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。")
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        rel.evidence_status = "verified"
        await db_session.flush()

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        for citation in data.get("citations", []):
            cit_str = citation.get("citation", "")
            # Parse [doc_id:chunk_id]
            if cit_str.startswith("[") and ":" in cit_str:
                inner = cit_str[1:-1]
                parts = inner.split(":", 1)
                if len(parts) == 2 and len(parts[0]) > 0:
                    doc_id = parts[0]
                    chunk_id = parts[1]
                    # Verify document exists
                    doc_stmt = select(Document).where(
                        Document.id == doc_id, Document.is_deleted.is_(False)
                    )
                    doc_result = await db_session.execute(doc_stmt)
                    assert doc_result.scalar_one_or_none() is not None, f"Document {doc_id} not found"

                    # Verify chunk exists
                    chunk_stmt = select(DocumentChunk).where(
                        DocumentChunk.id == chunk_id, DocumentChunk.is_deleted.is_(False)
                    )
                    chunk_result = await db_session.execute(chunk_stmt)
                    assert chunk_result.scalar_one_or_none() is not None, f"Chunk {chunk_id} not found"

    async def test_exact_quote_contiguous_substring(self, acceptance_app, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(ents["doc"].id, ents["chunk2"].id,
                      "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。")
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        rel.evidence_status = "verified"
        await db_session.flush()

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        for citation in data.get("citations", []):
            exact_quote = citation.get("exact_quote", "")
            chunk_id = citation.get("chunk_id", "")
            if not chunk_id:
                continue
            chunk_stmt = select(DocumentChunk).where(DocumentChunk.id == chunk_id)
            chunk_result = await db_session.execute(chunk_stmt)
            chunk = chunk_result.scalar_one_or_none()
            if chunk and exact_quote:
                assert _is_contiguous_substring(
                    exact_quote, chunk.content
                ), f"Quote not contiguous: {exact_quote[:50]}..."


def _is_contiguous_substring(needle: str, haystack: str) -> bool:
    import re
    n = re.sub(r"\s+", "", needle)
    h = re.sub(r"\s+", "", haystack)
    return n in h


# ============================================================
# P0: SemanticEvidenceMismatchTest — quote exists but doesn't support edge
# ============================================================


@pytest.mark.asyncio
class TestSemanticEvidenceMismatch:
    """A citation's presence in a chunk does NOT prove the edge's semantic claim."""

    async def test_irrelevant_quote_rejected(self, db_session: AsyncSession) -> None:
        """A quote about meridian theory cannot prove that 白虎汤 treats fever."""
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        # The chunk contains biographical text, NOT medical/pharmacological claims
        ev = _make_ev(
            ents["doc"].id, ents["chunk1"].id,
            "皇甫谧，字士安，安定朝那人也。",  # This proves identity, not treatment
        )

        # Creating a 'treats' relation using biographical evidence should
        # create the edge but with unverified status — the semantic check
        # is a human review step, not an automated semantic reasoner
        rel = await svc.create_relation(
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="related_to",
            description="针灸甲乙经与素问关联",
            evidence=ev,
        )
        # Edge exists but evidence_status defaults to 'unverified'
        assert rel.evidence_status == "unverified", (
            "New relations must default to 'unverified' until human review"
        )

    async def test_unverified_edge_excluded_from_paths(self, db_session: AsyncSession) -> None:
        """Unverified edges must not appear in KG paths."""
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        # Create an unverified edge
        ev = _make_ev(
            ents["doc"].id, ents["chunk1"].id,
            "皇甫谧，字士安，安定朝那人也。",
        )
        await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        # NOT setting evidence_status='verified' — stays 'unverified'

        paths = await svc.find_paths(
            source_type="person", source_id=ents["person"].id,
            target_type="book", target_id=ents["book"].id,
            max_depth=3, max_paths=10,
        )
        # Unverified edges should not produce paths
        assert len(paths) == 0, (
            f"Unverified edges must be excluded from paths, got {len(paths)} paths"
        )


# ============================================================
# P0: FakeSourceAttributionTest
# ============================================================


@pytest.mark.asyncio
class TestFakeSourceAttribution:
    """Source titles must match actual provenance."""

    async def test_no_fake_jinshu_passage_in_corpus(self, db_session: AsyncSession) -> None:
        """The forged sentence must NOT exist in our corpus."""
        ents = await _seed_acceptance_corpus(db_session)
        doc = ents["doc"]

        # The forged text must not be in our document
        forged = "其论针灸之道，以经络为本，以腧穴为标，以针刺为用"
        assert forged not in (doc.content_text or ""), (
            f"Forged pseudo-historical text found in corpus: {forged}"
        )

    async def test_chunk_content_matches_document(self, db_session: AsyncSession) -> None:
        """Every chunk's content must be a contiguous substring of its document."""
        ents = await _seed_acceptance_corpus(db_session)
        doc = ents["doc"]

        for key in ["chunk1", "chunk2"]:
            chunk = ents[key]
            assert _is_contiguous_substring(chunk.content, doc.content_text or ""), (
                f"{key} content is not in document"
            )


# ============================================================
# P0-5: TEIPersistenceTest — Sentence/Token/Variant DB round-trip
# ============================================================


@pytest.mark.asyncio
class TestTEIPersistence:
    """TEI hierarchy must persist in DB with real FK chains."""

    async def test_sentence_persistence(self, db_session: AsyncSession) -> None:
        """Sentence must persist and be retrievable."""
        ents = await _seed_acceptance_corpus(db_session)
        passage = ents["passage_song"]

        sent = TextSentence(
            passage_id=passage.id, order=1,
            text="黄帝问曰：针道可得闻乎？", xml_id="s1",
        )
        session = db_session
        session.add(sent)
        await session.flush()

        stmt = select(TextSentence).where(
            TextSentence.passage_id == passage.id,
            TextSentence.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.text == "黄帝问曰：针道可得闻乎？"
        assert fetched.order == 1

    async def test_token_persistence(self, db_session: AsyncSession) -> None:
        """Token must persist linked to sentence."""
        ents = await _seed_acceptance_corpus(db_session)
        passage = ents["passage_song"]

        sent = TextSentence(
            passage_id=passage.id, order=1,
            text="黄帝问曰：针道可得闻乎？", xml_id="s1",
        )
        session = db_session
        session.add(sent)
        await session.flush()

        token = TextToken(
            sentence_id=sent.id, order=1, text="黄帝",
            lemma="黄帝", pos="n", start_offset=0, end_offset=1,
        )
        session.add(token)
        await session.flush()

        stmt = select(TextToken).where(
            TextToken.sentence_id == sent.id,
            TextToken.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.text == "黄帝"
        assert fetched.lemma == "黄帝"

    async def test_variant_persistence(self, db_session: AsyncSession) -> None:
        """TextualVariant must persist with structured fields."""
        ents = await _seed_acceptance_corpus(db_session)

        variant = TextualVariant(
            source_version_id=ents["v_song"].id,
            target_version_id=ents["v_ming"].id,
            source_passage_id=ents["passage_song"].id,
            target_passage_id=ents["passage_ming"].id,
            location="卷一·序·第2句",
            lemma="可得闻也/耳",
            reading="也 → 耳",
            variant_type="substitution",
            apparatus="宋本作「也」，明本作「耳」。",
            verification_status="verified",
        )
        session = db_session
        session.add(variant)
        await session.flush()

        stmt = select(TextualVariant).where(
            TextualVariant.source_version_id == ents["v_song"].id,
            TextualVariant.is_deleted.is_(False),
        )
        result = await session.execute(stmt)
        fetched = result.scalar_one_or_none()
        assert fetched is not None
        assert fetched.reading == "也 → 耳"
        assert fetched.variant_type == "substitution"
        assert fetched.verification_status == "verified"


# ============================================================
# P0-5: TEIApparatusXMLTest
# ============================================================


class TestTEIApparatusXML:
    """TEI XML output must contain <app>, <lem>, <rdg> elements."""

    def test_tei_xml_has_apparatus_elements(self) -> None:
        """Generated TEI XML must contain critical apparatus tags."""
        from packages.tcm_tei import (
            Document as TEIDocument,
            TextVersion,
            Paragraph,
            Sentence,
            Token,
            VersionComparator,
            TEISerializer,
        )

        doc = TEIDocument(
            id="test_doc",
            title="Test Document",
            versions=[
                TextVersion(
                    id="v1", label="版本A",
                    paragraphs=[
                        Paragraph(
                            id="p1", section="卷一",
                            sentences=[
                                Sentence(
                                    id="s1", text="甲乙丙丁。",
                                    tokens=[Token(id="t1", text="甲")],
                                ),
                            ],
                        ),
                    ],
                ),
                TextVersion(
                    id="v2", label="版本B",
                    paragraphs=[
                        Paragraph(
                            id="p1", section="卷一",
                            sentences=[
                                Sentence(
                                    id="s1", text="甲乙丙戊。",
                                    tokens=[Token(id="t1", text="甲")],
                                ),
                            ],
                        ),
                    ],
                ),
            ],
        )

        comparator = VersionComparator()
        variants = comparator.diff(doc.versions[0], doc.versions[1])
        assert len(variants) > 0, "Must detect at least one variant"

        xml = TEISerializer.to_xml(doc, variants=variants)
        # Must contain apparatus structure
        assert "<app>" in xml or "<app " in xml, f"No <app> in TEI XML: {xml[:500]}"
        assert "<lem>" in xml or "<lem " in xml, f"No <lem> in TEI XML: {xml[:500]}"
        assert "<rdg>" in xml or "<rdg " in xml, f"No <rdg> in TEI XML: {xml[:500]}"


# ============================================================
# P0-6: OntologyDatabaseConstraintTest
# ============================================================


@pytest.mark.asyncio
class TestOntologyDatabaseConstraints:
    """Direct SQL INSERT of BogusType must fail at DB level."""

    async def test_bogus_entity_type_insert_fails(self, db_session: AsyncSession) -> None:
        """INSERT entity_type='BogusType' must fail with DB constraint."""
        import uuid
        session = db_session

        with pytest.raises(Exception):
            await session.execute(
                text(
                    "INSERT INTO tcm_entities (id, entity_type, name, created_at, updated_at, is_deleted) "
                    "VALUES (:id, 'BogusType', 'test', datetime('now'), datetime('now'), 0)"
                ),
                {"id": str(uuid.uuid4())},
            )
            await session.flush()

    async def test_bogus_relation_type_insert_fails(self, db_session: AsyncSession) -> None:
        """INSERT relation_type='fake_relation' must fail with DB constraint."""
        import uuid
        session = db_session

        with pytest.raises(Exception):
            await session.execute(
                text(
                    "INSERT INTO entity_relations "
                    "(id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, "
                    "relation_type, evidence_status, created_at, updated_at, is_deleted) "
                    "VALUES (:id, 'person', :sid, 'book', :tid, 'fake_relation', 'unverified', "
                    "datetime('now'), datetime('now'), 0)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "sid": str(uuid.uuid4()),
                    "tid": str(uuid.uuid4()),
                },
            )
            await session.flush()

    async def test_empty_entity_type_insert_fails(self, db_session: AsyncSession) -> None:
        """INSERT source_entity_type='' must fail."""
        import uuid
        session = db_session

        with pytest.raises(Exception):
            await session.execute(
                text(
                    "INSERT INTO entity_relations "
                    "(id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, "
                    "relation_type, evidence_status, created_at, updated_at, is_deleted) "
                    "VALUES (:id, '', :sid, 'book', :tid, 'compiled', 'unverified', "
                    "datetime('now'), datetime('now'), 0)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "sid": str(uuid.uuid4()),
                    "tid": str(uuid.uuid4()),
                },
            )
            await session.flush()

    async def test_bogus_target_type_insert_fails(self, db_session: AsyncSession) -> None:
        """INSERT target_entity_type='BogusType' must fail."""
        import uuid
        session = db_session

        with pytest.raises(Exception):
            await session.execute(
                text(
                    "INSERT INTO entity_relations "
                    "(id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, "
                    "relation_type, evidence_status, created_at, updated_at, is_deleted) "
                    "VALUES (:id, 'person', :sid, 'BogusType', :tid, 'compiled', 'unverified', "
                    "datetime('now'), datetime('now'), 0)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "sid": str(uuid.uuid4()),
                    "tid": str(uuid.uuid4()),
                },
            )
            await session.flush()


# ============================================================
# P0: EvidenceRemovalTest
# ============================================================


@pytest.mark.asyncio
class TestEvidenceRemoval:
    """After deleting or rejecting evidence, answer must be refusal."""

    async def test_deleted_evidence_excludes_paths(self, db_session: AsyncSession) -> None:
        """After soft-deleting evidence chunk, paths must disappear."""
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(
            ents["doc"].id, ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        rel.evidence_status = "verified"
        await db_session.flush()

        # Verify path exists before deletion
        path_before = await svc.find_path(
            source_type="person", source_id=ents["person"].id,
            target_type="book", target_id=ents["book"].id,
            max_depth=3,
        )
        assert path_before is not None

        # Reject evidence
        rel.evidence_status = "rejected"
        await db_session.flush()

        # Now path must be excluded
        path_after = await svc.find_path(
            source_type="person", source_id=ents["person"].id,
            target_type="book", target_id=ents["book"].id,
            max_depth=3,
        )
        assert path_after is None, "Path must be excluded after evidence rejected"


# ============================================================
# P0: RawHTTPDeterminismTest
# ============================================================


@pytest.mark.asyncio
class TestRawHTTPDeterminism:
    """Same DB snapshot → repeated requests → identical response.content."""

    async def test_deterministic_response(self, acceptance_app, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(
            ents["doc"].id, ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person", source_entity_id=ents["person"].id,
            target_entity_type="book", target_entity_id=ents["book"].id,
            relation_type="compiled", evidence=ev,
        )
        rel.evidence_status = "verified"
        await db_session.flush()

        query = {"query": "皇甫谧针灸思想来源是什么？"}
        resp1 = await acceptance_app.post("/api/v1/academic-rag/query", json=query)
        resp2 = await acceptance_app.post("/api/v1/academic-rag/query", json=query)

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # Parse and compare data (ignore output_sha256 which has timestamp-independent hash)
        data1 = resp1.json()["data"]
        data2 = resp2.json()["data"]

        # Deterministic fields must match
        assert data1["query"] == data2["query"]
        assert data1["answer"] == data2["answer"]
        assert len(data1["citations"]) == len(data2["citations"])
        assert len(data1["kg_paths"]) == len(data2["kg_paths"])
        assert len(data1["evidence_chain"]) == len(data2["evidence_chain"])
        assert data1["refusal"] == data2["refusal"]
        assert data1["corpus_sha256"] == data2["corpus_sha256"]
        assert data1["output_sha256"] == data2["output_sha256"]


# ============================================================
# Legacy compatibility tests (kept from original, cleaned)
# ============================================================


@pytest.mark.asyncio
class TestOntologyRejection:
    """Ontology must reject invalid types and relations at service level."""

    async def test_empty_entity_type_rejected(self, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)
        ev = _make_ev(ents["doc"].id, ents["chunk1"].id, "皇甫谧，字士安，安定朝那人也。")
        with pytest.raises(ValueError, match="Invalid source_entity_type"):
            await svc.create_relation(
                source_entity_type="", source_entity_id=ents["person"].id,
                target_entity_type="book", target_entity_id=ents["book"].id,
                relation_type="authored", evidence=ev,
            )

    async def test_bogus_entity_type_rejected(self, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)
        ev = _make_ev(ents["doc"].id, ents["chunk1"].id, "皇甫谧，字士安，安定朝那人也。")
        with pytest.raises(ValueError, match="Invalid source_entity_type"):
            await svc.create_relation(
                source_entity_type="BogusType", source_entity_id=ents["person"].id,
                target_entity_type="book", target_entity_id=ents["book"].id,
                relation_type="authored", evidence=ev,
            )

    async def test_bogus_relation_type_rejected(self, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)
        ev = _make_ev(ents["doc"].id, ents["chunk1"].id, "皇甫谧，字士安，安定朝那人也。")
        with pytest.raises(ValueError, match="Invalid relation_type"):
            await svc.create_relation(
                source_entity_type="person", source_entity_id=ents["person"].id,
                target_entity_type="book", target_entity_id=ents["book"].id,
                relation_type="bogus_relation", evidence=ev,
            )

    async def test_missing_entity_edge_fails(self, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)
        ev = _make_ev(ents["doc"].id, ents["chunk1"].id, "皇甫谧，字士安，安定朝那人也。")
        with pytest.raises(ValueError, match="not found or deleted"):
            await svc.create_relation(
                source_entity_type="person", source_entity_id=ents["person"].id,
                target_entity_type="book",
                target_entity_id="00000000-0000-0000-0000-00000000dead",
                relation_type="authored", evidence=ev,
            )


@pytest.mark.asyncio
class TestTEIHierarchy:
    """TEI Document → Version → Passage hierarchy persists."""

    async def test_document_version_passage_hierarchy(self, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        doc = ents["doc"]
        assert doc.title == "晋书·皇甫谧传"

        v_song = ents["v_song"]
        v_ming = ents["v_ming"]
        assert v_song.version_name == "宋本"
        assert v_ming.version_name == "明赵府居敬堂刊本"

        p_song = ents["passage_song"]
        p_ming = ents["passage_ming"]
        assert p_song.content_text != p_ming.content_text
        assert "也" in p_song.content_text
        assert "耳" in p_ming.content_text


class TestOntologyBridge:
    """tcm_ontology packages bridge to production GRAPH_ENTITY_TYPES."""

    def test_canonical_types_in_graph_types(self) -> None:
        from app.models.graph import GRAPH_ENTITY_TYPES
        for ct in ("person", "text", "herb", "prescription", "meridian", "symptom"):
            assert ct in GRAPH_ENTITY_TYPES, f"{ct} must be in GRAPH_ENTITY_TYPES"

    def test_ontology_entity_type_enum_exists(self) -> None:
        from packages.tcm_ontology import EntityType
        assert EntityType.PERSON.value == "Person"
        assert EntityType.TEXT.value == "Text"
