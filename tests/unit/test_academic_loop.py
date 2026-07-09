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


@pytest.mark.asyncio
async def test_confidence_conflict_penalty(db_session: AsyncSession):
    """TREAT vs CONTRAINDICATE conflict → 0.5× penalty + logic_checked=False."""
    entity_a = AcademicEntity(name="商阳", entity_type=AcademicEntityType.ACUPOINT)
    entity_b = AcademicEntity(name="齿痛", entity_type=AcademicEntityType.DISEASE)
    db_session.add_all([entity_a, entity_b])
    await db_session.flush()

    # 1. TREAT relation (主治)
    treat_rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="TREAT",
        description="商阳穴主治齿痛",
    )
    db_session.add(treat_rel)
    await db_session.flush()

    # Bind LEVEL_2 evidence → score = 0.9 normally
    ev = Evidence(
        description="宋校本证据",
        evidence_level=EvidenceLevel.LEVEL_2,
    )
    db_session.add(ev)
    await db_session.flush()

    from app.models.academic_relation import relation_evidences
    from sqlalchemy import insert

    await db_session.execute(
        insert(relation_evidences).values(
            relation_id=treat_rel.id, evidence_id=ev.id
        )
    )
    await db_session.flush()

    # 2. CONTRAINDICATE relation (禁刺齿痛) — same entity pair
    contra_rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="CONTRAINDICATE",
        description="商阳穴禁刺齿痛",
    )
    db_session.add(contra_rel)
    await db_session.flush()

    score = await calculate_relation_confidence(db_session, treat_rel.id)

    # With single LEVEL_2 evidence: base = 0.9, conflict penalty = *0.5 → 0.45
    assert score == 0.45

    # Verify RelationConfidence was updated
    from app.models.academic_relation import RelationConfidence
    from sqlalchemy import select as _select

    conf_result = await db_session.execute(
        _select(RelationConfidence).where(
            RelationConfidence.relation_id == treat_rel.id
        )
    )
    confidence = conf_result.scalar_one_or_none()
    assert confidence is not None
    assert confidence.logic_checked is False
    assert "conflict" in (confidence.calculation_log or "").lower()
    assert "conflict_penalty" in (confidence.calculation_log or "")
    assert confidence.calculated_score == 0.45


@pytest.mark.asyncio
async def test_confidence_conflict_reverse(db_session: AsyncSession):
    """CONTRAINDICATE vs TREAT conflict (symmetric) → 0.5× penalty."""
    entity_a = AcademicEntity(name="合谷", entity_type=AcademicEntityType.ACUPOINT)
    entity_b = AcademicEntity(name="头痛", entity_type=AcademicEntityType.DISEASE)
    db_session.add_all([entity_a, entity_b])
    await db_session.flush()

    # 1. TREAT exists first
    treat_rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="TREAT",
        description="合谷穴主治头痛",
    )
    db_session.add(treat_rel)
    await db_session.flush()

    # 2. Now calculate confidence on CONTRAINDICATE — should detect TREAT as conflict
    contra_rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="CONTRAINDICATE",
        description="合谷穴禁刺头痛",
    )
    db_session.add(contra_rel)
    await db_session.flush()

    ev = Evidence(
        description="宋本校勘证据",
        evidence_level=EvidenceLevel.LEVEL_2,
    )
    db_session.add(ev)
    await db_session.flush()

    from app.models.academic_relation import relation_evidences
    from sqlalchemy import insert

    await db_session.execute(
        insert(relation_evidences).values(
            relation_id=contra_rel.id, evidence_id=ev.id
        )
    )
    await db_session.flush()

    score = await calculate_relation_confidence(db_session, contra_rel.id)
    # Single LEVEL_2 = 0.9, conflict × 0.5 → 0.45
    assert score == 0.45

    from app.models.academic_relation import RelationConfidence
    from sqlalchemy import select as _sel

    conf_result = await db_session.execute(
        _sel(RelationConfidence).where(
            RelationConfidence.relation_id == contra_rel.id
        )
    )
    confidence = conf_result.scalar_one_or_none()
    assert confidence is not None
    assert confidence.logic_checked is False
    import json
    log = json.loads(confidence.calculation_log or "{}")
    assert log["conflict_penalty"] is True
    assert log["conflicting_relation_id"] == treat_rel.id
    assert log["current_relation_type"] == "CONTRAINDICATE"
    assert log["conflicting_relation_type"] == "TREAT"
    assert log["source_entity_id"] == entity_a.id
    assert log["target_entity_id"] == entity_b.id


