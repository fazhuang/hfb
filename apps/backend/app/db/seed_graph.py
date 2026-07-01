"""
Seed data for Knowledge Graph — EntityRelation records that augment
FK-derived edges with curated scholarly relationships.

FK-derived edges (auto-computed by GraphService, NOT stored here):
  - Book.author_id → Person  (fk_author)
  - Version.book_id → Book   (fk_book)
  - Passage.version_id → Version (fk_passage_to_version)

Version relations (stored in version_relations, seeded elsewhere):
  - Version → Version (derived_from, revised_from, etc.)

This file seeds explicit cross-entity scholarly relationships:
  - Person → Book  (authored, compiled, commented_on)
  - Person → Person (studied — one scholar studied another's work)
  - Book → Book (cited_in)
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.book import Book
from app.models.graph import EntityRelation
from app.models.person import Person


async def seed_graph(session: AsyncSession) -> dict[str, int]:
    """Insert seed EntityRelations for the knowledge graph.

    Returns counts of inserted records.
    """
    counts: dict[str, int] = {}

    # Get seed persons and books by name
    person_stmt = select(Person).where(Person.is_deleted.is_(False))
    p_result = await session.execute(person_stmt)
    persons: dict[str, Person] = {p.name: p for p in p_result.scalars().all()}

    book_stmt = select(Book).where(Book.is_deleted.is_(False))
    b_result = await session.execute(book_stmt)
    books: dict[str, Book] = {b.title: b for b in b_result.scalars().all()}

    relation_count = 0

    # Helper: create a relation if entities exist
    async def _add(
        src_type: str,
        src_name: str,
        tgt_type: str,
        tgt_name: str,
        rel_type: str,
        description: str = "",
    ) -> None:
        nonlocal relation_count

        if src_type == "person":
            src = persons.get(src_name)
        elif src_type == "book":
            src = books.get(src_name)
        else:
            return  # version/passage — not available at seed time

        if tgt_type == "person":
            tgt = persons.get(tgt_name)
        elif tgt_type == "book":
            tgt = books.get(tgt_name)
        else:
            return

        if src is None or tgt is None:
            return

        if src.id == tgt.id:
            return  # skip self-loops

        # Check for existing
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

        er = EntityRelation(
            source_entity_type=src_type,
            source_entity_id=src.id,
            target_entity_type=tgt_type,
            target_entity_id=tgt.id,
            relation_type=rel_type,
            description=description,
        )
        session.add(er)
        relation_count += 1

    # ---- Person → Book (authored) ----
    await _add(
        "person", "皇甫谧", "book", "针灸甲乙经", "authored", "皇甫谧编撰《针灸甲乙经》"
    )
    await _add(
        "person", "张仲景", "book", "伤寒杂病论", "authored", "张仲景著《伤寒杂病论》"
    )
    await _add(
        "person", "李时珍", "book", "本草纲目", "authored", "李时珍著《本草纲目》"
    )

    # ---- Person → Person (studied) ----
    # 李时珍 studied 张仲景's work
    if "李时珍" in persons and "张仲景" in persons:
        await _add(
            "person",
            "李时珍",
            "person",
            "张仲景",
            "studied",
            "李时珍对张仲景《伤寒论》有深入研究",
        )
    if "李时珍" in persons and "皇甫谧" in persons:
        await _add(
            "person",
            "李时珍",
            "person",
            "皇甫谧",
            "studied",
            "李时珍引用皇甫谧《针灸甲乙经》的腧穴体系",
        )

    # ---- Book → Book (cited_in) ----
    if "本草纲目" in books and "伤寒杂病论" in books:
        await _add(
            "book",
            "本草纲目",
            "book",
            "伤寒杂病论",
            "cited_in",
            "《本草纲目》引用《伤寒杂病论》方剂",
        )
    if "本草纲目" in books and "针灸甲乙经" in books:
        await _add(
            "book",
            "本草纲目",
            "book",
            "针灸甲乙经",
            "cited_in",
            "《本草纲目》引用《针灸甲乙经》腧穴",
        )
    if "针灸甲乙经" in books and "伤寒杂病论" in books:
        await _add(
            "book",
            "针灸甲乙经",
            "book",
            "伤寒杂病论",
            "cited_in",
            "《针灸甲乙经》参考《伤寒杂病论》辨证体系",
        )

    await session.flush()
    counts["entity_relations"] = relation_count
    return counts
