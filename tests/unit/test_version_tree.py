"""Tests for version tree — post-blocker-2 hardening.

Verifies that compute_version_tree() handles real UUID version IDs
without crashing on hyphen-split, supports exhaustive multi-layer
traversal without artificial depth caps, and produces deterministic output.
"""

import uuid

import pytest
from app.models.book import Book
from app.models.chapter import Chapter
from app.models.passage import Passage
from app.models.version import Version
from app.models.version_relation import VersionDiff
from app.models.version_relation import VersionRelation
from app.services.version_center import compute_distance_matrix
from app.services.version_center import compute_version_tree
from tests.conftest_db import db_session  # noqa: F401


# ── helpers ──────────────────────────────────────────────────────────


async def _seed_version_tree(db_session, version_ids: list[str]) -> None:
    """Seed multiple versions with a shared book + chapter for testing."""
    book = Book(id="b-vt-1", title="Test Book")
    db_session.add(book)
    await db_session.flush()

    chapter = Chapter(id="ch-vt-1", book_id=book.id, title="Test Chapter", order=1)
    db_session.add(chapter)
    await db_session.flush()

    for i, vid in enumerate(version_ids):
        v = Version(id=vid, book_id=book.id, version_name=f"Version {i}")
        db_session.add(v)
        p = Passage(
            id=f"pass-{i}-{vid[:8]}",
            chapter_id=chapter.id,
            version_id=vid,
            content_text=f"Content of version {i}",
            order=i + 1,
        )
        db_session.add(p)
    await db_session.flush()


async def _add_version_relation(
    db_session,
    source_id: str,
    target_id: str,
    relation_type: str = "derived_from",
) -> VersionRelation:
    rel = VersionRelation(
        source_version_id=source_id,
        target_version_id=target_id,
        relation_type=relation_type,
        description=f"{source_id[:8]} -> {target_id[:8]}",
    )
    db_session.add(rel)
    await db_session.flush()
    return rel


# ── existing tests ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_real_uuid_closest_to_no_crash(db_session):
    """Two standard 36-char UUID versions: no crash, closest_to correct."""
    vid_a = str(uuid.uuid4())
    vid_b = str(uuid.uuid4())

    await _seed_version_tree(db_session, [vid_a, vid_b])
    await _add_version_relation(db_session, vid_a, vid_b)

    diff = VersionDiff(
        source_version_id=vid_a,
        target_version_id=vid_b,
        diff_data='{"lines_changed": 50, "total_lines": 200}',
        diff_summary="test",
        total_differences=5,
    )
    db_session.add(diff)
    await db_session.flush()

    tree = await compute_version_tree(db_session, vid_a)
    assert tree is not None
    assert tree["root_version"]["id"] == vid_a

    closest = tree["closest_to"]
    assert len(closest) >= 1, f"Expected at least one closest version, got {closest}"
    closest_ids = [c["version_id"] for c in closest]
    assert vid_b in closest_ids, f"closest_to missing {vid_b}, got {closest_ids}"


@pytest.mark.asyncio
async def test_four_version_three_layer_lineage(db_session):
    """Four versions in a 3-layer chain: all edges and versions discovered."""
    v_root = str(uuid.uuid4())
    v_mid1 = str(uuid.uuid4())
    v_mid2 = str(uuid.uuid4())
    v_leaf = str(uuid.uuid4())

    await _seed_version_tree(db_session, [v_root, v_mid1, v_mid2, v_leaf])

    await _add_version_relation(db_session, v_root, v_mid1)
    await _add_version_relation(db_session, v_mid1, v_mid2)
    await _add_version_relation(db_session, v_mid2, v_leaf)

    tree = await compute_version_tree(db_session, v_root)
    assert len(tree["tree"]) == 3, f"Expected 3 edges, got {len(tree['tree'])}"

    tree_ids = set()
    for edge in tree["tree"]:
        tree_ids.add(edge["parent_id"])
        tree_ids.add(edge["child_id"])
    tree_ids.add(v_root)
    assert v_root in tree_ids
    assert v_mid1 in tree_ids
    assert v_mid2 in tree_ids
    assert v_leaf in tree_ids


