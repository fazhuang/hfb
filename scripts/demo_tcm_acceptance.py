#!/usr/bin/env python3
"""Demo script — 验证 Academic RAG acceptance using PRODUCTION HTTP API.

P0: Must call the HTTP API, not import the service directly.
P0-3: Use real source evidence for compiled_from relationships.
P0-1: Demonstrate refusal when no verified source path exists.

1. Ontology 映射 (packages/tcm_ontology → production GRAPH_ENTITY_TYPES)
2. KG 多跳查询 + evidence verification through official verify_relation()
3. TEI 版本对比 (VersionComparator + TEISerializer)
4. Academic RAG via HTTP API with exact question
5. NO-verified-path refusal demo

Run: uv run python scripts/demo_tcm_acceptance.py

Exits non-zero if any check fails.
"""

import asyncio
import json as _json
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
_packages_dir = str(_project_root / "packages")
if _packages_dir not in sys.path:
    sys.path.insert(0, _packages_dir)

_backend_dir = str(_project_root / "apps" / "backend")
if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)

from tcm_ontology import EntityType, EntityRegistry, SchemaLoader  # noqa: E402
from tcm_tei import (  # noqa: E402
    Token,
    Sentence,
    Paragraph,
    TextVersion,
    Document,
    VersionComparator,
    TEISerializer,
)

EXIT = 0


def fail(msg: str) -> None:
    global EXIT
    print(f"\nFAIL: {msg}")
    EXIT = 1


