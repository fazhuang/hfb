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
import type { GraphEdgeData, GraphNodeData } from '@/types/graph';

export type { GraphEdgeData, GraphNodeData } from '@/types/graph';

const { t } = useI18n();

const props = defineProps<{
  nodes: Array<GraphNodeData>;
  edges: Array<GraphEdgeData>;
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

// The vis-network instance is attached to the DOM node so E2E tests can select
// edges programmatically (edges render on a Canvas, not in the DOM).
interface NetworkHostElement extends HTMLElement {
  __visNetwork?: Network | null;
}

let network: Network | null = null;

// Entity type colors — every value is a design token (resolved to a computed
// value before being handed to the vis-network canvas).
const TYPE_COLORS: Record<string, { bg: string; border: string; highlight: string }> = {
  person: { bg: 'var(--color-accent-light)', border: 'var(--color-accent)', highlight: 'var(--color-info-bg)' },
  book: { bg: 'var(--color-warning-bg)', border: 'var(--color-warning)', highlight: 'var(--color-warning)' },
  version: { bg: 'var(--color-success-bg)', border: 'var(--color-success)', highlight: 'var(--color-success)' },
  passage: { bg: 'var(--color-accent-light)', border: 'var(--color-accent)', highlight: 'var(--color-info-bg)' },
};

const TYPE_ICONS: Record<string, string> = {
  person: '👤',
  book: '📚',
  version: '📖',
  passage: '📜',
};

const DEFAULT_COLOR = {
  bg: 'var(--color-page-bg)',
  border: 'var(--color-border)',
  highlight: 'var(--color-hover)',
};

// vis-network draws on a canvas where a CSS var() string is an invalid fill
// color and falls back to black. Resolve the token to its computed value before
// handing it to the canvas. Fallback resolves a neutral token — never a raw hex.
function resolveToken(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function resolveColor(value: string): string {
  const match = value.match(/^var\(([^)]+)\)$/);
  if (!match || !match[1]) return value;
  return resolveToken(match[1].trim()) || resolveToken('--color-page-bg');
}

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
            background: resolveColor(colors.bg),
            border: resolveColor(colors.border),
            highlight: { background: resolveColor(colors.highlight), border: resolveColor(colors.border) },
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
          color: resolveColor('var(--color-text-secondary)'),
          strokeWidth: 0,
          align: 'middle' as const,
        },
        color: { color: resolveColor('var(--color-text-muted)'), highlight: resolveColor('var(--color-accent)') },
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
    (networkRef.value as NetworkHostElement).__visNetwork = network;
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
  const lines: Array<string> = [];
  lines.push(`${node.label}`);
  lines.push(`类型: ${node.entity_type}`);
  if (p.name) lines.push(`姓名: ${p.name}`);
  if (p.title) lines.push(`书名: ${p.title}`);
  if (p.version_name) lines.push(`版本: ${p.version_name}`);
  if (p.dynasty) lines.push(`朝代: ${p.dynasty}`);
  if (p.era) lines.push(`时期: ${p.era}`);
  if (p.category) lines.push(`分类: ${p.category}`);
  if (p.repository) lines.push(`收藏: ${p.repository}`);
  if (p.content_preview) lines.push(`内容: ${p.content_preview}`);
  return lines.join('\n');
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
