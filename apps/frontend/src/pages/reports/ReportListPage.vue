<template>
  <div class="reports-page">
    <!-- Page Header -->
    <ResearchPageHeader
      title="研究报告"
      description="查看所有研究课题生成的报告，支持筛选、查看和导出。"
      :breadcrumbs="[{ label: 'Reports' }]"
    />

    <div class="rp-body">
      <!-- Toolbar -->
      <ResearchReportsToolbar
        :status-filter="statusFilter"
        @update:status-filter="setStatusFilter"
      />

      <!-- Content Area -->
      <div class="rp-content">
        <!-- Loading -->
        <LoadingState
          v-if="loading"
          message="正在加载报告..."
        />

        <!-- Error -->
        <ErrorState
          v-else-if="error"
          :message="error"
          title="报告加载失败"
          @retry="retry"
        />

        <!-- Empty: no reports at all -->
        <EmptyState
          v-else-if="!loading && items.length === 0 && statusFilter === ''"
          title="暂无报告"
          description="在任意研究课题中运行研究工作流后，生成的报告将显示在这里。"
          icon="📄"
        />

        <!-- Empty: filter returned no results -->
        <EmptyState
          v-else-if="!loading && items.length === 0 && statusFilter !== ''"
          :title="`暂无「${statusFilterLabel}」的报告`"
          description="尝试选择其他状态筛选条件，或清除筛选查看全部报告。"
          icon="🔍"
        >
          <template #action>
            <button
              class="rp-clear-filter-btn"
              @click="setStatusFilter('')"
            >
              清除筛选
            </button>
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
        <button
          :disabled="page <= 1"
          @click="setPage(page - 1)"
        >
          上一页
        </button>
        <span class="rp-page-info">{{ page }} / {{ totalPages }}</span>
        <button
          :disabled="page >= totalPages"
          @click="setPage(page + 1)"
        >
          下一页
        </button>
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
 * ref: docs/20-product/2010-project-list-migration.md
 */
import { onMounted } from 'vue';
import { useResearchReports } from '@/composables/useResearchReports';
import type { ReportItem } from '@/composables/useResearchReports';

import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import ResearchReportsToolbar from '@/components/reports/ResearchReportsToolbar.vue';
import ResearchReportList from '@/components/reports/ResearchReportList.vue';

const {
  items,
  page,
  totalPages,
  loading,
  error,
  statusFilter,
  statusFilterLabel,
  exporting,
  exportError,
  fetchReports,
  setPage,
  setStatusFilter,
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
  padding: 24px 32px;
}

.rp-content {
  min-height: 200px;
}

/* ---- Clear filter button ---- */
.rp-clear-filter-btn {
  padding: 8px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  font-size: 13px;
  cursor: pointer;
  color: var(--color-accent, #2b6cb0);
  transition: all 0.15s;
}

.rp-clear-filter-btn:hover {
  background: var(--color-hover, #edf2f7);
  border-color: var(--color-accent, #2b6cb0);
}

/* ---- Pagination ---- */
.rp-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 28px;
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
}

.rp-pagination button {
  padding: 6px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  transition: all 0.15s;
}

.rp-pagination button:hover:not(:disabled) {
  background: var(--color-hover, #edf2f7);
  border-color: var(--color-accent, #2b6cb0);
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
    padding: 16px 20px;
  }
}
</style>
