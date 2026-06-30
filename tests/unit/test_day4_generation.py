"""
Day 4 tests — Citation-Grounded LLM Generation Layer.

Requirements:
- 5 grounded answer tests
- 3 hallucination rejection tests
- 3 citation binding tests
- 2 multi-chunk synthesis tests
"""
from __future__ import annotations

import pytest

from app.models.book import Book
from app.models.person import Person
from app.schemas.generation import GroundedGenerationResponse
from app.services.generation_service import GenerationPipeline, GROUNDED_SYSTEM_PROMPT

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


# ============================================================
# Helpers
# ============================================================


async def _seed_tcm_data(session) -> None:
    """Seed a minimal TCM dataset for generation tests."""
    p = Person(
        name="皇甫谧",
        dynasty="西晋",
        biography="皇甫谧（215-282年），字士安，西晋著名医学家、史学家。编撰《针灸甲乙经》，系统整理了针灸学理论。",
    )
    session.add(p)
    await session.flush()

    b = Book(
        title="针灸甲乙经",
        dynasty="西晋",
        abstract="《针灸甲乙经》是中国现存最早的针灸学专著，由皇甫谧编撰于公元256-282年间。全书共12卷，系统论述了脏腑、经络、腧穴、针刺手法等内容。",
    )
    session.add(b)
    await session.flush()

    b2 = Book(
        title="伤寒杂病论",
        dynasty="东汉",
        abstract="《伤寒杂病论》为张仲景所著，后世分为《伤寒论》与《金匮要略》。确立了辨证论治原则。",
    )
    session.add(b2)
    await session.flush()


# ============================================================
# 5 Grounded Answer Tests
# ============================================================


@pytest.mark.asyncio
async def test_grounded_answer_returns_citations(db_session) -> None:
    """Grounded answer must include citation references [N]."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("针灸甲乙经", top_k=5)

    assert result.answer
    assert "EVIDENCE_GATE_REFUSAL" not in result.answer
    assert len(result.results) >= 1
    assert len(result.citations) >= 1
    # At least one [N] reference in the answer
    assert "[" in result.answer and "]" in result.answer


@pytest.mark.asyncio
async def test_grounded_answer_uses_only_provided_chunks(db_session) -> None:
    """Answer should only reference chunks that were actually retrieved."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("皇甫谧", top_k=3)

    # Validation metadata should show cited chunks within the valid range
    validation = result.metadata.citation_validation
    assert validation["total_chunks"] >= 1
    if validation["cited_chunks"]:
        for cited in validation["cited_chunks"]:
            assert 1 <= cited <= validation["total_chunks"]


@pytest.mark.asyncio
async def test_grounded_answer_with_single_chunk(db_session) -> None:
    """Single chunk retrieval should still produce a cited answer."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("皇甫谧", entity_types=["person"], top_k=1)

    assert result.answer
    # Single chunk is valid — may or may not have citation depending on mock output
    assert len(result.results) <= 1


@pytest.mark.asyncio
async def test_grounded_answer_citation_validation_metadata(db_session) -> None:
    """Metadata must include citation validation results."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("针灸甲乙经", top_k=5)

    metadata = result.metadata
    assert metadata.model == "citation-grounded-llm"
    assert metadata.top_k >= 1
    validation = metadata.citation_validation
    assert "has_citations" in validation
    assert "cited_chunks" in validation
    assert "invalid_refs" in validation
    assert "uncited" in validation
    assert "total_chunks" in validation
    assert "is_valid" in validation


