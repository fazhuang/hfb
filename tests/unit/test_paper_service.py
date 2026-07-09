"""Integration tests for PaperService — 8-module paper generation."""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.services.paper_service import PaperService


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
        # Pre-seed reviewer user + role for verify_relation
        from app.models.user import User, Role, Permission as PermModel
        from app.models.user import user_role as ur_table, role_permission as rp_table

        reviewer = User(
            id="test-reviewer",
            username="test-reviewer",
            email="reviewer@test.com",
            hashed_password="test",
            is_active=True,
            is_superuser=False,
        )
        session.add(reviewer)
        await session.flush()

        review_role = Role(
            id="role-reviewer",
            name="Reviewer",
            description="Test reviewer role",
            is_system=True,
        )
        session.add(review_role)
        await session.flush()

        review_perm = PermModel(
            id="perm-graph-review",
            resource="graph",
            action="review",
            description="Review graph evidence",
        )
        session.add(review_perm)
        await session.flush()

        await session.execute(
            ur_table.insert().values(user_id=reviewer.id, role_id=review_role.id)
        )
        await session.execute(
            rp_table.insert().values(
                role_id=review_role.id, permission_id=review_perm.id
            )
        )
        await session.flush()

        yield session

    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_paper_empty_graph(db_session):
    """Paper generation with no academic edges should return empty chains."""
    svc = PaperService(db_session)
    paper = await svc.generate_paper(
        source_type="person",
        source_id="nonexistent",
        target_type="book",
        target_id="nonexistent",
    )
    assert paper["paper_id"] is not None
    assert len(paper["paper_id"]) == 64  # SHA-256 hex
    assert "modules" in paper
    assert "markdown" in paper
    modules = paper["modules"]
    assert "title" in modules
    assert "abstract" in modules
    assert modules["abstract"]["path_count"] == 0


@pytest.mark.asyncio
async def test_generate_paper_produces_markdown(db_session):
    """Paper generation should produce well-formed Markdown."""
    svc = PaperService(db_session)
    paper = await svc.generate_paper(
        source_type="person",
        source_id="p1",
    )
    md = paper["markdown"]
    assert md.startswith("# ")
    assert "## 摘要" in md
    assert "## 证据链" in md
    assert "## 讨论与冲突检测" in md
    assert "## 方法论附注" in md


@pytest.mark.asyncio
async def test_generate_paper_deterministic(db_session):
    """Same inputs should produce the same paper_id (SHA-256)."""
    svc1 = PaperService(db_session)
    svc2 = PaperService(db_session)
    paper1 = await svc1.generate_paper(
        source_type="person",
        source_id="p1",
        target_type="book",
        target_id="b1",
    )
    paper2 = await svc2.generate_paper(
        source_type="person",
        source_id="p1",
        target_type="book",
        target_id="b1",
    )
    assert paper1["paper_id"] == paper2["paper_id"]


# ── Blocking-item: PaperService inherits multi_hop safety boundary ──


@pytest.mark.asyncio
async def test_paper_service_excludes_tampered_relation(db_session):
    """PaperService must not write tampered relations into evidence_chains."""
    from app.models.book import Book
    from app.models.chapter import Chapter
    from app.models.document import Document
    from app.models.document_chunk import DocumentChunk
    from app.models.passage import Passage
    from app.models.person import Person
    from app.models.version import Version
    from app.services.graph_service import GraphService
    from app.schemas.graph import GraphEvidence

    # Seed entities
    person = Person(id="p-ps-1", name="作者")
    book1 = Book(id="b-ps-1", title="著作A")
    book2 = Book(id="b-ps-2", title="著作B")
    db_session.add_all([person, book1, book2])
    await db_session.flush()

    doc = Document(id="d-ps-1", title="文献", content_text="撰《著作A》及《著作B》等。")
    db_session.add(doc)
    await db_session.flush()

    chapter = Chapter(id="ch-ps-1", book_id=book1.id, title="章", order=1)
    db_session.add(chapter)
    await db_session.flush()

    version = Version(id="v-ps-1", book_id=book1.id, version_name="版本")
    db_session.add(version)
    await db_session.flush()

    passage = Passage(
        id="pass-ps-1",
        chapter_id=chapter.id,
        version_id=version.id,
        content_text="撰《著作A》及《著作B》等。",
        order=1,
    )
    db_session.add(passage)
    await db_session.flush()

    chunk = DocumentChunk(
        id="chunk-ps-1",
        document_id=doc.id,
        chunk_index=0,
        content="撰《著作A》及《著作B》等。",
        token_count=10,
        passage_id=passage.id,
    )
    db_session.add(chunk)
    await db_session.flush()

    gs = GraphService(db_session)
    ev1 = GraphEvidence(
        document_id=doc.id,
        chunk_id=chunk.id,
        exact_quote="撰《著作A》及《著作B》等。",
        citation=f"[{doc.id}:{chunk.id}]",
    )
    r1 = await gs.create_relation(
        source_entity_type="person",
        source_entity_id=person.id,
        target_entity_type="book",
        target_entity_id=book1.id,
        relation_type="compiled",
        description="hop1",
        evidence=ev1,
    )
    r1 = await gs.verify_relation(
        relation_id=r1.id,
        claim_text="作者编撰著作A",
        evidence_document_id=doc.id,
        evidence_version_id=version.id,
        evidence_passage_id=passage.id,
        evidence_chunk_id=chunk.id,
        evidence_quote="撰《著作A》及《著作B》等。",
        evidence_source_uri="https://ctext.org/test",
        verified_by="test-reviewer",
    )

    # Create r2 but tamper it: set verified status without verify_relation()
    ev2 = GraphEvidence(
        document_id=doc.id,
        chunk_id=chunk.id,
        exact_quote="撰《著作A》及《著作B》等。",
        citation=f"[{doc.id}:{chunk.id}]",
    )
    r2 = await gs.create_relation(
        source_entity_type="book",
        source_entity_id=book1.id,
        target_entity_type="book",
        target_entity_id=book2.id,
        relation_type="compiled_from",
        description="hop2",
        evidence=ev2,
    )
    # Tamper: set verified but omit verified_at (simulates DB tamper bypass)
    r2.evidence_status = "verified"
    r2.verified_by = "test-reviewer"
    # verified_at intentionally left None — query-time re-validation must catch this
    r2.claim_text = "test"
    r2.evidence_source_uri = "https://ctext.org/test2"
    r2.evidence_version_id = version.id
    r2.evidence_passage_id = passage.id
    await db_session.flush()

    paper_svc = PaperService(db_session)
    paper = await paper_svc.generate_paper(
        source_type="person",
        source_id=person.id,
        target_type="book",
        target_id=book2.id,
    )
    evidence_chains = paper["modules"]["evidence_chains"]
    # Tampered r2 is excluded → no 2-hop path
    assert len(evidence_chains) == 0, (
        f"Tampered relation must not appear in evidence_chains. Got {len(evidence_chains)}"
    )
