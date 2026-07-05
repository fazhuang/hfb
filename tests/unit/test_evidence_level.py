"""Tests for evidence_level derivation in GraphService."""

import pytest
from app.models.graph import EntityRelation
from app.services.graph_service import GraphService
from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


@pytest.mark.asyncio
async def test_derive_evidence_level_l0_no_evidence(db_session):
    """EntityRelation with only claim_text → L0."""
    er = EntityRelation(
        source_entity_type="person",
        source_entity_id="test-src-id",
        target_entity_type="book",
        target_entity_id="test-tgt-id",
        relation_type="authored",
        claim_text="some claim",
    )
    level = await GraphService._derive_evidence_level(db_session, er)
    assert level == 0


@pytest.mark.asyncio
async def test_derive_evidence_level_l1_document_only(db_session):
    """EntityRelation with document_id but no passage → L1."""
    er = EntityRelation(
        source_entity_type="person",
        source_entity_id="test-src-id",
        target_entity_type="book",
        target_entity_id="test-tgt-id",
        relation_type="authored",
        evidence_document_id="doc-1",
        evidence_citation="test citation",
    )
    level = await GraphService._derive_evidence_level(db_session, er)
    assert level == 1


@pytest.mark.asyncio
async def test_derive_evidence_level_l2_version_passage(db_session):
    """EntityRelation with version_id + passage_id → L2."""
    er = EntityRelation(
        source_entity_type="person",
        source_entity_id="test-src-id",
        target_entity_type="book",
        target_entity_id="test-tgt-id",
        relation_type="authored",
        evidence_document_id="doc-1",
        evidence_citation="test citation",
        evidence_version_id="ver-1",
        evidence_passage_id="pass-1",
    )
    level = await GraphService._derive_evidence_level(db_session, er)
    assert level == 2


@pytest.mark.asyncio
async def test_derive_evidence_level_l3_quote_verified(db_session):
    """EntityRelation L2 + quote + verified → L3."""
    er = EntityRelation(
        source_entity_type="person",
        source_entity_id="test-src-id",
        target_entity_type="book",
        target_entity_id="test-tgt-id",
        relation_type="authored",
        evidence_document_id="doc-1",
        evidence_citation="test citation",
        evidence_version_id="ver-1",
        evidence_passage_id="pass-1",
        evidence_quote="exact quote text",
        evidence_status="verified",
    )
    level = await GraphService._derive_evidence_level(db_session, er)
    assert level == 3
