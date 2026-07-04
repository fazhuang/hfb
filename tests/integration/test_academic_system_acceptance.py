"""
Academic System Acceptance Tests — P0 hardened.

Verification:
  P0-1: Exact question via HTTP API, strict refusal state machine
  P0-2: Evidence verification through official verify_relation() only
  P0-3: Real source evidence for compiled_from, no biographical quotes for book relationships
  P0-4: Stable ID evidence chain, no array-index citation binding
  P0-5: TEI real ForeignKeys — orphan inserts must fail
  P0-6: Database default values — 'unverified' without extra quotes
  P0-7: Acceptance tests that actually assert what the spec requires

Every test that needs verified relations MUST use GraphService.verify_relation().
Direct assignment of evidence_status is FORBIDDEN.
"""

from __future__ import annotations

import uuid
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


# Only verifiable historical content
_JINSHU_BIO = (
    "皇甫谧，字士安，安定朝那人也。"
    "居贫，躬自稼穑，带经而农，遂博综典籍百家之言。"
    "沉静寡欲，始有高尚之志，以著述为务，自号玄晏先生。"
    "后得风痹疾，犹手不辍卷。"
    "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。"
)

# 《黄帝三部针灸甲乙经序》— the actual preface by Huangfu Mi explaining sources
# Verifiable content: 皇甫谧自序说明三部来源
_PREFACE_CONTENT = (
    "乃撰集三部，使事类相从，删其浮辞，除其重复，论其精要，至为十二卷。"
    "按《七略》艺文志，《黄帝内经》十八卷，今有《针经》九卷、《素问》九卷，"
    "二九十八卷，即《内经》也。"
    "又有《明堂孔穴针灸治要》，皆黄帝岐伯遗事也。"
)

_ZJYJ_SONG_PASSAGE = "黄帝问曰：针道可得闻乎？岐伯对曰：可得闻也。"
_ZJYJ_MING_PASSAGE = "黄帝问曰：针道可得闻乎？岐伯对曰：可得闻耳。"


