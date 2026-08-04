<template>
  <div class="lib-search-bar">
    <div class="lib-search-input-wrap">
      <label for="lib-search-input" class="sr-only">{{ t('common.search') }}</label>
      <input
        id="lib-search-input"
        v-model="query"
        type="text"
        :placeholder="'搜索文献标题…'"
        @keyup.enter="emitSearch"
      />
      <button class="lib-search-btn" @click="emitSearch" aria-label="搜索文献">
        {{ t('common.search') }}
      </button>
    </div>
    <div class="lib-filter-chips">
      <label for="lib-copyright-filter" class="sr-only">版权筛选</label>
      <select
        id="lib-copyright-filter"
        v-model="copyrightStatus"
        class="lib-filter-select"
        @change="emitSearch"
      >
        <option value="">— 版权 —</option>
        <option v-for="cs in COPYRIGHT_STATUSES" :key="cs" :value="cs">
          {{ COPYRIGHT_LABELS[cs] || cs }}
        </option>
      </select>
      <label for="lib-review-filter" class="sr-only">审核状态筛选</label>
      <select
        id="lib-review-filter"
        v-model="reviewStatus"
        class="lib-filter-select"
        @change="emitSearch"
      >
        <option value="">— 审核 —</option>
        <option v-for="rs in REVIEW_STATUSES" :key="rs" :value="rs">
          {{ REVIEW_LABELS[rs] || rs }}
        </option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import {
  COPYRIGHT_STATUSES,
  COPYRIGHT_LABELS,
  REVIEW_STATUSES,
  REVIEW_LABELS,
} from '@/types/library';
import type { LibraryFilters } from '@/types/library';

const { t } = useI18n();

const props = defineProps<{
  filters?: LibraryFilters;
}>();

const emit = defineEmits<{
  (e: 'search', filters: { query: string; copyrightStatus: string; reviewStatus: string }): void;
}>();

const query = ref(props.filters?.query ?? '');
const copyrightStatus = ref(props.filters?.copyrightStatus ?? '');
const reviewStatus = ref(props.filters?.reviewStatus ?? '');

// Sync child local refs when parent clears filters
watch(
  () => props.filters,
  (f) => {
    if (!f) return;
    query.value = f.query ?? '';
    copyrightStatus.value = f.copyrightStatus ?? '';
    reviewStatus.value = f.reviewStatus ?? '';
  },
  { deep: true },
);

function emitSearch() {
  emit('search', {
    query: query.value.trim(),
    copyrightStatus: copyrightStatus.value,
    reviewStatus: reviewStatus.value,
  });
}
</script>

<style scoped>
.lib-search-bar {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-3);
  align-items: center;
}

.lib-search-input-wrap {
  display: flex;
  gap: var(--space-2);
  flex: 1;
  min-width: 0;
  max-width: 560px;
}

.lib-search-input-wrap input {
  padding: var(--space-2) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 14px;
  min-width: 0;
  flex: 1;
  max-width: 400px;
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  transition: border-color var(--transition-base);
}

.lib-search-input-wrap input:focus-visible {
  border-color: var(--color-accent);
  outline: 2px solid var(--color-accent);
  outline-offset: -1px;
}

.lib-search-btn {
  padding: var(--space-2) 16px;
  background: var(--color-accent);
  color: var(--color-on-accent);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: 13px;
  font-weight: var(--font-medium);
  transition: background var(--transition-base);
  white-space: nowrap;
}

.lib-search-btn:hover {
  background: var(--color-accent-hover);
}

.lib-search-btn:focus-visible {
  background: var(--color-accent-hover);
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
}

.lib-filter-chips {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.lib-filter-select {
  padding: var(--space-2) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 13px;
  background: var(--color-navbar-bg, var(--color-surface));
  color: var(--color-text-primary);
  min-width: 120px;
  transition: border-color var(--transition-base);
  cursor: pointer;
}

.lib-filter-select:focus-visible {
  border-color: var(--color-accent);
  outline: 2px solid var(--color-accent);
  outline-offset: -1px;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .lib-search-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .lib-search-input-wrap {
    max-width: none;
  }

  .lib-search-input-wrap input {
    max-width: none;
  }

  .lib-filter-chips {
    justify-content: flex-start;
  }

  .lib-filter-select {
    flex: 1;
    max-width: none;
  }
}
</style>
