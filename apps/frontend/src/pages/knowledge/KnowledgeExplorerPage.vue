<template>
  <div class="knowledge-page">
    <ResearchPageHeader
      :title="t('graph.title')"
      :description="t('graph.subtitle')"
      :breadcrumbs="[{ label: t('workspace.knowledgeNav') }]"
    />

    <!-- Academic timeline strip — persistent, spans full width below the header -->
    <TimelineCanvas
      :events="timelineEvents"
      :loading="timelineLoading"
      :error="timelineError"
      :empty-text="t('common.noData')"
      :active-id="activeNode?.id ?? null"
      @retry="loadTimeline"
      @select="onTimelineSelect"
    />

    <div class="knowledge-body">
      <!-- Sidebar -->
      <aside class="knowledge-sidebar">
        <!-- Search -->
        <div class="search-section">
          <div class="search-input-wrapper">
            <input
              v-model="searchQuery"
              type="text"
              class="search-input"
              :placeholder="t('graph.searchPlaceholder')"
              @keyup.enter="onSearch"
            />
            <button class="search-btn" :disabled="searchLoading" @click="onSearch">
              {{ t('common.search') }}
            </button>
          </div>

          <!-- Type filter chips -->
          <div class="type-filters">
            <button
              v-for="et in ENTITY_TYPES"
              :key="et.value"
              class="type-chip"
              :class="{ 'type-chip--active': selectedTypes.includes(et.value) }"
              @click="toggleType(et.value)"
            >
              {{ ENTITY_TYPE_ICONS[et.value] }} {{ et.label }}
            </button>
          </div>
        </div>

        <!-- Search Results -->
        <div v-if="searchResults.length > 0" class="search-results">
          <div class="results-header">
            {{ t('graph.searchResults') }} ({{ searchResults.length }})
          </div>
          <ul class="results-list">
            <li
              v-for="node in searchResults"
              :key="node.id"
              class="result-item"
              :class="{ 'result-item--active': activeNode?.id === node.id }"
              @click="selectEntity(node)"
            >
              <span class="result-icon">{{ getIcon(node.entity_type) }}</span>
              <div class="result-info">
                <span class="result-label">{{ node.label }}</span>
                <span class="result-type">{{ node.entity_type }}</span>
              </div>
            </li>
          </ul>
        </div>

        <div v-else-if="searchQuery && !searchLoading && searchPerformed" class="search-results">
          <p class="no-results">{{ t('common.noData') }}</p>
        </div>

        <!-- Entity Detail -->
        <div v-if="activeNode" class="entity-detail">
          <h3 class="detail-title">{{ getIcon(activeNode.entity_type) }} {{ activeNode.label }}</h3>
          <span class="detail-type">{{ activeNode.entity_type }}</span>

          <dl v-if="propertyEntries.length > 0" class="detail-props">
            <template v-for="[key, value] in propertyEntries" :key="key">
              <dt>{{ key }}</dt>
              <dd>{{ value }}</dd>
            </template>
          </dl>

          <div class="detail-actions">
            <button class="action-btn" @click="loadNeighborhood(activeNode)">
              🔍 {{ t('graph.neighborhood') }}
            </button>
            <button class="action-btn" @click="loadSubgraph(activeNode)">
              🌐 {{ t('graph.expand') }}
            </button>
          </div>
        </div>

        <!-- Edge Detail (selected edge evidence) -->
        <div v-if="activeEdge" class="edge-detail">
          <h3 class="detail-title">📎 {{ activeEdge.label }}</h3>

          <div class="edge-evidence">
            <div class="evidence-field">
              <span class="evidence-label">原文引证</span>
              <blockquote class="evidence-quote">
                {{ activeEdge.evidence.exact_quote }}
              </blockquote>
            </div>

            <div class="evidence-field">
              <span class="evidence-label">出处</span>
              <span class="evidence-value">{{ activeEdge.evidence.citation }}</span>
            </div>

            <div class="evidence-field">
              <span class="evidence-label">文献 ID</span>
              <span class="evidence-value">
                <router-link
                  v-if="activeEdge.evidence.document_id"
                  :to="{ name: 'library-detail', params: { id: activeEdge.evidence.document_id } }"
                  class="evidence-link"
                >
                  {{ activeEdge.evidence.document_id }}
                </router-link>
                <span v-else>—</span>
              </span>
            </div>

            <div v-if="activeEdge.evidence.passage_id" class="evidence-field">
              <span class="evidence-label">条文 ID</span>
              <span class="evidence-value">{{ activeEdge.evidence.passage_id }}</span>
            </div>

            <div v-if="safeSourceUri" class="evidence-field">
              <span class="evidence-label">来源</span>
              <a
                :href="safeSourceUri"
                target="_blank"
                rel="noopener noreferrer"
                class="evidence-link"
              >
                {{ safeSourceUri }}
              </a>
            </div>
          </div>
        </div>
      </aside>

      <!-- Main Canvas -->
      <main class="knowledge-main">
        <div class="view-toolbar">
          <button
            v-for="vt in VIEW_TABS"
            :key="vt.value"
            class="view-tab"
            :class="{ 'view-tab--active': viewMode === vt.value }"
            :aria-pressed="viewMode === vt.value"
            @click="switchView(vt.value)"
          >
            <HfbIcon :icon="vt.icon" :size="15" />
            <span>{{ t(vt.label) }}</span>
          </button>
        </div>

        <div class="view-canvas">
          <GraphCanvas
            v-if="viewMode === 'network'"
            :nodes="graphNodes"
            :edges="graphEdges"
            :loading="graphLoading"
            :error="graphError"
            :center-node-id="activeNode?.id"
            :empty-text="t('graph.emptyHint')"
            @retry="retryLastAction"
            @node-click="onNodeClick"
            @node-double-click="onNodeDoubleClick"
            @edge-click="onEdgeClick"
          />

          <GenealogyTreeCanvas
            v-else-if="viewMode === 'genealogy'"
            :root="genealogyRoot"
            :loading="genealogyLoading"
            :error="genealogyError"
            :empty-text="t('common.noData')"
            :active-id="activeNode?.id ?? null"
            @retry="loadGenealogy"
            @select="onGenealogySelect"
          />

          <GeographicMapCanvas
            v-else
            :points="geoPoints"
            :loading="geoLoading"
            :error="geoError"
            :empty-text="t('common.noData')"
            :active-id="activeNode?.id ?? null"
            @retry="loadGeo"
            @select="onGeoSelect"
          />
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import GraphCanvas from '@/components/graph/GraphCanvas.vue';
import TimelineCanvas from '@/components/graph/TimelineCanvas.vue';
import GenealogyTreeCanvas from '@/components/graph/GenealogyTreeCanvas.vue';
import GeographicMapCanvas from '@/components/graph/GeographicMapCanvas.vue';
import HfbIcon from '@/components/common/HfbIcon.vue';
import type { GraphEdgeData as GraphCanvasEdge } from '@/components/graph/GraphCanvas.vue';
import type { LucideIconName } from '@/components/common/HfbIcon.vue';
import {
  ENTITY_TYPES,
  ENTITY_TYPE_ICONS,
  getEntitySubgraph,
  getNeighbors,
  getGenealogy,
  getGeo,
  getTimeline,
  searchEntities,
} from '@/api/graph';
import type {
  GenealogyTreeNode,
  GeoDistributionPoint,
  GraphEdgeData,
  GraphNodeData,
  TimelineEvent,
} from '@/types/graph';

