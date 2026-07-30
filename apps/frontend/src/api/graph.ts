/**
 * Graph API client — typed wrappers for /api/v1/graph endpoints.
 *
 * Task 2A: Knowledge Graph minimal page — entity search, neighbors, subgraph.
 * Uses real Graph API; no mocks, no static data.
 */

import api from './client';

// ============================================================
// Types — mirror backend schemas (apps/backend/app/schemas/graph.py)
// ============================================================

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

interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  message: string;
}

// ============================================================
// Entity type constants
// ============================================================

export const ENTITY_TYPES = [
  { value: 'person', label: '人物' },
  { value: 'book', label: '书籍' },
  { value: 'version', label: '版本' },
  { value: 'passage', label: '条文' },
] as const;

export const ENTITY_TYPE_ICONS: Record<string, string> = {
  person: '👤',
  book: '📚',
  version: '📖',
  passage: '📜',
};

// ============================================================
// API functions
// ============================================================

/**
 * Search for entities in the knowledge graph.
 * GET /api/v1/graph/entities?q=&types=person,book&limit=20
 */
export async function searchEntities(
  q: string,
  types: Array<string>,
  limit = 20,
): Promise<Array<GraphNodeData>> {
  const { data } = await api.get<ApiEnvelope<Array<GraphNodeData>>>('/api/v1/graph/entities', {
    params: { q: q.trim(), types: types.join(','), limit },
  });
  return data.data ?? [];
}

/**
 * Get 1-hop neighborhood of an entity.
 * GET /api/v1/graph/neighbors/{entity_type}/{entity_id}
 */
export async function getNeighbors(
  entityType: string,
  entityId: string,
): Promise<NeighborResult | null> {
  const { data } = await api.get<ApiEnvelope<NeighborResult>>(
    `/api/v1/graph/neighbors/${entityType}/${entityId}`,
  );
  return data.data ?? null;
}

/**
 * Get 2-hop subgraph centered on an entity.
 * GET /api/v1/graph/entity/{entity_type}/{entity_id}
 */
export async function getEntitySubgraph(
  entityType: string,
  entityId: string,
): Promise<Subgraph | null> {
  const { data } = await api.get<ApiEnvelope<Subgraph>>(
    `/api/v1/graph/entity/${entityType}/${entityId}`,
  );
  return data.data ?? null;
}
