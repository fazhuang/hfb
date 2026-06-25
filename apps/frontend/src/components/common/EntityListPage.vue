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
  padding: 32px 24px;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-header h1 {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
}

.search-box {
  display: flex;
  gap: 8px;
}

.search-box input {
  padding: 8px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 14px;
  min-width: 200px;
  background: var(--color-page-bg, #f7fafc);
  color: var(--color-text-primary, #1a365d);
}

.search-btn {
  padding: 8px 16px;
  background: var(--color-accent, #2b6cb0);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}

.entity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.entity-card {
  padding: 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
  background: var(--color-navbar-bg, #fff);
}

.entity-card:hover {
  border-color: var(--color-accent, #2b6cb0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 8px;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.meta-tag {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--color-tag-bg, #edf2f7);
  border-radius: 4px;
  color: var(--color-text-secondary, #4a5568);
}

.card-subtitle {
  font-size: 13px;
  color: var(--color-text-muted, #a0aec0);
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.loading-state, .error-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted, #a0aec0);
  font-size: 14px;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 32px;
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
}

.pagination button {
  padding: 6px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  cursor: pointer;
  font-size: 13px;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
</style>
