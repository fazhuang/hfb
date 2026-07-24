<template>
  <div class="graph-explorer">
    <!-- Search & Controls -->
    <aside class="graph-sidebar">
      <div class="sidebar-header">
        <h2 class="sidebar-title">{{ t('graph.title') }}</h2>
        <p class="sidebar-subtitle">{{ t('graph.subtitle') }}</p>
      </div>

      <!-- Entity Search -->
      <div class="search-section">
        <div class="search-input-wrapper">
          <input
            v-model="searchQuery"
            type="text"
            class="search-input"
            :placeholder="t('graph.searchPlaceholder')"
            @keyup.enter="searchEntities"
          />
          <button class="search-btn" @click="searchEntities" :disabled="searchLoading">
            {{ t('common.search') }}
          </button>
        </div>

        <!-- Type filter chips -->
        <div class="type-filters">
          <button
            v-for="et in entityTypes"
            :key="et.value"
            class="type-chip"
            :class="{ 'type-chip--active': selectedTypes.includes(et.value) }"
            @click="toggleType(et.value)"
          >
            {{ et.label }}
          </button>
        </div>
      </div>

      <!-- Search Results -->
      <div v-if="searchResults.length > 0" class="search-results">
        <div class="results-header">{{ t('graph.searchResults') }} ({{ searchResults.length }})</div>
        <ul class="results-list">
          <li
            v-for="node in searchResults"
            :key="node.id"
            class="result-item"
            :class="{ 'result-item--active': activeNode?.id === node.id }"
            @click="exploreNode(node)"
          >
            <span class="result-icon">{{ getTypeIcon(node.entity_type) }}</span>
            <div class="result-info">
              <span class="result-label">{{ node.label }}</span>
              <span class="result-type">{{ node.entity_type }}</span>
            </div>
          </li>
        </ul>
      </div>

      <!-- Active Node Info -->
      <div v-if="activeNode" class="node-info">
        <h3 class="node-info-title">{{ activeNode.label }}</h3>
        <dl class="node-info-list">
          <template v-for="(value, key) in activeNode.properties" :key="key">
            <dt>{{ key }}</dt>
            <dd>{{ value }}</dd>
          </template>
        </dl>
        <div class="node-info-actions">
          <button class="action-btn" @click="loadNeighborhood(activeNode)">
            🔍 {{ t('graph.neighborhood') }}
          </button>
          <button class="action-btn" @click="loadSubgraph(activeNode)">
            🌐 {{ t('graph.expand') }}
          </button>
        </div>
      </div>
    </aside>

    <!-- Graph Canvas -->
    <main class="graph-main">
      <GraphCanvas
        :nodes="graphNodes"
        :edges="graphEdges"
        :loading="graphLoading"
        :error="graphError"
        :center-node-id="activeNode?.id"
        @node-click="onNodeClick"
        @node-double-click="onNodeDoubleClick"
        @retry="retryLastAction"
      />
    </main>

    <!-- Path Finding Panel -->
    <div v-if="showPathPanel" class="path-panel">
      <div class="path-panel-header">
        <span>{{ t('graph.pathFinding') }}</span>
        <button class="close-btn" @click="showPathPanel = false">×</button>
      </div>
      <div class="path-panel-body">
        <div class="path-field">
          <label>{{ t('graph.source') }}</label>
          <input type="text" :value="pathSource?.label || ''" readonly class="path-input" />
        </div>
        <div class="path-field">
          <label>{{ t('graph.target') }}</label>
          <input type="text" :value="pathTarget?.label || ''" readonly class="path-input" />
        </div>
        <button class="action-btn action-btn--primary" @click="findPath" :disabled="!pathSource || !pathTarget || pathLoading">
          {{ pathLoading ? t('common.loading') : t('graph.findPath') }}
        </button>

        <div v-if="pathResult" class="path-result">
          <div v-if="pathResult.nodes.length > 0" class="path-success">
            ✅ {{ t('graph.pathFound', { length: pathResult.length }) }}
          </div>
          <div v-else class="path-empty">
            ❌ {{ t('graph.noPath') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import api from '@/api/client';
import GraphCanvas from '@/components/graph/GraphCanvas.vue';
import type { GraphNodeData, GraphEdgeData } from '@/components/graph/GraphCanvas.vue';

const { t } = useI18n();
const route = useRoute();

// --- Search ---
const searchQuery = ref('');
const searchLoading = ref(false);
const searchResults = ref<GraphNodeData[]>([]);
const entityTypes = [
  { value: 'person', label: '👤 ' + t('nav.persons') },
  { value: 'book', label: '📚 ' + t('nav.books') },
  { value: 'version', label: '📖 ' + t('graph.versions') },
  { value: 'passage', label: '📜 ' + t('graph.passages') },
];
const selectedTypes = ref<string[]>(['person', 'book', 'version', 'passage']);

function toggleType(type: string) {
  const idx = selectedTypes.value.indexOf(type);
  if (idx >= 0) {
    selectedTypes.value.splice(idx, 1);
  } else {
    selectedTypes.value.push(type);
  }
}

// --- Graph data ---
const graphNodes = ref<GraphNodeData[]>([]);
const graphEdges = ref<GraphEdgeData[]>([]);
const graphLoading = ref(false);
const graphError = ref<string | null>(null);
const activeNode = ref<GraphNodeData | null>(null);

// --- Path finding ---
const showPathPanel = ref(false);
const pathSource = ref<GraphNodeData | null>(null);
const pathTarget = ref<GraphNodeData | null>(null);
const pathLoading = ref(false);
const pathResult = ref<{ nodes: unknown[]; length: number } | null>(null);

let lastApiCall: (() => Promise<void>) | null = null;

// --- Entity Search ---

async function searchEntities() {
  searchLoading.value = true;
  searchResults.value = [];
  try {
    const typesParam = selectedTypes.value.join(',');
    const { data } = await api.get('/api/v1/graph/entities', {
      params: { q: searchQuery.value.trim(), types: typesParam, limit: 20 },
    });
    searchResults.value = (data.data ?? []) as GraphNodeData[];
  } catch (e: unknown) {
    console.error('Search failed:', e);
  } finally {
    searchLoading.value = false;
  }
}

// --- Graph Exploration ---

/**
 * Pre-load entity or trace from route query on mount.
 *
 * Supports:
 *   ?type=person&id=<uuid>   → load neighborhood for the given entity
 *   ?trace=<traceId>         → search for entities matching the trace id,
 *                              fall back to loading evidence subgraph
 */
onMounted(async () => {
  const entityType = route.query.type as string | undefined;
  const entityId = route.query.id as string | undefined;
  const traceId = route.query.trace as string | undefined;

  // Priority 1: explicit entity type + id
  if (entityType && entityId) {
    const node: GraphNodeData = {
      id: `${entityType}:${entityId}`,
      entity_type: entityType,
      entity_id: entityId,
      label: `${entityType}/${entityId.slice(0, 8)}`,
      properties: {},
    };
    activeNode.value = node;
    await loadNeighborhood(node);
    return;
  }

  // Priority 2: trace id — search entities that match this trace
  if (traceId) {
    searchQuery.value = traceId;
    await searchEntities();
    // If the trace matches a known entity, auto-load its neighborhood
    if (searchResults.value.length === 1) {
      await exploreNode(searchResults.value[0]!);
    } else if (searchResults.value.length > 0) {
      // Multiple matches — show them all in the results list
      // (user clicks one to explore)
    }
    return;
  }
});

async function exploreNode(node: GraphNodeData) {
  activeNode.value = node;
  await loadNeighborhood(node);
}

async function loadNeighborhood(node: GraphNodeData) {
  graphLoading.value = true;
  graphError.value = null;
  lastApiCall = () => loadNeighborhood(node);
  try {
    const { data } = await api.get(`/api/v1/graph/neighbors/${node.entity_type}/${node.entity_id}`);
    const result = data.data;
    if (result) {
      graphNodes.value = [result.center, ...(result.neighbors ?? [])] as GraphNodeData[];
      graphEdges.value = (result.edges ?? []) as GraphEdgeData[];
    }
  } catch (e: unknown) {
    graphError.value = (e as Error).message ?? 'Failed to load';
  } finally {
    graphLoading.value = false;
  }
}

async function loadSubgraph(node: GraphNodeData) {
  graphLoading.value = true;
  graphError.value = null;
  lastApiCall = () => loadSubgraph(node);
  try {
    const { data } = await api.get(`/api/v1/graph/entity/${node.entity_type}/${node.entity_id}`);
    const result = data.data;
    if (result) {
      graphNodes.value = (result.nodes ?? []) as GraphNodeData[];
      graphEdges.value = (result.edges ?? []) as GraphEdgeData[];
    }
  } catch (e: unknown) {
    graphError.value = (e as Error).message ?? 'Failed to load';
  } finally {
    graphLoading.value = false;
  }
}

function retryLastAction() {
  if (lastApiCall) lastApiCall();
}

// --- Graph Canvas events ---

function onNodeClick(node: GraphNodeData) {
  activeNode.value = node;
}

function onNodeDoubleClick(node: GraphNodeData) {
  activeNode.value = node;
  // If shift is held, set as path target; else set as source or expand
  if (pathSource.value && node.id !== pathSource.value.id) {
    pathTarget.value = node;
    showPathPanel.value = true;
  } else {
    loadNeighborhood(node);
  }
}

// --- Path Finding ---

async function findPath() {
  if (!pathSource.value || !pathTarget.value) return;
  pathLoading.value = true;
  pathResult.value = null;
  try {
    const { data } = await api.get('/api/v1/graph/path', {
      params: {
        source_type: pathSource.value.entity_type,
        source_id: pathSource.value.entity_id,
        target_type: pathTarget.value.entity_type,
        target_id: pathTarget.value.entity_id,
      },
    });
    const result = data.data;
    if (result && result.nodes?.length > 0) {
      // Show the path on the canvas
      graphNodes.value = (result.nodes ?? []) as GraphNodeData[];
      graphEdges.value = (result.edges ?? []) as GraphEdgeData[];
      pathResult.value = result;
    } else {
      pathResult.value = { nodes: [], length: 0 };
    }
  } catch (e: unknown) {
    console.error('Path find failed:', e);
  } finally {
    pathLoading.value = false;
  }
}

// --- Helpers ---

function getTypeIcon(entityType: string): string {
  const icons: Record<string, string> = { person: '👤', book: '📚', version: '📖', passage: '📜' };
  return icons[entityType] || '●';
}
</script>

<style scoped>
.graph-explorer {
  display: grid;
  grid-template-columns: 320px 1fr;
  height: calc(100vh - 56px); /* subtract navbar height */
  overflow: hidden;
}

/* --- Sidebar --- */
.graph-sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  background: var(--color-navbar-bg, var(--color-surface));
  overflow-y: auto;
}

.sidebar-header {
  padding: var(--space-5) 20px 12px;
}

.sidebar-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.sidebar-subtitle {
  margin: var(--space-1) 0 0;
  font-size: 12px;
  color: var(--color-text-muted);
}

/* --- Search --- */
.search-section {
  padding: 0 var(--space-5) 12px;
}

.search-input-wrapper {
  display: flex;
  gap: var(--space-1-5);
}

.search-input {
  flex: 1;
  padding: var(--space-2) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  outline: none;
  transition: border-color var(--transition-base);
}

.search-input:focus {
  border-color: var(--color-accent);
}

.search-btn {
  padding: var(--space-2) 16px;
  border: none;
  border-radius: var(--radius-md);
  background: var(--color-accent);
  color: white;
  font-size: 13px;
  cursor: pointer;
  transition: opacity var(--transition-base);
}

.search-btn:hover {
  opacity: 0.9;
}

.search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* --- Type Filters --- */
.type-filters {
  display: flex;
  gap: var(--space-1-5);
  margin-top: 8px;
  flex-wrap: wrap;
}

.type-chip {
  padding: var(--space-1) 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  color: var(--color-text-secondary, var(--color-text-muted));
  transition: all var(--transition-base);
}

.type-chip--active {
  border-color: var(--color-accent);
  background: var(--color-accent);
  color: var(--color-accent);
}

/* --- Search Results --- */
.search-results {
  padding: 0 var(--space-5);
}

.results-header {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--color-text-muted);
  margin-bottom: 6px;
}

