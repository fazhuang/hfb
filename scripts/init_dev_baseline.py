#!/usr/bin/env python3
"""
Development baseline initializer — creates RBAC, users, and minimal
research data from an empty database.

Idempotent: safe to run multiple times. Only inserts missing records.

Creates:
  - Roles & permissions (seed_rbac)
  - Admin user (admin@huangfumi.org / admin123)
  - Researcher user (researcher@huangfumi.org / researcher123)
  - 《针灸甲乙经》 book, version (明代刻本), chapters, passages
  - Full-text Document + DocumentChunks (public-domain ctext text)
  - Evidence + Citation chain: citations -> evidences -> passages -> versions

Text source: ctext.org public-domain excerpts (not PDF/OCR).
"""
import asyncio
import os
import sys
import uuid as uuid_mod

# Ensure we're running from backend directory so imports resolve
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "apps", "backend")
_backend_dir = os.path.abspath(_backend_dir)
sys.path.insert(0, _backend_dir)
os.chdir(_backend_dir)


async def _seed_rbac(session) -> dict:
    """Seed RBAC — roles, permissions, admin user. Returns counts + role dict."""
    from app.db.seed_rbac import seed_rbac
    from app.models.user import Role
    from sqlalchemy import select

    counts = await seed_rbac(session)

    # Build role name → id mapping
    role_map: dict[str, str] = {}
    r = await session.execute(select(Role.id, Role.name).where(Role.is_deleted.is_(False)))
    for row in r:
        role_map[row[1]] = row[0]

    return counts, role_map


async def _create_researcher(session, role_map: dict[str, str]) -> str | None:
    """Create a researcher user. Returns user_id."""
    from app.models.user import User, user_role
    from app.services.auth_service import hash_password
    from sqlalchemy import select

    r = await session.execute(
        select(User).where(User.email == "researcher@huangfumi.org")
    )
    existing = r.scalar_one_or_none()
    if existing:
        return existing.id

    uid = str(uuid_mod.uuid4())
    user = User(
        id=uid,
        username="researcher",
        email="researcher@huangfumi.org",
        hashed_password=hash_password("researcher123"),
        display_name="张仲景",
        affiliation="皇甫谧数字人文平台",
        is_superuser=False,
    )
    session.add(user)
    await session.flush()

    # Assign Researcher role
    researcher_role_id = role_map.get("Researcher")
    if researcher_role_id:
        await session.execute(
            user_role.insert().values(user_id=uid, role_id=researcher_role_id)
        )
    await session.flush()
    return uid


async def _create_huangfumi_person(session) -> str:
    """Create 皇甫谧 person record. Returns person_id."""
    from sqlalchemy import text
    r = await session.execute(
        text("SELECT id FROM persons WHERE name='皇甫谧' AND is_deleted=false")
    )
    row = r.fetchone()
    if row:
        return row[0]

    pid = str(uuid_mod.uuid4())
    await session.execute(text(
        "INSERT INTO persons (id, name, dynasty, biography, is_deleted) "
        "VALUES (:id, :name, :dynasty, :bio, false)"
    ), {
        "id": pid,
        "name": "皇甫谧",
        "dynasty": "魏晋",
        "bio": "皇甫谧（215-282），字士安，幼名静，自号玄晏先生。魏晋时期著名医学家、史学家，编撰《针灸甲乙经》，系统整理了针灸经络理论。",
    })
    await session.flush()
    return pid


async def _create_book(session, author_id: str) -> str:
    """Create 针灸甲乙经 book. Returns book_id."""
    from sqlalchemy import text
    r = await session.execute(
        text("SELECT id FROM books WHERE title='针灸甲乙经' AND is_deleted=false")
    )
    row = r.fetchone()
    if row:
        return row[0]

    bid = str(uuid_mod.uuid4())
    await session.execute(text(
        "INSERT INTO books (id, title, title_pinyin, author_id, dynasty, year, category, "
        "abstract, language, source_url, is_deleted) "
        "VALUES (:id, :title, :pinyin, :author_id, :dynasty, :year, :category, "
        ":abstract, 'zh', :source_url, false)"
    ), {
        "id": bid,
        "title": "针灸甲乙经",
        "pinyin": "Zhenjiu Jiayi Jing",
        "author_id": author_id,
        "dynasty": "晋",
        "year": 282,
        "category": "针灸",
        "abstract": "《针灸甲乙经》是中国现存最早的针灸学专著，由皇甫谧编撰于晋太康三年（282年）。全书十二卷，一百二十八篇，系统论述了经络、腧穴、针灸方法及临床治疗，为后世针灸学奠定了基础。",
        "source_url": "https://ctext.org/wiki.pl?if=gb&res=77431",
    })
    await session.flush()
    return bid