async def _seed_acceptance_corpus(session: AsyncSession) -> dict[str, Any]:
    """Seed verifiable acceptance corpus with real historical content.

    Returns dict of created entities keyed by label.
    """
    # Person: 皇甫谧
    person = Person(
        name="皇甫谧",
        name_zh="皇甫谧",
        courtesy_name="士安",
        pseudonym="玄晏先生",
        dynasty="魏晋",
        birth_year=215,
        death_year=282,
        birth_place="安定朝那",
        biography="魏晋医学家，著《针灸甲乙经》",
        expertise="针灸",
        notable_works="针灸甲乙经",
    )
    session.add(person)
    await session.flush()

    # Book: 针灸甲乙经
    book = Book(
        title="针灸甲乙经",
        dynasty="魏晋",
        year=256,
        category="针灸",
        abstract="皇甫谧编纂的针灸学经典",
        author_id=person.id,
    )
    session.add(book)
    await session.flush()

    # Source texts (attested in Huangfu Mi's own preface)
    suwen = Book(
        title="素问",
        dynasty="汉",
        year=0,
        category="医经",
        abstract="《黄帝内经素问》，针灸甲乙经主要来源之一",
    )
    zhenjing = Book(
        title="针经",
        dynasty="汉",
        year=0,
        category="医经",
        abstract="即《灵枢经》，针灸甲乙经主要来源之一",
    )
    mingtang = Book(
        title="明堂孔穴针灸治要",
        dynasty="汉",
        year=0,
        category="针灸",
        abstract="明堂孔穴针灸治要，皇甫谧序中提及的来源之一",
    )
    session.add_all([suwen, zhenjing, mingtang])
    await session.flush()

    # Versions
    v_song = Version(
        book_id=book.id,
        version_name="宋本",
        era="北宋",
        repository="中国国家图书馆",
        description="北宋刻本《针灸甲乙经》",
    )
    v_ming = Version(
        book_id=book.id,
        version_name="明赵府居敬堂刊本",
        era="明",
        repository="赵府居敬堂",
        description="明刻本《针灸甲乙经》",
    )
    session.add_all([v_song, v_ming])
    await session.flush()

    # Document 1 — 《晋书·皇甫谧传》
    doc = Document(
        title="晋书·皇甫谧传",
        dynasty="唐",
        category="史书",
        content_text=_JINSHU_BIO,
    )
    session.add(doc)
    await session.flush()

    # Chunks for biography
    chunk1 = DocumentChunk(
        document_id=doc.id,
        chunk_index=0,
        content=(
            "皇甫谧，字士安，安定朝那人也。"
            "居贫，躬自稼穑，带经而农，遂博综典籍百家之言。"
            "沉静寡欲，始有高尚之志，以著述为务，自号玄晏先生。"
        ),
        token_count=60,
    )
    chunk2 = DocumentChunk(
        document_id=doc.id,
        chunk_index=1,
        content=(
            "后得风痹疾，犹手不辍卷。"
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。"
        ),
        token_count=35,
    )
    session.add_all([chunk1, chunk2])
    await session.flush()

    # Document 2 — 《黄帝三部针灸甲乙经序》 (the actual preface)
    doc_preface = Document(
        title="黄帝三部针灸甲乙经序",
        dynasty="魏晋",
        category="序跋",
        content_text=_PREFACE_CONTENT,
    )
    session.add(doc_preface)
    await session.flush()

    # Chunks for preface
    preface_chunk = DocumentChunk(
        document_id=doc_preface.id,
        chunk_index=0,
        content=_PREFACE_CONTENT,
        token_count=80,
    )
    session.add(preface_chunk)
    await session.flush()

    # Chapter MUST come before Passage — FK constraint is now real
    from app.models.chapter import Chapter

    chapter = Chapter(
        id="00000000-0000-0000-0000-000000000001",
        book_id=book.id,
        title="卷一",
        order=1,
    )
    session.add(chapter)
    await session.flush()

    # Passages
    passage_song = Passage(
        chapter_id="00000000-0000-0000-0000-000000000001",
        version_id=v_song.id,
        order=1,
        content_text=_ZJYJ_SONG_PASSAGE,
    )
    passage_ming = Passage(
        chapter_id="00000000-0000-0000-0000-000000000001",
        version_id=v_ming.id,
        order=1,
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
        "doc_preface": doc_preface,
        "chunk1": chunk1,
        "chunk2": chunk2,
        "preface_chunk": preface_chunk,
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


def _is_contiguous_substring(needle: str, haystack: str) -> bool:
    import re

    n = re.sub(r"\s+", "", needle)
    h = re.sub(r"\s+", "", haystack)
    return n in h


# ============================================================
# HTTP test fixture
# ============================================================


@pytest_asyncio.fixture
async def acceptance_app(db_session: AsyncSession):
    """Build a FastAPI test app with auth overrides."""
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
    fastapi_app.dependency_overrides[auth_mod.get_current_user] = (
        override_get_current_user
    )
    fastapi_app.dependency_overrides[auth_mod.get_auth_service] = (
        override_get_auth_service
    )

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    fastapi_app.dependency_overrides.clear()


# ============================================================
# Helper: create and verify a relation through official API
# ============================================================


async def _create_and_verify_relation(
    session: AsyncSession,
    source_entity_type: str,
    source_entity_id: str,
    target_entity_type: str,
    target_entity_id: str,
    relation_type: str,
    description: str,
    ev: GraphEvidence,
    *,
    claim_text: str,
    evidence_version_id: str,
    evidence_passage_id: str,
    evidence_source_uri: str,
    verified_by: str = "test-reviewer",
) -> Any:
    """P0-2: Create a relation and verify it through the official API only."""
    svc = GraphService(session)
    rel = await svc.create_relation(
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        target_entity_type=target_entity_type,
        target_entity_id=target_entity_id,
        relation_type=relation_type,
        description=description,
        evidence=ev,
    )
    # Must default to 'unverified'
    assert rel.evidence_status == "unverified"

    verified = await svc.verify_relation(
        relation_id=rel.id,
        claim_text=claim_text,
        evidence_document_id=ev.document_id,
        evidence_version_id=evidence_version_id,
        evidence_passage_id=evidence_passage_id,
        evidence_chunk_id=ev.chunk_id,
        evidence_quote=ev.exact_quote,
        evidence_source_uri=evidence_source_uri,
        verified_by=verified_by,
    )
    assert verified.evidence_status == "verified"
    assert verified.verified_by == verified_by
    assert verified.verified_at is not None
    return verified


# ============================================================
# P0-7.1: NoVerifiedPathMustRefuseTest
# ============================================================


@pytest.mark.asyncio
class TestNoVerifiedPathMustRefuse:
    """P0-7.1: With matching chunks but NO verified edges, refusal MUST be true."""

    async def test_chunks_without_verified_edges_refuses(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Chunks matching keywords exist but no verified KG edge — must refuse."""
        ents = await _seed_acceptance_corpus(db_session)

        # Create an edge but do NOT verify it — stays unverified
        svc = GraphService(db_session)
        ev = _make_ev(
            ents["doc"].id,
            ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        await svc.create_relation(
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            evidence=ev,
        )
        # NOT verified — stays unverified
        await db_session.flush()

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        # Chunks exist but no verified edge → must refuse
        assert data["refusal"] is True, (
            f"Expected refusal=True when no verified edges exist. "
            f"Got refusal={data['refusal']}, answer={data['answer'][:100]}"
        )
        assert data["citations"] == []
        assert data["kg_paths"] == []
        assert data["evidence_chain"] == []


# ============================================================
# P0-7.2: RejectedEvidenceMustRefuseHTTPTest
# ============================================================


@pytest.mark.asyncio
class TestRejectedEvidenceMustRefuseHTTP:
    """P0-7.2: Reject the only evidence, then HTTP must return refusal=true."""

    async def test_reject_only_evidence_causes_refusal(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(
            ents["doc"].id,
            ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            evidence=ev,
        )
        # Verify it
        await svc.verify_relation(
            relation_id=rel.id,
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_document_id=ev.document_id,
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
            verified_by="test-reviewer",
        )
        await db_session.flush()

        # Now reject the evidence by directly setting status (the only path
        # to reject is via DB update since verify_relation rejects non-unverified)
        rel.evidence_status = "rejected"
        await db_session.flush()

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["refusal"] is True, (
            f"Expected refusal=True after rejecting only evidence. "
            f"Got refusal={data['refusal']}"
        )
        assert data["citations"] == []
        assert data["kg_paths"] == []
        assert data["evidence_chain"] == []


# ============================================================
# P0-7.3: SemanticMismatchCannotBeVerifiedTest
# ============================================================


@pytest.mark.asyncio
class TestSemanticMismatchCannotBeVerified:
    """P0-7.3: Using biographical quote to prove book-source relationship must fail verification."""

    async def test_biography_quote_cannot_prove_compiled_from(
        self, db_session: AsyncSession
    ) -> None:
        """'皇甫谧，字士安...' proves identity, not that 甲乙经 compiled_from 素问."""
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        # Create compiled_from edge with biographical quote
        ev = _make_ev(
            ents["doc"].id,
            ents["chunk1"].id,
            "皇甫谧，字士安，安定朝那人也。",  # This proves identity, not source
        )
        rel = await svc.create_relation(
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            evidence=ev,
        )
        # The quote IS in the chunk, so create_relation succeeds.
        # But it's a biographical quote — verify_relation must reject it.

        # Call verify_relation and assert it fails with semantic policy error
        with pytest.raises(ValueError, match="Semantic evidence policy"):
            await svc.verify_relation(
                relation_id=rel.id,
                claim_text="针灸甲乙经以素问为编纂来源",
                evidence_document_id=ev.document_id,
                evidence_version_id=ents["v_song"].id,
                evidence_passage_id=ents["passage_song"].id,
                evidence_chunk_id=ev.chunk_id,
                evidence_quote=ev.exact_quote,
                evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
                verified_by="test-reviewer",
            )

        # After failed verification, status must remain 'unverified'
        await db_session.refresh(rel)
        assert rel.evidence_status == "unverified"
        assert rel.verified_by is None
        assert rel.verified_at is None

        # Unverified edges must not produce paths
        paths = await svc.find_paths(
            source_type="person",
            source_id=ents["person"].id,
            target_type="book",
            target_id=ents["suwen"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths) == 0, (
            f"Unverified edges must not produce paths. Got {len(paths)} paths."
        )

    async def test_preface_quote_can_prove_compiled_from(
        self, db_session: AsyncSession
    ) -> None:
        """Real preface quote with source-derivation markers must pass verification."""
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        # Use real preface evidence: explicitly names 《素问》 as source
        ev = _make_ev(
            ents["doc_preface"].id,
            ents["preface_chunk"].id,
            "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
        )
        rel = await svc.create_relation(
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            evidence=ev,
        )
        assert rel.evidence_status == "unverified"

        # Must pass verification
        verified = await svc.verify_relation(
            relation_id=rel.id,
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_document_id=ev.document_id,
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_chunk_id=ev.chunk_id,
            evidence_quote=ev.exact_quote,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
            verified_by="test-reviewer",
        )
        assert verified.evidence_status == "verified"
        assert verified.verified_by == "test-reviewer"
        assert verified.verified_at is not None


# ============================================================
# P0-7.4: VerifiedProvenanceCompletenessTest
# ============================================================


@pytest.mark.asyncio
class TestVerifiedProvenanceCompleteness:
    """P0-7.4: Verified relations missing any audit field must be invisible."""

    async def test_missing_verified_by_excluded(self, db_session: AsyncSession) -> None:
        """Verified relation without verified_by must be excluded from paths."""
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(
            ents["doc"].id,
            ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            evidence=ev,
        )
        # Set status to 'verified' but do NOT set verified_by — simulate broken state
        # This bypasses verify_relation() to test the query-time check
        rel.evidence_status = "verified"
        rel.claim_text = "皇甫谧编撰《针灸甲乙经》"
        rel.evidence_source_uri = "https://ctext.org/jinshu/huangfu-mi-zhuan"
        rel.evidence_version_id = ents["v_song"].id
        rel.evidence_passage_id = ents["passage_song"].id
        # verified_by is left None → must be excluded
        await db_session.flush()

        paths = await svc.find_paths(
            source_type="person",
            source_id=ents["person"].id,
            target_type="book",
            target_id=ents["book"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths) == 0, (
            f"Relation without verified_by must be excluded from paths. Got {len(paths)} paths."
        )

    async def test_missing_source_uri_excluded(self, db_session: AsyncSession) -> None:
        """Verified relation with pseudo document:UUID source_uri must be excluded."""
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(
            ents["doc"].id,
            ents["chunk2"].id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        rel = await svc.create_relation(
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            evidence=ev,
        )
        # Set status to 'verified' but source_uri is pseudo
        rel.evidence_status = "verified"
        rel.claim_text = "皇甫谧编撰《针灸甲乙经》"
        rel.evidence_source_uri = f"document:{ev.document_id}"  # pseudo URI
        rel.verified_by = "test-reviewer"
        from datetime import datetime, timezone

        rel.verified_at = datetime.now(timezone.utc)
        await db_session.flush()

        paths = await svc.find_paths(
            source_type="person",
            source_id=ents["person"].id,
            target_type="book",
            target_id=ents["book"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths) == 0, (
            f"Relation with pseudo document:UUID source_uri must be excluded. Got {len(paths)} paths."
        )


# ============================================================
# P0-7.5: TEIOrphanFKTest
# ============================================================


@pytest.mark.asyncio
class TestTEIOrphanFK:
    """P0-7.5: Direct SQL insert of orphan Sentence/Token/Variant must fail."""

    async def test_orphan_sentence_insert_fails(self, db_session: AsyncSession) -> None:
        """Sentence referencing non-existent passage must fail."""
        await _seed_acceptance_corpus(db_session)

        with pytest.raises(Exception):
            await db_session.execute(
                text(
                    "INSERT INTO text_sentences "
                    '(id, passage_id, "order", text, created_at, updated_at, is_deleted) '
                    "VALUES (:id, :pid, 1, 'test', datetime('now'), datetime('now'), 0)"
                ),
                {"id": str(uuid.uuid4()), "pid": str(uuid.uuid4())},
            )
            await db_session.flush()

    async def test_orphan_token_insert_fails(self, db_session: AsyncSession) -> None:
        """Token referencing non-existent sentence must fail."""
        await _seed_acceptance_corpus(db_session)

        with pytest.raises(Exception):
            await db_session.execute(
                text(
                    "INSERT INTO text_tokens "
                    '(id, sentence_id, "order", text, created_at, updated_at, is_deleted) '
                    "VALUES (:id, :sid, 1, 'test', datetime('now'), datetime('now'), 0)"
                ),
                {"id": str(uuid.uuid4()), "sid": str(uuid.uuid4())},
            )
            await db_session.flush()

    async def test_orphan_variant_insert_fails(self, db_session: AsyncSession) -> None:
        """Variant referencing non-existent version must fail."""
        await _seed_acceptance_corpus(db_session)

        with pytest.raises(Exception):
            await db_session.execute(
                text(
                    "INSERT INTO textual_variants "
                    "(id, source_version_id, target_version_id, reading, "
                    "verification_status, created_at, updated_at, is_deleted) "
                    "VALUES (:id, :sv, :tv, 'test', 'unverified', "
                    "datetime('now'), datetime('now'), 0)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "sv": str(uuid.uuid4()),
                    "tv": str(uuid.uuid4()),
                },
            )
            await db_session.flush()


# ============================================================
# P0-7.6: DefaultValueTest
# ============================================================


@pytest.mark.asyncio
class TestDefaultValueTest:
    """P0-7.6: Database default for verification status must be exactly 'unverified'."""

    async def test_entity_relation_default_is_unverified(
        self, db_session: AsyncSession
    ) -> None:
        """Insert EntityRelation without evidence_status — must read back as 'unverified'."""
        ents = await _seed_acceptance_corpus(db_session)

        rid = str(uuid.uuid4())
        pid = ents["person"].id
        bid = ents["suwen"].id

        # Insert omitting evidence_status
        await db_session.execute(
            text(
                "INSERT INTO entity_relations "
                "(id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, "
                "relation_type, created_at, updated_at, is_deleted) "
                "VALUES (:id, 'person', :sid, 'book', :tid, 'related_to', "
                "datetime('now'), datetime('now'), 0)"
            ),
            {"id": rid, "sid": pid, "tid": bid},
        )
        await db_session.flush()

        result = await db_session.execute(
            text("SELECT evidence_status FROM entity_relations WHERE id = :id"),
            {"id": rid},
        )
        row = result.fetchone()
        assert row is not None
        status = row[0]
        # Must be exactly 'unverified' — no extra quotes
        assert status == "unverified", f"Expected 'unverified', got {status!r}"
        assert status != "'unverified'"
        assert status != "'''unverified'''"

    async def test_textual_variant_default_is_unverified(
        self, db_session: AsyncSession
    ) -> None:
        """Insert TextualVariant without verification_status — must read back as 'unverified'."""
        ents = await _seed_acceptance_corpus(db_session)

        vid = str(uuid.uuid4())

        await db_session.execute(
            text(
                "INSERT INTO textual_variants "
                "(id, source_version_id, target_version_id, reading, "
                "created_at, updated_at, is_deleted) "
                "VALUES (:id, :sv, :tv, 'test reading', "
                "datetime('now'), datetime('now'), 0)"
            ),
            {
                "id": vid,
                "sv": ents["v_song"].id,
                "tv": ents["v_ming"].id,
            },
        )
        await db_session.flush()

        result = await db_session.execute(
            text("SELECT verification_status FROM textual_variants WHERE id = :id"),
            {"id": vid},
        )
        row = result.fetchone()
        assert row is not None
        status = row[0]
        assert status == "unverified", f"Expected 'unverified', got {status!r}"
        assert status != "'unverified'"


# ============================================================
# P0-7.7: RawHTTPDeterminismTest
# ============================================================


@pytest.mark.asyncio
class TestRawHTTPDeterminism:
    """P0-7.7: Same DB snapshot → repeated requests → identical response.content."""

    async def test_raw_content_determinism(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """repeated HTTP calls must return identical response.content bytes."""
        ents = await _seed_acceptance_corpus(db_session)

        # Create and properly verify both edges
        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        await _create_and_verify_relation(
            db_session,
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            ev=_make_ev(
                ents["doc_preface"].id,
                ents["preface_chunk"].id,
                "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
            ),
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )

        query = {"query": "皇甫谧针灸思想来源是什么？"}
        resp1 = await acceptance_app.post("/api/v1/academic-rag/query", json=query)
        resp2 = await acceptance_app.post("/api/v1/academic-rag/query", json=query)

        assert resp1.status_code == 200
        assert resp2.status_code == 200

        # P0-7.7: must compare raw response.content
        assert resp1.content == resp2.content, (
            "HTTP response content must be byte-identical for repeated calls"
        )

    async def test_deterministic_fields(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Structural deterministic fields must match."""
        ents = await _seed_acceptance_corpus(db_session)

        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        await _create_and_verify_relation(
            db_session,
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            ev=_make_ev(
                ents["doc_preface"].id,
                ents["preface_chunk"].id,
                "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
            ),
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )

        query = {"query": "皇甫谧针灸思想来源是什么？"}
        resp1 = await acceptance_app.post("/api/v1/academic-rag/query", json=query)
        resp2 = await acceptance_app.post("/api/v1/academic-rag/query", json=query)

        data1 = resp1.json()["data"]
        data2 = resp2.json()["data"]

        assert data1["query"] == data2["query"]
        assert data1["answer"] == data2["answer"]
        assert data1["refusal"] == data2["refusal"]
        assert data1["corpus_sha256"] == data2["corpus_sha256"]
        assert data1["output_sha256"] == data2["output_sha256"]
        assert len(data1["citations"]) == len(data2["citations"])
        assert len(data1["kg_paths"]) == len(data2["kg_paths"])


# ============================================================
# P0-7.8: ExactAnswerSemanticsTest
# ============================================================


@pytest.mark.asyncio
class TestExactAnswerSemantics:
    """P0-7.8: Success answer must contain verifiable source work names."""

    async def test_answer_contains_source_text_names(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Answer must explicitly name evidence-supported source texts."""
        ents = await _seed_acceptance_corpus(db_session)

        # Create 2-hop path: 皇甫谧 → compiled → 针灸甲乙经 → compiled_from → 素问
        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        await _create_and_verify_relation(
            db_session,
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            ev=_make_ev(
                ents["doc_preface"].id,
                ents["preface_chunk"].id,
                "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
            ),
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        # Must be successful (2-hop path exists with verified evidence)
        assert data["refusal"] is False, (
            f"Expected success, got refusal: {data['answer'][:200]}"
        )

        # Answer must contain at least one source work name with evidence
        answer = data["answer"]
        # Check for book names in answer (with or without guillemets)
        has_source_name = any(
            name in answer for name in ["素问", "针经", "明堂孔穴针灸治要"]
        )
        assert has_source_name, (
            f"Answer must mention evidence-supported source works. Got: {answer[:300]}"
        )


# ============================================================
# P0-7.9: CitationProvenanceTest
# ============================================================


@pytest.mark.asyncio
class TestCitationProvenance:
    """P0-7.9: Successful path citations must have version_id, passage_id, source_uri."""

    async def test_citations_have_provenance_in_success_response(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """In a successful response, verify via official API and check citations."""
        ents = await _seed_acceptance_corpus(db_session)

        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        await _create_and_verify_relation(
            db_session,
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            ev=_make_ev(
                ents["doc_preface"].id,
                ents["preface_chunk"].id,
                "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
            ),
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["refusal"] is False

        # P0-7.9: In success path, the underlying verified relation has complete provenance.
        # We verify at the GraphService level where the full EntityRelation is available.
        svc = GraphService(db_session)
        validated = await svc.get_validated_relations_for_entity(
            "person",
            ents["person"].id,
        )
        assert len(validated) > 0, "Must have at least one validated relation"
        for er, _ev in validated:
            # Each verified relation must have complete provenance
            assert er.evidence_source_uri, "source_uri must be non-empty"
            assert er.verified_by, "verified_by must be non-empty"
            assert er.verified_at, "verified_at must be non-empty"
            assert er.claim_text, "claim_text must be non-empty"
            # source_uri must not be pseudo document:UUID
            assert not er.evidence_source_uri.startswith("document:"), (
                f"source_uri must not be pseudo document:UUID, got {er.evidence_source_uri}"
            )

        # P0-2: Also assert the HTTP JSON carries provenance in citations
        for citation in data["citations"]:
            assert citation.get("version_id", ""), (
                f"Citation version_id must be non-empty: {citation}"
            )
            assert citation.get("passage_id", ""), (
                f"Citation passage_id must be non-empty: {citation}"
            )
            assert citation.get("source_uri", ""), (
                f"Citation source_uri must be non-empty: {citation}"
            )
            assert citation.get("exact_quote", ""), (
                f"Citation exact_quote must be non-empty: {citation}"
            )

        # P0-2: Every edge in every path must have claim_text
        for path in data["kg_paths"]:
            for edge in path.get("edges", []):
                assert edge.get("claim_text", ""), (
                    f"Edge claim_text must be non-empty: {edge}"
                )
                assert edge.get("version_id", ""), (
                    f"Edge version_id must be non-empty: {edge}"
                )
                assert edge.get("passage_id", ""), (
                    f"Edge passage_id must be non-empty: {edge}"
                )
                assert edge.get("source_uri", ""), (
                    f"Edge source_uri must be non-empty: {edge}"
                )


# ============================================================
# P0-2: CitationProvenanceSurvivesHttpProjectionTest
# ============================================================


@pytest.mark.asyncio
class TestCitationProvenanceSurvivesHttpProjection:
    """P0-2: Every provenance field must survive the full HTTP projection chain.

    EntityRelation → GraphEvidence → AcademicKGEdge → AcademicCitation
    must be lossless. Check the raw HTTP JSON, not just DB objects.
    """

    async def test_http_provenance_chain_is_lossless(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Full provenance chain via HTTP: version_id, passage_id, source_uri,
        exact_quote, claim_text all non-empty. ID cross-references resolve."""
        ents = await _seed_acceptance_corpus(db_session)

        # Create 2-hop path: person → compiled → book → compiled_from → suwen
        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        await _create_and_verify_relation(
            db_session,
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            ev=_make_ev(
                ents["doc_preface"].id,
                ents["preface_chunk"].id,
                "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
            ),
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        body = resp.json()
        data = body["data"]

        # --- Condition 1: refusal is False ---
        assert data["refusal"] is False, (
            f"Expected refusal=False, got {data['refusal']}"
        )

        # --- Condition 2: citations non-empty ---
        assert len(data["citations"]) > 0, "citations must be non-empty"

        # --- Condition 3: at least one 2-hop path ---
        two_hop_paths = [p for p in data["kg_paths"] if p.get("hop_count", 0) >= 2]
        assert len(two_hop_paths) > 0, "Must have at least one 2-hop path"

        # --- Condition 4: every citation has all provenance fields non-empty ---
        for citation in data["citations"]:
            assert citation.get("version_id"), f"Citation version_id empty: {citation}"
            assert citation.get("passage_id"), f"Citation passage_id empty: {citation}"
            assert citation.get("source_uri"), f"Citation source_uri empty: {citation}"
            assert citation.get("exact_quote"), (
                f"Citation exact_quote empty: {citation}"
            )

        # --- Condition 5: every edge has claim_text non-empty ---
        for path in data["kg_paths"]:
            for edge in path.get("edges", []):
                assert edge.get("claim_text"), f"Edge claim_text empty: {edge}"
                assert edge.get("version_id"), f"Edge version_id empty: {edge}"
                assert edge.get("passage_id"), f"Edge passage_id empty: {edge}"
                assert edge.get("source_uri"), f"Edge source_uri empty: {edge}"

        # --- Condition 6: evidence_chain IDs resolve to real objects ---
        evidence_chain = data["evidence_chain"]
        assert len(evidence_chain) > 0, "evidence_chain must be non-empty"

        # Collect all IDs from edges and citations for cross-reference
        all_edge_ids: set[str] = set()
        all_evidence_ids: set[str] = set()
        all_citation_ids: set[str] = {c["citation_id"] for c in data["citations"]}
        for path in data["kg_paths"]:
            for edge in path.get("edges", []):
                if edge.get("edge_id"):
                    all_edge_ids.add(edge["edge_id"])
                if edge.get("evidence_id"):
                    all_evidence_ids.add(edge["evidence_id"])

        for link in evidence_chain:
            # path_id must be non-empty
            assert link.get("path_id"), f"Link path_id empty: {link}"

            # edge_ids must resolve to edges in kg_paths
            for eid in link.get("edge_ids", []):
                assert eid in all_edge_ids, (
                    f"Link edge_id '{eid}' not found in any kg_path edge"
                )

            # evidence_ids must resolve to edges
            for evid in link.get("evidence_ids", []):
                assert evid in all_evidence_ids, (
                    f"Link evidence_id '{evid}' not found in any kg_path edge"
                )

            # citation_ids must resolve to citations
            for cid in link.get("citation_ids", []):
                assert cid in all_citation_ids, (
                    f"Link citation_id '{cid}' not found in citations"
                )

        # --- Condition 7: same provenance fields across the chain ---
        # Every citation's document_id + chunk_id must match at least one edge's
        # evidence_citation which encodes [document_id:chunk_id]
        for citation in data["citations"]:
            expected_cit = f"[{citation['document_id']}:{citation['chunk_id']}]"
            found = False
            for path in data["kg_paths"]:
                for edge in path.get("edges", []):
                    if edge.get("evidence_citation") == expected_cit:
                        found = True
                        # Cross-check: exact_quote must also match
                        assert edge.get("evidence_quote") == citation.get(
                            "exact_quote"
                        ), (
                            f"Edge evidence_quote mismatch: "
                            f"edge={edge.get('evidence_quote', '')[:60]}, "
                            f"citation={citation.get('exact_quote', '')[:60]}"
                        )
                        break
                if found:
                    break
            assert found, (
                f"Citation [{citation['document_id']}:{citation['chunk_id']}] "
                f"not referenced by any edge"
            )


# ============================================================
# P0-1: ExactQuestionTest — no query rewriting
# ============================================================


@pytest.mark.asyncio
class TestExactQuestion:
    """The exact question MUST be submitted without rewriting."""

    async def test_exact_question_no_rewrite(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Submit the exact question via HTTP."""
        ents = await _seed_acceptance_corpus(db_session)

        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        exact_question = "皇甫谧针灸思想来源是什么？"
        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": exact_question},
        )
        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["query"] == exact_question

    async def test_no_query_rewrite_in_request(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Verify the query arrives exactly as sent."""
        ents = await _seed_acceptance_corpus(db_session)

        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        original = "皇甫谧针灸思想来源是什么？"
        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": original},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["query"] == original


# ============================================================
# P0-1: ResponseContractTest
# ============================================================


@pytest.mark.asyncio
class TestResponseContract:
    """Response MUST contain all required fields."""

    REQUIRED_FIELDS = [
        "answer",
        "citations",
        "kg_paths",
        "evidence_chain",
        "refusal",
        "query",
        "corpus_sha256",
        "output_sha256",
    ]

    async def test_all_required_fields_present(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Every required field must be present."""
        ents = await _seed_acceptance_corpus(db_session)

        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        for field in self.REQUIRED_FIELDS:
            assert field in data, f"Missing required field: {field}"

    async def test_success_path_fields_non_empty(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """With 2-hop verified path, all lists must be non-empty."""
        ents = await _seed_acceptance_corpus(db_session)

        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        await _create_and_verify_relation(
            db_session,
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            ev=_make_ev(
                ents["doc_preface"].id,
                ents["preface_chunk"].id,
                "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
            ),
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["refusal"] is False
        assert len(data["answer"]) > 0
        assert len(data["citations"]) > 0
        assert len(data["kg_paths"]) > 0
        assert len(data["evidence_chain"]) > 0

    async def test_refusal_when_no_evidence(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """When no evidence exists, response must be refusal=True with empty lists."""
        await _seed_acceptance_corpus(db_session)

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "张仲景方剂来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["refusal"] is True
        assert data["citations"] == []
        assert data["kg_paths"] == []
        assert data["evidence_chain"] == []


# ============================================================
# P0-1: MultiHopPathTest
# ============================================================


@pytest.mark.asyncio
class TestMultiHopPath:
    """Must return at least one path with hop_count >= 2."""

    async def test_two_hop_path_in_kg_paths(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Verified 2-hop path must appear with hop_count >= 2."""
        ents = await _seed_acceptance_corpus(db_session)

        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        await _create_and_verify_relation(
            db_session,
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            ev=_make_ev(
                ents["doc_preface"].id,
                ents["preface_chunk"].id,
                "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
            ),
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["refusal"] is False
        kg_paths = data["kg_paths"]
        two_hop = [p for p in kg_paths if p.get("hop_count", 0) >= 2]
        assert len(two_hop) > 0, f"No 2-hop path found in: {kg_paths}"


# ============================================================
# Evidence-bound assertions
# ============================================================


@pytest.mark.asyncio
class TestEvidenceBinding:
    """Every claim binds to evidence."""

    async def test_evidence_chain_claims_bound(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Evidence chain links must have claims."""
        ents = await _seed_acceptance_corpus(db_session)

        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        await _create_and_verify_relation(
            db_session,
            source_entity_type="book",
            source_entity_id=ents["book"].id,
            target_entity_type="book",
            target_entity_id=ents["suwen"].id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            ev=_make_ev(
                ents["doc_preface"].id,
                ents["preface_chunk"].id,
                "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
            ),
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )

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

    async def test_citations_from_validated_paths_only(
        self, acceptance_app, db_session: AsyncSession
    ) -> None:
        """Citations must come from validated path evidence, not raw keyword hits."""
        ents = await _seed_acceptance_corpus(db_session)

        # Create ONLY 1-hop verified path, not 2-hop. The system should refuse
        # because hop_count >= 2 is required.
        await _create_and_verify_relation(
            db_session,
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            ev=_make_ev(
                ents["doc"].id,
                ents["chunk2"].id,
                "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            ),
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_version_id=ents["v_song"].id,
            evidence_passage_id=ents["passage_song"].id,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )

        resp = await acceptance_app.post(
            "/api/v1/academic-rag/query",
            json={"query": "皇甫谧针灸思想来源是什么？"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]

        # Only 1-hop path exists → must refuse (hop_count >= 2 required)
        assert data["refusal"] is True, (
            f"Only 1-hop path with no 2-hop → must refuse. "
            f"Got refusal={data['refusal']}"
        )
        assert data["citations"] == []
        assert data["kg_paths"] == []


# ============================================================
# Unverified edge exclusion
# ============================================================


@pytest.mark.asyncio
class TestUnverifiedEdgeExclusion:
    """Unverified edges must not appear in KG paths."""

    async def test_unverified_edge_excluded_from_paths(
        self, db_session: AsyncSession
    ) -> None:
        """Unverified edges must not produce paths."""
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)

        ev = _make_ev(
            ents["doc"].id,
            ents["chunk1"].id,
            "皇甫谧，字士安，安定朝那人也。",
        )
        await svc.create_relation(
            source_entity_type="person",
            source_entity_id=ents["person"].id,
            target_entity_type="book",
            target_entity_id=ents["book"].id,
            relation_type="compiled",
            evidence=ev,
        )
        # NOT verified — stays unverified

        paths = await svc.find_paths(
            source_type="person",
            source_id=ents["person"].id,
            target_type="book",
            target_id=ents["book"].id,
            max_depth=3,
            max_paths=10,
        )
        assert len(paths) == 0, (
            f"Unverified edges must be excluded from paths, got {len(paths)} paths"
        )


# ============================================================
# Fake Source + TEI + Ontology tests
# ============================================================


@pytest.mark.asyncio
class TestFakeSourceAttribution:
    """Source titles must match actual provenance."""

    async def test_no_fake_jinshu_passage_in_corpus(
        self, db_session: AsyncSession
    ) -> None:
        """The forged sentence must NOT exist in our corpus."""
        ents = await _seed_acceptance_corpus(db_session)
        doc = ents["doc"]
        forged = "其论针灸之道，以经络为本，以腧穴为标，以针刺为用"
        assert forged not in (doc.content_text or ""), (
            f"Forged pseudo-historical text found in corpus: {forged}"
        )

    async def test_chunk_content_matches_document(
        self, db_session: AsyncSession
    ) -> None:
        """Every chunk's content must be a contiguous substring of its document."""
        ents = await _seed_acceptance_corpus(db_session)
        doc = ents["doc"]
        for key in ["chunk1", "chunk2"]:
            chunk = ents[key]
            assert _is_contiguous_substring(chunk.content, doc.content_text or ""), (
                f"{key} content is not in document"
            )


@pytest.mark.asyncio
class TestTEIPersistence:
    """TEI hierarchy must persist in DB with real FK chains."""

    async def test_sentence_persistence(self, db_session: AsyncSession) -> None:
        """Sentence must persist and be retrievable."""
        ents = await _seed_acceptance_corpus(db_session)
        passage = ents["passage_song"]

        sent = TextSentence(
            passage_id=passage.id,
            order=1,
            text="黄帝问曰：针道可得闻乎？",
            xml_id="s1",
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

    async def test_token_persistence(self, db_session: AsyncSession) -> None:
        """Token must persist linked to sentence."""
        ents = await _seed_acceptance_corpus(db_session)
        passage = ents["passage_song"]

        sent = TextSentence(
            passage_id=passage.id,
            order=1,
            text="黄帝问曰：针道可得闻乎？",
            xml_id="s1",
        )
        session = db_session
        session.add(sent)
        await session.flush()

        token = TextToken(
            sentence_id=sent.id,
            order=1,
            text="黄帝",
            lemma="黄帝",
            pos="n",
            start_offset=0,
            end_offset=1,
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
                    id="v1",
                    label="版本A",
                    paragraphs=[
                        Paragraph(
                            id="p1",
                            section="卷一",
                            sentences=[
                                Sentence(
                                    id="s1",
                                    text="甲乙丙丁。",
                                    tokens=[Token(id="t1", text="甲")],
                                ),
                            ],
                        ),
                    ],
                ),
                TextVersion(
                    id="v2",
                    label="版本B",
                    paragraphs=[
                        Paragraph(
                            id="p1",
                            section="卷一",
                            sentences=[
                                Sentence(
                                    id="s1",
                                    text="甲乙丙戊。",
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
        assert len(variants) > 0

        xml = TEISerializer.to_xml(doc, variants=variants)
        assert "<app>" in xml or "<app " in xml
        assert "<lem>" in xml or "<lem " in xml
        assert "<rdg>" in xml or "<rdg " in xml


@pytest.mark.asyncio
class TestOntologyDatabaseConstraints:
    """Direct SQL INSERT of BogusType must fail at DB level."""

    async def test_bogus_entity_type_insert_fails(
        self, db_session: AsyncSession
    ) -> None:
        """INSERT entity_type='BogusType' must fail with DB constraint."""
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

    async def test_bogus_relation_type_insert_fails(
        self, db_session: AsyncSession
    ) -> None:
        """INSERT relation_type='fake_relation' must fail with DB constraint."""
        session = db_session
        with pytest.raises(Exception):
            await session.execute(
                text(
                    "INSERT INTO entity_relations "
                    "(id, source_entity_type, source_entity_id, target_entity_type, target_entity_id, "
                    "relation_type, created_at, updated_at, is_deleted) "
                    "VALUES (:id, 'person', :sid, 'book', :tid, 'fake_relation', "
                    "datetime('now'), datetime('now'), 0)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "sid": str(uuid.uuid4()),
                    "tid": str(uuid.uuid4()),
                },
            )
            await session.flush()


@pytest.mark.asyncio
class TestOntologyRejection:
    """Ontology must reject invalid types and relations at service level."""

    async def test_bogus_relation_type_rejected(self, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)
        ev = _make_ev(
            ents["doc"].id, ents["chunk1"].id, "皇甫谧，字士安，安定朝那人也。"
        )
        with pytest.raises(ValueError, match="Invalid relation_type"):
            await svc.create_relation(
                source_entity_type="person",
                source_entity_id=ents["person"].id,
                target_entity_type="book",
                target_entity_id=ents["book"].id,
                relation_type="bogus_relation",
                evidence=ev,
            )

    async def test_missing_entity_edge_fails(self, db_session: AsyncSession) -> None:
        ents = await _seed_acceptance_corpus(db_session)
        svc = GraphService(db_session)
        ev = _make_ev(
            ents["doc"].id, ents["chunk1"].id, "皇甫谧，字士安，安定朝那人也。"
        )
        with pytest.raises(ValueError, match="not found or deleted"):
            await svc.create_relation(
                source_entity_type="person",
                source_entity_id=ents["person"].id,
                target_entity_type="book",
                target_entity_id="00000000-0000-0000-0000-00000000dead",
                relation_type="authored",
                evidence=ev,
            )


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


# ============================================================
# Legacy compatibility tests
# ============================================================


@pytest.mark.asyncio
class TestTEIHierarchy:
    """TEI Document → Version → Passage hierarchy persists."""

    async def test_document_version_passage_hierarchy(
        self, db_session: AsyncSession
    ) -> None:
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
