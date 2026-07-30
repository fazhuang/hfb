"""V4 Visualization API — strict typed graph output, corpus-bound.

P0: Unified trace module for trace_ids/evidence_ids.
P0: citation graph: only citation edges, no hierarchy/co_occurrence fallback.
P0: timeline: real era/time evidence required; empty when absent.
P0: document graph: one node per unique document, edges only with shared evidence.
P0: evidence_ids from trace registry, not raw chunk_ids.
P0: saves QueryHistory with full InternalTraceRecord for strict resolver.
"""
from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.schemas.v4 import (
    V4ApiEnvelope,
    V4TraceabilityBlock,
    V4VisualizationGraphRequest,
    VisualizationEdge,
    VisualizationGraph,
    VisualizationNode,
)
from app.services.graph_service import GraphService
from app.services.trace_lineage import (
    TraceLineageError,
    build_viz_traces,
    extract_source_documents,
    make_trace_id,
)
from app.services.workspace_service import WorkspaceService

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
                "source_documents": ", ".join(n.source_document_ids) if n.source_document_ids else "",
                "source_document_count": str(len(n.source_document_ids)),
                "source_chunk_count": str(len(n.source_chunk_ids)),
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


def _build_citation_graph(cg) -> VisualizationGraph:
    """Build a bipartite citation graph: concept nodes + document nodes + citation edges.

    Each citation edge is evidence-backed: concept -> document, with evidence_ids
    resolvable through trace -> chunk -> document -> passage -> citation.
    No co_occurrence or hierarchy fallback.
    """
    # 1. Build concept nodes (same as concept graph)
    concept_nodes = []
    for n in cg.nodes:
        trace_ids = []
        seen_tids: set[str] = set()
        for ev in n.evidence:
            tid = make_trace_id(ev.document_id, ev.chunk_id)
            if tid not in seen_tids:
                seen_tids.add(tid)
                trace_ids.append(tid)
        concept_nodes.append(VisualizationNode(
            id=n.concept_id,
            type="concept",
            label=n.display_label,
            metadata={
                "normalized_label": n.normalized_label,
                "source_documents": ", ".join(n.source_document_ids) if n.source_document_ids else "",
                "source_document_count": str(len(n.source_document_ids)),
            },
            trace_ids=trace_ids,
        ))

    # 2. Build document nodes — one per unique document with evidence
    doc_evidence: dict[str, list] = {}  # document_id -> list of (concept_id, evidence)
    for n in cg.nodes:
        for ev in n.evidence:
            doc_evidence.setdefault(ev.document_id, []).append((n.concept_id, ev))

    doc_nodes = {}
    for doc_id, ev_pairs in doc_evidence.items():
        trace_ids = []
        seen_tids = set()
        for _, ev in ev_pairs:
            tid = make_trace_id(ev.document_id, ev.chunk_id)
            if tid not in seen_tids:
                seen_tids.add(tid)
                trace_ids.append(tid)
        doc_nodes[doc_id] = VisualizationNode(
            id=doc_id,
            type="document",
            label=doc_id,
            metadata={"evidence_count": str(len(ev_pairs))},
            trace_ids=trace_ids,
        )

    # 3. Build citation edges: concept -> document, with deduped evidence_ids
    all_nodes = concept_nodes + list(doc_nodes.values())
    edges = []
    seen_edge_keys: set[tuple[str, str]] = set()

    for n in cg.nodes:
        concept_id = n.concept_id
        # Group evidence by document_id for this concept
        concept_doc_evidence: dict[str, list] = {}
        for ev in n.evidence:
            concept_doc_evidence.setdefault(ev.document_id, []).append(ev)

        for doc_id, ev_list in concept_doc_evidence.items():
            edge_key = (concept_id, doc_id)
            # Aggregate all evidence_ids for this concept-document pair
            evidence_ids = []
            seen_eids = set()
            for ev in ev_list:
                tid = make_trace_id(ev.document_id, ev.chunk_id)
                if tid not in seen_eids:
                    seen_eids.add(tid)
                    evidence_ids.append(tid)

            if edge_key not in seen_edge_keys:
                seen_edge_keys.add(edge_key)
                edges.append(VisualizationEdge(
                    source=concept_id,
                    target=doc_id,
                    type="citation",
                    weight=_compute_weight(len(ev_list)),
                    evidence_ids=evidence_ids,
                ))

    return VisualizationGraph(nodes=all_nodes, edges=edges)