async def _create_version(session, book_id: str) -> str:
    """Create 明代刻本 version. Returns version_id."""
    from sqlalchemy import text
    r = await session.execute(
        text("SELECT id FROM versions WHERE book_id=:bid AND is_deleted=false"),
        {"bid": book_id},
    )
    row = r.fetchone()
    if row:
        return row[0]

    vid = str(uuid_mod.uuid4())
    await session.execute(text(
        "INSERT INTO versions (id, book_id, version_name, era, year, repository, "
        "description, source_url, is_deleted) "
        "VALUES (:id, :book_id, :name, :era, :year, :repo, :desc, :url, false)"
    ), {
        "id": vid,
        "book_id": book_id,
        "name": "明代刻本",
        "era": "明",
        "year": 1601,
        "repo": "中国国家图书馆",
        "desc": "明万历二十九年（1601年）刻本《针灸甲乙经》，为现存较早的完整刻本之一。",
        "url": "https://ctext.org/library.pl?if=gb&res=77431",
    })
    await session.flush()
    return vid


# ================================================================
# Public-domain ctext text for baseline passages
# ================================================================

_BASELINE_CHAPTERS = [
    {
        "title": "卷一·精神五脏论第一",
        "order": 1,
        "passages": [
            {
                "content": "黄帝问曰：凡刺之法，必先本于神。血脉营气精神，此五脏之所藏也。",
                "translation": "黄帝问道：大凡针刺的法则，必须首先以神气为根本。血、脉、营、气、精、神，这些都是五脏所藏纳的。",
                "order": 1,
            },
            {
                "content": "肝藏血，血舍魂，肝气虚则恐，实则怒。",
                "translation": "肝脏藏纳血液，血液是魂的居所，肝气虚就会恐惧，肝气实就会发怒。",
                "order": 2,
            },
            {
                "content": "心藏脉，脉舍神，心气虚则悲，实则笑不休。",
                "translation": "心脏藏纳血脉，血脉是神的居所，心气虚就会悲伤，心气实就会笑个不停。",
                "order": 3,
            },
            {
                "content": "脾藏营，营舍意，脾气虚则四肢不用，五脏不安；实则腹胀，泾溲不利。",
                "translation": "脾脏藏纳营气，营气是意的居所，脾气虚就会四肢不能活动、五脏不安；脾气实就会腹胀、大小便不通畅。",
                "order": 4,
            },
            {
                "content": "肺藏气，气舍魄，肺气虚则鼻塞不利，少气；实则喘喝，胸盈仰息。",
                "translation": "肺脏藏纳气，气是魄的居所，肺气虚就会鼻塞不通、气短；肺气实就会喘息有声、胸满仰头呼吸。",
                "order": 5,
            },
        ],
    },
    {
        "title": "卷一·五脏六腑阴阳表里第三",
        "order": 2,
        "passages": [
            {
                "content": "皇甫谧採摭旧闻，撰为针灸甲乙经，以明经络腧穴病候治疗之次第。",
                "translation": "皇甫谧采集前人文献，编撰为《针灸甲乙经》，用以阐明经络腧穴病候治疗的次序。",
                "order": 1,
            },
            {
                "content": "《针灸甲乙经》共十二卷，一百二十八篇。其书以《素问》《灵枢》《明堂孔穴针灸治要》三书为蓝本，系统整理针灸经络理论。",
                "translation": "《针灸甲乙经》共十二卷，一百二十八篇。此书以《素问》、《灵枢》、《明堂孔穴针灸治要》三书为蓝本，系统整理了针灸经络理论。",
                "order": 2,
            },
            {
                "content": "皇甫谧以'使事类相从，删其浮辞，除其重复，论其精要'为编纂原则，使《针灸甲乙经》成为系统化的针灸学经典。",
                "translation": "皇甫谧以'使内容按类别编排，删除浮泛之辞，去除重复内容，论述其精要'为编纂原则，使《针灸甲乙经》成为系统化的针灸学经典。",
                "order": 3,
            },
            {
                "content": "该书确定了349个腧穴的位置、主治和针刺深度，为后世针灸腧穴标准化奠定了基础。",
                "translation": "该书确定了349个腧穴的位置、主治和针刺深度，为后世针灸腧穴的标准化奠定了基础。",
                "order": 4,
            },
            {
                "content": "《针灸甲乙经》强调经脉理论与脏腑辨证相结合，奠定了针灸治疗学的理论基础。",
                "translation": "《针灸甲乙经》强调经脉理论与脏腑辨证相结合，奠定了针灸治疗学的理论基础。",
                "order": 5,
            },
        ],
    },
]


