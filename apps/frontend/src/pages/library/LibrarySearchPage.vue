<template>
  <div class="library-page">
    <ResearchPageHeader
      title="Library"
      description="古籍文献搜索与全文阅读"
      :breadcrumbs="[{ label: 'Library' }]"
    />

    <div class="lib-body">
      <!-- Search & Filter -->
      <LibrarySearchBar @search="onSearch" />

      <!-- Loading: Skeleton cards -->
      <div v-if="loading" class="lib-skeleton-list" aria-busy="true" aria-label="正在加载文献列表">
        <div v-for="i in 5" :key="i" class="lib-skeleton-card hfb-skeleton hfb-skeleton--rect hfb-skeleton--pulse">
          <div class="lib-skeleton-title hfb-skeleton__line hfb-skeleton__line--pulse" />
          <div class="lib-skeleton-meta hfb-skeleton__line hfb-skeleton__line--pulse" />
          <div class="lib-skeleton-badges">
            <span class="hfb-skeleton hfb-skeleton--pulse" style="width:56px;height:20px;display:inline-block;border-radius:var(--radius-sm)" />
            <span class="hfb-skeleton hfb-skeleton--pulse" style="width:48px;height:20px;display:inline-block;border-radius:var(--radius-sm)" />
          </div>
        </div>
      </div>

      <!-- Error -->
      <ErrorState v-else-if="error" :message="error" @retry="fetchPage(page)" />

      <!-- Empty: no documents at all -->
      <EmptyState
        v-else-if="total === 0 && !isSearchActive"
        title="暂无文献"
        description="文献库中还没有文献记录，请稍后再来。"
        icon="📚"
      />

      <!-- Empty: search/filter returned no results -->
      <EmptyState
        v-else-if="items.length === 0 && isSearchActive"
        title="未找到匹配的文献"
        :description="searchEmptyDescription"
        icon="🔍"
      >
        <template #action>
          <button class="lib-clear-btn" @click="clearAllFilters">清空筛选条件</button>
        </template>
      </EmptyState>

      <!-- Document List -->
      <template v-else>
        <div class="lib-results-header">
          <span role="status" aria-live="polite" class="lib-results-count">
            共 <strong>{{ total }}</strong> 条结果
            <template v-if="isSearchActive"> — 关键词「{{ filters.query }}」</template>
          </span>
        </div>

        <div class="lib-list" role="list" aria-label="文献列表">
          <LibraryDocumentCard v-for="doc in items" :key="doc.id" :doc="doc" role="listitem" />
        </div>

        <!-- Pagination -->
        <nav v-if="totalPages > 1" class="lib-pagination" aria-label="分页导航">
          <button :disabled="page <= 1" @click="fetchPage(page - 1)" aria-label="上一页">
            {{ t('common.back') }}
          </button>
          <ol class="lib-page-numbers">
            <li v-for="p in visiblePages" :key="p">
              <button
                :class="{ 'lib-page-current': p === page }"
                :aria-current="p === page ? 'page' : undefined"
                :aria-label="`第 ${p} 页`"
                @click="fetchPage(p)"
              >
                {{ p }}
              </button>
            </li>
          </ol>
          <button :disabled="page >= totalPages" @click="fetchPage(page + 1)" aria-label="下一页">
            {{ t('common.next') }}
          </button>
        </nav>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * LibrarySearchPage — 文献中心列表页
 *
 * Data source: GET /api/v1/documents (real backend)
 *
 * Route: /library
 *
 * ref: docs/20-product/2010-task008-library-migration.md
 */
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import LibrarySearchBar from '@/components/library/LibrarySearchBar.vue';
import LibraryDocumentCard from '@/components/library/LibraryDocumentCard.vue';
import { useLibraryList } from '@/composables/useLibrary';
import type { LibraryFilters } from '@/types/library';

const { t } = useI18n();

const filters = ref<LibraryFilters>({
  query: '',
  copyrightStatus: '',
  reviewStatus: '',
  dynasty: '',
  category: '',
  sourceName: '',
});

