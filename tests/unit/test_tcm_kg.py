"""Unit tests for TCM Knowledge Graph package."""

import pytest

from tcm_kg.models import Node, Edge, Subgraph
from tcm_kg.store import GraphStore
from tcm_kg.query import GraphQuery
from tcm_kg.builder import KGBuilder


class TestNode:
    def test_create_node(self) -> None:
        node = Node(id="p1", type="Person", properties={"name": "皇甫谧"})
        assert node.id == "p1"
        assert node.type == "Person"
        assert node.properties["name"] == "皇甫谧"

    def test_node_equality(self) -> None:
        a = Node(id="x", type="T", properties={})
        b = Node(id="x", type="U", properties={"extra": True})
        assert a == b
        assert hash(a) == hash(b)

    def test_node_inequality(self) -> None:
        a = Node(id="x", type="T", properties={})
        b = Node(id="y", type="T", properties={})
        assert a != b


class TestEdge:
    def test_create_edge(self) -> None:
        edge = Edge(
            source_id="p1",
            target_id="t1",
            relation="authored",
            weight=0.9,
            source_ref="《晋书·皇甫谧传》",
        )
        assert edge.source_id == "p1"
        assert edge.relation == "authored"
        assert edge.weight == 0.9

    def test_edge_defaults(self) -> None:
        edge = Edge(source_id="a", target_id="b", relation="related_to")
        assert edge.weight == 1.0
        assert edge.source_ref is None

    def test_edge_equality(self) -> None:
        a = Edge("a", "b", "r", source_ref="ref1")
        b = Edge("a", "b", "r", source_ref="ref1")
        assert a == b

    def test_edge_different_source_ref(self) -> None:
        a = Edge(source_id="a", target_id="b", relation="r", source_ref="ref1")
        b = Edge(source_id="a", target_id="b", relation="r", source_ref="ref2")
        assert a != b


class TestSubgraph:
    def test_empty_subgraph(self) -> None:
        sg = Subgraph()
        assert sg.node_count == 0
        assert sg.edge_count == 0

    def test_populated_subgraph(self) -> None:
        sg = Subgraph(
            nodes={"a": Node(id="a", type="T", properties={})},
            edges=[Edge("a", "b", "r")],
        )
        assert sg.node_count == 1
        assert sg.edge_count == 1


class TestGraphStore:
    @pytest.fixture
    def store(self) -> GraphStore:
        return GraphStore()

    def test_add_node(self, store: GraphStore) -> None:
        node = Node(id="p1", type="Person", properties={"name": "华佗"})
        store.add_node(node)
        assert store.node_count == 1
        assert store.has_node("p1")

    def test_get_node(self, store: GraphStore) -> None:
        node = Node(id="t1", type="Text", properties={"title": "伤寒论"})
        store.add_node(node)
        retrieved = store.get_node("t1")
        assert retrieved is not None
        assert retrieved.properties["title"] == "伤寒论"

    def test_get_node_missing(self, store: GraphStore) -> None:
        assert store.get_node("nonexistent") is None

    def test_overwrite_node(self, store: GraphStore) -> None:
        store.add_node(Node(id="x", type="Person", properties={"name": "旧名"}))
        store.add_node(Node(id="x", type="Person", properties={"name": "新名"}))
        assert store.get_node("x").properties["name"] == "新名"  # type: ignore[union-attr]

    def test_add_edge_skips_missing_nodes(self, store: GraphStore) -> None:
        store.add_node(Node(id="a", type="Person", properties={"name": "A"}))
        store.add_edge(Edge("a", "b", "related_to"))
        assert store.edge_count == 0  # b doesn't exist

    def test_add_edge_success(self, store: GraphStore) -> None:
        store.add_node(Node(id="a", type="Person", properties={"name": "A"}))
        store.add_node(Node(id="b", type="Person", properties={"name": "B"}))
        store.add_edge(Edge("a", "b", "related_to"))
        assert store.edge_count == 1

    def test_neighbors_out(self, store: GraphStore) -> None:
        store.add_node(Node(id="a", type="Person", properties={"name": "A"}))
        store.add_node(Node(id="b", type="Text", properties={"title": "B"}))
        store.add_node(Node(id="c", type="Text", properties={"title": "C"}))
        store.add_edge(Edge("a", "b", "authored"))
        store.add_edge(Edge("a", "c", "commented_on"))

        neighbors = store.neighbors_out("a")
        assert len(neighbors) == 2
        target_ids = {n.id for n, _ in neighbors}
        assert target_ids == {"b", "c"}

    def test_neighbors_in(self, store: GraphStore) -> None:
        store.add_node(Node(id="a", type="Person", properties={"name": "A"}))
        store.add_node(Node(id="b", type="Text", properties={"title": "B"}))
        store.add_node(Node(id="c", type="Text", properties={"title": "C"}))
        store.add_edge(Edge("a", "b", "authored"))
        store.add_edge(Edge("c", "b", "references"))

        neighbors = store.neighbors_in("b")
        assert len(neighbors) == 2
        source_ids = {n.id for n, _ in neighbors}
        assert source_ids == {"a", "c"}

    def test_nodes_property_returns_copy(self, store: GraphStore) -> None:
        store.add_node(Node(id="x", type="Person", properties={"name": "X"}))
        nodes = store.nodes
        nodes["y"] = Node(id="y", type="Person", properties={})
        assert store.node_count == 1  # store not mutated