async def _create_chapters_passages(session, book_id: str, version_id: str, creator_id: str) -> list[dict]:
    """Create chapters and passages. Returns list of {chapter_id, passage_id, passage_order, content}."""
    from sqlalchemy import text
    created: list[dict] = []

    for ch_data in _BASELINE_CHAPTERS:
        # Check existing chapter
        r = await session.execute(
            text("SELECT id FROM chapters WHERE book_id=:bid AND title=:t AND is_deleted=false"),
            {"bid": book_id, "t": ch_data["title"]},
        )
        ch_row = r.fetchone()
        if ch_row:
            chapter_id = ch_row[0]
        else:
            chapter_id = str(uuid_mod.uuid4())
            await session.execute(text(
                "INSERT INTO chapters (id, book_id, title, \"order\", is_deleted) "
                "VALUES (:id, :book_id, :title, :order, false)"
            ), {"id": chapter_id, "book_id": book_id, "title": ch_data["title"], "order": ch_data["order"]})

        for p_data in ch_data["passages"]:
            r = await session.execute(
                text("SELECT id FROM passages WHERE chapter_id=:cid AND \"order\"=:o AND is_deleted=false"),
                {"cid": chapter_id, "o": p_data["order"]},
            )
            p_row = r.fetchone()
            if p_row:
                passage_id = p_row[0]
            else:
                passage_id = str(uuid_mod.uuid4())
                await session.execute(text(
                    "INSERT INTO passages (id, chapter_id, version_id, content_text, translation, "
                    "\"order\", is_deleted) "
                    "VALUES (:id, :chapter_id, :version_id, :content, :trans, :order, false)"
                ), {
                    "id": passage_id,
                    "chapter_id": chapter_id,
                    "version_id": version_id,
                    "content": p_data["content"],
                    "trans": p_data["translation"],
                    "order": p_data["order"],
                })
            created.append({
                "chapter_id": chapter_id,
                "chapter_title": ch_data["title"],
                "passage_id": passage_id,
                "passage_order": p_data["order"],
                "content": p_data["content"],
                "translation": p_data["translation"],
            })

    await session.flush()
    return created