const { items, total, loading, error, page, totalPages, fetchPage } = useLibraryList(filters);

const isSearchActive = computed(() => {
  const f = filters.value;
  return (
    f.query.trim().length > 0 ||
    f.copyrightStatus !== '' ||
    f.reviewStatus !== '' ||
    f.dynasty !== '' ||
    f.category !== '' ||
    f.sourceName !== ''
  );
});

const searchEmptyDescription = computed(
  () => `没有文献与 "${filters.value.query}" 匹配，请尝试其他关键词。`,
);

/** Visible page numbers — show up to 7 pages centered around current */
const visiblePages = computed(() => {
  const totalP = totalPages.value;
  const cur = page.value;
  if (totalP <= 7) {
    return Array.from({ length: totalP }, (_, i) => i + 1);
  }
  let start = Math.max(1, cur - 3);
  const end = Math.min(totalP, start + 6);
  start = Math.max(1, end - 6);
  return Array.from({ length: end - start + 1 }, (_, i) => start + i);
});

function onSearch(f: { query: string; copyrightStatus: string; reviewStatus: string }) {
  filters.value.query = f.query;
  filters.value.copyrightStatus = f.copyrightStatus;
  filters.value.reviewStatus = f.reviewStatus;
  fetchPage(1);
}

function clearAllFilters() {
  filters.value.query = '';
  filters.value.copyrightStatus = '';
  filters.value.reviewStatus = '';
  filters.value.dynasty = '';
  filters.value.category = '';
  filters.value.sourceName = '';
  fetchPage(1);
}

onMounted(() => fetchPage(1));
</script>

<style scoped>
.library-page {
  min-height: 100%;
}

.lib-body {
  padding: var(--space-6) var(--space-8);
}

/* ---- Skeleton ---- */
.lib-skeleton-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-4);
}

.lib-skeleton-card {
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
}

.lib-skeleton-title {
  width: 50%;
  margin-bottom: var(--space-2);
}

.lib-skeleton-meta {
  width: 30%;
  margin-bottom: var(--space-2);
}

.lib-skeleton-badges {
  display: flex;
  gap: var(--space-2);
  padding-top: var(--space-1);
}

/* ---- Results header ---- */
.lib-results-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.lib-results-count {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.lib-results-count strong {
  color: var(--color-text-primary);
  font-weight: var(--font-semibold);
}

/* ---- List ---- */
.lib-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-top: var(--space-1);
}

/* ---- Clear button ---- */
.lib-clear-btn {
  padding: var(--btn-padding-md);
  border: 1px solid var(--color-accent);
  border-radius: var(--btn-radius);
  background: var(--color-surface);
  color: var(--color-accent);
  font-size: var(--text-base);
  cursor: pointer;
  transition: background var(--transition-base);
}

.lib-clear-btn:hover {
  background: var(--color-hover);
}

.lib-clear-btn:focus-visible {
  background: var(--color-hover);
}

/* ---- Pagination ---- */
.lib-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  margin-top: var(--space-7);
  font-size: var(--text-sm);
}

.lib-pagination button {
  padding: var(--btn-padding-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
  min-width: 36px;
  text-align: center;
}

.lib-pagination button:hover:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.lib-pagination button:focus-visible:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.lib-pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.lib-page-current {
  background: var(--color-accent) !important;
  border-color: var(--color-accent) !important;
  color: var(--color-on-accent) !important;
  font-weight: var(--font-semibold);
}

.lib-page-numbers {
  display: flex;
  gap: var(--space-1);
  list-style: none;
  margin: 0;
  padding: 0;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .lib-body {
    padding: var(--space-4) var(--space-5);
  }

  .lib-skeleton-title {
    width: 70%;
  }

  .lib-skeleton-meta {
    width: 50%;
  }

  .lib-pagination {
    flex-wrap: wrap;
  }
}
</style>