class TestGraphQuery:
    @pytest.fixture
    def populated_store(self) -> GraphStore:
        """Build: 皇甫谧 → authored → 针灸甲乙经 → treats → 方剂 → treats → 症候"""
        store = GraphStore()

        store.add_node(Node(
            id="person_huangfumi",
            type="Person",
            properties={"name": "皇甫谧", "name_zh": "皇甫谧", "dynasty": "魏晋"},
        ))
        store.add_node(Node(
            id="text_zhenjiu",
            type="Text",
            properties={"title": "针灸甲乙经", "title_zh": "鍼灸甲乙經", "category": "针灸"},
        ))
        store.add_node(Node(
            id="prescription_baihu",
            type="Prescription",
            properties={"name": "白虎汤", "name_zh": "白虎湯"},
        ))
        store.add_node(Node(
            id="prescription_guizhi",
            type="Prescription",
            properties={"name": "桂枝汤", "name_zh": "桂枝湯"},
        ))
        store.add_node(Node(
            id="symptom_fever",
            type="Symptom",
            properties={"name": "发热", "name_zh": "發熱", "category": "热证"},
        ))
        store.add_node(Node(
            id="herb_gancao",
            type="Herb",
            properties={"name": "甘草", "latin_name": "Glycyrrhiza uralensis"},
        ))

        store.add_edge(Edge("person_huangfumi", "text_zhenjiu", "authored",
                             weight=1.0, source_ref="《晋书·皇甫谧传》"))
        store.add_edge(Edge("text_zhenjiu", "prescription_guizhi", "contains",
                             weight=0.95, source_ref="《针灸甲乙经·卷七》"))
        store.add_edge(Edge("text_zhenjiu", "prescription_baihu", "contains",
                             weight=0.85, source_ref="《针灸甲乙经·卷七》"))
        store.add_edge(Edge("prescription_baihu", "symptom_fever", "treats",
                             weight=0.9, source_ref="《伤寒论》"))
        store.add_edge(Edge("prescription_baihu", "herb_gancao", "contains",
                             weight=1.0, source_ref="《伤寒论》"))
        store.add_edge(Edge("prescription_guizhi", "symptom_fever", "treats",
                             weight=0.8, source_ref="《伤寒论》"))

        return store

    def test_find_path_direct(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        paths = q.find_path("person_huangfumi", "text_zhenjiu", max_hops=1)
        assert len(paths) == 1
        assert paths[0][0].relation == "authored"

    def test_find_path_two_hops(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        # 皇甫谧 → 针灸甲乙经 → 白虎汤 (2 hops)
        paths = q.find_path("person_huangfumi", "prescription_baihu", max_hops=2)
        assert len(paths) >= 1
        # First hop: authored, Second hop: contains
        path = paths[0]
        assert path[0].relation == "authored"
        assert path[1].relation == "contains"

    def test_find_path_four_hops(self, populated_store: GraphStore) -> None:
        """Acceptance test: 皇甫谧 → 针灸甲乙经 → 方剂 → 症候 (4 hops)"""
        q = GraphQuery(populated_store)
        # 皇甫谧 → authored → 针灸甲乙经 → contains → 白虎汤 → treats → 发热 = 3 hops
        # Also: 白虎汤 → contains → 甘草 = 1 more hop from 白虎汤
        paths = q.find_path("person_huangfumi", "symptom_fever", max_hops=3)
        # Two possible paths via two prescriptions
        assert len(paths) >= 2

        # Verify at least one path goes: authored → contains → treats
        found_expected = False
        for path in paths:
            rels = [e.relation for e in path]
            if rels == ["authored", "contains", "treats"]:
                found_expected = True
                break
        assert found_expected

    def test_find_path_no_path(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        # No path from 甘草 back to 皇甫谧 (edges are directional)
        paths = q.find_path("herb_gancao", "person_huangfumi", max_hops=5)
        assert len(paths) == 0

    def test_find_path_nonexistent_node(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        assert q.find_path("ghost", "person_huangfumi") == []
        assert q.find_path("person_huangfumi", "ghost") == []

    def test_shortest_path(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        path = q.shortest_path("person_huangfumi", "prescription_baihu", max_hops=5)
        assert path is not None
        assert len(path) == 2  # 2 hops is shortest
        assert path[0].source_id == "person_huangfumi"
        assert path[-1].target_id == "prescription_baihu"

    def test_expand_subgraph(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        sub = q.expand("text_zhenjiu", max_hops=1)
        # 针灸甲乙经 → 白虎汤, 桂枝汤 (2 prescriptions)
        assert sub.node_count >= 3  # self + 2 prescriptions
        assert sub.edge_count == 2

    def test_expand_with_relation_filter(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        sub = q.expand("prescription_baihu", relation="treats", max_hops=1)
        # 白虎汤 → treats → 发热 only (contains → 甘草 filtered out)
        has_symptom = any(
            n.type == "Symptom" for n in sub.nodes.values()
        )
        has_herb = any(
            n.type == "Herb" for n in sub.nodes.values()
        )
        assert has_symptom
        assert not has_herb

    def test_related_entities(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        related = q.related_entities("text_zhenjiu", max_hops=1)
        # Should find the two prescriptions
        assert len(related) == 2
        types = {n.type for n in related}
        assert types == {"Prescription"}

    def test_related_entities_max_hops_2(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        related = q.related_entities("person_huangfumi", max_hops=2)
        # 皇甫谧 → 针灸甲乙经 (1) → 白虎汤 + 桂枝汤 (2)
        assert len(related) >= 3

    def test_connected(self, populated_store: GraphStore) -> None:
        q = GraphQuery(populated_store)
        assert q.connected("person_huangfumi")
        assert not q.connected("symptom_fever")  # fever has no outgoing edges


class TestKGBuilder:
    def test_from_triples(self) -> None:
        triples = [
            (
                Node("p1", "Person", {"name": "皇甫谧"}),
                "authored",
                Node("t1", "Text", {"title": "针灸甲乙经"}),
            ),
            (
                Node("t1", "Text", {"title": "针灸甲乙经"}),
                "contains",
                Node("pres1", "Prescription", {"name": "白虎汤"}),
            ),
        ]
        store = KGBuilder.from_triples(triples)
        assert store.node_count == 3
        assert store.edge_count == 2

        # Verify edge exists
        paths = GraphQuery(store).find_path("p1", "pres1", max_hops=2)
        assert len(paths) == 1

    def test_from_triples_with_source_refs(self) -> None:
        triples = [
            (
                Node("p1", "Person", {"name": "华佗"}),
                "authored",
                Node("t1", "Text", {"title": "中藏经"}),
            ),
        ]
        store = KGBuilder.from_triples(
            triples,
            source_refs=["《三国志·华佗传》"],
        )
        path = GraphQuery(store).find_path("p1", "t1")[0]
        assert path[0].source_ref == "《三国志·华佗传》"

    def test_merge(self) -> None:
        store = KGBuilder.from_triples([
            (Node("a", "Person", {"name": "A"}), "authored", Node("b", "Text", {"title": "B"})),
        ])
        assert store.node_count == 2

        KGBuilder.merge(store, [
            (Node("a", "Person", {"name": "A"}), "authored", Node("c", "Text", {"title": "C"})),
        ])
        assert store.node_count == 3
        assert store.edge_count == 2
