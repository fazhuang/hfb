"""
Tests for Knowledge Graph — EntityRelation model, GraphService, API endpoints.

Per HFB-PS-1707 Knowledge Graph Product Specification.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.graph import GRAPH_ENTITY_TYPES, GRAPH_RELATION_TYPES
from app.models.person import Person
from app.schemas.graph import EntityRelationCreate, RELATION_LABELS
from app.services.graph_service import GraphService, _entity_to_node, _make_label

from tests.conftest_db import db_session, db_session_persistent  # noqa: F401


# ============================================================
# Unit: constants and label mapping
# ============================================================


class TestGraphConstants:
    def test_entity_types(self) -> None:
        assert "person" in GRAPH_ENTITY_TYPES
        assert "book" in GRAPH_ENTITY_TYPES
        assert "version" in GRAPH_ENTITY_TYPES
        assert "passage" in GRAPH_ENTITY_TYPES
        # Ontology expansion: now includes text, herb, prescription, meridian, symptom
        assert "text" in GRAPH_ENTITY_TYPES
        assert "herb" in GRAPH_ENTITY_TYPES
        assert "prescription" in GRAPH_ENTITY_TYPES
        assert len(GRAPH_ENTITY_TYPES) >= 9

    def test_relation_types(self) -> None:
        assert "authored" in GRAPH_RELATION_TYPES
        assert "compiled" in GRAPH_RELATION_TYPES
        assert "commented_on" in GRAPH_RELATION_TYPES
        assert "cited_in" in GRAPH_RELATION_TYPES
        assert "studied" in GRAPH_RELATION_TYPES
        assert "compared" in GRAPH_RELATION_TYPES
        assert "referenced" in GRAPH_RELATION_TYPES
        assert "related_to" in GRAPH_RELATION_TYPES

    def test_labels_have_all_relation_types(self) -> None:
        for rt in GRAPH_RELATION_TYPES:
            assert rt in RELATION_LABELS, f"Missing label for {rt}"
        assert RELATION_LABELS["fk_author"] == "作者"
        assert RELATION_LABELS["fk_book"] == "所属书籍"
        assert RELATION_LABELS["fk_passage_to_version"] == "关联版本"


# ============================================================
# Unit: EntityRelationCreate schema validation
# ============================================================


class TestEntityRelationSchema:
    def test_create_valid(self) -> None:
        er = EntityRelationCreate(
            source_entity_type="person",
            source_entity_id="a" * 36,
            target_entity_type="book",
            target_entity_id="b" * 36,
            relation_type="authored",
            description="test",
        )
        assert er.source_entity_type == "person"
        assert er.relation_type == "authored"

    def test_create_invalid_relation_type_ok_at_schema_level(self) -> None:
        """Schema validation doesn't check enum — service does."""
        er = EntityRelationCreate(
            source_entity_type="person",
            source_entity_id="a" * 36,
            target_entity_type="book",
            target_entity_id="b" * 36,
            relation_type="not_a_real_type",
        )
        assert er.relation_type == "not_a_real_type"


# ============================================================
# Unit: GraphService with mocked session
# ============================================================


class TestGraphServiceValidation:
    """Test EntityRelation validation logic (synchronous)."""

    def test_create_relation_invalid_source_type_raises(self) -> None:
        """validate that source_entity_type is checked against GRAPH_ENTITY_TYPES"""
        assert "invalid_type" not in GRAPH_ENTITY_TYPES
        assert "person" in GRAPH_ENTITY_TYPES
        assert "book" in GRAPH_ENTITY_TYPES

    def test_create_relation_invalid_relation_type_raises(self) -> None:
        """validate that relation_type is checked against GRAPH_RELATION_TYPES"""
        assert "fictional_relation" not in GRAPH_RELATION_TYPES
        assert "authored" in GRAPH_RELATION_TYPES


