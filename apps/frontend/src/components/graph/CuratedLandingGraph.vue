<template>
  <div class="landing-graph-container">
    <div class="graph-header">
      <span class="graph-badge">{{ t('graph.title') }}</span>
      <h3 class="graph-title">魏晋名医皇甫谧与《针灸甲乙经》学术关系网络</h3>
    </div>

    <!-- 5 大分维图例 Legend -->
    <div class="graph-legend" role="list" aria-label="学术研究维度图例">
      <div
        v-for="item in legends"
        :key="item.key"
        class="legend-item"
        :class="`type-${item.key}`"
        role="listitem"
      >
        <span class="legend-dot" aria-hidden="true"></span>
        <span class="legend-label">{{ item.label }}</span>
      </div>
    </div>

    <div class="graph-svg-wrapper">
      <svg
        class="landing-svg"
        viewBox="0 0 600 400"
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label="皇甫谧与针灸甲乙经学术关系网络"
      >
        <!-- 连线组 -->
        <g class="edges-group">
          <line
            v-for="(edge, idx) in computedEdges"
            :key="`edge-${idx}`"
            :x1="edge.x1"
            :y1="edge.y1"
            :x2="edge.x2"
            :y2="edge.y2"
            class="graph-edge"
            :class="{
              'is-active':
                activeNodeId && (edge.source === activeNodeId || edge.target === activeNodeId),
            }"
          />
        </g>

        <!-- 节点组 -->
        <g class="nodes-group">
          <g
            v-for="node in nodes"
            :key="node.id"
            class="graph-node-group"
            :class="[
              `type-${node.category}`,
              {
                'is-active': activeNodeId === node.id,
                'is-connected': isConnected(node.id),
                'is-dimmed': activeNodeId && activeNodeId !== node.id && !isConnected(node.id),
              },
            ]"
            :transform="`translate(${node.x}, ${node.y})`"
            tabindex="0"
            role="button"
            :aria-label="`${node.label} (${categoryLabels[node.category]})`"
            @mouseenter="activeNodeId = node.id"
            @mouseleave="activeNodeId = null"
            @focus="activeNodeId = node.id"
            @blur="activeNodeId = null"
          >
            <!-- 节点外圈脉冲光晕 (仅中心节点皇甫谧) -->
            <circle v-if="node.id === 'person:huangfu_mi'" r="44" class="pulse-ring" />
            <!-- 节点主图形 -->
            <circle :r="node.r" class="node-circle" />
            <!-- 节点文本 -->
            <text dy="0.35em" text-anchor="middle" class="node-text">
              {{ node.label }}
            </text>
          </g>
        </g>
      </svg>
    </div>

    <!-- 底部节点学术来源说明 card -->
    <div class="graph-info-card" role="region" aria-live="polite">
      <div v-if="selectedNode" class="info-content">
        <div class="info-meta">
          <span class="info-tag" :class="`type-${selectedNode.category}`">
            {{ categoryLabels[selectedNode.category] }}
          </span>
          <span class="info-id">{{ selectedNode.id }}</span>
        </div>
        <strong class="info-title">{{ selectedNode.label }}</strong>
        <p class="info-desc">{{ selectedNode.description }}</p>
      </div>
      <div v-else class="info-content is-empty">
        <span class="info-icon">💡</span>
        <p class="info-desc">悬停或通过键盘 Tab 聚焦节点，可探索魏晋针灸文献考据渊源与 5 大维度演变图谱。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

export type NodeCategory = 'work' | 'person' | 'edition' | 'transmission' | 'research';

export interface NodeData {
  id: string;
  label: string;
  category: NodeCategory;
  x: number;
  y: number;
  r: number;
  description: string;
}

export interface EdgeData {
  source: string;
  target: string;
}

export interface ComputedEdge {
  source: string;
  target: string;
  x1: number;
  y1: number;
  x2: number;
  y2: number;
}

export interface LegendItem {
  key: NodeCategory;
  label: string;
}

const activeNodeId = ref<string | null>(null);

const categoryLabels: Record<NodeCategory, string> = {
  work: '著作',
  person: '人物',
  edition: '版本',
  transmission: '地域传播',
  research: '现代研究',
};

