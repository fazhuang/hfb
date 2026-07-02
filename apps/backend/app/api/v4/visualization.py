"""V4 Visualization API — strict typed graph output, corpus-bound.

P0: Unified trace module for trace_ids/evidence_ids.
P0: citation graph: only citation edges, no hierarchy/co_occurrence fallback.
P0: timeline: real era/time evidence required; empty when absent.
P0: document graph: one node per unique document, edges only with shared evidence.
P0: evidence_ids from trace registry, not raw chunk_ids.
"""
from __future__ import annotations

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
from app.services.trace_lineage import make_trace_id

router = APIRouter(prefix="/visualization", tags=["Visualization V4"])

guard_viz = require_permission("ai", "read")


def _relation_to_viz_type(relation_type: str) -> str:
    """Map ConceptEdge.relation_type to VisualizationEdge.type. Fail closed."""
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
    """Compute edge weight: min(evidence_count / max_evidence, 1.0)."""
    if max_evidence <= 0:
        return 0.0
    return min(evidence_count / max_evidence, 1.0)


def _evidence_to_ids(evidence_list: list) -> list[str]:
    """Build evidence_ids from GraphEvidence list using trace registry."""
    ids: list[str] = []
    seen: set[str] = set()
    for ev in evidence_list:
        tid = make_trace_id(ev.document_id, ev.chunk_id)
        if tid not in seen:
            seen.add(tid)
            ids.append(tid)
    return ids


def _convert_concept_to_viz(cg) -> VisualizationGraph:
    """Convert ConceptGraph to strict VisualizationGraph.

    trace_ids from unified trace module.
    evidence_ids from unified trace registry.
    weight computed from evidence count.
    """
    nodes = []
    for n in cg.nodes:
        trace_ids = []
        seen: set[str] = set()
        for ev in n.evidence:
            tid = make_trace_id(ev.document_id, ev.chunk_id)
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

    global_max_evidence = max((len(e.evidence) for e in cg.edges), default=1)
    edges = []
    for e in cg.edges:
        evidence_ids = _evidence_to_ids(e.evidence)
        edges.append(VisualizationEdge(
            source=e.source_concept_id,
            target=e.target_concept_id,
            type=_relation_to_viz_type(e.relation_type),
            weight=_compute_weight(len(e.evidence), global_max_evidence),
            evidence_ids=evidence_ids,
        ))

    return VisualizationGraph(nodes=nodes, edges=edges)


