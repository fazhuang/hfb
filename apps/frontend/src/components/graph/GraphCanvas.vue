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
    <div ref="networkRef" class="graph-network" :class="{ 'graph-network--ready': nodes.length > 0 }"></div>
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
}>();

const containerRef = ref<HTMLElement | null>(null);
const networkRef = ref<HTMLElement | null>(null);

let network: Network | null = null;

// Entity type colors
const TYPE_COLORS: Record<string, { bg: string; border: string; highlight: string }> = {
  person: { bg: '#E8F4FD', border: '#2196F3', highlight: '#BBDEFB' },
  book: { bg: '#FEF3E2', border: '#FF9800', highlight: '#FFE0B2' },
  version: { bg: '#E8F5E9', border: '#4CAF50', highlight: '#C8E6C9' },
  passage: { bg: '#F3E5F5', border: '#9C27B0', highlight: '#E1BEE7' },
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
    props.nodes.map((n) => {
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
    props.edges.map((e) => ({
      id: e.id,
      from: e.source_id,
      to: e.target_id,
      label: e.label,
      title: `${e.label} (${e.source})`,
      arrows: 'to',
      font: { size: 10, color: '#666', strokeWidth: 0, align: 'middle' as const },
      color: { color: '#999', highlight: '#2196F3' },
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
      network.focus(newCenter, { scale: 1.5, animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
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
  border-radius: 8px;
  overflow: hidden;
  background: var(--color-page-bg, #fafafa);
  border: 1px solid var(--color-border, #e2e8f0);
}

.graph-network {
  width: 100%;
  height: 100%;
  min-height: 500px;
  opacity: 0;
  transition: opacity 0.3s;
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
  gap: 12px;
  color: var(--color-text-secondary, #718096);
  font-size: 14px;
}

.graph-state--error {
  color: var(--color-error, #e53e3e);
}

.graph-retry-btn {
  padding: 6px 16px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 6px;
  background: transparent;
  color: var(--color-accent, #2b6cb0);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.15s;
}

.graph-retry-btn:hover {
  background: var(--color-accent, #2b6cb0);
  color: white;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--color-border, #e2e8f0);
  border-top-color: var(--color-accent, #2b6cb0);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
