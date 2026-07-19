<template>
  <div class="rrt-root" role="toolbar" aria-label="报告筛选工具栏">
    <div class="rrt-filter-group">
      <label for="report-status-filter" class="rrt-label">状态筛选</label>
      <select
        id="report-status-filter"
        class="rrt-select"
        :value="statusFilter"
        @change="onChange"
      >
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
  margin-bottom: 16px;
}

.rrt-filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.rrt-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-text-secondary, #4a5568);
  white-space: nowrap;
}

.rrt-select {
  padding: 6px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  font-size: 13px;
  color: var(--color-text-primary, #1a365d);
  cursor: pointer;
  min-width: 120px;
  transition: border-color 0.15s;
}

.rrt-select:focus-visible {
  outline: 2px solid var(--color-accent, #2b6cb0);
  outline-offset: 1px;
}

.rrt-select:hover {
  border-color: var(--color-accent, #2b6cb0);
}
</style>