.results-list {
  list-style: none;
  margin: 0;
  padding: 0;
}

.result-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) 10px;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background var(--transition-fast);
}

.result-item:hover {
  background: var(--color-hover);
}

.result-item--active {
  background: var(--color-accent-light);
}

.result-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.result-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.result-label {
  font-size: 13px;
  color: var(--color-text-primary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.result-type {
  font-size: 11px;
  color: var(--color-text-muted);
}

/* --- Node Info --- */
.node-info {
  padding: var(--space-4) 20px;
  border-top: 1px solid var(--color-border);
  margin-top: auto;
}

.node-info-title {
  margin: 0 0 var(--space-2-5);
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.node-info-list {
  margin: 0;
  font-size: 12px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-0-5) 8px;
}

.node-info-list dt {
  color: var(--color-text-muted);
  font-weight: 500;
}

.node-info-list dd {
  margin: 0;
  color: var(--color-text-secondary, var(--color-text-muted));
  overflow: hidden;
  text-overflow: ellipsis;
}

.node-info-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: 12px;
}

.action-btn {
  flex: 1;
  padding: var(--space-2) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  color: var(--color-text-secondary, var(--color-text-muted));
  transition: all var(--transition-base);
  text-align: center;
}

.action-btn:hover {
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.action-btn--primary {
  background: var(--color-accent);
  color: white;
  border-color: var(--color-accent);
}

.action-btn--primary:hover {
  opacity: 0.9;
  background: var(--color-accent);
}

/* --- Main Canvas --- */
.graph-main {
  position: relative;
  overflow: hidden;
}

/* --- Path Panel --- */
.path-panel {
  position: absolute;
  right: 16px;
  bottom: 16px;
  width: 280px;
  background: var(--color-navbar-bg, var(--color-surface));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-card-hover);
  z-index: var(--z-dropdown);
}

.path-panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2-5) 14px;
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border);
}

.path-panel-body {
  padding: var(--space-3-5);
}

.path-field {
  margin-bottom: 10px;
}

.path-field label {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: var(--color-text-muted);
  margin-bottom: 4px;
}

.path-input {
  width: 100%;
  padding: var(--space-1-5) 10px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  font-size: 12px;
  background: var(--color-page-bg);
  color: var(--color-text-primary);
}

.close-btn {
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 18px;
  color: var(--color-text-muted);
}

.path-result {
  margin-top: 10px;
  font-size: 13px;
}

.path-success {
  color: var(--color-success, var(--color-success-text));
}

.path-empty {
  color: var(--color-error, var(--color-error-text));
}

/* --- Responsive --- */
@media (max-width: 768px) {
  .graph-explorer {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .graph-sidebar {
    max-height: 40vh;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }

  .node-info {
    display: none;
  }
}
</style>