@pytest.mark.asyncio
async def test_from_middle_sees_ancestors_and_descendants(db_session):
    """Query from a middle version: both ancestors and all descendants visible."""
    v_root = str(uuid.uuid4())
    v_mid = str(uuid.uuid4())
    v_leaf1 = str(uuid.uuid4())
    v_leaf2 = str(uuid.uuid4())

    await _seed_version_tree(db_session, [v_root, v_mid, v_leaf1, v_leaf2])

    await _add_version_relation(db_session, v_root, v_mid)
    await _add_version_relation(db_session, v_mid, v_leaf1)
    await _add_version_relation(db_session, v_mid, v_leaf2)

    tree = await compute_version_tree(db_session, v_mid)

    tree_ids = set()
    for edge in tree["tree"]:
        tree_ids.add(edge["parent_id"])
        tree_ids.add(edge["child_id"])
    tree_ids.add(v_mid)

    assert v_root in tree_ids, "Ancestor v_root not visible from middle"
    assert v_leaf1 in tree_ids, "Descendant v_leaf1 not visible from middle"
    assert v_leaf2 in tree_ids, "Descendant v_leaf2 not visible from middle"
    assert len(tree["tree"]) == 3


@pytest.mark.asyncio
async def test_cycle_terminates_no_duplicate_edges(db_session):
    """Cycle in version relations: terminates, no duplicate edges, deterministic."""
    v_a = str(uuid.uuid4())
    v_b = str(uuid.uuid4())

    await _seed_version_tree(db_session, [v_a, v_b])

    await _add_version_relation(db_session, v_a, v_b)
    await _add_version_relation(db_session, v_b, v_a)

    tree = await compute_version_tree(db_session, v_a)
    edge_count = len(tree["tree"])
    dedup_count = len(
        set((e["parent_id"], e["child_id"], e["relation_type"]) for e in tree["tree"])
    )
    assert edge_count == dedup_count, (
        f"Duplicate edges: {edge_count} raw, {dedup_count} unique"
    )
    assert edge_count <= 2


@pytest.mark.asyncio
async def test_consecutive_calls_consistent(db_session):
    """Two consecutive calls produce identical business data."""
    v_a = str(uuid.uuid4())
    v_b = str(uuid.uuid4())

    await _seed_version_tree(db_session, [v_a, v_b])
    await _add_version_relation(db_session, v_a, v_b)

    tree1 = await compute_version_tree(db_session, v_a)
    tree2 = await compute_version_tree(db_session, v_a)

    assert tree1["root_version"] == tree2["root_version"]
    assert tree1["tree"] == tree2["tree"]
    assert tree1["distance_matrix"] == tree2["distance_matrix"]
    assert tree1["closest_to"] == tree2["closest_to"]


# ── new tests: no artificial depth cap ───────────────────────────────


@pytest.mark.asyncio
async def test_five_version_four_edge_full_lineage(db_session):
    """Five UUID versions with four consecutive relations: all 4 edges
    returned, leaf version visible.  This exceeds the old MAX_DEPTH=3 cap."""
    versions = [str(uuid.uuid4()) for _ in range(5)]
    # v0 → v1 → v2 → v3 → v4
    await _seed_version_tree(db_session, versions)
    for i in range(4):
        await _add_version_relation(db_session, versions[i], versions[i + 1])

    tree = await compute_version_tree(db_session, versions[0])
    assert len(tree["tree"]) == 4, f"Expected 4 edges, got {len(tree['tree'])}"
    all_ids: set[str] = set()
    for e in tree["tree"]:
        all_ids.add(e["parent_id"])
        all_ids.add(e["child_id"])
    all_ids.add(versions[0])
    assert len(all_ids) == 5, f"Expected 5 versions, got {len(all_ids)}: {all_ids}"
    assert versions[4] in all_ids, "Leaf version must be visible"


@pytest.mark.asyncio
async def test_ten_version_long_chain_no_truncation(db_session):
    """Ten UUID versions in a long chain: no truncation, all edges returned."""
    versions = [str(uuid.uuid4()) for _ in range(10)]
    await _seed_version_tree(db_session, versions)
    for i in range(9):
        await _add_version_relation(db_session, versions[i], versions[i + 1])

    tree = await compute_version_tree(db_session, versions[0])
    assert len(tree["tree"]) == 9, (
        f"Expected 9 edges for 10-version chain, got {len(tree['tree'])}"
    )
    all_ids: set[str] = set()
    for e in tree["tree"]:
        all_ids.add(e["parent_id"])
        all_ids.add(e["child_id"])
    all_ids.add(versions[0])
    assert len(all_ids) == 10, f"Expected all 10 versions, got {len(all_ids)}"
    assert versions[9] in all_ids, "Tenth version must be visible"


