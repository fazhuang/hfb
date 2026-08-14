<template>
  <div class="entity-list-page">
    <div class="page-header">
      <div class="page-header-title">
        <h1>{{ title }}</h1>
      </div>
      <div class="search-box">
        <HfbIcon icon="search" :size="16" class="search-leading-icon" />
        <input
          v-model="query"
          type="text"
          :placeholder="t('common.search') + '…'"
          @keyup.enter="search"
        />
        <button class="search-btn" @click="search">
          <HfbIcon icon="search" :size="14" />
          <span>{{ t('common.search') }}</span>
        </button>
      </div>
    </div>

    <div v-if="loading" class="loading-state" aria-busy="true">{{ t('common.loading') }}</div>

    <div v-else-if="error" class="error-wrap">
      <ErrorState :message="error" :show-retry="!isAuthError" @retry="fetch(page, limit, query)" />
      <button v-if="isAuthError" class="login-redirect-btn" @click="goToLogin">
        {{ t('auth.login', '前往登录') }}
      </button>
    </div>

    <EmptyState
      v-else-if="items.length === 0"
      title="暂无记录"
      description="还没有相关古籍数据。"
      icon="book-open"
    />

    <div v-else class="entity-grid">
      <div
        v-for="item in items"
        :key="item.id"
        class="entity-card"
        role="button"
        tabindex="0"
        @click="$router.push(`${routePrefix}/${item.id}`)"
        @keydown.enter="$router.push(`${routePrefix}/${item.id}`)"
      >
        <div class="card-anchor" aria-hidden="true">
          <HfbIcon icon="book-open" :size="18" />
        </div>
        <div class="card-body">
          <h3 class="card-title">{{ getTitle(item) }}</h3>
          <div class="card-meta">
            <span v-for="meta in getMeta(item)" :key="meta" class="meta-tag">{{ meta }}</span>
          </div>
          <div v-if="props.getSubtitle?.(item)" class="card-subtitle">
            {{ props.getSubtitle?.(item) }}
          </div>
        </div>
      </div>
    </div>

    <div v-if="total > limit" class="pagination">
      <button :disabled="page <= 1" @click="goPage(page - 1)">{{ t('common.back') }}</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="goPage(page + 1)">
        {{ t('common.next') }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter, useRoute } from 'vue-router';
import HfbIcon from '@/components/common/HfbIcon.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import { useEntityList, type EntityBrief } from '@/composables/useApi';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();

const props = withDefaults(
  defineProps<{
    endpoint: string;
    title: string;
    routePrefix: string;
    getTitle: (item: EntityBrief) => string;
    getMeta: (item: EntityBrief) => Array<string>;
    getSubtitle?: (item: EntityBrief) => string | null;
  }>(),
  {
    getSubtitle: undefined,
  },
);

const { items, total, loading, error, fetch } = useEntityList<EntityBrief>(props.endpoint);

const isAuthError = computed<boolean>(() => {
  if (!error.value) return false;
  return (
    error.value.includes('未登录') ||
    error.value.includes('登录会话已过期') ||
    error.value.includes('401')
  );
});

function goToLogin(): void {
  router.push({ name: 'login', query: { redirect: route.fullPath } });
}

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
  width: 100%;
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

.page-header-title h1 {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
  font-family: var(--font-serif);
  letter-spacing: 0.02em;
}

.search-box {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  position: relative;
}

.search-leading-icon {
  position: absolute;
  left: 12px;
  color: var(--color-text-muted);
  pointer-events: none;
}

.search-box input {
  padding: var(--space-2) var(--space-3) var(--space-2) 38px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  min-width: 200px;
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  transition: border-color var(--transition-base);
}

.search-box input:focus-visible {
  border-color: var(--color-accent);
  outline: 2px solid var(--color-accent);
  outline-offset: -1px;
}

.search-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-2) var(--space-4);
  background: var(--color-accent);
  color: var(--color-on-accent);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: var(--text-sm);
  transition: background var(--transition-base);
}

.search-btn:hover {
  background: var(--color-accent-hover);
}

.entity-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--space-4);
}

.entity-card {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  cursor: pointer;
  box-shadow: var(--shadow-card-xs);
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base);
  background: var(--color-surface);
}

.entity-card:hover,
.entity-card:focus-visible {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-card-hover);
  outline: none;
}

.card-anchor {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-accent-light);
  color: var(--color-accent);
}

.card-body {
  min-width: 0;
  flex: 1;
}

.card-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
  font-family: var(--font-serif);
  letter-spacing: 0.02em;
}

.card-meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--space-1-5);
  margin-bottom: var(--space-2);
}

.meta-tag {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  padding: 2px 10px;
  background: var(--color-tag-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  color: var(--color-text-secondary);
  line-height: 1.6;
}

/* 首个标签（朝代/主类别）强调为学术主色 */
.meta-tag:first-child {
  background: var(--color-accent-light);
  border-color: transparent;
  color: var(--color-accent);
  font-weight: var(--font-semibold);
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

.loading-state {
  text-align: center;
  padding: var(--space-15) var(--space-5);
  color: var(--color-text-muted);
  font-size: var(--text-base);
}

.error-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
}

.login-redirect-btn {
  padding: var(--space-2) var(--space-4);
  background: var(--color-accent);
  color: var(--color-on-accent);
  border: none;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  transition: background var(--transition-base);
}

.login-redirect-btn:hover {
  background: var(--color-accent-hover);
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