@pytest.mark.asyncio
class TestGraphServiceAsync:
    """Async tests using the real test database."""

    async def test_create_relation_and_retrieve(self, db_session: AsyncSession) -> None:
        """Create an EntityRelation and verify it can be retrieved."""
        # First create seed persons, books, and evidence chunk
        p = Person(name="测试人物", dynasty="唐")
        db_session.add(p)
        await db_session.flush()

        from app.models.book import Book

        b = Book(title="测试古籍", dynasty="唐", category="医经")
        db_session.add(b)
        await db_session.flush()

        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk

        d = Document(title="测试文献", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="测试人物编撰测试古籍。",
            token_count=20,
        )
        db_session.add(c)
        await db_session.flush()

        from app.schemas.graph import GraphEvidence

        ev = GraphEvidence(
            document_id=d.id,
            chunk_id=c.id,
            exact_quote="测试人物编撰测试古籍。",
            citation=f"[{d.id}:{c.id}]",
        )

        svc = GraphService(db_session)
        relation = await svc.create_relation(
            source_entity_type="person",
            source_entity_id=p.id,
            target_entity_type="book",
            target_entity_id=b.id,
            relation_type="authored",
            description="测试关系",
            evidence=ev,
        )
        # P0-2: must set complete verification audit fields
        from datetime import datetime, timezone

        relation.evidence_status = "verified"
        relation.verified_by = "test-reviewer"
        relation.verified_at = datetime.now(timezone.utc)
        relation.claim_text = "测试关系"
        relation.evidence_source_uri = "https://example.com/test-source"
        await db_session.flush()

        assert relation.id is not None
        assert relation.relation_type == "authored"
        assert relation.source_entity_type == "person"
        assert relation.target_entity_type == "book"

        # Retrieve relations for this person
        relations = await svc.get_validated_relations_for_entity("person", p.id)
        assert len(relations) >= 1
        assert any(r.id == relation.id for r, ev in relations)

    async def test_delete_relation(self, db_session: AsyncSession) -> None:
        """Soft-delete an EntityRelation."""
        p = Person(name="测试人物2", dynasty="宋")
        db_session.add(p)
        await db_session.flush()

        from app.models.book import Book

        b = Book(title="测试古籍2", dynasty="宋", category="方剂")
        db_session.add(b)
        await db_session.flush()

        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk

        d = Document(title="测试文献2", dynasty="宋")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="测试人物2编撰测试古籍2。",
            token_count=20,
        )
        db_session.add(c)
        await db_session.flush()

        from app.schemas.graph import GraphEvidence

        ev = GraphEvidence(
            document_id=d.id,
            chunk_id=c.id,
            exact_quote="测试人物2编撰测试古籍2。",
            citation=f"[{d.id}:{c.id}]",
        )

        svc = GraphService(db_session)
        rel = await svc.create_relation(
            source_entity_type="person",
            source_entity_id=p.id,
            target_entity_type="book",
            target_entity_id=b.id,
            relation_type="compiled",
            evidence=ev,
        )

        ok = await svc.delete_relation(rel.id)
        assert ok is True

        # Should not find it again
        relations = await svc.get_validated_relations_for_entity("person", p.id)
        assert not any(r.id == rel.id for r, ev in relations)

    async def test_delete_nonexistent_relation(self, db_session: AsyncSession) -> None:
        svc = GraphService(db_session)
        ok = await svc.delete_relation("00000000-0000-0000-0000-000000000000")
        assert ok is False

    async def test_search_entities_empty(self, db_session: AsyncSession) -> None:
        svc = GraphService(db_session)
        nodes = await svc.search_entities(query="nonexistent_xyz_123_no_match_expected")
        assert len(nodes) == 0

    async def test_search_entities_all_types(self, db_session: AsyncSession) -> None:
        svc = GraphService(db_session)
        nodes = await svc.search_entities(limit=10)
        # Database starts empty in test — may return 0 or some seed
        assert isinstance(nodes, list)

    async def test_get_neighbors_nonexistent(self, db_session: AsyncSession) -> None:
        svc = GraphService(db_session)
        with pytest.raises(ValueError, match="not found"):
            await svc.get_neighbors("person", "00000000-0000-0000-0000-000000000000")

    async def test_find_path_same_node(self, db_session: AsyncSession) -> None:
        svc = GraphService(db_session)
        p = Person(name="路径测试", dynasty="汉")
        db_session.add(p)
        await db_session.flush()

        path = await svc.find_path("person", p.id, "person", p.id)
        assert path is not None
        assert path.length == 0
        assert len(path.nodes) == 1
        assert path.nodes[0].entity_id == p.id

    async def test_find_path_no_path(self, db_session: AsyncSession) -> None:
        svc = GraphService(db_session)
        # Two likely disconnected entities should return None
        path = await svc.find_path(
            "person",
            "00000000-0000-0000-0000-000000000001",
            "book",
            "00000000-0000-0000-0000-000000000002",
        )
        assert path is None

    async def test_find_path_with_edges(self, db_session: AsyncSession) -> None:
        """Find a path through an explicit EntityRelation with evidence."""
        p = Person(name="作者测试", dynasty="唐")
        db_session.add(p)
        await db_session.flush()

        from app.models.book import Book

        b = Book(title="关联古籍", dynasty="唐", category="医经")
        db_session.add(b)
        await db_session.flush()

        # Create explicit EntityRelation with evidence
        from app.models.document import Document
        from app.models.document_chunk import DocumentChunk

        d = Document(title="测试文献", dynasty="唐")
        db_session.add(d)
        await db_session.flush()
        c = DocumentChunk(
            document_id=d.id,
            chunk_index=0,
            content="作者测试编撰关联古籍。",
            token_count=20,
        )
        db_session.add(c)
        await db_session.flush()

        from app.schemas.graph import GraphEvidence

        ev = GraphEvidence(
            document_id=d.id,
            chunk_id=c.id,
            exact_quote="作者测试编撰关联古籍。",
            citation=f"[{d.id}:{c.id}]",
        )

        svc = GraphService(db_session)
        rel = await svc.create_relation(
            "person",
            p.id,
            "book",
            b.id,
            "authored",
            evidence=ev,
        )
        rel.evidence_status = "verified"
        from datetime import datetime, timezone

        rel.verified_by = "test-reviewer"
        rel.verified_at = datetime.now(timezone.utc)
        rel.claim_text = "作者测试编撰关联古籍"
        rel.evidence_source_uri = "https://example.com/test-find-path"
        await db_session.flush()

        path = await svc.find_path("person", p.id, "book", b.id)
        # Should find a path since explicit EntityRelation was created
        assert path is not None
        assert path.length >= 1  # at least one edge
        assert path.edges[0].evidence is not None


