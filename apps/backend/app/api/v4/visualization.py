"""V4 Visualization API — strict typed graph output, corpus-bound."""
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

router = APIRouter(prefix="/visualization", tags=["Visualization V4"])

guard_viz = require_permission("ai", "read")


# Relation type mapping from ConceptEdge.relation_type to VisualizationEdge.type
_RELATION_TO_VIZ_TYPE: dict[str, str] = {
    "co_occurs_with": "co_occurrence",
    "narrower_than": "hierarchy",
    "broader_than": "hierarchy",
}


def _convert_concept_graph_to_viz(cg) -> VisualizationGraph:
    """Convert GraphService ConceptGraph to strict VisualizationGraph."""
    nodes = [
        VisualizationNode(
            id=n.concept_id,
            type="concept",
            label=n.display_label,
            metadata={
                "normalized_label": n.normalized_label,
                "source_documents": str(len(n.source_document_ids)),
                "source_chunks": str(len(n.source_chunk_ids)),
            },
            trace_ids=[ev.citation for ev in n.evidence],
        )
        for n in cg.nodes
    ]
    edges = [
        VisualizationEdge(
            source=e.source_concept_id,
            target=e.target_concept_id,
            type=_RELATION_TO_VIZ_TYPE.get(e.relation_type, "co_occurrence"),  # type: ignore[arg-type]
            weight=0.5,
            evidence_ids=[ev.citation for ev in e.evidence],
        )
        for e in cg.edges
    ]
    return VisualizationGraph(nodes=nodes, edges=edges)


def _claim_to_viz_node(c) -> VisualizationNode:
    """Convert a CrossDocumentClaim to a VisualizationNode."""
    return VisualizationNode(
        id=c.document_id,
        type="document",
        label=c.document_id,
        metadata={},
        trace_ids=[c.chunk_id],
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
    """Generate structured visualization data. Strict schema, corpus-bound."""
    gs = GraphService(db)

    if body.graph_type == "concept":
        cg = await gs.build_concept_graph(body.concept_labels)
        graph = _convert_concept_graph_to_viz(cg)
        source_entities = body.concept_labels
        edge_evidence = [e.evidence_ids for e in graph.edges]

    elif body.graph_type == "citation":
        cg = await gs.build_concept_graph(body.concept_labels)
        graph = _convert_concept_graph_to_viz(cg)
        graph.edges = [e for e in graph.edges if e.type == "citation"] or graph.edges
        source_entities = body.concept_labels
        edge_evidence = [e.evidence_ids for e in graph.edges]

    elif body.graph_type == "timeline":
        cda = await gs.cross_document_analysis(
            body.concept_labels[0] if body.concept_labels else "针灸"
        )
        claims = cda.supporting_claims or []
        nodes = [_claim_to_viz_node(c) for c in claims]
        graph = VisualizationGraph(nodes=nodes, edges=[])
        source_entities = [c.document_id for c in claims]
        edge_evidence = []

    elif body.graph_type == "document":
        cda = await gs.cross_document_analysis(
            body.concept_labels[0] if body.concept_labels else "针灸"
        )
        claims = cda.supporting_claims or []
        nodes = [_claim_to_viz_node(c) for c in claims]
        doc_ids = list({n.id for n in nodes})
        edges = [
            VisualizationEdge(
                source=doc_ids[i],
                target=doc_ids[j],
                type="co_occurrence",
                weight=0.5,
                evidence_ids=[],
            )
            for i in range(len(doc_ids))
            for j in range(i + 1, len(doc_ids))
        ]
        graph = VisualizationGraph(nodes=nodes, edges=edges)
        source_entities = doc_ids
        edge_evidence = []

    traceability = V4TraceabilityBlock(
        query_id="",
        trace_ids=[t for n in graph.nodes for t in n.trace_ids],
        citation_count=len(graph.edges),
        source_documents=sorted(set(source_entities)),
    )

    return V4ApiEnvelope(
        success=True,
        data=graph.model_dump(),
        message="ok",
        traceability=traceability,
    )
