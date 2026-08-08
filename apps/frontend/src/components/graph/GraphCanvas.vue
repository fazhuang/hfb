<template>
  <div ref="containerRef" class="graph-container">
    <div v-if="loading" class="graph-state graph-state--loading">
      <span class="spinner"></span>
      {{ t('common.loading') }}
    </div>
    <div v-else-if="error" class="graph-state graph-state--error">
      {{ error }}
      <button class="graph-retry-btn" @click="$emit('retry')">{{ t('common.retry') }}</button>
    </div>
    <div v-else-if="nodes.length === 0" class="graph-state graph-state--empty">
      {{ emptyText || t('graph.emptyHint') }}
    </div>
    <div
      ref="networkRef"
      class="graph-network"
      :class="{ 'graph-network--ready': nodes.length > 0 }"
    ></div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { Network } from 'vis-network';
import { DataSet } from 'vis-data';
import 'vis-network/styles/vis-network.min.css';

const { t } = useI18n();

export interface GraphNodeData {
  id: string;
  entity_type: string;
  entity_id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphEdgeData {
  id: string;
  source_id: string;
  target_id: string;
  relation_type: string;
  label: string;
  source: string;
  evidence?: {
    document_id?: string;
    chunk_id?: string;
    exact_quote?: string;
    citation?: string;
    version_id?: string;
    passage_id?: string;
    source_uri?: string;
    claim_text?: string;
  };
}

const props = defineProps<{
  nodes: GraphNodeData[];
  edges: GraphEdgeData[];
  loading?: boolean;
  error?: string | null;
  emptyText?: string;
  centerNodeId?: string;
}>();

const emit = defineEmits<{
  (e: 'retry'): void;
  (e: 'node-click', node: GraphNodeData): void;
  (e: 'node-double-click', node: GraphNodeData): void;
  (e: 'edge-click', edge: GraphEdgeData): void;
}>();

const containerRef = ref<HTMLElement | null>(null);
const networkRef = ref<HTMLElement | null>(null);

let network: Network | null = null;

// Entity type colors
const TYPE_COLORS: Record<string, { bg: string; border: string; highlight: string }> = {
  person: { bg: 'var(--color-accent-light)', border: 'var(--color-accent)', highlight: '#BBDEFB' },
  book: { bg: 'var(--color-warning-bg)', border: 'var(--color-warning)', highlight: '#FFE0B2' },
  version: { bg: 'var(--color-success-bg)', border: 'var(--color-success)', highlight: '#C8E6C9' },
  passage: { bg: 'var(--color-accent-light)', border: 'var(--color-accent)', highlight: '#E1BEE7' },
};

const TYPE_ICONS: Record<string, string> = {
  person: '👤',
  book: '📚',
  version: '📖',
  passage: '📜',
};

const DEFAULT_COLOR = { bg: '#F5F5F5', border: '#9E9E9E', highlight: '#E0E0E0' };

function buildNetwork() {
  if (!networkRef.value || props.nodes.length === 0) return;

  // Destroy existing network
  if (network) {
    network.destroy();
    network = null;
  }

  const visNodes = new DataSet(
    props.nodes
      .filter((n) => n && n.id)
      .map((n) => {
        const colors = TYPE_COLORS[n.entity_type] || DEFAULT_COLOR;
        const icon = TYPE_ICONS[n.entity_type] || '●';
        return {
          id: n.id,
          label: `${icon} ${n.label}`,
          title: buildTooltip(n),
          color: {
            background: colors.bg,
            border: colors.border,
            highlight: { background: colors.highlight, border: colors.border },
          },
          font: { size: 13, face: '-apple-system, BlinkMacSystemFont, "PingFang SC", sans-serif' },
          shape: 'box' as const,
          borderWidth: 2,
          margin: { top: 8, right: 12, bottom: 8, left: 12 },
        };
      }),
  );

  const visEdges = new DataSet(
    props.edges
      .filter((e) => e && e.id && e.source_id && e.target_id)
      .map((e) => ({
        id: e.id,
        from: e.source_id,
        to: e.target_id,
        label: e.label,
        title: `${e.label} (${e.source})`,
        arrows: 'to',
        font: {
          size: 10,
          color: 'var(--color-text-secondary)',
          strokeWidth: 0,
          align: 'middle' as const,
        },
        color: { color: 'var(--color-text-muted)', highlight: 'var(--color-accent)' },
        width: 1.5,
        smooth: { enabled: true, type: 'continuous', roundness: 0.5 },
      })),
  );

  const options = {
    physics: {
      solver: 'forceAtlas2Based' as const,
      forceAtlas2Based: {
        gravitationalConstant: -30,
        centralGravity: 0.005,
        springLength: 180,
        springConstant: 0.04,
      },
      stabilization: { iterations: 100 },
    },
    interaction: {
      hover: true,
      tooltipDelay: 200,
      zoomView: true,
      dragView: true,
      navigationButtons: false,
    },
    layout: {
      improvedLayout: true,
    },
  };

  network = new Network(networkRef.value, { nodes: visNodes, edges: visEdges }, options);

  // Expose the vis-network instance on the DOM element so E2E tests can
  // select edges programmatically (edges live on a Canvas, not in the DOM).
  if (networkRef.value) {
    (networkRef.value as any).__visNetwork = network;
  }

  // Events
  network.on('click', (params) => {
    if (params.nodes.length === 1) {
      const nodeData = props.nodes.find((n) => n.id === params.nodes[0]);
      if (nodeData) {
        emit('node-click', nodeData);
      }
    }
  });

  network.on('doubleClick', (params) => {
    if (params.nodes.length === 1) {
      const nodeData = props.nodes.find((n) => n.id === params.nodes[0]);
      if (nodeData) {
        emit('node-double-click', nodeData);
      }
    }
  });

  // Edge click — emit edge data for evidence inspection
  network.on('selectEdge', (params) => {
    if (params.edges.length === 1) {
      const edgeData = props.edges.find((e) => e.id === params.edges[0]);
      if (edgeData) {
        emit('edge-click', edgeData);
      }
    }
  });

  // Center on centerNodeId if provided
  if (props.centerNodeId) {
    nextTick(() => {
      network?.focus(props.centerNodeId!, { scale: 1.2, animation: true });
    });
  }
}

function buildTooltip(node: GraphNodeData): string {
  const p = node.properties;
  let tip = `<div style="max-width:300px;font-size:13px;line-height:1.5;">`;
  tip += `<strong>${node.label}</strong><br>`;
  tip += `<span style="color:#888;">${node.entity_type}</span>`;
  if (p.name) tip += `<br>姓名: ${p.name}`;
  if (p.title) tip += `<br>书名: ${p.title}`;
  if (p.version_name) tip += `<br>版本: ${p.version_name}`;
  if (p.dynasty) tip += `<br>朝代: ${p.dynasty}`;
  if (p.era) tip += `<br>时期: ${p.era}`;
  if (p.category) tip += `<br>分类: ${p.category}`;
  if (p.repository) tip += `<br>收藏: ${p.repository}`;
  if (p.content_preview) tip += `<br>内容: ${p.content_preview}`;
  tip += `</div>`;
  return tip;
}

function destroyNetwork() {
  if (network) {
    network.destroy();
    network = null;
  }
}

onMounted(() => {
  nextTick(() => buildNetwork());
});

onUnmounted(() => {
  destroyNetwork();
});

watch(
  () => [props.nodes, props.edges],
  () => {
    nextTick(() => buildNetwork());
  },
  { deep: true },
);

watch(
  () => props.centerNodeId,
  (newCenter) => {
    if (newCenter && network) {
      network.focus(newCenter, {
        scale: 1.5,
        animation: { duration: 500, easingFunction: 'easeInOutQuad' },
      });
    }
  },
);
</script>

<style scoped>
.graph-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 500px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
}

.graph-network {
  width: 100%;
  height: 100%;
  min-height: 500px;
  opacity: 0;
  transition: opacity var(--transition-slow);
}

.graph-network--ready {
  opacity: 1;
}

.graph-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 500px;
  gap: var(--space-3);
  color: var(--color-text-secondary, var(--color-text-muted));
  font-size: 14px;
}

.graph-state--error {
  color: var(--color-error, var(--color-error-text));
}

.graph-retry-btn {
  padding: var(--space-1-5) 16px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-accent);
  cursor: pointer;
  font-size: 13px;
  transition: all var(--transition-base);
}

.graph-retry-btn:hover {
  background: var(--color-accent);
  color: white;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin var(--transition-spinner) linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