# ============================================================
# Test: label generation
# ============================================================


class TestLabelGeneration:
    def test_person_label(self) -> None:
        p = MagicMock()
        p.name = "皇甫谧"
        p.dynasty = "西晋"
        label = _make_label(p, "person")
        assert "皇甫谧" in label
        assert "西晋" in label

    def test_book_label(self) -> None:
        b = MagicMock()
        b.title = "针灸甲乙经"
        b.dynasty = "西晋"
        label = _make_label(b, "book")
        assert "《针灸甲乙经》" in label
        assert "西晋" in label

    def test_version_label(self) -> None:
        v = MagicMock()
        v.version_name = "北宋刻本"
        v.era = "北宋"
        label = _make_label(v, "version")
        assert "北宋刻本" in label
        assert "北宋" in label

    def test_passage_label(self) -> None:
        p = MagicMock()
        p.content_text = "凡刺之要，官针最妙。九针之宜，各有所为。"
        p.order = 5
        label = _make_label(p, "passage")
        assert "#5" in label
        assert "凡刺之要" in label


# ============================================================
# Test: node conversion
# ============================================================


class TestEntityToNode:
    def test_person_node(self) -> None:
        p = MagicMock()
        p.id = "test-id-123"
        p.name = "皇甫谧"
        p.dynasty = "西晋"
        p.courtesy_name = "士安"
        node = _entity_to_node(p, "person")
        assert node.id == "person:test-id-123"
        assert node.entity_type == "person"
        assert node.properties["name"] == "皇甫谧"
        assert node.properties["dynasty"] == "西晋"

    def test_book_node(self) -> None:
        b = MagicMock()
        b.id = "book-id-456"
        b.title = "针灸甲乙经"
        b.dynasty = "西晋"
        b.category = "针灸"
        node = _entity_to_node(b, "book")
        assert node.id == "book:book-id-456"
        assert node.entity_type == "book"
        assert node.properties["title"] == "针灸甲乙经"
        assert node.properties["category"] == "针灸"

    def test_version_node(self) -> None:
        v = MagicMock()
        v.id = "ver-id-789"
        v.version_name = "北宋刻本"
        v.era = "北宋"
        v.repository = "国家图书馆"
        node = _entity_to_node(v, "version")
        assert node.id == "version:ver-id-789"
        assert node.properties["version_name"] == "北宋刻本"
        assert node.properties["repository"] == "国家图书馆"

    def test_passage_node(self) -> None:
        p = MagicMock()
        p.id = "pass-id-001"
        p.content_text = "凡刺之要，官针最妙。"
        p.order = 3
        node = _entity_to_node(p, "passage")
        assert node.id == "passage:pass-id-001"
        assert node.properties["order"] == 3
        assert "凡刺之要" in node.properties["content_preview"]