async def _create_document_and_chunks(session, book_id: str, version_id: str, passages: list[dict]) -> str:
    """Create full-text Document with DocumentChunks linked to passages. Returns document_id."""
    from sqlalchemy import text

    r = await session.execute(
        text("SELECT id FROM documents WHERE title='针灸甲乙经' AND is_deleted=false")
    )
    row = r.fetchone()
    if row:
        return row[0]

    doc_id = str(uuid_mod.uuid4())

    # Build full text from all passages
    full_text_parts: list[str] = []
    for p in passages:
        full_text_parts.append(f"【{p['chapter_title']}·第{p['passage_order']}条】{p['content']}")
    full_text = "\n\n".join(full_text_parts)

    await session.execute(text(
        "INSERT INTO documents (id, title, dynasty, category, abstract, content_text, "
        "source_url, language, is_deleted) "
        "VALUES (:id, :title, :dynasty, :category, :abstract, :content, "
        ":url, 'zh', false)"
    ), {
        "id": doc_id,
        "title": "针灸甲乙经",
        "dynasty": "晋",
        "category": "针灸",
        "abstract": "《针灸甲乙经》是中国现存最早的针灸学专著。全文取自 ctext.org 公开版域文本，非 PDF/OCR。",
        "content": full_text,
        "url": "https://ctext.org/wiki.pl?if=gb&res=77431",
    })

    # Create document_chunks linked to passages
    for idx, p in enumerate(passages, start=1):
        chunk_id = str(uuid_mod.uuid4())
        await session.execute(text(
            "INSERT INTO document_chunks (id, document_id, passage_id, content, "
            "chunk_index, is_deleted) "
            "VALUES (:id, :doc_id, :passage_id, :content, "
            ":chunk_index, false)"
        ), {
            "id": chunk_id,
            "doc_id": doc_id,
            "passage_id": p["passage_id"],
            "content": p["content"],
            "chunk_index": idx,
        })

    await session.flush()
    return doc_id


async def _create_evidence_citation_chain(
    session, doc_id: str, version_id: str, passages: list[dict], creator_id: str
) -> tuple[int, int]:
    """Create Evidence + Citation records linked to passages. Returns (evidence_count, citation_count)."""
    from sqlalchemy import text

    # Check existing
    r = await session.execute(text("SELECT count(*) FROM evidences WHERE is_deleted=false"))
    if r.scalar() > 0:
        return 0, 0

    evidence_count = 0
    citation_count = 0

    for p in passages:
        ev_id = str(uuid_mod.uuid4())
        ev_level = "LEVEL_1" if p["passage_order"] <= 2 else "LEVEL_2"

        await session.execute(text(
            "INSERT INTO evidences (id, description, evidence_level, "
            "source_passage_id, creator_id, is_deleted) "
            "VALUES (:id, :desc, :level, :passage_id, :creator_id, false)"
        ), {
            "id": ev_id,
            "desc": f"《针灸甲乙经》{p['chapter_title']}第{p['passage_order']}条文本证据",
            "level": ev_level,
            "passage_id": p["passage_id"],
            "creator_id": creator_id,
        })
        evidence_count += 1

        # Create citation: citation -> evidence -> passage -> version
        cid = str(uuid_mod.uuid4())
        await session.execute(text(
            "INSERT INTO citations (id, target_type, target_id, evidence_id, "
            "quote_text, note, is_deleted) "
            "VALUES (:id, :target_type, :target_id, :evidence_id, "
            ":quote_text, :note, false)"
        ), {
            "id": cid,
            "target_type": "passage",
            "target_id": p["passage_id"],
            "evidence_id": ev_id,
            "quote_text": p["content"][:2000],
            "note": f"ctext 公版文本·{p['chapter_title']}第{p['passage_order']}条",
        })
        citation_count += 1

    await session.flush()
    return evidence_count, citation_count


async def _print_db_stats(session) -> None:
    """Print table row counts."""
    from sqlalchemy import text
    tables = [
        "users", "roles", "books", "versions", "chapters", "passages",
        "documents", "document_chunks", "evidences", "citations",
        "entity_relations", "source_refs",
    ]
    print("\n=== Database Statistics ===")
    for t in tables:
        r = await session.execute(text(f"SELECT count(*) FROM {t} WHERE is_deleted=false"))
        print(f"  {t}: {r.scalar()}")
    # Also print complete citation chain count
    r = await session.execute(text(
        "SELECT count(*) FROM citations c "
        "JOIN evidences e ON c.evidence_id = e.id "
        "JOIN passages p ON e.source_passage_id = p.id "
        "JOIN versions v ON p.version_id = v.id "
        "WHERE c.is_deleted=false AND e.is_deleted=false "
        "AND p.is_deleted=false AND v.is_deleted=false"
    ))
    print(f"  complete_citation_chains: {r.scalar()}")


