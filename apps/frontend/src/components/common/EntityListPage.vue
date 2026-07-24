<template>
  <div class="entity-list-page">
    <div class="page-header">
      <h1>{{ title }}</h1>
      <div class="header-actions">
        <div class="search-box">
          <input
            v-model="query"
            type="text"
            :placeholder="t('common.search') + '...'"
            @keyup.enter="search"
          />
          <button class="search-btn" @click="search">{{ t('common.search') }}</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading-state">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else-if="items.length === 0" class="empty-state">{{ t('common.noData') }}</div>

    <div v-else class="entity-grid">
      <div v-for="item in items" :key="item.id" class="entity-card" @click="$router.push(`${routePrefix}/${item.id}`)">
        <h3 class="card-title">{{ getTitle(item) }}</h3>
        <div class="card-meta">
          <span v-for="meta in getMeta(item)" :key="meta" class="meta-tag">{{ meta }}</span>
        </div>
        <div v-if="props.getSubtitle?.(item)" class="card-subtitle">{{ props.getSubtitle?.(item) }}</div>
      </div>
    </div>

    <div v-if="total > limit" class="pagination">
      <button :disabled="page <= 1" @click="goPage(page - 1)">{{ t('common.back') }}</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="goPage(page + 1)">{{ t('common.next') }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useEntityList, type EntityBrief } from '@/composables/useApi';

const { t } = useI18n();

const props = withDefaults(defineProps<{
  endpoint: string;
  title: string;
  routePrefix: string;
  getTitle: (item: EntityBrief) => string;
  getMeta: (item: EntityBrief) => Array<string>;
  getSubtitle?: (item: EntityBrief) => string | null;
}>(), {
  getSubtitle: undefined,
});

const { items, total, loading, error, fetch } = useEntityList<EntityBrief>(props.endpoint);

const query = ref('');
const page = ref(1);
const limit = ref(20);

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)));

function search() {
  page.value = 1;
  fetch(page.value, limit.value, query.value);
}

function goPage(p: number) {
  page.value = p;
  fetch(page.value, limit.value, query.value);
}

onMounted(() => fetch());
</script>

<style scoped>
.entity-list-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-6);
  flex-wrap: wrap;
  gap: var(--space-4);
}

.page-header h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
}

.search-box {
  display: flex;
  gap: var(--space-2);
}

.search-box input {
  padding: var(--space-2) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  min-width: 200px;
  background: var(--color-page-bg);
  color: var(--color-text-primary);
}

.search-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--color-accent);
  color: white;
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: var(--text-sm);
}

.entity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.entity-card {
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  cursor: pointer;
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
  background: var(--color-surface);
}

.entity-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-sm);
}

.card-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1-5);
  margin-bottom: var(--space-2);
}

.meta-tag {
  font-size: var(--text-xs);
  padding: var(--space-0-5) 8px;
  background: var(--color-tag-bg);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
}

.card-subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  line-height: var(--leading-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: var(--space-15) var(--space-5);
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-8);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.pagination button {
  padding: var(--btn-padding-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  font-size: var(--text-sm);
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
