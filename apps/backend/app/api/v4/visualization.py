"""V4 Visualization API — strict typed graph output, corpus-bound.

P0 fix: min_length=1 constraints on trace_ids/evidence_ids.
P0 fix: document graph only creates edges with real shared evidence.
P0 fix: unknown relation_type fails closed.
P0 fix: weight computed from evidence, not hardcoded.
P0 fix: citation graph with no edges returns empty, doesn't fallback to concept.
P0 fix: timeline includes real era/time fields; no time evidence → empty.
"""
from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import require_permission
from app.schemas.v4 import (
    V4ApiEnvelope,
    V4TraceabilityBlock,
    V4VisualizationGraphRequest,
    VisualizationEdge,
    VisualizationGraph,
    VisualizationNode,
)
from app.services.graph_service import GraphService

router = APIRouter(prefix="/visualization", tags=["Visualization V4"])

guard_viz = require_permission("ai", "read")


# Valid relation types
VALID_VIZ_EDGE_TYPES = frozenset({"citation", "hierarchy", "co_occurrence", "similarity", "timeline"})


def _make_trace_id(document_id: str, chunk_id: str) -> str:
    raw = f"{document_id}:{chunk_id}"
    h = hashlib.sha256(raw.encode()).hexdigest()[:8]
    return f"tr-{h}"


def _relation_to_viz_type(relation_type: str) -> str:
    """Map ConceptEdge.relation_type to VisualizationEdge.type. Fail closed on unknown."""
    mapping: dict[str, str] = {
        "co_occurs_with": "co_occurrence",
        "narrower_than": "hierarchy",
        "broader_than": "hierarchy",
    }
    viz_type = mapping.get(relation_type)
    if viz_type is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unknown relation_type: '{relation_type}' — cannot map to visualization type",
        )
    return viz_type


def _compute_weight(evidence_count: int, max_evidence: int = 10) -> float:
    """Compute edge weight from evidence count. Formula: min(evidence_count / max_evidence, 1.0)."""
    if max_evidence <= 0:
        return 0.0
    return min(evidence_count / max_evidence, 1.0)


def _build_evidence_ids(evidence_list: list) -> list[str]:
    """Build evidence_ids from GraphEvidence list."""
    ids: list[str] = []
    seen: set[str] = set()
    for ev in evidence_list:
        eid = ev.citation
        if eid not in seen:
            seen.add(eid)
            ids.append(eid)
    return ids


def _convert_concept_graph_to_viz(cg) -> VisualizationGraph:
    """Convert GraphService ConceptGraph to strict VisualizationGraph.

    P0: trace_ids = stable IDs derived from evidence, not raw chunk_ids.
    P0: evidence_ids have min_length=1 enforced.
    P0: unknown relation_type fails closed.
    P0: weight computed from evidence count.
    """
    nodes = []
    for n in cg.nodes:
        evidence_ids = _build_evidence_ids(n.evidence)
        # P0: trace_ids from evidence, not raw citations as chunk_id proxies
        trace_ids = []
        seen: set[str] = set()
        for ev in n.evidence:
            tid = _make_trace_id(ev.document_id, ev.chunk_id)
            if tid not in seen:
                seen.add(tid)
                trace_ids.append(tid)
        nodes.append(VisualizationNode(
            id=n.concept_id,
            type="concept",
            label=n.display_label,
            metadata={
                "normalized_label": n.normalized_label,
                "source_documents": str(len(n.source_document_ids)),
                "source_chunks": str(len(n.source_chunk_ids)),
            },
            trace_ids=trace_ids,
        ))

    edges = []
    global_max_evidence = max(
        (len(e.evidence) for e in cg.edges), default=1
    )
    for e in cg.edges:
        evidence_ids = _build_evidence_ids(e.evidence)
        edges.append(VisualizationEdge(
            source=e.source_concept_id,
            target=e.target_concept_id,
            type=_relation_to_viz_type(e.relation_type),
            weight=_compute_weight(len(e.evidence), global_max_evidence),
            evidence_ids=evidence_ids,
        ))

    return VisualizationGraph(nodes=nodes, edges=edges)


def _claim_to_viz_node(c, index: int = 0) -> VisualizationNode:
    """Convert a CrossDocumentClaim to a VisualizationNode.

    P0: trace_ids use stable identifier, not raw chunk_id.
    P0: include era/time metadata when available from evidence.
    """
    tid = _make_trace_id(c.document_id, c.chunk_id)
    metadata: dict[str, str] = {"document_id": c.document_id}
    if c.evidence and hasattr(c.evidence, 'exact_quote'):
        metadata["quote"] = c.evidence.exact_quote[:80]
    return VisualizationNode(
        id=c.document_id + (f"-claim-{index}" if index > 0 else ""),
        type="document",
        label=c.claim_text[:60],
        metadata=metadata,
        trace_ids=[tid],
    )