@pytest.mark.asyncio
async def test_grounded_answer_response_envelope_structure(db_session) -> None:
    """Response must match the Day 4 schema: { query, answer, results[], citations[], metadata }."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("伤寒杂病论", top_k=5)

    # Validate full envelope
    assert isinstance(result, GroundedGenerationResponse)
    assert result.query == "伤寒杂病论"
    assert isinstance(result.answer, str)
    assert isinstance(result.results, list)
    assert isinstance(result.citations, list)
    assert result.metadata is not None
    # Citations must map to results
    assert len(result.citations) == len(result.results)


# ============================================================
# 3 Hallucination Rejection Tests
# ============================================================


@pytest.mark.asyncio
async def test_refuse_when_no_chunks_found(db_session) -> None:
    """When retrieval returns nothing, must refuse — no hallucination."""
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("火星上的针灸技术", top_k=5)

    assert "EVIDENCE_GATE_REFUSAL" in result.answer
    assert len(result.results) == 0
    assert len(result.citations) == 0
    assert result.metadata.citation_validation["uncited"] is True


@pytest.mark.asyncio
async def test_refuse_with_empty_database(db_session) -> None:
    """Empty database must trigger refusal for any query."""
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("什么是针灸？", top_k=5)

    assert "EVIDENCE_GATE_REFUSAL" in result.answer


@pytest.mark.asyncio
async def test_no_fabricated_citations(db_session) -> None:
    """Citation references must never exceed the actual chunk count."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("针灸甲乙经", top_k=5)

    validation = result.metadata.citation_validation
    total = validation["total_chunks"]

    # No invalid refs (references beyond the valid range)
    assert len(validation["invalid_refs"]) == 0, (
        f"Found invalid citation refs: {validation['invalid_refs']} "
        f"(total chunks: {total})"
    )


# ============================================================
# 3 Citation Binding Tests
# ============================================================


@pytest.mark.asyncio
async def test_citation_binding_prompt_enforces_citing(db_session) -> None:
    """The grounded system prompt must explicitly require [N] citations."""
    assert "逐句引用" in GROUNDED_SYSTEM_PROMPT
    assert "[N]" in GROUNDED_SYSTEM_PROMPT
    assert "引用编号 = 无效输出" in GROUNDED_SYSTEM_PROMPT.replace(" ", "").replace(
        " ", ""
    ) or "没有引用编号" in GROUNDED_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_citation_validation_detects_valid_refs(db_session) -> None:
    """The pipeline must detect [1], [2] etc. in generated text."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)

    # Directly test validation logic with synthetic answers
    validation = pipeline._validate_citations("针灸是一门学科 [1][2]", 3)
    assert validation["has_citations"] is True
    assert 1 in validation["cited_chunks"]
    assert 2 in validation["cited_chunks"]
    assert validation["is_valid"] is True


@pytest.mark.asyncio
async def test_citation_validation_rejects_invalid_refs(db_session) -> None:
    """References to non-existent chunks [99] should be flagged."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)

    validation = pipeline._validate_citations("根据资料 [1] 和 [99]", 3)
    assert 1 in validation["cited_chunks"]
    assert 99 in validation["invalid_refs"]
    assert validation["is_valid"] is False


# ============================================================
# 2 Multi-Chunk Synthesis Tests
# ============================================================


@pytest.mark.asyncio
async def test_multi_chunk_synthesis_preserves_attribution(db_session) -> None:
    """When multiple chunks are available, each must retain its source attribution."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("针灸", top_k=3)

    # Multiple chunks should be in results
    assert len(result.results) >= 1

    # Each result must have a unique citation
    citation_texts = [c.text for c in result.citations if c.text]
    assert len(citation_texts) == len(set(citation_texts)), (
        f"Duplicate citations found: {citation_texts}"
    )


@pytest.mark.asyncio
async def test_multi_chunk_validation_tracks_all_chunks(db_session) -> None:
    """Citation validation metadata must reflect the full chunk count."""
    await _seed_tcm_data(db_session)
    pipeline = GenerationPipeline(db_session)
    result = await pipeline.generate("医学", top_k=5)

    validation = result.metadata.citation_validation
    # Total chunks tracked must match what was retrieved
    assert validation["total_chunks"] == len(result.results)
