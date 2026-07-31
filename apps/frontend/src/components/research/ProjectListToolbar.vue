<template>
  <div class="plt-toolbar">
    <div class="plt-search">
      <label for="plt-search-input" class="sr-only">{{ t('common.search') }}</label>
      <input
        id="plt-search-input"
        v-model="query"
        type="search"
        :placeholder="t('researchWorkspace.searchMaterials')"
        class="plt-search-input"
        @input="onSearch"
      />
    </div>
    <div class="plt-clear">
      <button v-if="hasFilters" class="plt-clear-btn" @click="onClear">
        {{ t('researchWorkspace.clearFilters') || '清除筛选' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ProjectListToolbar — search and filter bar for the project list.
 *
 * NOTE: The backend GET /api/v1/workspace/sessions does NOT support
 * server-side search or status filtering. Search is applied client-side
 * by filtering the current page of results. The status filter is also
 * applied client-side. This is documented in the migration doc.
 */
import { ref, computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const props = withDefaults(
  defineProps<{
    modelValue?: string;
  }>(),
  {
    modelValue: '',
  },
);

const emit = defineEmits<{
  'update:modelValue': [value: string];
  search: [query: string];
  clear: [];
}>();

const query = ref(props.modelValue);

const hasFilters = computed(() => query.value.trim().length > 0);

// Debounce search to avoid excessive filtering
let timer: ReturnType<typeof setTimeout> | null = null;

function onSearch() {
  emit('update:modelValue', query.value);
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => {
    emit('search', query.value.trim());
  }, 300);
}

function onClear() {
  query.value = '';
  emit('update:modelValue', '');
  emit('search', '');
  emit('clear');
}

// Cleanup debounce timer on unmount
onBeforeUnmount(() => {
  if (timer) {
    clearTimeout(timer);
    timer = null;
  }
});
</script>

<style scoped>
.plt-toolbar {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-5);
  flex-wrap: wrap;
}

.plt-search {
  flex: 1;
  min-width: 0;
  max-width: 480px;
}

.plt-search-input {
  width: 100%;
  padding: var(--space-2-5) 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  transition: border-color var(--transition-base);
  box-sizing: border-box;
}

.plt-search-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.plt-clear-btn {
  padding: var(--space-2-5) 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  font-size: var(--text-sm);
  cursor: pointer;
  color: var(--color-text-secondary);
  white-space: nowrap;
  transition: all var(--transition-base);
}

.plt-clear-btn:hover {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.plt-clear-btn:focus-visible {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

/* Screen-reader only */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
