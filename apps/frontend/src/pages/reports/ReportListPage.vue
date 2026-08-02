<template>
  <div class="reports-page">
    <!-- Page Header -->
    <ResearchPageHeader
      title="研究报告"
      description="查看所有研究课题生成的报告，支持筛选、查看和导出。"
      :breadcrumbs="[{ label: 'Reports' }]"
    />

    <div class="rp-body">
      <!-- Toolbar — C1-1 unified HfbToolbar -->
      <form
        class="rp-toolbar-form"
        @submit.prevent="toolbarRef?.handleEnter()"
      >
        <HfbToolbar
          ref="toolbarRef"
          :searchable="false"
          :filters="reportToolbarFilters"
          :filter-values="filterValues"
          :loading="loading"
          loading-label="加载报告..."
          show-clear-button
          @search="onSearch"
          @update:filter-values="filterValues = $event"
        />
      </form>

      <!-- Content Area -->
      <div class="rp-content">
        <!-- Loading -->
        <LoadingState v-if="loading" message="正在加载报告..." />

        <!-- Error -->
        <ErrorState v-else-if="error" :message="error" title="报告加载失败" @retry="retry" />

        <!-- Empty: no reports at all -->
        <EmptyState
          v-else-if="!loading && items.length === 0 && !hasActiveFilters"
          title="暂无报告"
          description="在任意研究课题中运行研究工作流后，生成的报告将显示在这里。"
          icon="📄"
        />

        <!-- Empty: filter returned no results -->
        <EmptyState
          v-else-if="!loading && items.length === 0 && hasActiveFilters"
          :title="`暂无「${statusFilterLabel}」的报告`"
          description="尝试选择其他状态筛选条件，或清除筛选查看全部报告。"
          icon="🔍"
        >
          <template #action>
            <button class="rp-clear-filter-btn" @click="filterValues = { status: '' }">清除筛选</button>
          </template>
        </EmptyState>

        <!-- Report list -->
        <ResearchReportList
          v-else
          :items="items"
          :exporting="exporting"
          :export-error="exportError"
          @export="handleExport"
        />
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="rp-pagination">
        <button :disabled="page <= 1" @click="setPage(page - 1)">上一页</button>
        <span class="rp-page-info" :aria-label="`第 ${page} 页，共 ${totalPages} 页`"
          >{{ page }} / {{ totalPages }}</span
        >
        <button :disabled="page >= totalPages" @click="setPage(page + 1)">下一页</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ReportListPage — 研究报告列表页面
 *
 * Data source:
 *   GET /api/v4/research/reports?page=N&limit=N&status=ready|missing|failed|pending
 *
 * Routes to individual report results:
 *   /research/:sessionId/result/:runId
 *
 * Export:
 *   GET /api/v4/research/session/{sessionId}/runs/{runId}/export?format=markdown
 *
 * C1-1: Replaced ResearchReportsToolbar with unified HfbToolbar.
 *   Toolbar filter values are shared via filterValues ref bound with v-model:filterValues.
 *
 * ref: docs/20-product/2010-project-list-migration.md
 */
import { ref, computed, onMounted } from 'vue';
import { useResearchReports, REPORT_TOOLBAR_FILTERS } from '@/composables/useResearchReports';
import type { ReportItem } from '@/composables/useResearchReports';

import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import HfbToolbar from '@/components/common/HfbToolbar.vue';
import ResearchReportList from '@/components/reports/ResearchReportList.vue';

const toolbarRef = ref<InstanceType<typeof HfbToolbar> | null>(null);

const reportToolbarFilters = REPORT_TOOLBAR_FILTERS;

/** Whether any filter is currently active (non-empty status filter). */
const hasActiveFilters = computed(() => {
  const vals = filterValues.value;
  return Object.values(vals).some((v) => v !== null && v !== '');
});

const {
  items,
  page,
  totalPages,
  loading,
  error,
  filterValues,
  statusFilterLabel,
  exporting,
  exportError,
  fetchReports,
  onSearch,
  setPage,
  exportReport,
  retry,
} = useResearchReports();

// ---- Export handler ----
async function handleExport(item: ReportItem) {
  await exportReport(item.session_id, item.run_id);
}

// ---- Lifecycle ----
onMounted(() => {
  fetchReports();
});
</script>

<style scoped>
.reports-page {
  min-height: 100%;
}

.rp-body {
  padding: var(--space-6) var(--space-8);
}

.rp-content {
  min-height: 200px;
}

/* ---- Clear filter button ---- */
.rp-clear-filter-btn {
  padding: var(--btn-padding-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: var(--text-sm);
  cursor: pointer;
  color: var(--color-accent);
  transition: all var(--transition-base);
}

.rp-clear-filter-btn:hover {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.rp-clear-filter-btn:focus-visible {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

/* ---- Pagination ---- */
.rp-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-7);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.rp-pagination button {
  padding: var(--btn-padding-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
}

.rp-pagination button:hover:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.rp-pagination button:focus-visible:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.rp-pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.rp-page-info {
  min-width: 60px;
  text-align: center;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rp-body {
    padding: var(--space-4) var(--space-5);
  }
}
</style>
