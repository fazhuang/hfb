"""Adjacency-list graph store with bidirectional lookup."""

from __future__ import annotations

from tcm_kg.models import Edge, Node


class GraphStore:
    """In-memory graph store using adjacency lists.

    Supports:
    - O(1) node lookup by ID
    - O(1) edge insertion
    - O(degree) neighbor queries
    - Bidirectional traversal (forward + reverse indices)

    >>> store = GraphStore()
    >>> node = Node(id="p1", type="Person", properties={"name": "皇甫谧"})
    >>> store.add_node(node)
    >>> store.get_node("p1").properties["name"]
    '皇甫谧'
    """

    def __init__(self) -> None:
        self._nodes: dict[str, Node] = {}
        # source_id → list of outgoing edges
        self._edges_out: dict[str, list[Edge]] = {}
        # target_id → list of incoming edges
        self._edges_in: dict[str, list[Edge]] = {}

    def add_node(self, node: Node) -> None:
        """Add a node. Existing node with same ID is overwritten."""
        self._nodes[node.id] = node
        if node.id not in self._edges_out:
            self._edges_out[node.id] = []
        if node.id not in self._edges_in:
            self._edges_in[node.id] = []

    def get_node(self, node_id: str) -> Node | None:
        """Get a node by ID, or None if not found."""
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        """Check if a node exists."""
        return node_id in self._nodes

    def add_edge(self, edge: Edge) -> None:
        """Add a directed edge. Silently skips if source or target node missing."""
        if edge.source_id not in self._nodes or edge.target_id not in self._nodes:
            return
        self._edges_out.setdefault(edge.source_id, []).append(edge)
        self._edges_in.setdefault(edge.target_id, []).append(edge)

    def neighbors_out(self, node_id: str) -> list[tuple[Node, Edge]]:
        """Get all outgoing (target_node, edge) pairs."""
        if node_id not in self._edges_out:
            return []
        result: list[tuple[Node, Edge]] = []
        for edge in self._edges_out[node_id]:
            target = self._nodes.get(edge.target_id)
            if target is not None:
                result.append((target, edge))
        return result

    def neighbors_in(self, node_id: str) -> list[tuple[Node, Edge]]:
        """Get all incoming (source_node, edge) pairs."""
        if node_id not in self._edges_in:
            return []
        result: list[tuple[Node, Edge]] = []
        for edge in self._edges_in[node_id]:
            source = self._nodes.get(edge.source_id)
            if source is not None:
                result.append((source, edge))
        return result

    def edges_from(self, node_id: str) -> list[Edge]:
        """Get all outgoing edges from a node."""
        return list(self._edges_out.get(node_id, []))

    def edges_to(self, node_id: str) -> list[Edge]:
        """Get all incoming edges to a node."""
        return list(self._edges_in.get(node_id, []))

    @property
    def node_count(self) -> int:
        return len(self._nodes)

    @property
    def edge_count(self) -> int:
        return sum(len(edges) for edges in self._edges_out.values())

    @property
    def nodes(self) -> dict[str, Node]:
        """All nodes. Read-only access — mutate via add_node()."""
        return dict(self._nodes)

    def __repr__(self) -> str:
        return f"<GraphStore nodes={self.node_count} edges={self.edge_count}>"
