"""Unit tests for VersionComparisonService and commentary module-level functions.

Covers get_lineage, compare_passages, get_saved_diff, create_passage_mapping,
get_passage_mappings, add_relation, run_full_compare, and commentary CRUD.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from app.models.commentary import Commentary
from app.models.passage import Passage
from app.models.version import Version
from app.models.version_relation import PassageMapping, VersionDiff, VersionRelation
from app.schemas.commentary import CommentaryCreate
from app.services.version_center import (
    VersionComparisonService,
    compute_distance_matrix,
    compute_version_tree,
    create_commentary,
    get_commentaries_for_passage,
    get_commentary_chain,
    get_commentary_graph,
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _execute_scalars_all(*items):
    """Return a mock execute-result whose .scalars().all() yields *items."""
    m = MagicMock()
    m.scalars.return_value.all.return_value = list(items)
    return m


def _execute_scalar_one(item):
    """Return a mock execute-result whose .scalar_one_or_none() yields item."""
    m = MagicMock()
    m.scalar_one_or_none.return_value = item
    return m


def _make_passage(id_: str = "", content_text: str = "") -> Passage:
    p = MagicMock(spec=Passage)
    p.id = id_ or str(uuid4())
    p.content_text = content_text or "原文内容"
    return p


def _make_version(id_: str = "", version_name: str = "v1") -> Version:
    v = MagicMock(spec=Version)
    v.id = id_ or str(uuid4())
    v.version_name = version_name
    v.era = "song"
    v.repository = "test-repo"
    return v


def _make_version_relation(
    source_id: str = "",
    target_id: str = "",
    relation_type: str = "derived_from",
) -> VersionRelation:
    r = MagicMock(spec=VersionRelation)
    r.source_version_id = source_id or str(uuid4())
    r.target_version_id = target_id or str(uuid4())
    r.relation_type = relation_type
    r.description = "test desc"
    return r


def _make_version_diff(
    id_: str = "",
    source_id: str = "",
    target_id: str = "",
    diff_data: str = "[]",
    summary: str = "no diff",
    total: int = 0,
) -> VersionDiff:
    d = MagicMock(spec=VersionDiff)
    d.id = id_ or str(uuid4())
    d.source_version_id = source_id or str(uuid4())
    d.target_version_id = target_id or str(uuid4())
    d.diff_data = diff_data
    d.diff_summary = summary
    d.total_differences = total
    d.created_at = None
    return d


# ---------------------------------------------------------------------------
# VersionComparisonService — get_lineage
# ---------------------------------------------------------------------------


class TestGetLineage:
    @pytest.mark.asyncio
    async def test_version_not_found_raises(self):
        session = AsyncMock()
        svc = VersionComparisonService(session)
        svc.version_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match="Version not found"):
            await svc.get_lineage(str(uuid4()))

    @pytest.mark.asyncio
    async def test_no_relations_returns_empty_ancestors_descendants(self):
        vid = str(uuid4())
        ver = _make_version(vid, "宋刻本")

        session = AsyncMock()
        svc = VersionComparisonService(session)
        svc.version_repo.get_by_id = AsyncMock(return_value=ver)
        session.execute = AsyncMock(return_value=_execute_scalars_all())  # no relations

        result = await svc.get_lineage(vid)

        assert result["version"]["id"] == vid
        assert result["ancestors"] == []
        assert result["descendants"] == []

    @pytest.mark.asyncio
    async def test_with_ancestors_and_descendants(self):
        vid = str(uuid4())
        parent_id = str(uuid4())
        child_id = str(uuid4())

        ver = _make_version(vid, "明刻本")
        ancestor_rel = _make_version_relation(parent_id, vid, "derived_from")
        descendant_rel = _make_version_relation(vid, child_id, "revised_from")

        parent_ver = _make_version(parent_id, "宋刻本")
        child_ver = _make_version(child_id, "清刻本")

        session = AsyncMock()
        svc = VersionComparisonService(session)
        svc.version_repo.get_by_id = AsyncMock(return_value=ver)
        session.execute = AsyncMock(
            side_effect=[
                _execute_scalars_all(ancestor_rel, descendant_rel),  # relations
                _execute_scalars_all(parent_ver, child_ver),  # related versions
            ]
        )

        result = await svc.get_lineage(vid)

        assert len(result["ancestors"]) == 1
        assert result["ancestors"][0]["source"]["id"] == parent_id
        assert len(result["descendants"]) == 1
        assert result["descendants"][0]["target"]["id"] == child_id


# ---------------------------------------------------------------------------
# VersionComparisonService — compare_passages
# ---------------------------------------------------------------------------


class TestComparePassages:
    @pytest.mark.asyncio
    async def test_first_passage_not_found_raises(self):
        pid = str(uuid4())
        session = AsyncMock()
        svc = VersionComparisonService(session)
        svc.passage_repo.get_by_id = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match=f"Passage {pid} not found"):
            await svc.compare_passages(pid, str(uuid4()))

    @pytest.mark.asyncio
    async def test_second_passage_not_found_raises(self):
        pid1 = str(uuid4())
        pid2 = str(uuid4())
        p1 = _make_passage(pid1, "甲乙丙丁")

        session = AsyncMock()
        svc = VersionComparisonService(session)
        svc.passage_repo.get_by_id = AsyncMock(side_effect=[p1, None])

        with pytest.raises(ValueError, match=f"Passage {pid2} not found"):
            await svc.compare_passages(pid1, pid2)

    @pytest.mark.asyncio
    async def test_identical_texts_zero_differences(self):
        pid1 = str(uuid4())
        pid2 = str(uuid4())
        text = "针灸甲乙经卷一"
        p1 = _make_passage(pid1, text)
        p2 = _make_passage(pid2, text)

        session = AsyncMock()
        svc = VersionComparisonService(session)
        svc.passage_repo.get_by_id = AsyncMock(side_effect=[p1, p2])

        result = await svc.compare_passages(pid1, pid2)

        assert result["differences"] == 0
        assert result["operations"] == []
        assert result["similarity_ratio"] == 1.0

    @pytest.mark.asyncio
    async def test_different_texts_returns_diffs(self):
        pid1 = str(uuid4())
        pid2 = str(uuid4())
        p1 = _make_passage(pid1, "甲乙丙丁")
        p2 = _make_passage(pid2, "甲乙戊丁")

        session = AsyncMock()
        svc = VersionComparisonService(session)
        svc.passage_repo.get_by_id = AsyncMock(side_effect=[p1, p2])

        result = await svc.compare_passages(pid1, pid2)

        assert result["differences"] > 0
        assert len(result["operations"]) > 0
        assert result["similarity_ratio"] < 1.0
        assert result["source_passage"]["text"] == "甲乙丙丁"
        assert result["target_passage"]["text"] == "甲乙戊丁"

    @pytest.mark.asyncio
    async def test_insert_only_diff(self):
        pid1 = str(uuid4())
        pid2 = str(uuid4())
        p1 = _make_passage(pid1, "甲乙")
        p2 = _make_passage(pid2, "甲乙丙丁")

        session = AsyncMock()
        svc = VersionComparisonService(session)
        svc.passage_repo.get_by_id = AsyncMock(side_effect=[p1, p2])

        result = await svc.compare_passages(pid1, pid2)

        assert result["differences"] >= 1
        ops = result["operations"]
        assert any(o["op"] == "insert" for o in ops)


# ---------------------------------------------------------------------------
# VersionComparisonService — add_relation
# ---------------------------------------------------------------------------


class TestAddRelation:
    @pytest.mark.asyncio
    async def test_invalid_relation_type_raises(self):
        session = AsyncMock()
        svc = VersionComparisonService(session)

        with pytest.raises(ValueError, match="Invalid relation_type"):
            await svc.add_relation(str(uuid4()), str(uuid4()), "bogus_type")

    @pytest.mark.asyncio
    async def test_valid_relation_type_creates_relation(self):
        sid = str(uuid4())
        tid = str(uuid4())
        session = MagicMock()
        session.flush = AsyncMock()
        svc = VersionComparisonService(session)

        rel = await svc.add_relation(sid, tid, "derived_from", "desc", "evidence text")

        assert rel.source_version_id == sid
        assert rel.target_version_id == tid
        assert rel.relation_type == "derived_from"
        assert rel.description == "desc"
        assert rel.evidence == "evidence text"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()


# ---------------------------------------------------------------------------
# VersionComparisonService — get_saved_diff
# ---------------------------------------------------------------------------


class TestGetSavedDiff:
    @pytest.mark.asyncio
    async def test_not_found_returns_none(self):
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalar_one(None))
        svc = VersionComparisonService(session)

        result = await svc.get_saved_diff(str(uuid4()))
        assert result is None

    @pytest.mark.asyncio
    async def test_found_returns_parsed_diff(self):
        diff_id = str(uuid4())
        src_id = str(uuid4())
        tgt_id = str(uuid4())
        diff_data = json.dumps(
            [{"op": "replace", "source_text": "a", "target_text": "b"}]
        )
        diff = _make_version_diff(diff_id, src_id, tgt_id, diff_data, "1 diff", 1)

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalar_one(diff))
        svc = VersionComparisonService(session)

        result = await svc.get_saved_diff(diff_id)

        assert result is not None
        assert result["id"] == diff_id
        assert result["source_version_id"] == src_id
        assert result["target_version_id"] == tgt_id
        assert result["total_differences"] == 1
        assert isinstance(result["diff_data"], list)
        assert result["diff_data"][0]["op"] == "replace"


# ---------------------------------------------------------------------------
# VersionComparisonService — create_passage_mapping
# ---------------------------------------------------------------------------


class TestCreatePassageMapping:
    @pytest.mark.asyncio
    async def test_invalid_mapping_type_raises(self):
        session = AsyncMock()
        svc = VersionComparisonService(session)

        with pytest.raises(ValueError, match="Invalid mapping_type"):
            await svc.create_passage_mapping(str(uuid4()), str(uuid4()), "bogus")

    @pytest.mark.asyncio
    async def test_valid_mapping_created(self):
        sid = str(uuid4())
        tid = str(uuid4())
        session = MagicMock()
        session.flush = AsyncMock()
        svc = VersionComparisonService(session)

        mapping = await svc.create_passage_mapping(
            sid, tid, "equivalent", "same passage"
        )

        assert mapping.source_passage_id == sid
        assert mapping.target_passage_id == tid
        assert mapping.mapping_type == "equivalent"
        assert mapping.description == "same passage"
        session.add.assert_called_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_default_mapping_type(self):
        sid = str(uuid4())
        tid = str(uuid4())
        session = MagicMock()
        session.flush = AsyncMock()
        svc = VersionComparisonService(session)

        mapping = await svc.create_passage_mapping(sid, tid)

        assert mapping.mapping_type == "equivalent"


# ---------------------------------------------------------------------------
# VersionComparisonService — get_passage_mappings
# ---------------------------------------------------------------------------


class TestGetPassageMappings:
    @pytest.mark.asyncio
    async def test_no_passages_returns_empty(self):
        vid = str(uuid4())
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalars_all())  # empty
        svc = VersionComparisonService(session)

        result = await svc.get_passage_mappings(vid)
        assert result == []

    @pytest.mark.asyncio
    async def test_passages_without_mappings_returns_empty(self):
        vid = str(uuid4())
        p = _make_passage("p1", "text")

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _execute_scalars_all(p),  # passages query
                _execute_scalars_all(),  # mappings query — empty
            ]
        )
        svc = VersionComparisonService(session)

        result = await svc.get_passage_mappings(vid)
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_mappings_as_dicts(self):
        vid = str(uuid4())
        p = _make_passage("p1", "text")
        mapping = MagicMock(spec=PassageMapping)
        mapping.id = "m1"
        mapping.source_passage_id = "p1"
        mapping.target_passage_id = "p2"
        mapping.mapping_type = "equivalent"
        mapping.description = "desc"
        mapping.is_verified = True

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _execute_scalars_all(p),  # passages query
                _execute_scalars_all(mapping),  # mappings query
            ]
        )
        svc = VersionComparisonService(session)

        result = await svc.get_passage_mappings(vid)
        assert len(result) == 1
        assert result[0]["id"] == "m1"
        assert result[0]["mapping_type"] == "equivalent"


# ---------------------------------------------------------------------------
# VersionComparisonService — run_full_compare
# ---------------------------------------------------------------------------


def _run_full_compare_session(execute_side_effect):
    """Create a MagicMock session for run_full_compare with sync add + async execute/flush."""
    s = MagicMock()
    s.execute = (
        AsyncMock(side_effect=execute_side_effect)
        if isinstance(execute_side_effect, list)
        else AsyncMock(return_value=execute_side_effect)
    )
    s.flush = AsyncMock()
    return s


class TestRunFullCompare:
    @pytest.mark.asyncio
    async def test_order_aligned_fallback_when_no_mappings(self):
        src_id = str(uuid4())
        tgt_id = str(uuid4())
        p1 = _make_passage("p1", "甲乙丙丁")
        p2 = _make_passage("p2", "甲乙戊丁")

        session = _run_full_compare_session(
            [
                _execute_scalars_all(p1),  # src passages
                _execute_scalars_all(p2),  # tgt passages
                _execute_scalars_all(),  # mappings — empty
            ]
        )
        svc = VersionComparisonService(session)

        # Patch compare_passages to avoid needing actual passage_repo
        svc.compare_passages = AsyncMock(
            return_value={
                "source_passage": {"id": "p1", "text": "甲乙丙丁"},
                "target_passage": {"id": "p2", "text": "甲乙戊丁"},
                "differences": 1,
                "operations": [
                    {"op": "replace", "source_text": "丙", "target_text": "戊"}
                ],
                "similarity_ratio": 0.75,
            }
        )

        result = await svc.run_full_compare(src_id, tgt_id)

        assert result["passage_pairs"] == 1
        assert result["total_differences"] >= 1
        assert "diff_id" in result

    @pytest.mark.asyncio
    async def test_source_only_adds_delete_placeholder(self):
        src_id = str(uuid4())
        tgt_id = str(uuid4())
        p1 = _make_passage("p1", "甲乙丙丁")

        session = _run_full_compare_session(
            [
                _execute_scalars_all(p1),  # src passages
                _execute_scalars_all(),  # tgt passages — empty
                _execute_scalars_all(),  # mappings — empty
            ]
        )
        svc = VersionComparisonService(session)

        result = await svc.run_full_compare(src_id, tgt_id)

        assert result["passage_pairs"] == 1
        comps = result["comparisons"]
        assert comps[0]["target_passage"] is None
        assert any(o["op"] == "delete" for o in comps[0]["operations"])

    @pytest.mark.asyncio
    async def test_target_only_adds_insert_placeholder(self):
        src_id = str(uuid4())
        tgt_id = str(uuid4())
        p2 = _make_passage("p2", "甲乙丙丁")

        session = _run_full_compare_session(
            [
                _execute_scalars_all(),  # src passages — empty
                _execute_scalars_all(p2),  # tgt passages
                _execute_scalars_all(),  # mappings — empty
            ]
        )
        svc = VersionComparisonService(session)

        result = await svc.run_full_compare(src_id, tgt_id)

        assert result["passage_pairs"] == 1
        comps = result["comparisons"]
        assert comps[0]["source_passage"] is None
        assert any(o["op"] == "insert" for o in comps[0]["operations"])


# ---------------------------------------------------------------------------
# Commentary module-level functions
# ---------------------------------------------------------------------------


class TestCreateCommentary:
    @pytest.mark.asyncio
    async def test_creates_and_returns_response(self):
        cid = str(uuid4())
        c = MagicMock(spec=Commentary)
        c.id = cid
        c.passage_id = "pid-1"
        c.version_id = "vid-1"
        c.author_id = "aid-1"
        c.commentary_type = "end_of_passage"
        c.layer = "modern"
        c.content_text = "此条为..."
        c.target_position_start = 0
        c.target_position_end = 10
        c.parent_id = None
        c.relation_type = None
        c.created_at = datetime.now(UTC)
        c.updated_at = datetime.now(UTC)

        session = MagicMock()
        session.flush = AsyncMock()
        session.refresh = AsyncMock()

        data = CommentaryCreate(
            passage_id="pid-1",
            version_id="vid-1",
            author_id="aid-1",
            commentary_type="end_of_passage",
            layer="modern",
            content_text="此条为...",
            target_position_start=0,
            target_position_end=10,
            parent_id=None,
            relation_type=None,
        )

        with patch("app.services.version_center.Commentary", return_value=c):
            resp = await create_commentary(session, data)

        session.add.assert_called_once_with(c)
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once_with(c)
        assert resp.id == cid
        assert resp.passage_id == "pid-1"
        assert resp.content_text == "此条为..."
        assert resp.commentary_type == "end_of_passage"


class TestGetCommentariesForPassage:
    @pytest.mark.asyncio
    async def test_returns_all_commentaries(self):
        pid = str(uuid4())
        now = datetime.now(UTC)
        c = MagicMock(spec=Commentary)
        c.id = "c1"
        c.passage_id = pid
        c.version_id = None
        c.author_id = None
        c.commentary_type = "end_of_passage"
        c.layer = "modern"
        c.content_text = "注文"
        c.target_position_start = None
        c.target_position_end = None
        c.parent_id = None
        c.relation_type = None
        c.created_at = now
        c.updated_at = now

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalars_all(c))

        results = await get_commentaries_for_passage(session, pid)

        assert len(results) == 1
        assert results[0].id == "c1"
        assert results[0].content_text == "注文"

    @pytest.mark.asyncio
    async def test_filters_by_layer(self):
        pid = str(uuid4())
        now = datetime.now(UTC)
        c = MagicMock(spec=Commentary)
        c.id = "c1"
        c.passage_id = pid
        c.version_id = None
        c.author_id = None
        c.commentary_type = "sub_commentary"
        c.layer = "tang"
        c.content_text = "唐注"
        c.target_position_start = None
        c.target_position_end = None
        c.parent_id = None
        c.relation_type = None
        c.created_at = now
        c.updated_at = now

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalars_all(c))

        results = await get_commentaries_for_passage(session, pid, layer="tang")

        assert len(results) == 1
        assert results[0].layer == "tang"


class TestGetCommentaryChain:
    @pytest.mark.asyncio
    async def test_single_commentary_chain(self):
        cid = str(uuid4())
        now = datetime.now(UTC)
        c = MagicMock(spec=Commentary)
        c.id = cid
        c.passage_id = str(uuid4())
        c.version_id = None
        c.author_id = None
        c.commentary_type = "end_of_passage"
        c.layer = "ming"
        c.content_text = "明人注"
        c.target_position_start = None
        c.target_position_end = None
        c.parent_id = None  # root
        c.relation_type = None
        c.created_at = now
        c.updated_at = now

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalar_one(c))

        chain = await get_commentary_chain(session, cid)

        assert len(chain) == 1
        assert chain[0].id == cid

    @pytest.mark.asyncio
    async def test_multi_level_chain_root_first(self):
        root_id = str(uuid4())
        mid_id = str(uuid4())
        leaf_id = str(uuid4())

        now = datetime.now(UTC)

        leaf = MagicMock(spec=Commentary)
        leaf.id = leaf_id
        leaf.passage_id = str(uuid4())
        leaf.version_id = None
        leaf.author_id = None
        leaf.commentary_type = "sub_commentary"
        leaf.layer = "song"
        leaf.content_text = "第三层"
        leaf.target_position_start = None
        leaf.target_position_end = None
        leaf.parent_id = mid_id
        leaf.relation_type = None
        leaf.created_at = now
        leaf.updated_at = now

        mid = MagicMock(spec=Commentary)
        mid.id = mid_id
        mid.passage_id = str(uuid4())
        mid.version_id = None
        mid.author_id = None
        mid.commentary_type = "sub_commentary"
        mid.layer = "tang"
        mid.content_text = "第二层"
        mid.target_position_start = None
        mid.target_position_end = None
        mid.parent_id = root_id
        mid.relation_type = None
        mid.created_at = now
        mid.updated_at = now

        root = MagicMock(spec=Commentary)
        root.id = root_id
        root.passage_id = str(uuid4())
        root.version_id = None
        root.author_id = None
        root.commentary_type = "end_of_passage"
        root.layer = "han"
        root.content_text = "第一层"
        root.target_position_start = None
        root.target_position_end = None
        root.parent_id = None
        root.relation_type = None
        root.created_at = now
        root.updated_at = now

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _execute_scalar_one(leaf),
                _execute_scalar_one(mid),
                _execute_scalar_one(root),
            ]
        )

        chain = await get_commentary_chain(session, leaf_id)

        assert len(chain) == 3
        assert chain[0].id == root_id  # root first
        assert chain[1].id == mid_id
        assert chain[2].id == leaf_id

    @pytest.mark.asyncio
    async def test_not_found_returns_empty(self):
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalar_one(None))

        chain = await get_commentary_chain(session, str(uuid4()))
        assert chain == []


class TestGetCommentaryGraph:
    @pytest.mark.asyncio
    async def test_returns_nodes_and_edges(self):
        pid = str(uuid4())
        now = datetime.now(UTC)
        parent = MagicMock(spec=Commentary)
        parent.id = "c-root"
        parent.passage_id = pid
        parent.version_id = None
        parent.author_id = None
        parent.commentary_type = "end_of_passage"
        parent.layer = "han"
        parent.content_text = "root"
        parent.target_position_start = None
        parent.target_position_end = None
        parent.parent_id = None
        parent.relation_type = None
        parent.created_at = now
        parent.updated_at = now

        child = MagicMock(spec=Commentary)
        child.id = "c-child"
        child.passage_id = pid
        child.version_id = None
        child.author_id = None
        child.commentary_type = "sub_commentary"
        child.layer = "tang"
        child.content_text = "child"
        child.target_position_start = None
        child.target_position_end = None
        child.parent_id = "c-root"
        child.relation_type = "expands"
        child.created_at = now
        child.updated_at = now

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalars_all(parent, child))

        graph = await get_commentary_graph(session, pid)

        assert len(graph["nodes"]) == 2
        assert len(graph["edges"]) == 1
        assert graph["edges"][0]["parent_id"] == "c-root"
        assert graph["edges"][0]["child_id"] == "c-child"
        assert graph["edges"][0]["relation_type"] == "expands"


# ---------------------------------------------------------------------------
# Module-level functions — version tree / distance
# ---------------------------------------------------------------------------


class TestComputeDistanceMatrix:
    @pytest.mark.asyncio
    async def test_no_diff_returns_max_distance(self):
        ids = [str(uuid4()), str(uuid4())]

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalar_one(None))

        matrix = await compute_distance_matrix(session, ids)

        key = f"{ids[0]}-{ids[1]}"
        assert key in matrix
        assert matrix[key] == 1.0

    @pytest.mark.asyncio
    async def test_with_diff_returns_computed_distance(self):
        ids = [str(uuid4()), str(uuid4())]
        diff = _make_version_diff(
            id_=str(uuid4()),
            source_id=ids[0],
            target_id=ids[1],
            diff_data=json.dumps({"lines_changed": 30, "total_lines": 100}),
        )

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalar_one(diff))

        matrix = await compute_distance_matrix(session, ids)

        key = f"{ids[0]}-{ids[1]}"
        assert matrix[key] == 0.3  # 30 / 100


class TestComputeVersionTree:
    @pytest.mark.asyncio
    async def test_version_not_found_raises(self):
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_execute_scalar_one(None))

        with pytest.raises(ValueError, match="not found"):
            await compute_version_tree(session, str(uuid4()))

    @pytest.mark.asyncio
    async def test_single_version_no_relations(self):
        vid = str(uuid4())
        ver = MagicMock(spec=Version)
        ver.id = vid
        ver.version_name = "孤本"
        ver.era = "ming"
        ver.year = 1600
        ver.book_id = str(uuid4())

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _execute_scalar_one(ver),  # root version lookup
                _execute_scalars_all(),  # up BFS — empty
                _execute_scalars_all(),  # down BFS — empty
                _execute_scalars_all(ver),  # all_versions query
                # distance matrix — compute_distance_matrix called
                # divergence — TextualVariant query
                _execute_scalars_all(),  # no variants
            ]
        )

        tree = await compute_version_tree(session, vid)

        assert tree["root_version"]["id"] == vid
        assert tree["tree"] == []
        assert tree["divergence_points"] == []
