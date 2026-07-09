"""Academic minimal viable loop — integration test.

Per academic_implementation_manual.md Step 4.
Tests the full chain: Book → Version → Chapter → Passage → Sentence → Token →
Variant → SourceRef → Evidence → AcademicEntity → AcademicRelation →
calculate_relation_confidence.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import (
    Book,
    Version,
    Chapter,
    Passage,
)
from app.models.version_criticism import Sentence, Token, Variant, VariantType
from app.models.academic_evidence import SourceRef, Evidence, EvidenceLevel
from app.models.academic_relation import (
    AcademicEntity,
    AcademicEntityType,
    AcademicRelation,
    RelationConfidence,
)
from app.api.v1.relations import calculate_relation_confidence

from tests.conftest_db import db_session  # noqa: F401


@pytest.mark.asyncio
async def test_academic_minimal_viable_loop(db_session: AsyncSession):
    """Full end-to-end academic evidence chain test."""

    # 1. Book + Versions
    book = Book(title="针灸甲乙经", dynasty="晋", year=282)
    db_session.add(book)
    await db_session.flush()

    v_song = Version(book_id=book.id, version_name="宋校本", era="北宋")
    v_ming = Version(book_id=book.id, version_name="明抄本", era="明代")
    db_session.add_all([v_song, v_ming])
    await db_session.flush()

    # 2. Chapter
    chapter = Chapter(book_id=book.id, title="卷十一·大肠腑病第八", order=11)
    db_session.add(chapter)
    await db_session.flush()

    # 3. Song edition Passage
    p_song = Passage(
        chapter_id=chapter.id,
        version_id=v_song.id,
        content_text="齿痛，商阳主之。",
        order=1,
    )
    db_session.add(p_song)
    await db_session.flush()

    s_song = Sentence(
        passage_id=p_song.id, content_text="齿痛，商阳主之。", order=1
    )
    db_session.add(s_song)
    await db_session.flush()

    t_yang = Token(sentence_id=s_song.id, char_text="阳", position=4)
    db_session.add(t_yang)
    await db_session.flush()

    # 4. Ming edition Passage
    p_ming = Passage(
        chapter_id=chapter.id,
        version_id=v_ming.id,
        content_text="齿痛，商阴主之。",
        order=1,
    )
    db_session.add(p_ming)
    await db_session.flush()

    s_ming = Sentence(
        passage_id=p_ming.id, content_text="齿痛，商阴主之。", order=1
    )
    db_session.add(s_ming)
    await db_session.flush()

    t_yin = Token(sentence_id=s_ming.id, char_text="阴", position=4)
    db_session.add(t_yin)
    await db_session.flush()

    # 5. Variant (阳 vs 阴)
    variant = Variant(
        base_token_id=t_yang.id,
        compare_token_id=t_yin.id,
        variant_type=VariantType.SUBSTITUTION,
        description="宋校本作阳，明抄本作阴。",
    )
    db_session.add(variant)
    await db_session.flush()

    # 6. Physical source + evidence
    ref = SourceRef(
        title="宋刻针灸甲乙经",
        author="高保衡等校",
        page_location="卷十一 p245",
    )
    db_session.add(ref)
    await db_session.flush()

    evidence = Evidence(
        description="宋校本《针灸甲乙经》原字为阳",
        evidence_level=EvidenceLevel.LEVEL_2,
        source_ref_id=ref.id,
        source_passage_id=p_song.id,
    )
    db_session.add(evidence)
    await db_session.flush()

    # 7. Academic entities + relation
    entity_acupoint = AcademicEntity(
        name="商阳", entity_type=AcademicEntityType.ACUPOINT
    )
    entity_disease = AcademicEntity(
        name="齿痛", entity_type=AcademicEntityType.DISEASE
    )
    db_session.add_all([entity_acupoint, entity_disease])
    await db_session.flush()

    relation = AcademicRelation(
        source_entity_id=entity_acupoint.id,
        target_entity_id=entity_disease.id,
        relation_type="TREAT",
        description="商阳穴主治齿痛",
    )
    db_session.add(relation)
    await db_session.flush()

    # Link evidence to relation — must use insert on the secondary table directly
    # to avoid lazy-loading the evidences relationship outside the greenlet.
    from app.models.academic_relation import relation_evidences
    from sqlalchemy import insert

    await db_session.execute(
        insert(relation_evidences).values(
            relation_id=relation.id, evidence_id=evidence.id
        )
    )
    await db_session.flush()

    # 8. Confidence calculation
    score = await calculate_relation_confidence(db_session, relation.id)

    # 9. Assertions
    assert score >= 0.89  # LEVEL_2 = 0.9
    assert variant.variant_type == VariantType.SUBSTITUTION
    assert variant.base_token.char_text == "阳"
    assert variant.compare_token.char_text == "阴"


@pytest.mark.asyncio
async def test_confidence_zero_if_no_evidence(db_session: AsyncSession):
    """Relation without evidence returns 0.0 confidence."""
    entity_a = AcademicEntity(name="合谷", entity_type=AcademicEntityType.ACUPOINT)
    entity_b = AcademicEntity(name="头痛", entity_type=AcademicEntityType.DISEASE)
    db_session.add_all([entity_a, entity_b])
    await db_session.flush()

    rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="TREAT",
        description="合谷穴主治头痛",
    )
    db_session.add(rel)
    await db_session.flush()

    score = await calculate_relation_confidence(db_session, rel.id)
    assert score == 0.0


@pytest.mark.asyncio
async def test_confidence_multiple_evidences(db_session: AsyncSession):
    """Multiple evidences should produce higher combined confidence."""
    entity_a = AcademicEntity(name="足三里", entity_type=AcademicEntityType.ACUPOINT)
    entity_b = AcademicEntity(name="胃痛", entity_type=AcademicEntityType.DISEASE)
    db_session.add_all([entity_a, entity_b])
    await db_session.flush()

    rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="TREAT",
        description="足三里穴主治胃痛",
    )
    db_session.add(rel)
    await db_session.flush()

    # LEVEL_1 (1.0) + LEVEL_2 (0.9) → 1 - (1-1.0)*(1-0.9) = 1 - 0 = 1.0
    ev1 = Evidence(
        description="出土帛书证据",
        evidence_level=EvidenceLevel.LEVEL_1,
    )
    ev2 = Evidence(
        description="宋本校勘证据",
        evidence_level=EvidenceLevel.LEVEL_2,
    )
    db_session.add_all([ev1, ev2])
    await db_session.flush()

    from app.models.academic_relation import relation_evidences
    from sqlalchemy import insert

    await db_session.execute(
        insert(relation_evidences).values(
            relation_id=rel.id, evidence_id=ev1.id
        )
    )
    await db_session.execute(
        insert(relation_evidences).values(
            relation_id=rel.id, evidence_id=ev2.id
        )
    )
    await db_session.flush()

    score = await calculate_relation_confidence(db_session, rel.id)
    assert score == 1.0  # 1 - (1-1.0)*(1-0.9) = 1.0