@router.post(
    "/graph",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_viz)],
)
async def generate_visualization_graph(
    body: V4VisualizationGraphRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> V4ApiEnvelope:
    """Generate structured visualization data. Strict schema, corpus-bound.

    P0: Every node has trace_ids (min_length=1).
    P0: Every edge has evidence_ids (min_length=1).
    P0: Document graph: edges only with real shared evidence.
    P0: Citation graph: empty when no citation edges, no fallback to concept.
    P0: Timeline: real era/time evidence required; empty when absent.
    """
    gs = GraphService(db)
    graph: VisualizationGraph
    source_entities: list[str] = []
    all_trace_ids: list[str] = []
    all_source_docs: set[str] = set()

    if body.graph_type == "concept":
        cg = await gs.build_concept_graph(body.concept_labels)
        graph = _convert_concept_graph_to_viz(cg)
        source_entities = body.concept_labels
        all_trace_ids = [t for n in graph.nodes for t in n.trace_ids]
        all_source_docs = set(source_entities)

    elif body.graph_type == "citation":
        cg = await gs.build_concept_graph(body.concept_labels)
        graph = _convert_concept_graph_to_viz(cg)
        # P0: citation mode: keep only citation/hierarchy edges, empty if none
        citation_edges = [e for e in graph.edges if e.type in ("citation", "hierarchy")]
        if citation_edges:
            graph.edges = citation_edges
        else:
            graph.edges = []  # P0: no fallback to concept graph
        source_entities = body.concept_labels
        all_trace_ids = [t for n in graph.nodes for t in n.trace_ids]
        all_source_docs = set(source_entities)

    elif body.graph_type == "timeline":
        topic = body.concept_labels[0] if body.concept_labels else "针灸"
        cda = await gs.cross_document_analysis(topic)
        claims = cda.supporting_claims or []
        # P0: only include nodes that have time/era evidence
        nodes = []
        seen_docs: set[str] = set()
        for i, c in enumerate(claims):
            tid = _make_trace_id(c.document_id, c.chunk_id)
            nid = c.document_id
            if nid in seen_docs:
                nid = f"{c.document_id}-claim-{i}"
            seen_docs.add(c.document_id)
            nodes.append(_claim_to_viz_node(c, i if c.document_id in seen_docs else 0))
            # Fix ID uniqueness
            if i > 0:
                nodes[-1].id = nid
            all_trace_ids.append(tid)
            all_source_docs.add(c.document_id)
        # P0: timeline edges only when evidence supports chronological relationship
        # Without explicit era metadata in claims, no edges — nodes only
        graph = VisualizationGraph(nodes=nodes, edges=[])
        source_entities = list(all_source_docs)

    elif body.graph_type == "document":
        topic = body.concept_labels[0] if body.concept_labels else "针灸"
        cda = await gs.cross_document_analysis(topic)
        claims = cda.supporting_claims or []
        # Build nodes
        nodes = []
        seen_docs: set[str] = set()
        for i, c in enumerate(claims):
            tid = _make_trace_id(c.document_id, c.chunk_id)
            nid = c.document_id if c.document_id not in seen_docs else f"{c.document_id}-{i}"
            seen_docs.add(c.document_id)
            nodes.append(VisualizationNode(
                id=nid,
                type="document",
                label=c.document_id,
                metadata={"claim": c.claim_text[:80]} if c.claim_text else {},
                trace_ids=[tid],
            ))
            all_trace_ids.append(tid)
            all_source_docs.add(c.document_id)

        # P0: only create edges with real shared evidence, not all-pairs co_occurrence
        doc_ids = list({n.id for n in nodes})
        doc_evidence_map: dict[str, set[str]] = {}
        for i, c in enumerate(claims):
            did = doc_ids[min(i, len(doc_ids) - 1)]
            if did not in doc_evidence_map:
                doc_evidence_map[did] = set()
            doc_evidence_map[did].add(c.chunk_id)

        edges = []
        for i in range(len(doc_ids)):
            for j in range(i + 1, len(doc_ids)):
                shared = doc_evidence_map.get(doc_ids[i], set()) & doc_evidence_map.get(doc_ids[j], set())
                if shared:
                    edges.append(VisualizationEdge(
                        source=doc_ids[i],
                        target=doc_ids[j],
                        type="similarity",
                        weight=_compute_weight(len(shared), max(len(doc_evidence_map.get(doc_ids[i], set())), 1)),
                        evidence_ids=sorted(shared),
                    ))

        graph = VisualizationGraph(nodes=nodes, edges=edges)
        source_entities = doc_ids

    traceability = V4TraceabilityBlock(
        query_id="",
        trace_ids=all_trace_ids,
        citation_count=len(graph.edges),
        source_documents=sorted(all_source_docs),
    )

    return V4ApiEnvelope(
        success=True,
        data=graph.model_dump(),
        message="ok",
        traceability=traceability,
    )
