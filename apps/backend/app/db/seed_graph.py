"""
Seed data for Knowledge Graph — EntityRelation records that augment
FK-derived edges with curated scholarly relationships.

FK-derived edges (auto-computed by GraphService, NOT stored here):
  - Book.author_id → Person  (fk_author)
  - Version.book_id → Book   (fk_book)
  - Passage.version_id → Version (fk_passage_to_version)

Version relations (stored in version_relations, seeded elsewhere):
  - Version → Version (derived_from, revised_from, etc.)

Sprint 3 P0: Seed relations are SOFT-DELETED if they lack structured evidence.
Only relations backed by actual corpus chunks are created as active.
"""

from __future__ import annotations

import re
from datetime import UTC

from app.models.book import Book
from app.models.document_chunk import DocumentChunk
from app.models.graph import EntityRelation
from app.models.person import Person
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def seed_graph(session: AsyncSession) -> dict[str, int]:
    """Seed knowledge graph relations.

    Sprint 3 P0:
      - Soft-deletes any existing EntityRelation that lacks structured evidence.
      - Only creates new relations when a matching corpus chunk exists.
      - Never creates evidence-free relations.

    Returns counts of operations.
    """
    from datetime import datetime

    counts: dict[str, int] = {"entity_relations_created": 0, "orphan_relations_deleted": 0}

    # ---- Step 1: Soft-delete all existing evidence-free EntityRelations ----
    # ponytail: old seed data without structured evidence gets soft-deleted,
    # not erased, so the data is recoverable if needed.
    orphan_stmt = select(EntityRelation).where(
        EntityRelation.is_deleted.is_(False),
        EntityRelation.evidence_quote.is_(None),
    )
    orphan_result = await session.execute(orphan_stmt)
    orphans = orphan_result.scalars().all()
    now = datetime.now(UTC)
    for orphan in orphans:
        orphan.is_deleted = True  # type: ignore[assignment]
        orphan.deleted_at = now  # type: ignore[assignment]
    counts["orphan_relations_deleted"] = len(orphans)
    if orphans:
        await session.flush()

    # ---- Step 2: Get seed persons, books, and chunks ----
    person_stmt = select(Person).where(Person.is_deleted.is_(False))
    p_result = await session.execute(person_stmt)
    persons: dict[str, Person] = {p.name: p for p in p_result.scalars().all()}

    book_stmt = select(Book).where(Book.is_deleted.is_(False))
    b_result = await session.execute(book_stmt)
    books: dict[str, Book] = {b.title: b for b in b_result.scalars().all()}

    # Fetch all available chunks to use as evidence
    chunk_stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.is_deleted.is_(False))
        .order_by(DocumentChunk.id)
    )
    chunk_result = await session.execute(chunk_stmt)
    all_chunks = chunk_result.scalars().all()

    # ---- Step 3: Helper that only creates relations with real corpus evidence ----

    async def _add_evidenced(
        src_type: str,
        src_name: str,
        tgt_type: str,
        tgt_name: str,
        rel_type: str,
        concepts: list[str],
        description: str = "",
    ) -> None:
        """Create a relation only if a corpus chunk contains evidence.

        Searches for a chunk that contains ALL specified concept strings,
        then creates the relation with structured evidence from that chunk.
        If no such chunk exists, the relation is NOT created.
        """
        src: Person | Book | None = None
        tgt: Person | Book | None = None

        if src_type == "person":
            src = persons.get(src_name)
        elif src_type == "book":
            src = books.get(src_name)
        else:
            return

        if tgt_type == "person":
            tgt = persons.get(tgt_name)
        elif tgt_type == "book":
            tgt = books.get(tgt_name)
        else:
            return

        if src is None or tgt is None or src.id == tgt.id:
            return

        # Check for existing active relation
        existing = await session.execute(
            select(EntityRelation).where(
                EntityRelation.source_entity_type == src_type,
                EntityRelation.source_entity_id == src.id,
                EntityRelation.target_entity_type == tgt_type,
                EntityRelation.target_entity_id == tgt.id,
                EntityRelation.relation_type == rel_type,
                EntityRelation.is_deleted.is_(False),
            )
        )
        if existing.scalar_one_or_none() is not None:
            return

        # Find a chunk that contains ALL concepts as evidence
        evidence_chunk = None
        evidence_quote = None
        for chunk in all_chunks:
            if all(concept in chunk.content for concept in concepts):
                # Find containing sentence
                sentences = re.split(r"(?<=[。！？.!?])", chunk.content)
                for sent in sentences:
                    if all(concept in sent for concept in concepts):
                        evidence_chunk = chunk
                        evidence_quote = sent.strip()
                        break
                if evidence_chunk is not None:
                    break

        if evidence_chunk is None or evidence_quote is None:
            # No corpus evidence — do NOT create the relation
            return

        er = EntityRelation(
            source_entity_type=src_type,
            source_entity_id=src.id,
            target_entity_type=tgt_type,
            target_entity_id=tgt.id,
            relation_type=rel_type,
            description=description,
            evidence_document_id=evidence_chunk.document_id,
            evidence_chunk_id=evidence_chunk.id,
            evidence_quote=evidence_quote,
            evidence_citation=f"[{evidence_chunk.document_id}:{evidence_chunk.id}]",
        )
        session.add(er)
        counts["entity_relations_created"] += 1

    # ---- Step 4: Create relations only if corpus chunks provide evidence ----

    # Person → Book (authored)
    await _add_evidenced(
        "person", "皇甫谧", "book", "针灸甲乙经", "authored",
        ["皇甫谧", "针灸甲乙经"],
        "皇甫谧编撰《针灸甲乙经》",
    )
    await _add_evidenced(
        "person", "张仲景", "book", "伤寒杂病论", "authored",
        ["张仲景", "伤寒杂病论"],
        "张仲景著《伤寒杂病论》",
    )
    await _add_evidenced(
        "person", "李时珍", "book", "本草纲目", "authored",
        ["李时珍", "本草纲目"],
        "李时珍著《本草纲目》",
    )

    # Person → Person (studied)
    await _add_evidenced(
        "person", "李时珍", "person", "张仲景", "studied",
        ["李时珍", "张仲景"],
        "李时珍对张仲景《伤寒论》有深入研究",
    )
    await _add_evidenced(
        "person", "李时珍", "person", "皇甫谧", "studied",
        ["李时珍", "皇甫谧"],
        "李时珍引用皇甫谧《针灸甲乙经》的腧穴体系",
    )

    # Book → Book (cited_in)
    await _add_evidenced(
        "book", "本草纲目", "book", "伤寒杂病论", "cited_in",
        ["本草纲目", "伤寒杂病论"],
        "《本草纲目》引用《伤寒杂病论》方剂",
    )
    await _add_evidenced(
        "book", "本草纲目", "book", "针灸甲乙经", "cited_in",
        ["本草纲目", "针灸甲乙经"],
        "《本草纲目》引用《针灸甲乙经》腧穴",
    )
    await _add_evidenced(
        "book", "针灸甲乙经", "book", "伤寒杂病论", "cited_in",
        ["针灸甲乙经", "伤寒杂病论"],
        "《针灸甲乙经》参考《伤寒杂病论》辨证体系",
    )

    await session.flush()
    return counts