@router.post(
    "/graph",
    response_model=V4ApiEnvelope,
    dependencies=[Depends(guard_viz)],
)
async def generate_visualization_graph(
    body: V4VisualizationGraphRequest,
    db: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> V4ApiEnvelope:
    """Generate structured visualization data. Strict schema, corpus-bound.

    Sprint 4 P0: Saves QueryHistory with full InternalTraceRecord so
    strict resolver can resolve every trace_id.

    Backward compat: If session_id is omitted, auto-creates a persistent
    research session for the current user so no visualization is orphaned.
    """

    ws = WorkspaceService(db)

    # Resolve session: auto-create for backward compat without mutating request DTO
    resolved_session_id: str
    if body.session_id:
        resolved_session_id = body.session_id
    else:
        research_session = await ws.create_session(
            current_user, f"可视化 - {', '.join(body.concept_labels[:3])}"
        )
        resolved_session_id = str(research_session.id)

    # Verify session ownership
    research_session = await ws.get_session(resolved_session_id)
    if research_session is None or research_session.user_id != current_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

    gs = GraphService(db)
    graph: VisualizationGraph
    graph_type: str = body.graph_type
    topic_labels = body.concept_labels

    # Collect all evidence traces from graph construction for trace building
    all_evidence_traces: list = []

    if graph_type == "concept":
        cg = await gs.build_concept_graph(topic_labels)
        graph = _convert_concept_to_viz(cg)
        for n in cg.nodes:
            all_evidence_traces.extend(n.evidence)

    elif graph_type == "citation":
        cg = await gs.build_concept_graph(topic_labels)
        graph = _build_citation_graph(cg)
        for n in cg.nodes:
            all_evidence_traces.extend(n.evidence)

    elif graph_type == "timeline":
        topic = topic_labels[0] if topic_labels else "针灸"
        cda = await gs.cross_document_analysis(topic)
        claims = cda.supporting_claims or []
        all_evidence_traces = list(claims)

        nodes = []
        trace_ids_seen: set[str] = set()
        for i, c in enumerate(claims):
            tid = make_trace_id(c.document_id, c.chunk_id)
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
                trace_ids_seen.add(tid)

        graph = VisualizationGraph(nodes=nodes, edges=[])

    elif graph_type == "document":
        topic = topic_labels[0] if topic_labels else "针灸"
        cda = await gs.cross_document_analysis(topic)
        claims = cda.supporting_claims or []
        all_evidence_traces = list(claims)

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

        doc_list = list(doc_nodes.items())
        edges = []
        for i in range(len(doc_list)):
            for j in range(i + 1, len(doc_list)):
                did_a, info_a = doc_list[i]
                did_b, info_b = doc_list[j]
                shared = info_a["chunk_ids"] & info_b["chunk_ids"]
                if shared:
                    evidence_ids = [
                        make_trace_id(did_a, cid)
                        for cid in shared
                    ]
                    edges.append(VisualizationEdge(
                        source=did_a,
                        target=did_b,
                        type="similarity",
                        weight=_compute_weight(len(shared)),
                        evidence_ids=evidence_ids,
                    ))

        graph = VisualizationGraph(nodes=nodes, edges=edges)

    # Build InternalTraceRecords from evidence — always try, may be empty
    internal_traces: list = []
    if all_evidence_traces:
        try:
            internal_traces = await build_viz_traces(db, all_evidence_traces)
        except TraceLineageError:
            return V4ApiEnvelope(
                success=False,
                data={"error": "TRACE_LINEAGE_INCOMPLETE"},
                message="Visualization cannot proceed: unmapped passage linkage",
                traceability=None,
            )

    # P0: Always persist QueryHistory, including empty graphs
    evidence_ids: list[str] = []
    if internal_traces:
        evidence_ids = [r.trace_id for r in internal_traces]
    else:
        evidence_ids = sorted({
            make_trace_id(t.document_id, t.chunk_id)
            for t in all_evidence_traces
            if hasattr(t, 'document_id') and hasattr(t, 'chunk_id')
        })

    source_docs = extract_source_documents(all_evidence_traces)
    dedup_citation_count = len(evidence_ids)

    qh = await ws.create_query_history(
        session_id=resolved_session_id,
        query_text=f"viz-{graph_type}-{'-'.join(topic_labels)[:32]}",
        query_type="visualization",
        result_summary=json.dumps({
            "graph_type": graph_type,
            "traces": [r.to_dict() for r in internal_traces],
            "node_count": len(graph.nodes),
            "edge_count": len(graph.edges),
            "source_documents": source_docs,
            "evidence_status": "empty" if len(graph.edges) == 0 and len(graph.nodes) == 0 else "ok",
        }, ensure_ascii=False),
        citation_count=dedup_citation_count,
    )

    traceability = V4TraceabilityBlock(
        query_id=qh.id,
        trace_ids=evidence_ids,
        citation_count=dedup_citation_count,
        source_documents=sorted(set(source_docs)),
        session_id=resolved_session_id,
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
    if hasattr(c, 'evidence') and c.evidence and hasattr(c.evidence, 'exact_quote'):
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
