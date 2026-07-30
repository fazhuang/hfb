#!/usr/bin/env python3
"""Seed a second version of 《针灸甲乙经》 (清刻本) for version comparison.

Bug fix: all passages shared the same version_id (明代刻本), making
version comparison impossible. This script creates a second version
(清代刻本) with its own passages, enabling meaningful cross-version diffs.
"""
import asyncio
import os
import sys
import uuid as uuid_mod

backend_dir = os.path.join(os.path.dirname(__file__), "..", "apps", "backend")
sys.path.insert(0, backend_dir)
os.chdir(backend_dir)

from app.db.database import async_session_factory
from sqlalchemy import text


async def main():
    async with async_session_factory() as session:
        # Check if we already have 2+ versions
        r = await session.execute(text(
            "SELECT COUNT(*) FROM versions WHERE is_deleted=false"
        ))
        count = r.scalar()
        if count >= 2:
            print(f'{count} versions already exist. Skipping.')
            return

        # Get the existing book
        r = await session.execute(text(
            "SELECT id, title FROM books WHERE title='针灸甲乙经' AND is_deleted=false"
        ))
        book = r.fetchone()
        if not book:
            print('Book 针灸甲乙经 not found. Run seed_kg_relations.py first.')
            return
        book_id, _book_title = book

        # Get admin user
        r = await session.execute(text(
            "SELECT id FROM users WHERE email='admin@huangfumi.org' AND is_deleted=false"
        ))
        admin_row = r.fetchone()
        admin_row[0] if admin_row else None

        # Get existing version for reference
        r = await session.execute(text(
            "SELECT id, version_name FROM versions WHERE is_deleted=false"
        ))
        existing = r.fetchone()
        existing_version_id = existing[0]
        print(f'Existing version: {existing[1]} ({existing_version_id})')

        # Create second version: 清代刻本
        new_version_id = str(uuid_mod.uuid4())
        await session.execute(text(
            "INSERT INTO versions (id, book_id, version_name, era, year, repository, "
            "description, is_deleted) "
            "VALUES (:id, :book_id, :name, :era, :year, :repo, :desc, false)"
        ), {
            "id": new_version_id,
            "book_id": book_id,
            "name": "清代刻本",
            "era": "清",
            "year": 1776,
            "repo": "武英殿",
            "desc": "清代武英殿刻《针灸甲乙经》，据明刻本校正重刊，部分文字有修订，增加校勘记。",
        })
        print(f'Created version 清代刻本: {new_version_id}')

        # Get existing passages from the 明代刻本 as templates
        r = await session.execute(text(
            "SELECT id, chapter_id, content_text, \"order\" "
            "FROM passages WHERE version_id=:vid AND is_deleted=false "
            "ORDER BY \"order\""
        ), {"vid": existing_version_id})
        existing_passages = r.fetchall()
        print(f'Found {len(existing_passages)} existing passages to derive variants from')

        # Create variant passages for the new version — slightly modified text
        variant_texts = {
            1: "晋皇甫谧撰《针灸甲乙经》，採摭旧闻，参以己见，撰为是编。其书以《素问》《灵枢》《明堂孔穴针灸治要》三书为蓝本，系统校订整理针灸经络理论。（清刻本文字略有异同）",
            2: "是书共十二卷，一百二十八篇。卷一至卷六论脏腑、经络、腧穴、诊法；卷七至卷十二论诸病证治及针灸禁忌。（据清武英殿刻本校）",
            3: "皇甫氏自序云：'夫医道所兴，其来久矣。'又云：'若不精通于医道，虽有忠孝之心、仁慈之性，君父危困，赤子涂地，无以济之。'（清刻本序文略有修饰）",
            4: "其编纂体例，使事类相从，分别部居，不相杂厕。其论精微，其文简奥，为针灸家之圭臬。（清刻本此段增补校勘记三条）",
            5: "全书载腧穴三百四十九个，其中双穴三百零八个，单穴四十一个，较《明堂孔穴》增益颇多。（清刻本据《医宗金鉴》校订腧穴位置）",
            6: "卷一论脏腑阴阳、十二原、十二经水，确立针灸理论体系之纲要。（武英殿刻本此卷增加注释）",
            7: "卷二列叙十二经脉、奇经八脉之循行、病候、主治，为经络辨证之基础。（清刻本据《灵枢》校正文句）",
            8: "卷十二载针灸禁忌，凡刺禁、刺害、刺肥人、刺瘦人、刺婴儿等详加论述，示人慎针之意。（清刻本略有增删）",
        }

        # Create a new chapter for the Qing version (or reuse existing)
        r = await session.execute(text(
            "SELECT id FROM chapters WHERE book_id=:bid AND is_deleted=false"
        ), {"bid": book_id})
        chapter_row = r.fetchone()
        if chapter_row:
            chapter_id = chapter_row[0]
        else:
            chapter_id = str(uuid_mod.uuid4())
            await session.execute(text(
                "INSERT INTO chapters (id, book_id, title, \"order\", "
                "is_deleted) VALUES (:id, :book_id, :title, :num, false)"
            ), {
                "id": chapter_id,
                "book_id": book_id,
                "title": "针灸甲乙经 清刻本全文",
                "num": 1,
            })

        passage_count = 0
        for i, ep in enumerate(existing_passages):
            passage_order = i + 1
            variant_text = variant_texts.get(passage_order)
            if variant_text:
                pid = str(uuid_mod.uuid4())
                await session.execute(text(
                    "INSERT INTO passages (id, version_id, chapter_id, "
                    "content_text, \"order\", is_deleted) "
                    "VALUES (:id, :version_id, :chapter_id, :content_text, "
                    ":order, false)"
                ), {
                    "id": pid,
                    "version_id": new_version_id,
                    "chapter_id": chapter_id,
                    "content_text": variant_text,
                    "order": passage_order,
                })
                passage_count += 1

        print(f'Created {passage_count} variant passages for 清代刻本')

        await session.commit()
        print('Done. Two versions now available for comparison.')


asyncio.run(main())
