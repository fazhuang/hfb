"""Node and Edge models for the TCM Knowledge Graph."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    """A node in the knowledge graph representing a TCM entity.

    Attributes:
        id: Unique identifier (e.g. "person_huangfumi", "text_zhenjiu_jia_yi_jing")
        type: Entity type from the ontology
        properties: Arbitrary key-value properties (name, dynasty, category, etc.)
        sources: List of source references (document IDs, citations)
    """

    id: str
    type: str  # EntityType value string, e.g. "Person", "Text"
    properties: dict[str, Any] = field(default_factory=dict)
    sources: list[str] = field(default_factory=list)

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.id == other.id


@dataclass
class Edge:
    """A directed relationship between two nodes in the knowledge graph.

    Attributes:
        source_id: ID of the source node
        target_id: ID of the target node
        relation: Relationship type ("authored", "treats", "part_of", etc.)
        weight: Confidence/weight score (0.0 to 1.0)
        source_ref: Citation or evidence reference for this relationship
    """

    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    source_ref: str | None = None

    def __hash__(self) -> int:
        return hash((self.source_id, self.target_id, self.relation, self.source_ref))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Edge):
            return NotImplemented
        return (
            self.source_id == other.source_id
            and self.target_id == other.target_id
            and self.relation == other.relation
            and self.source_ref == other.source_ref
        )


@dataclass
class Subgraph:
    """A subgraph extracted by query operations."""

    nodes: dict[str, Node] = field(default_factory=dict)
    edges: list[Edge] = field(default_factory=list)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)