// ============================================================
// Task 2A: Knowledge Graph page — multi-view integration (1707)
// ============================================================

const { t } = useI18n();

type ViewMode = 'network' | 'genealogy' | 'geo';

interface ViewTab {
  value: ViewMode;
  icon: LucideIconName;
  label: string;
}

const VIEW_TABS: Array<ViewTab> = [
  { value: 'network', icon: 'network', label: 'graph.viewMode.network' },
  { value: 'genealogy', icon: 'git-branch', label: 'graph.viewMode.genealogy' },
  { value: 'geo', icon: 'map', label: 'graph.viewMode.geo' },
];

const viewMode = ref<ViewMode>('network');

// --- Search state ---
const searchQuery = ref('');
const searchLoading = ref(false);
const searchPerformed = ref(false);
const searchResults = ref<Array<GraphNodeData>>([]);
const selectedTypes = ref<Array<string>>(['person', 'book', 'version', 'passage']);

let searchReqId = 0;

function toggleType(type: string) {
  const idx = selectedTypes.value.indexOf(type);
  if (idx >= 0) {
    selectedTypes.value.splice(idx, 1);
  } else {
    selectedTypes.value.push(type);
  }
}

async function onSearch() {
  if (!searchQuery.value.trim()) return;
  searchLoading.value = true;
  searchPerformed.value = true;
  searchResults.value = [];
  const reqId = ++searchReqId;
  try {
    const results = await searchEntities(searchQuery.value, selectedTypes.value, 20);
    if (reqId === searchReqId) {
      searchResults.value = results;
    }
  } catch {
    // keep results empty on error
  } finally {
    if (reqId === searchReqId) {
      searchLoading.value = false;
    }
  }
}

