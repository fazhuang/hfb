<template>
  <div class="genealogy-canvas">
    <div v-if="loading" class="gen-state">
      <span class="spinner"></span>
      {{ t('common.loading') }}
    </div>
    <div v-else-if="error" class="gen-state gen-state--error">
      {{ error }}
      <button class="gen-retry" @click="$emit('retry')">{{ t('common.retry') }}</button>
    </div>
    <div v-else-if="!root" class="gen-state">{{ emptyText }}</div>
    <div v-else class="gen-tree" role="tree">
      <GenealogyNode
        :node="root"
        :active-id="activeId"
        @select="$emit('select', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import type { GenealogyTreeNode } from '@/types/graph';
import GenealogyNode from './GenealogyNode.vue';

const { t } = useI18n();

defineProps<{
  root: GenealogyTreeNode | null;
  loading?: boolean;
  error?: string | null;
  emptyText?: string;
  activeId?: string | null;
}>();

defineEmits<{
  (e: 'select', node: GenealogyTreeNode): void;
  (e: 'retry'): void;
}>();
</script>

<style scoped>
.genealogy-canvas {
  width: 100%;
  height: 100%;
  min-height: 500px;
  padding: var(--space-5);
  overflow: auto;
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
}

.gen-state {
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

.gen-state--error {
  color: var(--color-error, var(--color-error-text));
}

.gen-retry {
  padding: var(--space-1-5) 16px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-accent);
  cursor: pointer;
  font-size: 13px;
}

.gen-tree {
  display: flex;
  justify-content: center;
  padding: var(--space-4) 0;
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
