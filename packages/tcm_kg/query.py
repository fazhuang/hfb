"""Multi-hop graph query engine using BFS traversal."""

from __future__ import annotations

from collections import deque

from tcm_kg.models import Edge, Node, Subgraph
from tcm_kg.store import GraphStore


class GraphQuery:
    """Query engine for the TCM knowledge graph.

    Supports:
    - Multi-hop path finding between two entities
    - Subgraph expansion from a starting node
    - Relation-filtered traversal

    >>> store = GraphStore()
    >>> # ... populate store ...
    >>> q = GraphQuery(store)
    >>> paths = q.find_path("huangfumi", "zhenjiu_jia_yi_jing", max_hops=2)
    """

    def __init__(self, store: GraphStore) -> None:
        self.store = store

    def find_path(
        self,
        start_id: str,
        end_id: str,
        max_hops: int = 3,
        relation: str | None = None,
    ) -> list[list[Edge]]:
        """Find all paths from start_id to end_id within max_hops.

        Returns list of paths, each path is a list of edges in order.
        Returns empty list if no path found or either node doesn't exist.
        """
        if start_id not in self.store._nodes or end_id not in self.store._nodes:
            return []
        if start_id == end_id:
            return [[]]

        # BFS: queue holds (current_node_id, path_edges_so_far)
        queue: deque[tuple[str, list[Edge]]] = deque([(start_id, [])])
        all_paths: list[list[Edge]] = []

        while queue:
            current_id, path = queue.popleft()
            if len(path) >= max_hops:
                continue

            for target, edge in self.store.neighbors_out(current_id):
                # ponytail: simple cycle prevention — don't revisit nodes in path
                visited_ids = {e.source_id for e in path} | {current_id}
                if target.id in visited_ids:
                    continue

                new_path = path + [edge]
                if target.id == end_id:
                    all_paths.append(new_path)
                else:
                    queue.append((target.id, new_path))

        return all_paths

    def expand(
        self,
        start_id: str,
        relation: str | None = None,
        max_hops: int = 2,
    ) -> Subgraph:
        """Expand a subgraph from start_id up to max_hops away.

        Returns all nodes and edges reachable within the hop limit.
        Optionally filter by relation type.
        """
        if start_id not in self.store._nodes:
            return Subgraph()

        sub = Subgraph()
        start_node = self.store.get_node(start_id)
        if start_node is None:
            return sub
        sub.nodes[start_id] = start_node

        current_layer = {start_id}
        for _hop in range(max_hops):
            next_layer: set[str] = set()
            for node_id in current_layer:
                for target, edge in self.store.neighbors_out(node_id):
                    if relation is not None and edge.relation != relation:
                        continue
                    if target.id not in sub.nodes:
                        sub.nodes[target.id] = target
                        next_layer.add(target.id)
                    sub.edges.append(edge)
            current_layer = next_layer
            if not current_layer:
                break

        return sub

    def related_entities(
        self,
        start_id: str,
        relation: str | None = None,
        max_hops: int = 2,
    ) -> list[Node]:
        """Return flat list of nodes reachable from start_id.

        The start_id itself is NOT included.
        """
        if start_id not in self.store._nodes:
            return []

        visited: dict[str, int] = {start_id: 0}  # node_id → distance
        queue: deque[tuple[str, int]] = deque([(start_id, 0)])
        result: list[Node] = []

        while queue:
            current_id, dist = queue.popleft()
            if dist >= max_hops:
                continue

            for target, edge in self.store.neighbors_out(current_id):
                if relation is not None and edge.relation != relation:
                    continue
                if target.id not in visited:
                    visited[target.id] = dist + 1
                    result.append(target)
                    queue.append((target.id, dist + 1))

        return result

    def shortest_path(
        self,
        start_id: str,
        end_id: str,
        max_hops: int = 5,
    ) -> list[Edge] | None:
        """Return the shortest path between two nodes, or None."""
        paths = self.find_path(start_id, end_id, max_hops=max_hops)
        if not paths:
            return None
        return min(paths, key=len)

    def connected(self, node_id: str, max_hops: int = 1) -> bool:
        """Check if a node has any outgoing edges."""
        return len(self.store.edges_from(node_id)) > 0