@pytest.mark.asyncio
async def test_long_chain_from_middle_sees_all(db_session):
    """Query from middle of a 10-version chain: all ancestors and descendants visible."""
    versions = [str(uuid.uuid4()) for _ in range(10)]
    await _seed_version_tree(db_session, versions)
    for i in range(9):
        await _add_version_relation(db_session, versions[i], versions[i + 1])

    # Query from index 5 (6th version)
    mid = versions[5]
    tree = await compute_version_tree(db_session, mid)

    all_ids: set[str] = set()
    for e in tree["tree"]:
        all_ids.add(e["parent_id"])
        all_ids.add(e["child_id"])
    all_ids.add(mid)

    # All 10 versions must be reachable
    assert len(all_ids) == 10, (
        f"Expected all 10 versions from middle, got {len(all_ids)}"
    )
    for v in versions:
        assert v in all_ids, f"Version {v[:8]} not visible from middle"


@pytest.mark.asyncio
async def test_branching_lineage_all_branches_visible(db_session):
    """Branching lineage: all branches visible from the root."""
    v_root = str(uuid.uuid4())
    v_a1 = str(uuid.uuid4())
    v_a2 = str(uuid.uuid4())
    v_b1 = str(uuid.uuid4())
    v_b2 = str(uuid.uuid4())
    v_leaf = str(uuid.uuid4())

    await _seed_version_tree(db_session, [v_root, v_a1, v_a2, v_b1, v_b2, v_leaf])

    # Branch A: v_root → v_a1 → v_a2 → v_leaf
    # Branch B: v_root → v_b1 → v_b2
    await _add_version_relation(db_session, v_root, v_a1)
    await _add_version_relation(db_session, v_a1, v_a2)
    await _add_version_relation(db_session, v_a2, v_leaf)
    await _add_version_relation(db_session, v_root, v_b1)
    await _add_version_relation(db_session, v_b1, v_b2)

    tree = await compute_version_tree(db_session, v_root)
    assert len(tree["tree"]) == 5, (
        f"Expected 5 edges across both branches, got {len(tree['tree'])}"
    )

    all_ids: set[str] = set()
    for e in tree["tree"]:
        all_ids.add(e["parent_id"])
        all_ids.add(e["child_id"])
    all_ids.add(v_root)

    expected = {v_root, v_a1, v_a2, v_b1, v_b2, v_leaf}
    assert all_ids == expected, (
        f"Missing versions in branching tree: {expected - all_ids}"
    )


@pytest.mark.asyncio
async def test_cycle_in_long_chain_terminates_no_duplicates(db_session):
    """Cycle in a longer chain: terminates without duplicates."""
    versions = [str(uuid.uuid4()) for _ in range(6)]
    await _seed_version_tree(db_session, versions)

    # Linear: v0 → v1 → v2 → v3 → v4 → v5, plus back-edge: v5 → v2 (cycle)
    for i in range(5):
        await _add_version_relation(db_session, versions[i], versions[i + 1])
    await _add_version_relation(db_session, versions[5], versions[2])

    tree = await compute_version_tree(db_session, versions[0])
    # Must terminate and contain all unique edges
    edge_count = len(tree["tree"])
    dedup_count = len(
        set((e["parent_id"], e["child_id"], e["relation_type"]) for e in tree["tree"])
    )
    assert edge_count == dedup_count, (
        f"Duplicate edges in cyclic chain: {edge_count} raw, {dedup_count} unique"
    )
    # All 7 edges must be present (6 edges: 5 forward + 1 back)
    assert edge_count == 6, f"Expected 6 edges in cyclic chain, got {edge_count}"


@pytest.mark.asyncio
async def test_long_chain_consecutive_calls_consistent(db_session):
    """Consecutive calls on a 10-version chain produce identical business data."""
    versions = [str(uuid.uuid4()) for _ in range(10)]
    await _seed_version_tree(db_session, versions)
    for i in range(9):
        await _add_version_relation(db_session, versions[i], versions[i + 1])

    tree1 = await compute_version_tree(db_session, versions[0])
    tree2 = await compute_version_tree(db_session, versions[0])

    assert tree1["root_version"] == tree2["root_version"]
    assert tree1["tree"] == tree2["tree"]
    assert tree1["distance_matrix"] == tree2["distance_matrix"]
    assert tree1["closest_to"] == tree2["closest_to"]


# ── distance matrix tests ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_distance_matrix_empty(db_session):
    """Empty version list -> empty matrix."""
    matrix = await compute_distance_matrix(db_session, [])
    assert matrix == {}


@pytest.mark.asyncio
async def test_distance_matrix_single_version(db_session):
    """Single version -> empty matrix (no pairs)."""
    matrix = await compute_distance_matrix(db_session, ["v1"])
    assert matrix == {}


@pytest.mark.asyncio
async def test_distance_matrix_no_diff_data(db_session):
    """Two versions with no VersionDiff -> max distance."""
    matrix = await compute_distance_matrix(db_session, ["v1", "v2"])
    assert matrix.get("v1-v2", matrix.get("v2-v1")) == 1.0
