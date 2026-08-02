<template>
  <div class="hfb-toolbar" role="search" aria-label="搜索筛选工具栏">
    <!-- Search input -->
    <div v-if="searchable" class="hfb-toolbar__search">
      <HfbInput
        :model-value="queryModel"
        type="search"
        :placeholder="searchPlaceholder"
        :disabled="loading"
        :clearable="true"
        size="md"
        @update:model-value="onSearchInput"
        @clear="onClear"
      >
        <template #prefix>
          <HfbIcon icon="search" :size="16" />
        </template>
      </HfbInput>
    </div>

    <!-- Filter chips -->
    <div v-if="filters.length > 0" class="hfb-toolbar__filters">
      <HfbSelect
        v-for="f in filters"
        :key="f.key"
        :model-value="filterValues[f.key] ?? null"
        :options="f.options"
        :label="f.label"
        :placeholder="f.placeholder ?? `— ${f.label} —`"
        :disabled="loading"
        :clearable="true"
        @update:model-value="(val) => onFilterChange(f.key, val)"
      />
    </div>

    <!-- Active filter indicator -->
    <div v-if="hasActiveFilters && showClearButton" class="hfb-toolbar__actions">
      <HfbButton variant="ghost" size="sm" @click="onClearAll">
        <template #icon>
          <HfbIcon icon="x" :size="14" />
        </template>
        清除筛选
      </HfbButton>
    </div>

    <!-- Loading indicator -->
    <div v-if="loading" class="hfb-toolbar__status" aria-live="polite">
      <span class="hfb-toolbar__loading-dot" aria-hidden="true" />
      <span>{{ loadingLabel }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * HfbToolbar — unified Search / Filter toolbar for entity list pages.
 *
 * C1-1 Search / Filter / Toolbar pattern convergence.
 *
 * Uses B3-approved primitives: HfbInput, HfbSelect, HfbButton, HfbIcon.
 * No direct hex, no any types, no unicode icons.
 *
 * Contract:
 *   - Debounced search input (300ms) with HfbIcon search prefix
 *   - Type-safe HfbSelect filter dropdowns via ToolbarFilter[]
 *   - Enter = immediate search (via handleEnter() exposed for parent form submit)
 *   - OnClear on HfbInput = clear search + emit empty search
 *   - Per-filter clear via HfbSelect clearable
 *   - Global clear-all via HfbButton ghost when filters active
 *   - Loading state with pulsing dot + label
 *   - Emits { query: string, filters: Record } on every search event
 *   - Responsive: stacks vertically on viewport width ≤ 768px
 */
import { ref, computed, onBeforeUnmount, nextTick } from 'vue';
import HfbInput from './HfbInput.vue';
import HfbSelect from './HfbSelect.vue';
import HfbButton from './HfbButton.vue';
import HfbIcon from './HfbIcon.vue';
import type { ToolbarFilter, ToolbarSearchPayload, ToolbarFilterValues } from '@/types/toolbar';

// ---- Props ----

const props = withDefaults(
  defineProps<{
    /** Whether to show the search input. */
    searchable?: boolean;
    /** Search input placeholder text. */
    searchPlaceholder?: string;
    /** Array of filter definitions (label + options). Empty = no filter dropdowns. */
    filters?: ToolbarFilter[];
    /** Current filter values, keyed by filter.key. */
    filterValues?: ToolbarFilterValues;
    /** Whether the toolbar is in loading state. */
    loading?: boolean;
    /** Label to show when loading. */
    loadingLabel?: string;
    /** Whether to show the "clear all filters" button when filters are active. */
    showClearButton?: boolean;
  }>(),
  {
    searchable: true,
    searchPlaceholder: '搜索...',
    filters: () => [],
    filterValues: () => ({}),
    loading: false,
    loadingLabel: '搜索中...',
    showClearButton: true,
  },
);

// ---- Emits ----

const emit = defineEmits<{
  /** Emitted on debounced search input, Enter key, filter change, clear, or clear-all. */
  search: [payload: ToolbarSearchPayload];
  /** Emitted when a filter value changes (before the search event). */
  'update:filterValues': [values: ToolbarFilterValues];
}>();

// ---- State ----

const queryModel = ref('');

// ---- Debounce timer ----

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

// ---- Derived ----

const hasActiveFilters = computed(() => {
  if (queryModel.value.trim().length > 0) return true;
  return Object.values(props.filterValues).some((v) => v !== null && v !== '');
});

// ---- Core: emit current state ----

function emitSearch() {
  const payload: ToolbarSearchPayload = {
    query: queryModel.value.trim(),
    filters: { ...props.filterValues },
  };
  emit('search', payload);
}

// ---- Debounced search ----

function debouncedEmit() {
  if (debounceTimer) clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => {
    emitSearch();
  }, 300);
}

function cancelDebounce() {
  if (debounceTimer) {
    clearTimeout(debounceTimer);
    debounceTimer = null;
  }
}

// ---- Search input ----

function onSearchInput(value: string) {
  queryModel.value = value;
  debouncedEmit();
}

// ---- Clear search ----

function onClear() {
  queryModel.value = '';
  cancelDebounce();
  emitSearch();
}

// ---- Filter change ----

function onFilterChange(key: string, value: string | number | null) {
  const newValues = { ...props.filterValues, [key]: value };
  emit('update:filterValues', newValues);
  // Wait for parent to apply new filterValues prop before emitting search
  void nextTick(() => emitSearch());
}

// ---- Clear all ----

function onClearAll() {
  queryModel.value = '';
  cancelDebounce();
  const resetValues: ToolbarFilterValues = {};
  for (const f of props.filters) {
    resetValues[f.key] = null;
  }
  emit('update:filterValues', resetValues);
  void nextTick(() => emitSearch());
}

// ---- Exposed API (for parent form Enter handling) ----

/** Call from parent @submit.prevent to trigger immediate search. */
function handleEnter(): void {
  cancelDebounce();
  emitSearch();
}

defineExpose({ handleEnter });

// ---- Cleanup ----

onBeforeUnmount(() => {
  cancelDebounce();
});
</script>

<style scoped>
.hfb-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
}

/* ---- Search ---- */
.hfb-toolbar__search {
  flex: 1;
  min-width: 0;
  max-width: 480px;
}

/* ---- Filters ---- */
.hfb-toolbar__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-2);
}

/* ---- Actions ---- */
.hfb-toolbar__actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

/* ---- Status / Loading ---- */
.hfb-toolbar__status {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.hfb-toolbar__loading-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: var(--radius-round);
  background: var(--color-accent);
  animation: hfb-toolbar-pulse var(--transition-spinner) var(--ease-in-out) infinite;
}

@keyframes hfb-toolbar-pulse {
  0%, 100% { opacity: 0.3; }
  50% { opacity: 1; }
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .hfb-toolbar {
    flex-direction: column;
    align-items: stretch;
  }

  .hfb-toolbar__search {
    max-width: none;
  }

  .hfb-toolbar__filters {
    flex-direction: column;
  }

  .hfb-toolbar__filters :deep(.hfb-select-wrapper) {
    max-width: none;
    width: 100%;
  }
}
</style>
