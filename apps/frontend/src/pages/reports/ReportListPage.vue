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
          :searchable="true"
          search-placeholder="搜索报告标题..."
          :filters="reportToolbarFilters"
          :filter-values="filterValues"
          :loading="loading"
          loading-label="加载报告..."
          show-clear-button
          @search="onSearch"
          @update:filter-values="onFilterValuesChange"
        />
      </form>

      <!-- Main content region -->
      <div
        class="rp-content"
        aria-live="polite"
        :aria-busy="loading"
      >
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

        <!-- Empty: client-side search or server filter returned no results -->
        <EmptyState
          v-else-if="!loading && displayedItems.length === 0 && hasActiveFilters"
          :title="'暂无匹配的报告'"
          description="尝试调整搜索关键词或筛选条件，或清除筛选查看全部报告。"
          icon="🔍"
        >
          <template #action>
            <button class="rp-clear-filter-btn" @click="clearFilters">清除筛选</button>
          </template>
        </EmptyState>

        <!-- Report list -->
        <ResearchReportList
          v-else
          :items="displayedItems"
          :exporting="exporting"
          :export-error="exportError"
          :last-export-run-id="lastExportRunId"
          @export="handleExport"
        />
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="rp-pagination">
        <HfbPagination
          :page="page"
          :total-pages="totalPages"
          :disabled="loading"
          @update:page="setPage"
        />
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
 *   searchable=true — client-side search filters displayed items by topic/session_title.
 *   Status filter sent server-side via GET /api/v4/research/reports?status=.
 *   API contract unchanged: server-side pagination (page/limit) preserved.
 *   Toolbar filter values synced via onFilterValuesChange which resets page to 1
 *   and calls setStatusFilter which re-fetches. clearFilters resets both search
 *   text and status filter, resets page to 1, and re-fetches.
 *
 * ref: docs/20-product/2010-project-list-migration.md
 */
import { ref, computed, onMounted } from 'vue';
import {
  useResearchReports,
  REPORT_TOOLBAR_FILTERS,
} from '@/composables/useResearchReports';
import type { ReportItem } from '@/composables/useResearchReports';
import type { ToolbarFilterValues } from '@/types/toolbar';

import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import HfbToolbar from '@/components/common/HfbToolbar.vue';
import HfbPagination from '@/components/common/HfbPagination.vue';
import ResearchReportList from '@/components/reports/ResearchReportList.vue';

const toolbarRef = ref<InstanceType<typeof HfbToolbar> | null>(null);

const reportToolbarFilters = REPORT_TOOLBAR_FILTERS;

const {
  items,
  page,
  totalPages,
  loading,
  error,
  filterValues,
  exporting,
  exportError,
  lastExportRunId,
  fetchReports,
  setPage,
  setStatusFilter,
  exportReport,
  retry,
} = useResearchReports();

// ---- Client-side search state ----
const searchQuery = ref('');

/** Is any filter (search query or status filter) active? */
const hasActiveFilters = computed(() => {
  if (searchQuery.value.trim().length > 0) return true;
  const vals = filterValues.value;
  return Object.values(vals).some((v) => v !== null && v !== '');
});

/** Server items filtered client-side by search query only (status is server-filtered). */
const displayedItems = computed<ReportItem[]>(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return items.value;
  return items.value.filter(
    (r) =>
      (r.topic || '').toLowerCase().includes(q) ||
      (r.session_title || '').toLowerCase().includes(q),
  );
});

// ---- Toolbar event handlers ----

/** Called on every debounced search input or Enter. Client-side only filter update. */
function onSearch(payload: { query: string }) {
  searchQuery.value = payload.query;
}

/** Called when a filter value changes in HfbToolbar. Triggers server re-fetch at page 1. */
function onFilterValuesChange(values: ToolbarFilterValues) {
  const newStatus = (values.status ?? '') as '' | 'ready' | 'missing' | 'failed' | 'pending';
  setStatusFilter(newStatus);
}

/** Reset all filters and search, then re-fetch at page 1. */
function clearFilters() {
  searchQuery.value = '';
  setStatusFilter('');
}

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
  margin-top: var(--space-7);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rp-body {
    padding: var(--space-4) var(--space-5);
  }
}
</style>