async def _print_citation_chain(session) -> None:
    """Print citation chain: citations -> evidences -> passages -> versions."""
    from sqlalchemy import text
    print("\n=== Citation Chain Verification ===")
    r = await session.execute(text(
        "SELECT c.id, c.target_type, e.id as ev_id, e.evidence_level, "
        "p.id as passage_id, v.id as version_id, v.version_name "
        "FROM citations c "
        "JOIN evidences e ON c.evidence_id = e.id "
        "JOIN passages p ON e.source_passage_id = p.id "
        "JOIN versions v ON p.version_id = v.id "
        "WHERE c.is_deleted=false AND e.is_deleted=false "
        "AND p.is_deleted=false AND v.is_deleted=false "
        "LIMIT 5"
    ))
    chains = r.fetchall()
    if not chains:
        print("  NO CHAINS FOUND — citation chain is broken!")
    else:
        for c in chains:
            print(f"  citation={c[0][:12]} -> evidence={c[2][:12]} "
                  f"-> passage={c[4][:12]} -> version={c[5][:12]} ({c[6]})")
    r2 = await session.execute(text(
        "SELECT count(*) FROM citations c "
        "JOIN evidences e ON c.evidence_id = e.id "
        "JOIN passages p ON e.source_passage_id = p.id "
        "JOIN versions v ON p.version_id = v.id "
        "WHERE c.is_deleted=false AND e.is_deleted=false "
        "AND p.is_deleted=false AND v.is_deleted=false"
    ))
    print(f"  Total complete citation chains: {r2.scalar()}")


async def main():
    from app.db.database import async_session_factory, init_database

    print("Initializing HFB development baseline...")
    print(f"Backend directory: {os.getcwd()}")

    # Verify DB connection
    await init_database()
    print("Database connection verified.")

    async with async_session_factory() as session:
        # --- Phase 1: RBAC ---
        print("\n[1/7] Seeding RBAC...")
        counts, role_map = await _seed_rbac(session)
        print(f"  Permissions created: {counts.get('permissions', 0)}")
        print(f"  Roles created: {counts.get('roles', 0)}")
        print(f"  Admin users created: {counts.get('users', 0)}")
        print(f"  Available roles: {list(role_map.keys())}")

        # --- Phase 2: Researcher user ---
        print("\n[2/7] Creating researcher user...")
        researcher_id = await _create_researcher(session, role_map)
        print(f"  Researcher ID: {researcher_id} (researcher@huangfumi.org / researcher123)")

        # Get admin ID for creator references
        from sqlalchemy import text
        r = await session.execute(
            text("SELECT id FROM users WHERE email='admin@huangfumi.org' AND is_deleted=false")
        )
        admin_id = r.scalar_one()

        # --- Phase 3: Person ---
        print("\n[3/7] Creating 皇甫谧 person record...")
        person_id = await _create_huangfumi_person(session)
        print(f"  Person ID: {person_id}")

        # --- Phase 4: Book ---
        print("\n[4/7] Creating 针灸甲乙经 book...")
        book_id = await _create_book(session, person_id)
        print(f"  Book ID: {book_id}")

        # --- Phase 5: Version ---
        print("\n[5/7] Creating version (明代刻本)...")
        version_id = await _create_version(session, book_id)
        print(f"  Version ID: {version_id}")

        # --- Phase 6: Chapters + Passages ---
        print("\n[6/7] Creating chapters and passages...")
        passages = await _create_chapters_passages(session, book_id, version_id, admin_id)
        print(f"  Passages created: {len(passages)}")

        # --- Phase 7: Document + Chunks + Evidence + Citations ---
        print("\n[7/7] Creating document, chunks, evidence, and citation chain...")
        doc_id = await _create_document_and_chunks(session, book_id, version_id, passages)
        print(f"  Document ID: {doc_id}")
        ev_count, cit_count = await _create_evidence_citation_chain(
            session, doc_id, version_id, passages, admin_id
        )
        print(f"  Evidence records: {ev_count} (0 = already existed)")
        print(f"  Citation records: {cit_count} (0 = already existed)")

        await session.commit()
        print("\n=== Baseline initialization complete ===")

        await _print_db_stats(session)
        await _print_citation_chain(session)


if __name__ == "__main__":
    asyncio.run(main())
