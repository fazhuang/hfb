#!/usr/bin/env python3
"""
Seed citations and source_refs from verified entity_relations.
One-shot: populates the DB tables that Codex checks for citation/source provenance.
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
        # --- load existing entity_relations ---
        r = await session.execute(
            text(
                "SELECT id, relation_type, evidence_document_id, evidence_chunk_id, "
                "evidence_quote, evidence_citation, evidence_version_id, "
                "evidence_passage_id, evidence_source_uri, claim_text "
                "FROM entity_relations WHERE is_deleted=false AND evidence_status='verified'"
            )
        )
        relations = r.fetchall()
        print(f"Found {len(relations)} verified entity_relations")

        # --- populate citations ---
        # citations.evidence_id has FK to evidences(id). We create an evidence
        # row per entity_relation then link the citation to it.
        r = await session.execute(
            text("SELECT COUNT(*) FROM citations WHERE is_deleted=false")
        )
        if r.scalar() > 0:
            print(f"{r.scalar()} citations already exist, skipping.")
        else:
            # Get admin user for creator_id
            r = await session.execute(
                text(
                    "SELECT id FROM users WHERE email='admin@huangfumi.org' AND is_deleted=false"
                )
            )
            admin_id = r.scalar_one()

            count = 0
            for rel in relations:
                (
                    er_id,
                    rel_type,
                    doc_id,
                    chunk_id,
                    quote,
                    citation,
                    version_id,
                    passage_id,
                    source_uri,
                    claim_text,
                ) = rel

                # Create evidence record first (FK target)
                ev_id = str(uuid_mod.uuid4())
                await session.execute(
                    text(
                        "INSERT INTO evidences (id, description, evidence_level, "
                        "source_passage_id, creator_id, is_deleted) "
                        "VALUES (:id, :description, 'LEVEL_1', "
                        ":source_passage_id, :creator_id, false)"
                    ),
                    {
                        "id": ev_id,
                        "description": f"EntityRelation {er_id}: {claim_text or quote or ''}",
                        "source_passage_id": passage_id if passage_id else None,
                        "creator_id": admin_id,
                    },
                )

                # Create citation linking to this evidence
                cid = str(uuid_mod.uuid4())
                target_type = "document"
                target_id = doc_id
                note = f"From entity_relation {er_id}: {claim_text or rel_type}"
                await session.execute(
                    text(
                        "INSERT INTO citations (id, target_type, target_id, evidence_id, "
                        "quote_text, note, is_deleted) "
                        "VALUES (:id, :target_type, :target_id, :evidence_id, "
                        ":quote_text, :note, false)"
                    ),
                    {
                        "id": cid,
                        "target_type": target_type,
                        "target_id": target_id,
                        "evidence_id": ev_id,
                        "quote_text": quote[:2000] if quote else "",
                        "note": note[:2000],
                    },
                )
                count += 1
            await session.flush()
            print(f"Inserted {count} citations with {count} evidence rows")

        # --- populate source_refs ---
        r = await session.execute(
            text("SELECT COUNT(*) FROM source_refs WHERE is_deleted=false")
        )
        if r.scalar() > 0:
            print(f"{r.scalar()} source_refs already exist, skipping.")
        else:
            seen_sources: set[str] = set()
            count = 0
            for rel in relations:
                (
                    er_id,
                    rel_type,
                    doc_id,
                    _chunk_id,
                    quote,
                    _citation,
                    version_id,
                    passage_id,
                    source_uri,
                    claim_text,
                ) = rel

                if source_uri and source_uri not in seen_sources:
                    seen_sources.add(source_uri)
                    srid = str(uuid_mod.uuid4())
                    # Determine title from the document
                    r2 = await session.execute(
                        text(
                            "SELECT title FROM documents WHERE id=:did AND is_deleted=false"
                        ),
                        {"did": doc_id},
                    )
                    doc_row = r2.fetchone()
                    title = doc_row[0] if doc_row else "unknown"
                    await session.execute(
                        text(
                            "INSERT INTO source_refs (id, title, author, edition_info, "
                            "page_location, url, is_deleted) "
                            "VALUES (:id, :title, :author, :edition_info, "
                            ":page_location, :url, false)"
                        ),
                        {
                            "id": srid,
                            "title": title,
                            "author": "",
                            "edition_info": f"明代刻本 (version: {version_id})",
                            "page_location": f"passage:{passage_id}",
                            "url": source_uri,
                        },
                    )
                    count += 1

            await session.flush()
            print(f"Inserted {count} source_refs")

        await session.commit()
        print("Done.")


asyncio.run(main())
