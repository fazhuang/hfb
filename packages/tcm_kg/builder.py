"""Knowledge graph builder — construct GraphStore from triples."""

from __future__ import annotations

from tcm_kg.models import Node, Edge
from tcm_kg.store import GraphStore


class KGBuilder:
    """Build a GraphStore from entity triples (source, relation, target).

    >>> builder = KGBuilder()
    >>> store = builder.from_triples([
    ...     (Node("p1", "Person", {"name": "皇甫谧"}), "authored",
    ...      Node("t1", "Text", {"title": "针灸甲乙经"})),
    ... ])
    >>> store.node_count
    2
    """

    @staticmethod
    def from_triples(
        triples: list[tuple[Node, str, Node]],
        source_refs: list[str] | None = None,
    ) -> GraphStore:
        """Build a graph store from a list of (source_node, relation, target_node) triples.

        Args:
            triples: List of (source, relation, target) triples.
            source_refs: Optional citation refs, one per triple. Empty string if None.
        """
        store = GraphStore()
        if source_refs is None:
            source_refs = [""] * len(triples)

        for i, (src_node, relation, tgt_node) in enumerate(triples):
            store.add_node(src_node)
            store.add_node(tgt_node)
            ref = source_refs[i] if i < len(source_refs) else ""
            store.add_edge(
                Edge(
                    source_id=src_node.id,
                    target_id=tgt_node.id,
                    relation=relation,
                    weight=1.0,
                    source_ref=ref,
                )
            )
        return store

    @staticmethod
    def merge(
        store: GraphStore,
        triples: list[tuple[Node, str, Node]],
        source_refs: list[str] | None = None,
    ) -> GraphStore:
        """Merge new triples into an existing store. Returns same store instance."""
        additions = KGBuilder.from_triples(triples, source_refs)
        for node in additions._nodes.values():
            store.add_node(node)
        for edges in additions._edges_out.values():
            for edge in edges:
                store.add_edge(edge)
        return store