// --- Graph state (network view) ---
const graphNodes = ref<Array<GraphNodeData>>([]);
const graphEdges = ref<Array<GraphEdgeData>>([]);
const graphLoading = ref(false);
const graphError = ref<string | null>(null);
const activeNode = ref<GraphNodeData | null>(null);
const activeEdge = ref<GraphEdgeData | null>(null);

let lastAction: (() => Promise<void>) | null = null;

// --- Multi-view state ---
const timelineEvents = ref<Array<TimelineEvent>>([]);
const timelineLoading = ref(false);
const timelineError = ref<string | null>(null);

const genealogyRoot = ref<GenealogyTreeNode | null>(null);
const genealogyLoading = ref(false);
const genealogyError = ref<string | null>(null);

const geoPoints = ref<Array<GeoDistributionPoint>>([]);
const geoLoading = ref(false);
const geoError = ref<string | null>(null);

async function selectEntity(node: GraphNodeData) {
  activeNode.value = node;
  activeEdge.value = null;
  await loadNeighborhood(node);
}

function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message;
  if (e && typeof e === 'object' && 'response' in e) {
    const resp = (e as { response?: { data?: { message?: string } } }).response;
    if (resp?.data?.message) return resp.data.message;
  }
  return t('common.error');
}

async function loadNeighborhood(node: GraphNodeData) {
  graphLoading.value = true;
  graphError.value = null;
  lastAction = () => loadNeighborhood(node);
  try {
    const result = await getNeighbors(node.entity_type, node.entity_id);
    if (result) {
      graphNodes.value = [result.center, ...(result.neighbors ?? [])];
      graphEdges.value = result.edges ?? [];
    } else {
      graphNodes.value = [node];
      graphEdges.value = [];
    }
  } catch (e: unknown) {
    graphError.value = errorMessage(e);
  } finally {
    graphLoading.value = false;
  }
}

async function loadSubgraph(node: GraphNodeData) {
  graphLoading.value = true;
  graphError.value = null;
  lastAction = () => loadSubgraph(node);
  try {
    const result = await getEntitySubgraph(node.entity_type, node.entity_id);
    if (result) {
      graphNodes.value = result.nodes ?? [];
      graphEdges.value = result.edges ?? [];
    }
  } catch (e: unknown) {
    graphError.value = errorMessage(e);
  } finally {
    graphLoading.value = false;
  }
}

async function loadTimeline() {
  timelineLoading.value = true;
  timelineError.value = null;
  try {
    timelineEvents.value = await getTimeline();
  } catch (e: unknown) {
    timelineError.value = errorMessage(e);
  } finally {
    timelineLoading.value = false;
  }
}

async function loadGenealogy() {
  genealogyLoading.value = true;
  genealogyError.value = null;
  try {
    genealogyRoot.value = await getGenealogy();
  } catch (e: unknown) {
    genealogyError.value = errorMessage(e);
  } finally {
    genealogyLoading.value = false;
  }
}

async function loadGeo() {
  geoLoading.value = true;
  geoError.value = null;
  try {
    geoPoints.value = await getGeo();
  } catch (e: unknown) {
    geoError.value = errorMessage(e);
  } finally {
    geoLoading.value = false;
  }
}

function retryLastAction() {
  if (lastAction) lastAction();
}

// --- View switching + cross-view focus linkage ---

function switchView(mode: ViewMode) {
  if (viewMode.value === mode) return;
  viewMode.value = mode;
  if (mode === 'genealogy' && genealogyRoot.value === null) loadGenealogy();
  else if (mode === 'geo' && geoPoints.value.length === 0) loadGeo();
}

/** Convert a bare (type, id, label) tuple into a GraphNodeData for focus. */
function toNode(entityType: string, entityId: string, label: string): GraphNodeData {
  return { id: `${entityType}:${entityId}`, entity_type: entityType, entity_id: entityId, label, properties: {} };
}

/** Focus an entity without triggering a network reload (used by sub-views). */
function focusEntity(node: GraphNodeData) {
  activeNode.value = node;
  activeEdge.value = null;
}

function onTimelineSelect(ev: TimelineEvent) {
  focusEntity(toNode(ev.entity_type, ev.entity_id, ev.label));
}

function onGenealogySelect(node: GenealogyTreeNode) {
  focusEntity(toNode(node.entity_type || 'version', node.entity_id, node.label));
}

function onGeoSelect(point: GeoDistributionPoint) {
  focusEntity(toNode(point.entity_type || 'version', point.entity_id, point.name));
}

// --- GraphCanvas events ---

function onNodeClick(node: GraphNodeData) {
  activeNode.value = node;
  activeEdge.value = null; // deselect edge when clicking node
}