const legends: Array<LegendItem> = [
  { key: 'work', label: '著作' },
  { key: 'person', label: '人物' },
  { key: 'edition', label: '版本' },
  { key: 'transmission', label: '地域传播' },
  { key: 'research', label: '现代研究' },
];

// 13 个精准划分 5 大已策展研究维度的静态 DOM 节点，中心节点为皇甫谧 (person:huangfu_mi)
const nodes: Array<NodeData> = [
  // 1. 中心节点 (person)
  {
    id: 'person:huangfu_mi',
    label: '皇甫谧',
    category: 'person',
    x: 300,
    y: 195,
    r: 36,
    description:
      '魏晋时期著名医学家、史学家、文献学家（215–282），字士安，号玄晏先生，撰《针灸甲乙经》。',
  },
  // 2. 著作维度 (work)
  {
    id: 'work:zhenjiu_jiayi_jing',
    label: '针灸甲乙经',
    category: 'work',
    x: 185,
    y: 105,
    r: 28,
    description: '中国现存最早的针灸学专著，分类整理《素问》《灵枢》《明堂孔穴针灸治要》。',
  },
  {
    id: 'work:diwang_shiji',
    label: '帝王世纪',
    category: 'work',
    x: 300,
    y: 75,
    r: 24,
    description: '皇甫谧所撰史学巨著，记载上古至魏晋帝王世代与重大历史事件。',
  },
  {
    id: 'work:gaoshi_zhuan',
    label: '高士传',
    category: 'work',
    x: 125,
    y: 80,
    r: 22,
    description: '皇甫谧撰历代隐逸人物传记，体现魏晋高洁名士思想风貌。',
  },
  // 3. 人物维度 (person)
  {
    id: 'person:huang_longxiang',
    label: '黄龙祥',
    category: 'person',
    x: 415,
    y: 110,
    r: 24,
    description: '现代针灸文献专家，基于多版本校勘整理权威学术校注本与针灸学术史。',
  },
  {
    id: 'person:xi_hong',
    label: '席弘',
    category: 'person',
    x: 505,
    y: 150,
    r: 22,
    description: '宋代针灸名家，席弘针法创始人，继承并弘扬《针灸甲乙经》针刺补泻法。',
  },
  // 4. 版本维度 (edition)
  {
    id: 'edition:zhengtong_daozang',
    label: '正统道藏本',
    category: 'edition',
    x: 125,
    y: 225,
    r: 24,
    description: '明正统十年（1445）刊印《正统道藏》洞神部本文汇集中收录的古刊本。',
  },
  {
    id: 'edition:siku_quanshu',
    label: '四库全书本',
    category: 'edition',
    x: 75,
    y: 155,
    r: 22,
    description: '清乾隆年间编纂《四库全书》子部医家类收录的《针灸甲乙经》影印本。',
  },
  // 5. 地域传播维度 (transmission)
  {
    id: 'transmission:anding_chaoge',
    label: '安定朝歌',
    category: 'transmission',
    x: 210,
    y: 310,
    r: 24,
    description: '皇甫谧出生与学术萌芽之地，魏晋时期西北针灸学术重镇。',
  },
  {
    id: 'transmission:longdong_chuanbo',
    label: '陇东传播',
    category: 'transmission',
    x: 100,
    y: 320,
    r: 22,
    description: '《针灸甲乙经》在陇东甘肃地区的学术继承与传统诊疗流传。',
  },
  {
    id: 'transmission:dongya_chuanbo',
    label: '东亚传播',
    category: 'transmission',
    x: 300,
    y: 340,
    r: 22,
    description: '隋唐以后传入朝鲜半岛与日本，成为东亚传统针灸医学典范教材。',
  },
  // 6. 现代研究维度 (research)
  {
    id: 'research:jingxue_kaoding',
    label: '现代经穴考订',
    category: 'research',
    x: 420,
    y: 285,
    r: 24,
    description: '结合现代解剖学与文献学考订《针灸甲乙经》349个腧穴定位。',
  },
  {
    id: 'research:wenxian_jiliang',
    label: '文献计量研究',
    category: 'research',
    x: 510,
    y: 260,
    r: 22,
    description: '利用数字人文与知识图谱方法分析《甲乙经》学术网络与引用频次。',
  },
];

