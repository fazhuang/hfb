<template>
  <div class="rrt-root" role="toolbar" aria-label="报告筛选工具栏">
    <div class="rrt-filter-group">
      <label for="report-status-filter" class="rrt-label">状态筛选</label>
      <select id="report-status-filter" class="rrt-select" :value="statusFilter" @change="onChange">
        <option value="">全部</option>
        <option value="ready">报告就绪</option>
        <option value="missing">报告缺失</option>
        <option value="failed">报告失败</option>
        <option value="pending">待生成</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { ReportStatusFilter } from '@/composables/useResearchReports';

defineProps<{
  statusFilter: ReportStatusFilter;
}>();

const emit = defineEmits<{
  'update:statusFilter': [value: ReportStatusFilter];
}>();

function onChange(e: Event) {
  const target = e.target as HTMLSelectElement;
  emit('update:statusFilter', target.value as ReportStatusFilter);
}
</script>

<style scoped>
.rrt-root {
  display: flex;
  align-items: center;
  margin-bottom: var(--space-4);
}

.rrt-filter-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.rrt-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  white-space: nowrap;
}

.rrt-select {
  padding: var(--space-1-5) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  cursor: pointer;
  min-width: 120px;
  transition: border-color var(--transition-base);
}

.rrt-select:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
  border-color: var(--color-accent);
}

.rrt-select:hover {
  border-color: var(--color-accent);
}
</style>