@pytest.mark.asyncio
async def test_confidence_conflict_log_structured(db_session: AsyncSession):
    """Calculation log contains structured conflict info including IDs."""
    entity_a = AcademicEntity(name="足三里", entity_type=AcademicEntityType.ACUPOINT)
    entity_b = AcademicEntity(name="胃痛", entity_type=AcademicEntityType.DISEASE)
    db_session.add_all([entity_a, entity_b])
    await db_session.flush()

    treat_rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="TREAT",
        description="足三里穴主治胃痛",
    )
    db_session.add(treat_rel)
    await db_session.flush()

    ev = Evidence(
        description="出土帛书证据",
        evidence_level=EvidenceLevel.LEVEL_1,
    )
    db_session.add(ev)
    await db_session.flush()

    from app.models.academic_relation import relation_evidences
    from sqlalchemy import insert
    await db_session.execute(
        insert(relation_evidences).values(
            relation_id=treat_rel.id, evidence_id=ev.id
        )
    )
    await db_session.flush()

    contra_rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="CONTRAINDICATE",
        description="足三里禁刺胃痛",
    )
    db_session.add(contra_rel)
    await db_session.flush()

    score = await calculate_relation_confidence(db_session, treat_rel.id)
    assert score == 0.5  # LEVEL_1 = 1.0, conflict × 0.5 → 0.5

    from app.models.academic_relation import RelationConfidence
    from sqlalchemy import select as _sel

    conf_result = await db_session.execute(
        _sel(RelationConfidence).where(
            RelationConfidence.relation_id == treat_rel.id
        )
    )
    confidence = conf_result.scalar_one_or_none()
    assert confidence is not None
    assert confidence.logic_checked is False

    import json
    log = json.loads(confidence.calculation_log or "{}")
    assert log["conflict_penalty"] is True
    assert log["conflicting_relation_id"] == contra_rel.id
    assert log["current_relation_type"] == "TREAT"
    assert log["conflicting_relation_type"] == "CONTRAINDICATE"
    assert log["source_entity_id"] == entity_a.id
    assert log["target_entity_id"] == entity_b.id
    assert "conflict_note" in log


@pytest.mark.asyncio
async def test_confidence_no_conflict_structured_log(db_session: AsyncSession):
    """No conflict → log is structured with conflict_penalty: false."""
    entity_a = AcademicEntity(name="商阳", entity_type=AcademicEntityType.ACUPOINT)
    entity_b = AcademicEntity(name="齿痛", entity_type=AcademicEntityType.DISEASE)
    db_session.add_all([entity_a, entity_b])
    await db_session.flush()

    rel = AcademicRelation(
        source_entity_id=entity_a.id,
        target_entity_id=entity_b.id,
        relation_type="TREAT",
        description="商阳穴主治齿痛",
    )
    db_session.add(rel)
    await db_session.flush()

    ev = Evidence(
        description="宋校本证据",
        evidence_level=EvidenceLevel.LEVEL_2,
    )
    db_session.add(ev)
    await db_session.flush()

    from app.models.academic_relation import relation_evidences
    from sqlalchemy import insert
    await db_session.execute(
        insert(relation_evidences).values(
            relation_id=rel.id, evidence_id=ev.id
        )
    )
    await db_session.flush()

    score = await calculate_relation_confidence(db_session, rel.id)
    assert score == 0.9  # no conflict

    from app.models.academic_relation import RelationConfidence
    from sqlalchemy import select as _sel
    conf_result = await db_session.execute(
        _sel(RelationConfidence).where(RelationConfidence.relation_id == rel.id)
    )
    confidence = conf_result.scalar_one_or_none()
    assert confidence is not None
    assert confidence.logic_checked is True

    import json
    log = json.loads(confidence.calculation_log or "{}")
    assert log["conflict_penalty"] is False
    assert "conflicting_relation_id" not in log
    assert "weights" in log


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_passage_detail_includes_sentences(db_session: AsyncSession):
    """GET /api/v1/passages/{id}/detail returns sentences/tokens/variants."""
    from sqlalchemy import select as _sel
    from app.models.book import Book as B
    from app.models.chapter import Chapter as C
    from app.models.passage import Passage as P
    from app.models.version import Version as V
    from app.models.version_criticism import (
        Sentence as S, Token as T, Variant as Var, VariantType,
    )

    book = B(id="bk-detail-1", title="测试书", dynasty="唐")
    db_session.add(book)
    await db_session.flush()

    ver = V(id="ver-detail-1", book_id=book.id, version_name="测试版本")
    db_session.add(ver)
    await db_session.flush()

    chap = C(id="ch-detail-1", book_id=book.id, title="测试章", order=1)
    db_session.add(chap)
    await db_session.flush()

    p = P(
        id="pass-detail-999", chapter_id=chap.id, version_id=ver.id,
        content_text="帝曰：善。", order=1,
    )
    db_session.add(p)
    await db_session.flush()

    s = S(id="sent-detail-1", passage_id=p.id, content_text="帝曰：善。", order=1)
    db_session.add(s)
    await db_session.flush()

    t = T(id="tok-detail-1", sentence_id=s.id, char_text="善", position=1)
    db_session.add(t)
    await db_session.flush()

    vt = Var(
        id="var-detail-1", base_token_id=t.id,
        variant_type=VariantType.SUBSTITUTION, description="善 ↔ 差",
    )
    db_session.add(vt)
    await db_session.flush()
    await db_session.commit()

    # Verify via ORM directly — the passage has sentences with tokens with variants
    from sqlalchemy.orm import selectinload

    stmt = (
        _sel(P)
        .options(
            selectinload(P.sentences)
            .selectinload(S.tokens)
            .selectinload(T.variants_as_base),
        )
        .where(P.id == "pass-detail-999")
    )
    result = await db_session.execute(stmt)
    passage = result.scalar_one_or_none()

    assert passage is not None
    assert len(passage.sentences) == 1
    assert passage.sentences[0].content_text == "帝曰：善。"
    assert len(passage.sentences[0].tokens) == 1
    tok = passage.sentences[0].tokens[0]
    assert tok.char_text == "善"
    assert len(tok.variants_as_base) == 1
    assert tok.variants_as_base[0].description == "善 ↔ 差"