// 关系连线 (围绕中心节点皇甫谧与 5 大维度关联)
const edges: Array<EdgeData> = [
  { source: 'person:huangfu_mi', target: 'work:zhenjiu_jiayi_jing' },
  { source: 'person:huangfu_mi', target: 'work:diwang_shiji' },
  { source: 'person:huangfu_mi', target: 'work:gaoshi_zhuan' },
  { source: 'person:huangfu_mi', target: 'person:huang_longxiang' },
  { source: 'person:huangfu_mi', target: 'person:xi_hong' },
  { source: 'person:huangfu_mi', target: 'transmission:anding_chaoge' },
  { source: 'person:huangfu_mi', target: 'research:jingxue_kaoding' },
  { source: 'work:zhenjiu_jiayi_jing', target: 'edition:zhengtong_daozang' },
  { source: 'work:zhenjiu_jiayi_jing', target: 'edition:siku_quanshu' },
  { source: 'work:zhenjiu_jiayi_jing', target: 'transmission:dongya_chuanbo' },
  { source: 'transmission:anding_chaoge', target: 'transmission:longdong_chuanbo' },
  { source: 'person:huang_longxiang', target: 'research:jingxue_kaoding' },
  { source: 'research:jingxue_kaoding', target: 'research:wenxian_jiliang' },
];

const nodeMap = computed<Map<string, NodeData>>(() => {
  const map = new Map<string, NodeData>();
  for (const n of nodes) {
    map.set(n.id, n);
  }
  return map;
});

const computedEdges = computed<Array<ComputedEdge>>(() => {
  const result: Array<ComputedEdge> = [];
  for (const e of edges) {
    const s = nodeMap.value.get(e.source);
    const t = nodeMap.value.get(e.target);
    if (s && t) {
      result.push({
        source: e.source,
        target: e.target,
        x1: s.x,
        y1: s.y,
        x2: t.x,
        y2: t.y,
      });
    }
  }
  return result;
});

const selectedNode = computed<NodeData | null>(() => {
  if (!activeNodeId.value) return null;
  return nodeMap.value.get(activeNodeId.value) ?? null;
});

function isConnected(nodeId: string): boolean {
  if (!activeNodeId.value) return false;
  if (nodeId === activeNodeId.value) return true;
  return edges.some(
    (e) =>
      (e.source === activeNodeId.value && e.target === nodeId) ||
      (e.target === activeNodeId.value && e.source === nodeId),
  );
}
</script>

<style scoped>
.landing-graph-container {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  width: 100%;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-2xl);
  padding: var(--space-5);
  box-shadow: var(--shadow-sm);
}

.graph-header {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.graph-badge {
  display: inline-block;
  align-self: flex-start;
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  color: var(--color-accent);
  background: var(--color-accent-light);
  padding: var(--space-0-5) var(--space-2-5);
  border-radius: var(--radius-full);
}

.graph-title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

/* 5 大分维图例 Legend */
.graph-legend {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-1) 0;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--radius-full);
  display: inline-block;
  box-sizing: border-box;
}

.legend-item.type-work .legend-dot {
  background: var(--color-surface);
  border: 2px solid var(--color-accent);
}
.legend-item.type-person .legend-dot {
  background: var(--color-accent);
}
.legend-item.type-edition .legend-dot {
  background: var(--color-info);
}
.legend-item.type-transmission .legend-dot {
  background: var(--color-warning);
}
.legend-item.type-research .legend-dot {
  background: var(--color-success);
}

.graph-svg-wrapper {
  position: relative;
  width: 100%;
  overflow: hidden;
  border-radius: var(--radius-xl);
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
}

.landing-svg {
  width: 100%;
  height: auto;
  display: block;
}

/* 连线 */
.graph-edge {
  stroke: var(--color-border);
  stroke-width: 1.5;
  transition:
    stroke var(--transition-base),
    stroke-width var(--transition-base),
    opacity var(--transition-base);
  vector-effect: non-scaling-stroke;
}

