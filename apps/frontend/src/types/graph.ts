/**
 * Graph visualization types — centralized single source of truth.
 *
 * Mirrors apps/backend/app/schemas/graph.py. Both the API client
 * (src/api/graph.ts) and the graph components import from here.
 */

export interface GraphNodeData {
  id: string; // composite key: "{entity_type}:{entity_id}"
  entity_type: string;
  entity_id: string;
  label: string; // display name
  properties: Record<string, unknown>;
}

export interface GraphEvidence {
  document_id: string;
  chunk_id: string;
  exact_quote: string;
  citation: string; // [document_id:chunk_id]
  version_id: string;
  passage_id: string;
  source_uri: string;
  claim_text: string;
}

export interface GraphEdgeData {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  label: string;
  source: string; // "explicit" | "fk" | "version" | "concept"
  evidence: GraphEvidence;
}

export interface NeighborResult {
  center: GraphNodeData;
  neighbors: Array<GraphNodeData>;
  edges: Array<GraphEdgeData>;
}

export interface Subgraph {
  nodes: Array<GraphNodeData>;
  edges: Array<GraphEdgeData>;
}

// ============================================================
// Multi-view visualization types
// ============================================================

export interface TimelineEvent {
  id: string;
  entity_type: string;
  entity_id: string;
  label: string;
  year: number | null;
  era: string;
  category: string; // "person" | "book" | "version"
  description: string;
  properties: Record<string, unknown>;
}

export interface GenealogyTreeNode {
  id: string;
  entity_type: string;
  entity_id: string;
  label: string;
  kind: string; // root | original | manuscript | translation | collated | blockprint | version
  era: string;
  year: number | null;
  repository: string;
  children: Array<GenealogyTreeNode>;
}

export interface GeoDistributionPoint {
  id: string;
  entity_type: string;
  entity_id: string;
  name: string;
  location: string;
  lat: number;
  lng: number;
  era: string;
  category: string; // "origin" | "repository"
  weight: number;
}
