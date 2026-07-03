"""RAG data models — evidence chains, citation paths, search results."""

from __future__ import annotations

from dataclasses import dataclass, field

from tcm_kg.models import Edge


@dataclass
class KGPath:
    """A path through the knowledge graph as evidence.

    Example: 皇甫谧 → authored → 针灸甲乙经 → treats → 方剂
    """

    edges: list[Edge] = field(default_factory=list)
    description: str = ""

    @property
    def hop_count(self) -> int:
        return len(self.edges)

    def __post_init__(self) -> None:
        if not self.description and self.edges:
            parts: list[str] = []
            for edge in self.edges:
                parts.append(f"--[{edge.relation}]-->")
            self.description = " ".join(parts)


@dataclass
class TextHit:
    """A matching passage from a structured document."""

    document_id: str
    paragraph_id: str
    sentence_ids: list[str] = field(default_factory=list)
    text: str = ""
    score: float = 0.0
    version_id: str | None = None


@dataclass
class EvidenceChain:
    """A complete evidence chain combining KG paths and text hits.

    Attributes:
        claim: The claim being supported/refuted
        kg_paths: Knowledge graph paths that support the claim
        document_hits: Specific text passages as evidence
        confidence: Aggregate confidence score (0.0 to 1.0)
    """

    claim: str
    kg_paths: list[KGPath] = field(default_factory=list)
    document_hits: list[TextHit] = field(default_factory=list)
    confidence: float = 0.0

    def __post_init__(self) -> None:
        if self.confidence == 0.0 and (self.kg_paths or self.document_hits):
            # Simple confidence heuristic: combine KG and text coverage
            kg_score = min(len(self.kg_paths) * 0.2, 0.5)
            text_score = min(sum(h.score for h in self.document_hits) * 0.1, 0.5)
            self.confidence = min(kg_score + text_score, 1.0)


@dataclass
class CitationPath:
    """Formatted citations for a claim.

    Supports multiple citation formats (inline, footnote, bibliography).
    """

    segments: list[tuple[str, str]] = field(default_factory=list)
    # Each segment: (document_id, formatted reference)
    format: str = "inline"  # "inline" | "footnote" | "bibliography"

    def to_inline(self) -> str:
        """Render citations as inline references."""
        parts: list[str] = []
        for i, (doc_id, ref) in enumerate(self.segments, 1):
            parts.append(f"[{i}] {ref}")
        return " ".join(parts)

    def to_footnote(self) -> str:
        """Render citations as footnotes."""
        parts: list[str] = []
        for i, (doc_id, ref) in enumerate(self.segments, 1):
            parts.append(f"[^{i}]: {ref}")
        return "\n".join(parts)

    def to_bibliography(self) -> str:
        """Render citations in bibliography format."""
        parts: list[str] = []
        for i, (doc_id, ref) in enumerate(self.segments, 1):
            parts.append(f"{i}. {ref}")
        return "\n".join(parts)


@dataclass
class SearchResult:
    """Combined search result from KG + literature retrieval."""

    query: str
    evidence: EvidenceChain = field(default_factory=lambda: EvidenceChain(claim=""))
    citation: CitationPath = field(default_factory=CitationPath)

    def __post_init__(self) -> None:
        if not self.evidence.claim:
            self.evidence.claim = self.query