@router.post(
    "/graph",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_viz)],
)
async def generate_visualization_graph(
    body: V4VisualizationGraphRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
) -> V4ApiEnvelope:
    """Generate structured visualization data. Strict schema, corpus-bound."""
    gs = GraphService(db)
    graph: VisualizationGraph
    all_trace_ids: list[str] = []
    all_source_docs: list[str] = []
    operation_id = ""

    if body.graph_type == "concept":
        cg = await gs.build_concept_graph(body.concept_labels)
        graph = _convert_concept_to_viz(cg)
        all_trace_ids = [t for n in graph.nodes for t in n.trace_ids]
        all_source_docs = body.concept_labels
        operation_id = f"viz-concept-{'-'.join(body.concept_labels)[:32]}"

    elif body.graph_type == "citation":
        cg = await gs.build_concept_graph(body.concept_labels)
        full_graph = _convert_concept_to_viz(cg)
        # P0: citation graph = ONLY citation edges. No hierarchy. No co_occurrence.
        citation_edges = [e for e in full_graph.edges if e.type == "citation"]
        graph = VisualizationGraph(nodes=full_graph.nodes, edges=citation_edges)
        all_trace_ids = [t for n in graph.nodes for t in n.trace_ids]
        all_source_docs = body.concept_labels
        operation_id = f"viz-citation-{'-'.join(body.concept_labels)[:32]}"

    elif body.graph_type == "timeline":
        topic = body.concept_labels[0] if body.concept_labels else "针灸"
        cda = await gs.cross_document_analysis(topic)
        claims = cda.supporting_claims or []

        # P0: timeline nodes only with real time/era evidence
        # Without explicit era/timestamp in claims, return empty graph
        nodes = []
        for i, c in enumerate(claims):
            tid = make_trace_id(c.document_id, c.chunk_id)
            # Check if evidence carries time metadata
            time_meta = _extract_time_evidence(c)
            if time_meta:
                nodes.append(VisualizationNode(
                    id=f"tl-{c.document_id}-{i}",
                    type="document",
                    label=f"{c.document_id}: {c.claim_text[:40]}",
                    metadata={
                        "document_id": c.document_id,
                        "era": time_meta.get("era", ""),
                        "year": time_meta.get("year", ""),
                        "quote": (c.evidence.exact_quote[:80] if hasattr(c, 'evidence') and c.evidence else ""),
                    },
                    trace_ids=[tid],
                ))
                all_trace_ids.append(tid)
                all_source_docs.append(c.document_id)

        # P0: no time evidence → empty graph
        graph = VisualizationGraph(nodes=nodes, edges=[])
        operation_id = f"viz-timeline-{topic[:32]}"

    elif body.graph_type == "document":
        topic = body.concept_labels[0] if body.concept_labels else "针灸"
        cda = await gs.cross_document_analysis(topic)
        claims = cda.supporting_claims or []

        # P0: one node per unique document
        doc_nodes: dict[str, dict] = {}
        for c in claims:
            did = c.document_id
            tid = make_trace_id(c.document_id, c.chunk_id)
            if did not in doc_nodes:
                doc_nodes[did] = {
                    "id": did,
                    "trace_ids": [],
                    "chunk_ids": set(),
                }
            doc_nodes[did]["trace_ids"].append(tid)
            doc_nodes[did]["chunk_ids"].add(c.chunk_id)
            all_trace_ids.append(tid)
            all_source_docs.append(did)

        nodes = [
            VisualizationNode(
                id=did,
                type="document",
                label=did,
                metadata={"claim_count": str(len(info["trace_ids"]))},
                trace_ids=sorted(set(info["trace_ids"])),
            )
            for did, info in doc_nodes.items()
        ]

        # P0: edges only with real shared evidence (shared chunk_ids)
        doc_list = list(doc_nodes.items())
        edges = []
        for i in range(len(doc_list)):
            for j in range(i + 1, len(doc_list)):
                did_a, info_a = doc_list[i]
                did_b, info_b = doc_list[j]
                shared = info_a["chunk_ids"] & info_b["chunk_ids"]
                if shared:
                    evidence_ids = [
                        make_trace_id(did_a, cid) if make_trace_id(did_a, cid) in all_trace_ids
                        else make_trace_id(did_b, cid)
                        for cid in shared
                    ]
                    edges.append(VisualizationEdge(
                        source=did_a,
                        target=did_b,
                        type="similarity",
                        weight=_compute_weight(len(shared)),
                        evidence_ids=[eid for eid in evidence_ids if eid],
                    ))

        graph = VisualizationGraph(nodes=nodes, edges=edges)
        operation_id = f"viz-document-{topic[:32]}"

    traceability = V4TraceabilityBlock(
        query_id=operation_id,
        trace_ids=all_trace_ids,
        citation_count=len(graph.edges),
        source_documents=sorted(set(all_source_docs)),
    )

    return V4ApiEnvelope(
        success=True,
        data=graph.model_dump(),
        message="ok",
        traceability=traceability,
    )


def _extract_time_evidence(c) -> dict | None:
    """Extract era/year from a CrossDocumentClaim's evidence. Returns None if absent."""
    meta = {}
    if hasattr(c, 'evidence') and c.evidence:
        if hasattr(c.evidence, 'exact_quote'):
            # Heuristic: scan for dynasty/year patterns in evidence quote
            import re
            quote = c.evidence.exact_quote
            era_match = re.search(r'(战国|秦|汉|三国|晋|南北朝|隋|唐|宋|辽|金|元|明|清)', quote)
            if era_match:
                meta["era"] = era_match.group(1)
            year_match = re.search(r'(\d{1,4})年', quote)
            if year_match:
                meta["year"] = year_match.group(1) + "年"
            if meta:
                return meta
    return None
