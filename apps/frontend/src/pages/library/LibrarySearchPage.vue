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

      <!-- Loading -->
      <LoadingState
        v-if="loading"
        :message="t('common.loading')"
      />

      <!-- Error -->
      <ErrorState
        v-else-if="error"
        :message="error"
        @retry="fetchPage(1)"
      />

      <!-- Empty: no documents at all -->
      <EmptyState
        v-else-if="total === 0 && !isSearchActive"
        title="暂无文献"
        description="文献库中还没有文献记录，请稍后再来。"
        icon="📚"
      />

      <!-- Empty: search returned no results -->
      <EmptyState
        v-else-if="items.length === 0 && isSearchActive"
        title="未找到匹配的文献"
        :description="searchEmptyDescription"
        icon="🔍"
      >
        <template #action>
          <button class="lib-clear-btn" @click="clearSearch">清除搜索</button>
        </template>
      </EmptyState>

      <!-- Document List -->
      <div v-else class="lib-list">
        <LibraryDocumentCard
          v-for="doc in items"
          :key="doc.id"
          :doc="doc"
        />
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="lib-pagination">
        <button :disabled="page <= 1" @click="fetchPage(page - 1)">{{ t('common.back') }}</button>
        <span class="lib-page-info">{{ page }} / {{ totalPages }}</span>
        <button :disabled="page >= totalPages" @click="fetchPage(page + 1)">{{ t('common.next') }}</button>
      </div>
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
import LoadingState from '@/components/common/LoadingState.vue';
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

const {
  items,
  total,
  loading,
  error,
  page,
  totalPages,
  fetchPage,
} = useLibraryList(filters);

const isSearchActive = computed(() => filters.value.query.trim().length > 0);

const searchEmptyDescription = computed(() =>
  `没有文献与 "${filters.value.query}" 匹配，请尝试其他关键词。`,
);

function onSearch(f: { query: string; copyrightStatus: string; reviewStatus: string }) {
  filters.value.query = f.query;
  filters.value.copyrightStatus = f.copyrightStatus;
  filters.value.reviewStatus = f.reviewStatus;
  fetchPage(1);
}

function clearSearch() {
  filters.value.query = '';
  filters.value.copyrightStatus = '';
  filters.value.reviewStatus = '';
  fetchPage(1);
}

onMounted(() => fetchPage(1));
</script>

<style scoped>
.library-page {
  min-height: 100%;
}

.lib-body {
  padding: 24px 32px;
}

.lib-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.lib-clear-btn {
  padding: 8px 20px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  color: var(--color-accent, #2b6cb0);
  font-size: 14px;
  cursor: pointer;
}

/* ---- Pagination ---- */
.lib-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 28px;
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
}

.lib-pagination button {
  padding: 6px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  cursor: pointer;
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  transition: all 0.15s;
}

.lib-pagination button:hover:not(:disabled) {
  background: var(--color-hover, #edf2f7);
  border-color: var(--color-accent, #2b6cb0);
}

.lib-pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.lib-page-info {
  min-width: 60px;
  text-align: center;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .lib-body {
    padding: 16px 20px;
  }
}
</style>
