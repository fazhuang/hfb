"""Tests for ConflictDetector."""

import pytest
from app.schemas.graph import EvidenceChainPath, EvidenceHop
from app.services.conflict_detector import ConflictDetector

from tests.conftest_db import db_session  # noqa: F401


def make_hop(
    source_type,
    source_id,
    target_type,
    target_id,
    relation_type="related_to",
    citation="",
    quote="",
    level=3,
):
    return EvidenceHop(
        source_type=source_type,
        source_id=source_id,
        target_type=target_type,
        target_id=target_id,
        relation_type=relation_type,
        evidence_level=level,
        confidence_score=0.85,
        citation=citation,
        exact_quote=quote,
        source_uri="",
    )


@pytest.mark.asyncio
async def test_empty_paths_no_conflicts(db_session):
    """No paths -> no conflicts."""
    conflicts = await ConflictDetector.detect(db_session, [])
    assert conflicts == []


@pytest.mark.asyncio
async def test_reverse_relation_detected(db_session):
    """A->B and B->A should be detected as topological conflict."""
    path1 = EvidenceChainPath(
        path_id="path1",
        hops=[make_hop("herb", "h1", "herb", "h2")],
        total_confidence=0.85,
        min_evidence_level=3,
    )
    path2 = EvidenceChainPath(
        path_id="path2",
        hops=[make_hop("herb", "h2", "herb", "h1")],
        total_confidence=0.85,
        min_evidence_level=3,
    )
    conflicts = await ConflictDetector.detect(db_session, [path1, path2])
    assert any(c.conflict_type == "topological_reverse" for c in conflicts)


@pytest.mark.asyncio
async def test_herb_incompatibility_detected(db_session):
    """甘草 and 甘遂 together should trigger 十八反."""
    path = EvidenceChainPath(
        path_id="path1",
        hops=[
            make_hop("prescription", "rx1", "herb", "h1", citation="甘草"),
            make_hop("prescription", "rx1", "herb", "h2", citation="甘遂"),
        ],
        total_confidence=0.72,
        min_evidence_level=2,
    )
    conflicts = await ConflictDetector.detect(db_session, [path])
    assert any(c.conflict_type == "tcm_herb_incompatibility" for c in conflicts)


@pytest.mark.asyncio
async def test_no_reverse_when_only_one_direction(db_session):
    """Only one direction -> no reverse conflict."""
    path = EvidenceChainPath(
        path_id="path1",
        hops=[make_hop("herb", "a", "herb", "b")],
        total_confidence=0.80,
        min_evidence_level=3,
    )
    conflicts = await ConflictDetector.detect(db_session, [path])
    assert not any(c.conflict_type == "topological_reverse" for c in conflicts)


@pytest.mark.asyncio
async def test_acupuncture_contra_conflict(db_session):
    """Two contraindication keywords in path -> acu conflict."""
    path = EvidenceChainPath(
        path_id="path1",
        hops=[
            make_hop("passage", "p1", "passage", "p2", quote="此穴禁针"),
            make_hop("passage", "p3", "passage", "p4", quote="不可刺也"),
        ],
        total_confidence=0.75,
        min_evidence_level=3,
    )
    conflicts = await ConflictDetector.detect(db_session, [path])
    assert any(c.conflict_type == "tcm_acupuncture_contra" for c in conflicts)


@pytest.mark.asyncio
async def test_single_acupuncture_keyword_no_conflict(db_session):
    """Only one contraindication keyword -> no conflict."""
    path = EvidenceChainPath(
        path_id="path1",
        hops=[
            make_hop("passage", "p1", "passage", "p2", quote="此穴禁针"),
        ],
        total_confidence=0.75,
        min_evidence_level=3,
    )
    conflicts = await ConflictDetector.detect(db_session, [path])
    assert not any(c.conflict_type == "tcm_acupuncture_contra" for c in conflicts)


@pytest.mark.asyncio
async def test_no_herb_incompatibility_without_pair(db_session):
    """Single herb -> no incompatibility."""
    path = EvidenceChainPath(
        path_id="path1",
        hops=[
            make_hop("herb", "h1", "herb", "h2", citation="甘草"),
        ],
        total_confidence=0.70,
        min_evidence_level=2,
    )
    conflicts = await ConflictDetector.detect(db_session, [path])
    assert not any(c.conflict_type == "tcm_herb_incompatibility" for c in conflicts)
