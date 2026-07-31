"""Seed verified EntityRelations for the Huangfu Mi KG backbone."""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
import uuid as uuid_mod

from app.db.database import async_session_factory
from app.schemas.graph import GraphEvidence
from app.services.graph_service import GraphService
from sqlalchemy import text


async def main():
    async with async_session_factory() as session:
        gs = GraphService(session)

        # --- fetch entity IDs ---
        r = await session.execute(
            text("SELECT id FROM persons WHERE name='皇甫谧' AND is_deleted=false")
        )
        huangfu_mi_id = r.scalar_one()

        r = await session.execute(
            text("SELECT id FROM books WHERE title='针灸甲乙经' AND is_deleted=false")
        )
        jiayi_book_id = r.scalar_one()

        r = await session.execute(
            text(
                "SELECT id FROM documents WHERE title='针灸甲乙经' AND is_deleted=false LIMIT 1"
            )
        )
        r.scalar_one()

        r = await session.execute(
            text("SELECT id FROM versions WHERE is_deleted=false")
        )
        version_id = r.scalar_one()

        r = await session.execute(
            text(
                "SELECT id FROM users WHERE email='admin@huangfumi.org' AND is_deleted=false"
            )
        )
        admin_id = r.scalar_one()

        # Check existing
        r = await session.execute(
            text("SELECT COUNT(*) FROM entity_relations WHERE is_deleted=false")
        )
        if r.scalar() > 0:
            print(f"{r.scalar()} relations already exist. Skipping.")
            return

        # --- chunk evidence ---
        r = await session.execute(
            text(
                "SELECT dc.id, dc.document_id, dc.passage_id FROM document_chunks dc "
                "WHERE dc.is_deleted=false AND dc.content LIKE '%皇甫谧採摭旧闻%'"
            )
        )
        c1 = r.fetchone()

        r = await session.execute(
            text(
                "SELECT dc.id, dc.document_id, dc.passage_id FROM document_chunks dc "
                "WHERE dc.is_deleted=false AND dc.content LIKE '%三书为蓝本%'"
            )
        )
        c2 = r.fetchone()

        r = await session.execute(
            text(
                "SELECT dc.id, dc.document_id, dc.passage_id FROM document_chunks dc "
                "WHERE dc.is_deleted=false AND dc.content LIKE '%使事类相从%'"
            )
        )
        c3 = r.fetchone()

        r = await session.execute(
            text(
                "SELECT dc.id, dc.document_id, dc.passage_id FROM document_chunks dc "
                "WHERE dc.is_deleted=false AND dc.content LIKE '%349个腧穴%'"
            )
        )
        c4 = r.fetchone()

        r = await session.execute(
            text(
                "SELECT dc.id, dc.document_id, dc.passage_id FROM document_chunks dc "
                "WHERE dc.is_deleted=false AND dc.content LIKE '%经脉理论与脏腑辨证%'"
            )
        )
        c5 = r.fetchone()

        src_uri = "https://ctext.org/library.pl?if=gb&res=77431"

        # --- Rel 1: 皇甫谧 --compiled--> 针灸甲乙经 ---
        q1 = "皇甫谧採摭旧闻，撰为针灸甲乙经，以明经络腧穴病候治疗之次第。"
        ev1 = GraphEvidence(
            document_id=c1[1],
            chunk_id=c1[0],
            exact_quote=q1,
            citation=f"[{c1[1]}:{c1[0]}]",
            version_id=version_id,
            passage_id=c1[2],
            source_uri=src_uri,
            claim_text="皇甫谧编撰了《针灸甲乙经》",
        )
        rel1 = await gs.create_relation(
            "person", huangfu_mi_id, "book", jiayi_book_id, "compiled", evidence=ev1
        )
        await gs.verify_relation(
            rel1.id,
            claim_text="皇甫谧编撰了《针灸甲乙经》",
            evidence_document_id=c1[1],
            evidence_version_id=version_id,
            evidence_passage_id=c1[2],
            evidence_chunk_id=c1[0],
            evidence_quote=q1,
            evidence_source_uri=src_uri,
            verified_by=admin_id,
        )
        print(f"Rel1: {rel1.id} verified")

        # --- Create 黄帝内经 book ---
        r = await session.execute(
            text(
                "SELECT id FROM books WHERE title LIKE '%黄帝内经%' AND is_deleted=false"
            )
        )
        row = r.fetchone()
        if row:
            hdnj_id = row[0]
        else:
            hdnj_id = str(uuid_mod.uuid4())
            await session.execute(
                text(
                    "INSERT INTO books (id, title, dynasty, is_deleted) "
                    "VALUES (:id, :title, :dynasty, false)"
                ),
                {"id": hdnj_id, "title": "黄帝内经", "dynasty": "战国"},
            )
            await session.flush()
            print(f"Created book 黄帝内经: {hdnj_id}")

        # --- Rel 2: 针灸甲乙经 --compiled_from--> 黄帝内经 ---
        q2 = "《针灸甲乙经》共十二卷，一百二十八篇。其书以《素问》《灵枢》《明堂孔穴针灸治要》三书为蓝本，系统整理针灸经络理论。"
        ev2 = GraphEvidence(
            document_id=c2[1],
            chunk_id=c2[0],
            exact_quote=q2,
            citation=f"[{c2[1]}:{c2[0]}]",
            version_id=version_id,
            passage_id=c2[2],
            source_uri=src_uri,
            claim_text="《针灸甲乙经》以《素问》《灵枢》《明堂孔穴针灸治要》三书为蓝本",
        )
        rel2 = await gs.create_relation(
            "book", jiayi_book_id, "book", hdnj_id, "compiled_from", evidence=ev2
        )
        await gs.verify_relation(
            rel2.id,
            claim_text="《针灸甲乙经》以《素问》《灵枢》《明堂孔穴针灸治要》三书为蓝本",
            evidence_document_id=c2[1],
            evidence_version_id=version_id,
            evidence_passage_id=c2[2],
            evidence_chunk_id=c2[0],
            evidence_quote=q2,
            evidence_source_uri=src_uri,
            verified_by=admin_id,
        )
        print(f"Rel2: {rel2.id} verified")

        # --- Rel 3-5: 针灸甲乙经 --contains--> passages ---
        passages_evidence = [
            (
                c3,
                "皇甫谧以'使事类相从，删其浮辞，除其重复，论其精要'为编纂原则，使《针灸甲乙经》成为系统化的针灸学经典。",
                "《针灸甲乙经》的编纂原则为'使事类相从，删其浮辞，除其重复，论其精要'",
            ),
            (
                c4,
                "该书确定了349个腧穴的位置、主治和针刺深度，为后世针灸腧穴标准化奠定了基础。",
                "《针灸甲乙经》确定了349个腧穴的位置、主治和针刺深度",
            ),
            (
                c5,
                "《针灸甲乙经》强调经脉理论与脏腑辨证相结合，奠定了针灸治疗学的理论基础。",
                "《针灸甲乙经》强调经脉理论与脏腑辨证相结合",
            ),
        ]
        for i, (c, quote, claim) in enumerate(passages_evidence, 3):
            ev = GraphEvidence(
                document_id=c[1],
                chunk_id=c[0],
                exact_quote=quote,
                citation=f"[{c[1]}:{c[0]}]",
                version_id=version_id,
                passage_id=c[2],
                source_uri=src_uri,
                claim_text=claim,
            )
            rel = await gs.create_relation(
                "book", jiayi_book_id, "passage", c[2], "contains", evidence=ev
            )
            await gs.verify_relation(
                rel.id,
                claim_text=claim,
                evidence_document_id=c[1],
                evidence_version_id=version_id,
                evidence_passage_id=c[2],
                evidence_chunk_id=c[0],
                evidence_quote=quote,
                evidence_source_uri=src_uri,
                verified_by=admin_id,
            )
            print(f"Rel{i}: {rel.id} verified")

        await session.commit()

        # Final count
        r = await session.execute(
            text("SELECT COUNT(*) FROM entity_relations WHERE is_deleted=false")
        )
        print(f"\nTotal relations: {r.scalar()}")


asyncio.run(main())
