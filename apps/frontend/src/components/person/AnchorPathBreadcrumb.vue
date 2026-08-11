<template>
  <div v-if="parsedNodes.length > 0" class="anchor-path-breadcrumb">
    <div class="breadcrumb-label">皇甫谧研究域回溯链：</div>
    <div class="breadcrumb-list">
      <template v-for="(node, index) in parsedNodes" :key="index">
        <div class="path-node">
          <span class="node-type" :style="node.style">[{{ node.typeLabel }}]</span>
          <span class="node-name">{{ node.label }}</span>
        </div>
        <span v-if="index < parsedNodes.length - 1" class="path-arrow">→</span>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

export interface PathNode {
  raw: string;
  prefix: string;
  id: string;
  label: string;
  typeLabel: string;
  style: Record<string, string>;
}

const props = defineProps<{
  anchorPath?: string | Array<string> | null;
}>();

const KNOWN_LABELS: Record<string, string> = {
  huangfu_mi: '皇甫谧',
  zhenjiu_jiayi_jing: '《针灸甲乙经》',
  shanghan_zabing_lun: '《伤寒杂病论》',
  bencao_gangmu: '《本草纲目》',
  huangdi_neijing: '《黄帝内经》',
  suwen: '《素问》',
  lingshu: '《灵枢》',
  lin_yi: '林亿',
  zhang_zhongjing: '张仲景',
  li_shizhen: '李时珍',
  wang_bing: '王冰',
  jiayi_jing: '《甲乙经》',
  daikao_scholar: '待考学者',
};

const parsedNodes = computed<Array<PathNode>>(() => {
  if (!props.anchorPath) return [];

  let rawList: Array<string> = [];
  if (Array.isArray(props.anchorPath)) {
    rawList = props.anchorPath;
  } else if (typeof props.anchorPath === 'string') {
    const trimmed = props.anchorPath.trim();
    if (trimmed.startsWith('[') && trimmed.endsWith(']')) {
      try {
        const parsed = JSON.parse(trimmed) as Array<unknown>;
        if (Array.isArray(parsed)) {
          rawList = parsed.filter((item): item is string => typeof item === 'string');
        }
      } catch {
        rawList = [trimmed];
      }
    } else if (trimmed.includes('->')) {
      rawList = trimmed.split('->').map((s: string) => s.trim());
    } else if (trimmed.length > 0) {
      rawList = [trimmed];
    }
  }

  return rawList.map((item: string): PathNode => {
    const parts = item.split(':');
    const firstPart = parts[0] ?? '';
    const prefix = parts.length > 1 ? firstPart.toLowerCase() : 'entity';
    const rawId: string = parts.length > 1 ? parts.slice(1).join(':') : firstPart;

    let typeLabel = '实体';
    let style: Record<string, string> = { color: 'var(--color-text-secondary)' };

    if (prefix === 'person') {
      typeLabel = '人物';
      style = { color: 'var(--color-accent)' };
    } else if (prefix === 'book') {
      typeLabel = '典籍';
      style = { color: 'var(--color-info-text)' };
    } else if (prefix === 'passage' || prefix === 'chapter') {
      typeLabel = '篇章';
      style = { color: 'var(--color-warning-text)' };
    } else if (prefix === 'concept' || prefix === 'term') {
      typeLabel = '概念';
      style = { color: 'var(--color-success-text)' };
    }

    const label = KNOWN_LABELS[rawId] || rawId.replace(/_/g, ' ');

    return {
      raw: item,
      prefix,
      id: rawId,
      label,
      typeLabel,
      style,
    };
  });
});
</script>

<style scoped>
.anchor-path-breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--space-2, 8px);
  padding: var(--space-3, 12px) var(--space-4, 16px);
  background: var(--color-active, var(--color-hover));
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg, 8px);
  font-size: var(--text-sm, 14px);
  margin-top: var(--space-3, 12px);
  margin-bottom: var(--space-4, 16px);
  flex-wrap: wrap;
}

.breadcrumb-label {
  font-weight: var(--font-semibold, 600);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.breadcrumb-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: var(--space-2, 8px);
}

.path-node {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1, 4px);
  padding: var(--space-0-5, 2px) var(--space-2, 8px);
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md, 6px);
}

.node-type {
  font-weight: var(--font-semibold, 600);
  font-size: var(--text-xs, 12px);
}

.node-name {
  color: var(--color-text-primary);
  font-weight: var(--font-medium, 500);
}

.path-arrow {
  color: var(--color-text-muted);
  font-weight: var(--font-bold, 700);
}
</style>