def sep(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ============================================================
# 验收 1: Ontology 实体类型映射
# ============================================================
sep("验收 1: Ontology — 实体类型 + JSON-LD + Production Bridge")

reg = EntityRegistry()
print(f"已注册类型: {[t.value for t in reg.list_types()]}")

person_schema = reg.get(EntityType.PERSON)
print(f"Person 属性: {person_schema.properties[:5]}...")
print(
    f"Person 有效关系: {[(r.name, r.target_type.value) for r in person_schema.relations]}"
)

loader = SchemaLoader()
jsonld = loader.dumps([person_schema])
print(f"JSON-LD 序列化: @context={jsonld['@context']['tcm']}")

reg.validate(
    EntityType.PERSON,
    {
        "name": "皇甫谧",
        "name_zh": "皇甫谧",
        "courtesy_name": "士安",
        "pseudonym": "玄晏先生",
        "dynasty": "魏晋",
        "birth_year": 215,
        "death_year": 282,
        "birth_place": "安定朝那",
        "biography": "魏晋医学家，著《针灸甲乙经》",
        "expertise": "针灸",
        "notable_works": "针灸甲乙经",
    },
)
print("皇甫谧 实体验证通过 ✓")

from app.models.graph import GRAPH_ENTITY_TYPES, GRAPH_RELATION_TYPES  # noqa: E402

canonical = {et.value.lower() for et in EntityType}
for ct in ("person", "text", "herb", "prescription", "meridian", "symptom"):
    in_production = ct in GRAPH_ENTITY_TYPES
    print(
        f"  {ct} in production GRAPH_ENTITY_TYPES: {'✓' if in_production else 'FAIL'}"
    )
    if not in_production:
        fail(f"{ct} must be in production GRAPH_ENTITY_TYPES")

# Verify compiled_from is in ontology
if "compiled_from" not in GRAPH_RELATION_TYPES:
    fail("compiled_from must be in GRAPH_RELATION_TYPES")
else:
    print("  compiled_from in GRAPH_RELATION_TYPES: ✓")

print(f"Production relation types: {sorted(GRAPH_RELATION_TYPES)}")
print("Ontology → Production bridge verified ✓")


# ============================================================
# 验收 2: KG 多跳查询 + verified evidence (production GraphService)
# ============================================================
sep("验收 2: Knowledge Graph — Production GraphService 多跳查询 + verify_relation()")


async def _seed_reviewer(session):
    """P0-3: seed a reviewer user + role + permission for verify_relation."""
    from app.models.user import User, Role  # noqa: E402
    from app.models.user import Permission as PermModel  # noqa: E402
    from app.models.user import user_role as ur_table  # noqa: E402
    from app.models.user import role_permission as rp_table  # noqa: E402

    reviewer = User(
        id="demo-reviewer",
        username="demo-reviewer",
        email="reviewer@demo.test",
        hashed_password="demo",
        is_active=True,
    )
    session.add(reviewer)
    await session.flush()
    review_role = Role(
        id="demo-review-role",
        name="Reviewer",
        description="Demo",
        is_system=True,
    )
    session.add(review_role)
    await session.flush()
    review_perm = PermModel(id="demo-graph-review", resource="graph", action="review")
    session.add(review_perm)
    await session.flush()
    await session.execute(
        ur_table.insert().values(user_id=reviewer.id, role_id=review_role.id)
    )
    await session.execute(
        rp_table.insert().values(role_id=review_role.id, permission_id=review_perm.id)
    )
    await session.flush()


async def demo_kg():
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )  # noqa: E402
    from app.db.base import Base  # noqa: E402
    from app.models.person import Person  # noqa: E402
    from app.models.book import Book  # noqa: E402
    from app.models.document import Document  # noqa: E402
    from app.models.document_chunk import DocumentChunk  # noqa: E402
    from app.models.version import Version  # noqa: E402
    from app.models.passage import Passage  # noqa: E402
    from app.models.chapter import Chapter  # noqa: E402
    from app.services.graph_service import GraphService  # noqa: E402
    from app.schemas.graph import GraphEvidence  # noqa: E402

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        await _seed_reviewer(session)

        # Seed data
        person = Person(
            name="皇甫谧",
            name_zh="皇甫谧",
            courtesy_name="士安",
            dynasty="魏晋",
            birth_year=215,
            death_year=282,
            expertise="针灸",
        )
        session.add(person)
        await session.flush()

        book = Book(
            title="针灸甲乙经", dynasty="魏晋", category="针灸", author_id=person.id
        )
        session.add(book)
        await session.flush()

        suwen = Book(title="素问", dynasty="汉", category="医经")
        session.add(suwen)
        await session.flush()

        v_song = Version(
            book_id=book.id,
            version_name="宋本",
            era="北宋",
            repository="中国国家图书馆",
        )
        session.add(v_song)
        await session.flush()

        chapter = Chapter(book_id=book.id, title="卷一", order=1)
        session.add(chapter)
        await session.flush()

        passage = Passage(
            chapter_id=chapter.id,
            version_id=v_song.id,
            order=1,
            content_text="黄帝问曰：针道可得闻乎？岐伯对曰：可得闻也。",
        )
        session.add(passage)
        await session.flush()

        # Document: 《晋书·皇甫谧传》— real biographical content
        doc_bio = Document(
            title="晋书·皇甫谧传",
            dynasty="唐",
            category="史书",
            content_text="皇甫谧，字士安，安定朝那人也。撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        session.add(doc_bio)
        await session.flush()

        chunk_bio = DocumentChunk(
            document_id=doc_bio.id,
            chunk_index=0,
            content="皇甫谧，字士安，安定朝那人也。撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            token_count=30,
        )
        session.add(chunk_bio)
        await session.flush()

        # Document: 《黄帝三部针灸甲乙经序》— real preface content about sources
        doc_preface = Document(
            title="黄帝三部针灸甲乙经序",
            dynasty="魏晋",
            category="序跋",
            content_text="乃撰集三部，使事类相从。按《七略》艺文志，《黄帝内经》十八卷，今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。又有《明堂孔穴针灸治要》，皆黄帝岐伯遗事也。",
        )
        session.add(doc_preface)
        await session.flush()

        chunk_preface = DocumentChunk(
            document_id=doc_preface.id,
            chunk_index=0,
            content="乃撰集三部，使事类相从。按《七略》艺文志，《黄帝内经》十八卷，今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。又有《明堂孔穴针灸治要》，皆黄帝岐伯遗事也。",
            token_count=60,
        )
        session.add(chunk_preface)
        await session.flush()

        def make_ev(doc_id: str, chunk_id: str, quote: str) -> GraphEvidence:
            return GraphEvidence(
                document_id=doc_id,
                chunk_id=chunk_id,
                exact_quote=quote,
                citation=f"[{doc_id}:{chunk_id}]",
            )

        svc = GraphService(session)

        # P0-2: Create and verify using official API only
        # Edge 1: 皇甫谧 --compiled--> 针灸甲乙经
        ev1 = make_ev(
            doc_bio.id,
            chunk_bio.id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        r1 = await svc.create_relation(
            source_entity_type="person",
            source_entity_id=person.id,
            target_entity_type="book",
            target_entity_id=book.id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            evidence=ev1,
        )
        print(f"Edge 1 created: {r1.relation_type} (status={r1.evidence_status})")

        # Verify through official API
        r1 = await svc.verify_relation(
            relation_id=r1.id,
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_document_id=ev1.document_id,
            evidence_version_id=v_song.id,
            evidence_passage_id=passage.id,
            evidence_chunk_id=ev1.chunk_id,
            evidence_quote=ev1.exact_quote,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
            verified_by="demo-reviewer",
        )
        print(
            f"Edge 1 verified: status={r1.evidence_status}, verified_by={r1.verified_by}"
        )

        # Edge 2: 针灸甲乙经 --compiled_from--> 素问
        # P0-3: Use REAL preface evidence, NOT biographical quote
        ev2 = make_ev(
            doc_preface.id,
            chunk_preface.id,
            "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
        )
        r2 = await svc.create_relation(
            source_entity_type="book",
            source_entity_id=book.id,
            target_entity_type="book",
            target_entity_id=suwen.id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            evidence=ev2,
        )
        print(f"Edge 2 created: {r2.relation_type} (status={r2.evidence_status})")

        r2 = await svc.verify_relation(
            relation_id=r2.id,
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_document_id=ev2.document_id,
            evidence_version_id=v_song.id,
            evidence_passage_id=passage.id,
            evidence_chunk_id=ev2.chunk_id,
            evidence_quote=ev2.exact_quote,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
            verified_by="demo-reviewer",
        )
        print(
            f"Edge 2 verified: status={r2.evidence_status}, verified_by={r2.verified_by}"
        )

        # Check all verified relations have complete provenance
        validated = await svc.get_validated_relations_for_entity("person", person.id)
        print(f"\nValidated relations for 皇甫谧: {len(validated)}")
        for er, _ev in validated:
            assert er.evidence_source_uri, "source_uri must be set"
            assert er.verified_by, "verified_by must be set"
            assert er.verified_at, "verified_at must be set"
            assert er.claim_text, "claim_text must be set"
            assert not er.evidence_source_uri.startswith("document:"), (
                "source_uri must be real URI"
            )
            print(
                f"  {er.relation_type}: source_uri={er.evidence_source_uri}, "
                f"verified_by={er.verified_by}"
            )

        # 1-hop
        path1 = await svc.find_path(
            source_type="person",
            source_id=person.id,
            target_type="book",
            target_id=book.id,
            max_depth=3,
        )
        if path1 is None:
            fail("1-hop path not found")
            return
        print(
            f"\n1-hop: {path1.nodes[0].label} --[{path1.edges[0].relation_type}]--> {path1.nodes[1].label}"
        )

        # 2-hop: person → suwen
        paths = await svc.find_paths(
            source_type="person",
            source_id=person.id,
            target_type="book",
            target_id=suwen.id,
            max_depth=3,
            max_paths=10,
        )
        print(f"\n2-hop paths found: {len(paths)}")
        if len(paths) == 0:
            fail("No 2-hop path found")
            return
        for p in paths:
            hops = " → ".join(e.relation_type for e in p.edges)
            labels = " → ".join(n.label for n in p.nodes)
            print(f"  {labels}")
            print(f"  hops: {hops} | length: {p.length}")
            for e in p.edges:
                print(
                    f"    edge evidence: {e.evidence.citation if e.evidence else 'NONE'}"
                )

        print("\n✓ Production GraphService multi-hop + verify_relation verified")

    await engine.dispose()


asyncio.run(demo_kg())
if EXIT:
    sys.exit(EXIT)


# ============================================================
# 验收 3: TEI 文献版本对比
# ============================================================
sep("验收 3: TEI 文献 — 版本对比 (异文系统) + Production Bridge")

doc = Document(
    id="zhenjiu_jia_yi_jing",
    title="针灸甲乙经",
    versions=[
        TextVersion(
            id="song_ben",
            label="宋本",
            paragraphs=[
                Paragraph(
                    id="para_1",
                    section="卷一·序",
                    sentences=[
                        Sentence(
                            id="s1",
                            text="黄帝问曰：针道可得闻乎？",
                            tokens=[Token(id="t1", text="黄")],
                        ),
                        Sentence(
                            id="s2",
                            text="岐伯对曰：可得闻也。",
                            tokens=[Token(id="t2", text="岐")],
                        ),
                    ],
                ),
            ],
        ),
        TextVersion(
            id="ming_ben",
            label="明赵府居敬堂刊本",
            paragraphs=[
                Paragraph(
                    id="para_1",
                    section="卷一·序",
                    sentences=[
                        Sentence(
                            id="s1",
                            text="黄帝问曰：针道可得闻乎？",
                            tokens=[Token(id="t1", text="黄")],
                        ),
                        Sentence(
                            id="s2",
                            text="岐伯对曰：可得闻耳。",
                            tokens=[Token(id="t2", text="岐")],
                        ),
                    ],
                ),
            ],
        ),
    ],
)

print(f"文献: {doc.title}")
print(f"版本: {[v.label for v in doc.versions]}")

comparator = VersionComparator()
variants = comparator.diff(doc.versions[0], doc.versions[1])

print(f"\n异文数: {len(variants)}")
if len(variants) == 0:
    fail("No variants detected")
else:
    for v in variants:
        print(f"\n  位置: {v.location}")
        for ver_id, text in v.readings.items():
            ver_label = (
                doc.get_version(ver_id).label if doc.get_version(ver_id) else ver_id
            )
            print(f"    [{ver_label}]: {text}")

xml = TEISerializer.to_xml(doc, variants=variants)
print(f"\nTEI XML 长度: {len(xml)} 字符")

has_app = ("<app>" in xml) or ("<app " in xml)
has_lem = ("<lem>" in xml) or ("<lem " in xml)
has_rdg = ("<rdg>" in xml) or ("<rdg " in xml)
print(
    f"TEI XML: <app>={'✓' if has_app else 'FAIL'} <lem>={'✓' if has_lem else 'FAIL'} <rdg>={'✓' if has_rdg else 'FAIL'}"
)

if not (has_app and has_lem and has_rdg):
    fail("TEI XML missing required apparatus structure (app/lem/rdg)")

print("\n✓ TEI version comparison verified")


# ============================================================
# 验收 4: Academic RAG via HTTP API (P0: production path)
# ============================================================
sep("验收 4: Academic RAG — Exact Question via HTTP API")


async def demo_academic_rag_http():
    """P0: Call the HTTP API, not import the service directly.

    P0-1 fix: seed, dependency_overrides, HTTP requests ALL inside the same
    session context. Use StaticPool for shared in-memory SQLite.
    """
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )  # noqa: E402
    from sqlalchemy.pool import StaticPool  # noqa: E402
    from app.db.base import Base  # noqa: E402
    from app.models.person import Person  # noqa: E402
    from app.models.book import Book  # noqa: E402
    from app.models.document import Document  # noqa: E402
    from app.models.document_chunk import DocumentChunk  # noqa: E402
    from app.models.version import Version  # noqa: E402
    from app.models.passage import Passage  # noqa: E402
    from app.models.chapter import Chapter  # noqa: E402
    from app.services.graph_service import GraphService  # noqa: E402
    from app.schemas.graph import GraphEvidence  # noqa: E402
    from main import app as fastapi_app  # noqa: E402
    from app.db.database import get_session  # noqa: E402
    from app.middleware import auth as auth_mod  # noqa: E402
    from httpx import ASGITransport, AsyncClient  # noqa: E402

    # Use StaticPool so the same in-memory SQLite connection is shared
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        await _seed_reviewer(session)

        # Seed data with real sources
        person = Person(
            name="皇甫谧",
            name_zh="皇甫谧",
            dynasty="魏晋",
            biography="魏晋医学家，著《针灸甲乙经》。",
            expertise="针灸",
        )
        session.add(person)
        await session.flush()

        book = Book(
            title="针灸甲乙经",
            dynasty="魏晋",
            category="针灸",
            author_id=person.id,
            abstract="针灸学经典著作，皇甫谧编纂。",
        )
        session.add(book)
        await session.flush()

        suwen = Book(
            title="素问",
            dynasty="汉",
            category="医经",
            abstract="《黄帝内经素问》，针灸甲乙经主要来源之一。",
        )
        session.add(suwen)
        await session.flush()

        v_song = Version(
            book_id=book.id,
            version_name="宋本",
            era="北宋",
            repository="中国国家图书馆",
        )
        session.add(v_song)
        await session.flush()

        chapter = Chapter(book_id=book.id, title="卷一", order=1)
        session.add(chapter)
        await session.flush()

        passage = Passage(
            chapter_id=chapter.id,
            version_id=v_song.id,
            order=1,
            content_text="黄帝问曰：针道可得闻乎？岐伯对曰：可得闻也。",
        )
        session.add(passage)
        await session.flush()

        # Real biography document
        doc_bio = Document(
            title="晋书·皇甫谧传",
            dynasty="唐",
            category="史书",
            content_text="皇甫谧，字士安，安定朝那人也。撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            source_url="https://ctext.org/jinshu/huangfu-mi-zhuan",
        )
        session.add(doc_bio)
        await session.flush()

        chunk_bio = DocumentChunk(
            document_id=doc_bio.id,
            chunk_index=0,
            content="皇甫谧，字士安，安定朝那人也。撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
            token_count=30,
        )
        session.add(chunk_bio)
        await session.flush()

        # Real preface document (the actual source evidence for compiled_from)
        doc_preface = Document(
            title="黄帝三部针灸甲乙经序",
            dynasty="魏晋",
            category="序跋",
            content_text="乃撰集三部，使事类相从。按《七略》艺文志，《黄帝内经》十八卷，今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。又有《明堂孔穴针灸治要》，皆黄帝岐伯遗事也。",
            source_url="https://ctext.org/zhenjiu-jiayi-jing/xu",
        )
        session.add(doc_preface)
        await session.flush()

        chunk_preface = DocumentChunk(
            document_id=doc_preface.id,
            chunk_index=0,
            content="乃撰集三部，使事类相从。按《七略》艺文志，《黄帝内经》十八卷，今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。又有《明堂孔穴针灸治要》，皆黄帝岐伯遗事也。",
            token_count=60,
        )
        session.add(chunk_preface)
        await session.flush()

        def make_ev(doc_id: str, chunk_id: str, quote: str) -> GraphEvidence:
            return GraphEvidence(
                document_id=doc_id,
                chunk_id=chunk_id,
                exact_quote=quote,
                citation=f"[{doc_id}:{chunk_id}]",
            )

        svc = GraphService(session)

        # P0-2: Create and verify via official API
        ev1 = make_ev(
            doc_bio.id,
            chunk_bio.id,
            "撰《针灸甲乙经》及《帝王世纪》《高士传》《逸士传》《列女传》等。",
        )
        r1 = await svc.create_relation(
            source_entity_type="person",
            source_entity_id=person.id,
            target_entity_type="book",
            target_entity_id=book.id,
            relation_type="compiled",
            description="皇甫谧编撰《针灸甲乙经》",
            evidence=ev1,
        )
        await svc.verify_relation(
            relation_id=r1.id,
            claim_text="皇甫谧编撰《针灸甲乙经》",
            evidence_document_id=ev1.document_id,
            evidence_version_id=v_song.id,
            evidence_passage_id=passage.id,
            evidence_chunk_id=ev1.chunk_id,
            evidence_quote=ev1.exact_quote,
            evidence_source_uri="https://ctext.org/jinshu/huangfu-mi-zhuan",
            verified_by="demo-reviewer",
        )

        # P0-3: Second-hop uses real preface evidence, NOT biographical quote
        ev2 = make_ev(
            doc_preface.id,
            chunk_preface.id,
            "今有《针经》九卷、《素问》九卷，二九十八卷，即《内经》也。",
        )
        r2 = await svc.create_relation(
            source_entity_type="book",
            source_entity_id=book.id,
            target_entity_type="book",
            target_entity_id=suwen.id,
            relation_type="compiled_from",
            description="针灸甲乙经编纂依据素问",
            evidence=ev2,
        )
        await svc.verify_relation(
            relation_id=r2.id,
            claim_text="针灸甲乙经以《素问》为主要编纂依据",
            evidence_document_id=ev2.document_id,
            evidence_version_id=v_song.id,
            evidence_passage_id=passage.id,
            evidence_chunk_id=ev2.chunk_id,
            evidence_quote=ev2.exact_quote,
            evidence_source_uri="https://ctext.org/zhenjiu-jiayi-jing/xu",
            verified_by="demo-reviewer",
        )

        await session.flush()

        # --- ALL HTTP work INSIDE the session context ---
        async def override_get_session():
            yield session

        async def override_get_current_user():
            return "demo-user"

        async def override_get_auth_service():
            class FakeAuth:
                async def has_permission(self, *a, **kw):
                    return True

                async def has_any_permission(self, *a, **kw):
                    return True

            return FakeAuth()

        fastapi_app.dependency_overrides[get_session] = override_get_session
        fastapi_app.dependency_overrides[auth_mod.get_current_user] = (
            override_get_current_user
        )
        fastapi_app.dependency_overrides[auth_mod.get_auth_service] = (
            override_get_auth_service
        )

        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                exact_question = "皇甫谧针灸思想来源是什么？"
                resp = await client.post(
                    "/api/v1/academic-rag/query",
                    json={"query": exact_question},
                )
                assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
                body = resp.json()
                data = body["data"]

                # Print FULL JSON (not truncated)
                print("\n--- Full Response JSON ---")
                print(_json.dumps(body, ensure_ascii=False, indent=2))

                print(f"\nQuery: {data['query']}")
                print(f"Refusal: {data['refusal']}")
                print(f"Answer:\n{data['answer']}")
                print(f"Citations: {len(data['citations'])}")
                print(f"KG paths: {len(data['kg_paths'])}")
                print(f"Evidence chain: {len(data['evidence_chain'])}")
                print(f"Corpus SHA256: {data['corpus_sha256']}")
                print(f"Output SHA256: {data['output_sha256']}")

                # P0: Verify refusal=false
                if data["refusal"]:
                    fail("refusal=True on a fully-verified 2-hop path — must be False")
                    return
                print("✓ refusal=False")

                # P0: Verify citations non-empty
                if not data["citations"]:
                    fail("citations is empty on success path")
                    return
                print("✓ citations non-empty")

                # P0: Verify at least one 2-hop path
                two_hop = [p for p in data["kg_paths"] if p.get("hop_count", 0) >= 2]
                if not two_hop:
                    fail(
                        f"No 2-hop path (got hop_counts: {[p.get('hop_count') for p in data['kg_paths']]})"
                    )
                    return
                print(f"✓ At least one 2-hop path: hop_count={two_hop[0]['hop_count']}")

                # P0: Verify evidence_chain complete
                if not data["evidence_chain"]:
                    fail("evidence_chain is empty on success path")
                    return
                print("✓ evidence_chain complete")

                # P0: Verify answer contains source text names
                answer = data["answer"]
                has_source = any(
                    name in answer for name in ["素问", "针经", "明堂孔穴针灸治要"]
                )
                if not has_source:
                    fail(
                        f"Answer must mention evidence-supported source works. Got: {answer[:300]}"
                    )
                    return
                print("✓ answer contains real source text names")

                # P0: Verify raw content determinism
                resp2 = await client.post(
                    "/api/v1/academic-rag/query",
                    json={"query": exact_question},
                )
                assert resp2.status_code == 200
                if resp.content != resp2.content:
                    fail("Raw HTTP response.content not deterministic on repeat call")
                print("✓ raw content deterministic")

                if EXIT == 0:
                    print("\n✓ Academic RAG HTTP acceptance verified")

        finally:
            fastapi_app.dependency_overrides.clear()

    await engine.dispose()


asyncio.run(demo_academic_rag_http())
if EXIT:
    sys.exit(EXIT)


# ============================================================
# 验收 5: No-verified-path refusal demo (P0-1)
# ============================================================
sep("验收 5: Refusal Demo — Chunks exist but NO verified source path")


async def demo_refusal():
    """P0-1: Demonstrate refusal when chunks match but no verified KG path."""
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )  # noqa: E402
    from sqlalchemy.pool import StaticPool  # noqa: E402
    from app.db.base import Base  # noqa: E402
    from app.models.person import Person  # noqa: E402
    from app.models.book import Book  # noqa: E402
    from app.models.document import Document  # noqa: E402
    from app.models.document_chunk import DocumentChunk  # noqa: E402
    from main import app as fastapi_app  # noqa: E402
    from app.db.database import get_session  # noqa: E402
    from app.middleware import auth as auth_mod  # noqa: E402
    from httpx import ASGITransport, AsyncClient  # noqa: E402

    engine = create_async_engine(
        "sqlite+aiosqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        # Seed: person + book + chunks (keywords WILL match)
        # But NO KG edges → must refuse
        person = Person(
            name="皇甫谧",
            name_zh="皇甫谧",
            dynasty="魏晋",
            biography="魏晋医学家",
            expertise="针灸",
        )
        session.add(person)
        await session.flush()

        book = Book(
            title="针灸甲乙经", dynasty="魏晋", category="针灸", author_id=person.id
        )
        session.add(book)
        await session.flush()

        # Chunk exists with matching keywords
        doc = Document(
            title="晋书·皇甫谧传",
            dynasty="唐",
            category="史书",
            content_text="皇甫谧撰《针灸甲乙经》等书。",
        )
        session.add(doc)
        await session.flush()

        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=0,
            content="皇甫谧撰《针灸甲乙经》等书。",
            token_count=10,
        )
        session.add(chunk)
        await session.flush()

        # --- ALL HTTP work INSIDE the session context ---
        async def override_get_session():
            yield session

        async def override_get_current_user():
            return "demo-user"

        async def override_get_auth_service():
            class FakeAuth:
                async def has_permission(self, *a, **kw):
                    return True

                async def has_any_permission(self, *a, **kw):
                    return True

            return FakeAuth()

        fastapi_app.dependency_overrides[get_session] = override_get_session
        fastapi_app.dependency_overrides[auth_mod.get_current_user] = (
            override_get_current_user
        )
        fastapi_app.dependency_overrides[auth_mod.get_auth_service] = (
            override_get_auth_service
        )

        try:
            transport = ASGITransport(app=fastapi_app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/academic-rag/query",
                    json={"query": "皇甫谧针灸思想来源是什么？"},
                )
                assert resp.status_code == 200
                body = resp.json()
                data = body["data"]

                # Print full refusal JSON
                print("\n--- Full Refusal Response JSON ---")
                print(_json.dumps(body, ensure_ascii=False, indent=2))

                print(f"\nRefusal: {data['refusal']}")
                print(f"Answer: {data['answer']}")
                print(f"Citations: {data['citations']}")
                print(f"KG paths: {data['kg_paths']}")
                print(f"Evidence chain: {data['evidence_chain']}")

                # Must refuse
                if not data["refusal"]:
                    fail(
                        "Must refuse when chunks exist but no verified path. Got refusal=False"
                    )
                    return
                print("✓ refusal=True")

                # All lists must be empty
                if data["citations"]:
                    fail(
                        f"Citations must be empty on refusal, got {len(data['citations'])}"
                    )
                    return
                if data["kg_paths"]:
                    fail(
                        f"KG paths must be empty on refusal, got {len(data['kg_paths'])}"
                    )
                    return
                if data["evidence_chain"]:
                    fail(
                        f"Evidence chain must be empty on refusal, got {len(data['evidence_chain'])}"
                    )
                    return
                print("✓ All lists empty on refusal")

                print("\n✓ Refusal demo verified")

        finally:
            fastapi_app.dependency_overrides.clear()

    await engine.dispose()


asyncio.run(demo_refusal())


# ============================================================
# 验收总结
# ============================================================
sep("验收总结")

if EXIT:
    print("\nFAIL — 存在未通过的检查项")
    sys.exit(EXIT)

print("""
✓ 1. Ontology → Production bridge: compiled_from in GRAPH_RELATION_TYPES
✓ 2. KG multi-hop: verified via official verify_relation() API
     - 1-hop + 2-hop with real preface evidence (not biographical quote)
     - Each verified relation has complete provenance (source_uri, verified_by, verified_at, claim_text)
✓ 3. TEI version comparison: Variant detection + TEI XML (app/lem/rdg)
✓ 4. Academic RAG via HTTP API:
     - refusal=False with 2-hop path
     - answer contains real source text names
     - Full JSON printed, not truncated
✓ 5. Refusal demo: chunks match keywords but no verified path → refusal=True
     - All lists empty

Production execution chain:
  HTTP API → ChineseQueryPlanner → corpus retrieval → GraphService multi-hop
  → evidence validation → P0-1 refusal state machine → strict response schema
""")
sys.exit(0)