.graph-edge.is-active {
  stroke: var(--color-accent);
  stroke-width: 2.5;
  opacity: 1;
}

/* 节点 */
.graph-node-group {
  cursor: pointer;
  outline: none;
  transition:
    opacity var(--transition-base),
    transform var(--transition-base);
}

.graph-node-group.is-dimmed {
  opacity: 0.25;
}

.graph-node-group:focus-visible .node-circle {
  stroke: var(--color-accent);
  stroke-width: 3px;
}

.node-circle {
  transition: all var(--transition-base);
  vector-effect: non-scaling-stroke;
}

.node-text {
  font-size: 11px;
  font-weight: var(--font-bold);
  pointer-events: none;
  user-select: none;
}

/* 类型配色方案（零 Hex 色值，全量 Design Tokens） */
.type-person .node-circle {
  fill: var(--color-accent);
  stroke: var(--color-accent-hover);
}
.type-person .node-text {
  fill: var(--color-on-accent);
  font-size: 13px;
}

.type-work .node-circle {
  fill: var(--color-surface);
  stroke: var(--color-accent);
  stroke-width: 2;
}
.type-work .node-text {
  fill: var(--color-accent);
}

.type-edition .node-circle {
  fill: var(--color-info-bg);
  stroke: var(--color-info);
  stroke-width: 1.5;
}
.type-edition .node-text {
  fill: var(--color-info-text);
}

.type-transmission .node-circle {
  fill: var(--color-warning-bg);
  stroke: var(--color-warning);
  stroke-width: 1.5;
}
.type-transmission .node-text {
  fill: var(--color-warning-text);
}

.type-research .node-circle {
  fill: var(--color-success-bg);
  stroke: var(--color-success);
  stroke-width: 1.5;
}
.type-research .node-text {
  fill: var(--color-success-text);
}

/* 悬停与激活放大 */
.graph-node-group.is-active .node-circle,
.graph-node-group:hover .node-circle {
  transform: scale(1.15);
  stroke: var(--color-accent-hover);
  stroke-width: 2.5;
}

/* 中心节点脉冲微动画 */
.pulse-ring {
  fill: none;
  stroke: var(--color-accent);
  stroke-width: 1.5;
  opacity: 0.3;
  animation: pulse-ring 2.5s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
  transform-origin: center;
}

@keyframes pulse-ring {
  0% {
    transform: scale(0.8);
    opacity: 0.6;
  }
  50% {
    transform: scale(1.15);
    opacity: 0.2;
  }
  100% {
    transform: scale(0.8);
    opacity: 0.6;
  }
}

/* 减缓动画 */
@media (prefers-reduced-motion: reduce) {
  .pulse-ring {
    animation: none;
  }
  .node-circle,
  .graph-node-group,
  .graph-edge {
    transition: none;
  }
}

/* 底部说明卡片 */
.graph-info-card {
  min-height: 76px;
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-3) var(--space-4);
  display: flex;
  align-items: center;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  width: 100%;
}

.info-content.is-empty {
  flex-direction: row;
  align-items: center;
  gap: var(--space-2-5);
  color: var(--color-text-muted);
}

.info-icon {
  font-size: 16px;
}

.info-meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.info-tag {
  font-size: var(--text-xs);
  font-weight: var(--font-bold);
  padding: 1px var(--space-2);
  border-radius: var(--radius-full);
}

.info-tag.type-work {
  color: var(--color-accent);
  background: var(--color-accent-light);
}
.info-tag.type-person {
  color: var(--color-on-accent);
  background: var(--color-accent);
}
.info-tag.type-edition {
  color: var(--color-info-text);
  background: var(--color-info-bg);
}
.info-tag.type-transmission {
  color: var(--color-warning-text);
  background: var(--color-warning-bg);
}
.info-tag.type-research {
  color: var(--color-success-text);
  background: var(--color-success-bg);
}

.info-id {
  font-size: var(--text-xs);
  font-family: var(--font-mono);
  color: var(--color-text-muted);
}

.info-title {
  font-size: var(--text-sm);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.info-desc {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-secondary);
  line-height: 1.45;
}
</style>