function onNodeDoubleClick(node: GraphNodeData) {
  activeNode.value = node;
  activeEdge.value = null;
  loadNeighborhood(node);
}

function onEdgeClick(edge: GraphCanvasEdge) {
  activeEdge.value = edge as unknown as GraphEdgeData;
}

// --- Computed ---

const propertyEntries = computed(() => {
  if (!activeNode.value) return [];
  const p = activeNode.value.properties;
  if (!p) return [];
  return Object.entries(p).filter(([, v]) => v !== null && v !== undefined && String(v).length > 0);
});

/** Only render source_uri as a clickable link when it uses https. */
const safeSourceUri = computed(() => {
  const uri = activeEdge.value?.evidence?.source_uri;
  if (!uri || typeof uri !== 'string') return null;
  if (/^https:\/\//i.test(uri.trim())) return uri.trim();
  return null;
});

// --- Helpers ---

function getIcon(entityType: string): string {
  return ENTITY_TYPE_ICONS[entityType] ?? '●';
}

onMounted(loadTimeline);
</script>

<style scoped>
.knowledge-page {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 56px); /* subtract navbar */
  overflow: hidden;
}

.knowledge-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  flex: 1;
  overflow: hidden;
}

/* --- Sidebar --- */
.knowledge-sidebar {
  display: flex;
  flex-direction: column;
  border-right: 1px solid var(--color-border);
  background: var(--color-navbar-bg, var(--color-surface));
  overflow-y: auto;
}

/* --- Search --- */
.search-section {
  padding: var(--space-4) var(--space-5) var(--space-3);
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
  white-space: nowrap;
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
  color: white;
}

/* --- Search Results --- */
.search-results {
  padding: 0 var(--space-5) var(--space-3);
}

.results-header {
  font-size: 11px;
  font-weight: 600;
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

.no-results {
  font-size: 13px;
  color: var(--color-text-muted);
  padding: var(--space-2) 0;
}

/* --- Entity Detail --- */
.entity-detail {
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--color-border);
  margin-top: auto;
}

.detail-title {
  margin: 0 0 var(--space-0-5);
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.detail-type {
  font-size: 11px;
  color: var(--color-text-muted);
}

.detail-props {
  margin: var(--space-3) 0 0;
  font-size: 12px;
  display: grid;
  grid-template-columns: auto 1fr;
  gap: var(--space-0-5) 8px;
}

.detail-props dt {
  color: var(--color-text-muted);
  font-weight: 500;
}

.detail-props dd {
  margin: 0;
  color: var(--color-text-secondary, var(--color-text-muted));
  overflow: hidden;
  text-overflow: ellipsis;
}

.detail-actions {
  display: flex;
  gap: var(--space-2);
  margin-top: var(--space-3);
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

/* --- Edge Detail --- */
.edge-detail {
  padding: var(--space-4) var(--space-5);
  border-top: 1px solid var(--color-border);
  margin-top: auto;
}

.edge-evidence {
  margin-top: var(--space-3);
}

.evidence-field {
  margin-bottom: var(--space-2-5);
}

.evidence-label {
  display: block;
  font-size: 10px;
  font-weight: 600;
  color: var(--color-text-muted);
  margin-bottom: 2px;
}

.evidence-value {
  font-size: 12px;
  color: var(--color-text-secondary, var(--color-text-muted));
  word-break: break-all;
}

.evidence-quote {
  margin: var(--space-1) 0 0;
  padding: var(--space-2) 10px;
  border-left: 3px solid var(--color-accent);
  background: var(--color-accent-light);
  font-size: 13px;
  color: var(--color-text-primary);
  line-height: 1.5;
}

.evidence-link {
  color: var(--color-accent);
  text-decoration: none;
  font-size: 12px;
}

.evidence-link:hover {
  text-decoration: underline;
}

/* --- Main Canvas --- */
.knowledge-main {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.view-toolbar {
  display: flex;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-3);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-navbar-bg, var(--color-surface));
  flex-shrink: 0;
}

.view-tab {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-1-5) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  color: var(--color-text-secondary, var(--color-text-muted));
  transition: all var(--transition-base);
  white-space: nowrap;
}

.view-tab:hover {
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.view-tab--active {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: white;
}

.view-canvas {
  flex: 1;
  overflow: hidden;
  position: relative;
}

.view-canvas > * {
  width: 100%;
  height: 100%;
}

/* --- Responsive --- */
@media (max-width: 768px) {
  .knowledge-body {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
  }

  .knowledge-sidebar {
    max-height: 40vh;
    border-right: none;
    border-bottom: 1px solid var(--color-border);
  }
}
</style>
