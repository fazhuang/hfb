/**
 * Graph API client — typed wrappers for /api/v1/graph endpoints.
 *
 * Types live in src/types/graph.ts (single source of truth, mirroring
 * apps/backend/app/schemas/graph.py). This module re-exports them so existing
 * `@/api/graph` imports keep working, and adds the request functions.
 */

import api from './client';
import type {
  GenealogyTreeNode,
  GeoDistributionPoint,
  GraphNodeData,
  NeighborResult,
  Subgraph,
  TimelineEvent,
} from '@/types/graph';

export type {
  GenealogyTreeNode,
  GeoDistributionPoint,
  GraphEdgeData,
  GraphEvidence,
  GraphNodeData,
  NeighborResult,
  Subgraph,
  TimelineEvent,
} from '@/types/graph';

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

interface ApiEnvelope<T> {
  success: boolean;
  data: T;
  message: string;
}

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

/**
 * Academic evolution timeline.
 * GET /api/v1/graph/timeline
 */
export async function getTimeline(): Promise<Array<TimelineEvent>> {
  const { data } = await api.get<ApiEnvelope<Array<TimelineEvent>>>(
    '/api/v1/graph/timeline',
  );
  return data.data ?? [];
}

/**
 * Version lineage tree.
 * GET /api/v1/graph/genealogy
 */
export async function getGenealogy(): Promise<GenealogyTreeNode | null> {
  const { data } = await api.get<ApiEnvelope<GenealogyTreeNode>>(
    '/api/v1/graph/genealogy',
  );
  return data.data ?? null;
}

/**
 * Geographic distribution of origins and repositories.
 * GET /api/v1/graph/geo?era=
 */
export async function getGeo(era?: string): Promise<Array<GeoDistributionPoint>> {
  const { data } = era
    ? await api.get<ApiEnvelope<Array<GeoDistributionPoint>>>('/api/v1/graph/geo', {
        params: { era },
      })
    : await api.get<ApiEnvelope<Array<GeoDistributionPoint>>>('/api/v1/graph/geo');
  return data.data ?? [];
}
