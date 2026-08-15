<template>
  <li class="gen-node" :class="`gen-node--${node.kind}`" role="treeitem" :aria-expanded="true">
    <button
      class="gen-node__label"
      :class="{ 'gen-node__label--active': activeId === node.id }"
      @click="$emit('select', node)"
    >
      <span class="gen-node__kind">{{ kindBadge }}</span>
      <span class="gen-node__name">{{ node.label }}</span>
      <span v-if="node.era" class="gen-node__meta">{{ node.era }}</span>
      <span v-if="node.year" class="gen-node__meta">{{ node.year }}</span>
    </button>
    <ul v-if="node.children.length > 0" class="gen-children" role="group">
      <GenealogyNode
        v-for="child in node.children"
        :key="child.id"
        :node="child"
        :active-id="activeId"
        @select="$emit('select', $event)"
      />
    </ul>
  </li>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { GenealogyTreeNode } from '@/types/graph';

const props = defineProps<{
  node: GenealogyTreeNode;
  activeId?: string | null;
}>();

defineEmits<{
  (e: 'select', node: GenealogyTreeNode): void;
}>();

const KIND_LABELS: Record<string, string> = {
  root: '本书',
  original: '正本',
  manuscript: '抄本',
  translation: '译本',
  collated: '校注本',
  blockprint: '刊本',
  version: '版本',
};

const kindBadge = computed(() => KIND_LABELS[props.node.kind] ?? '版本');
</script>

<style scoped>
.gen-node {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0 var(--space-2);
  position: relative;
}

.gen-node__label {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface, var(--color-page-bg));
  cursor: pointer;
  font-size: 12px;
  color: var(--color-text-primary);
  transition: all var(--transition-fast);
  max-width: 200px;
}

.gen-node__label:hover {
  background: var(--color-hover);
}

.gen-node__label--active {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px var(--color-accent-light);
}

.gen-node__kind {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  background: var(--color-accent-light);
  color: var(--color-accent);
  white-space: nowrap;
}

.gen-node--collated .gen-node__kind {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.gen-node--original .gen-node__kind,
.gen-node--root .gen-node__kind {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.gen-node--manuscript .gen-node__kind {
  background: var(--color-info-bg);
  color: var(--color-info-text);
}

.gen-node__name {
  white-space: nowrap;
}

.gen-node__meta {
  font-size: 10px;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.gen-children {
  display: flex;
  list-style: none;
  margin: var(--space-4) 0 0;
  padding: var(--space-2) 0 0;
  position: relative;
}

.gen-children::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  right: 50%;
  height: var(--space-2);
  border-top: 1px solid var(--color-border);
}
</style>
