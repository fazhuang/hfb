<template>
  <div class="version-detail-page">
    <div v-if="loading" class="loading-state">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-state">
      <p>{{ error }}</p>
      <button class="btn-back" @click="$router.back()">{{ t('common.back') }}</button>
    </div>
    <div v-else-if="version" class="version-content">
      <!-- Version header -->
      <div class="detail-header">
        <button class="btn-back-link" @click="$router.back()">&larr; {{ t('common.back') }}</button>
        <h1>{{ version.version_name }}</h1>
        <div class="header-meta">
          <span v-if="version.era" class="meta-tag">{{ version.era }}</span>
          <span v-if="version.repository" class="meta-tag">{{ version.repository }}</span>
          <span v-if="version.editor" class="meta-tag">{{ version.editor }}</span>
          <span class="meta-tag meta-id">ID: {{ version.id }}</span>
        </div>
      </div>

      <!-- Version metadata -->
      <div class="version-meta-card">
        <div v-if="version.book_id" class="info-row">
          <span class="info-label">{{ t('version.bookId') }}</span>
          <span class="info-value">{{ version.book_id }}</span>
        </div>
        <div v-if="version.shelf_mark" class="info-row">
          <span class="info-label">{{ t('version.shelfMark') }}</span>
          <span>{{ version.shelf_mark }}</span>
        </div>
        <div v-if="version.year" class="info-row">
          <span class="info-label">{{ t('version.year') }}</span>
          <span>{{ version.year }}</span>
        </div>
        <div v-if="version.description" class="info-row info-row-block">
          <span class="info-label">{{ t('version.description') }}</span>
          <p class="version-desc">{{ version.description }}</p>
        </div>
        <div v-if="version.source_url" class="info-row">
          <span class="info-label">{{ t('version.source') }}</span>
          <a :href="version.source_url" target="_blank" rel="noopener">{{ version.source_url }}</a>
        </div>
        <div class="info-row">
          <span class="info-label">{{ t('version.createdAt') }}</span>
          <span>{{ version.created_at ? new Date(version.created_at).toLocaleDateString() : '-' }}</span>
        </div>
      </div>

      <!-- Fulltext / Passages -->
      <div class="version-passages">
        <div class="passages-header">
          <h3>{{ t('version.passages') }} ({{ passages.length }})</h3>
          <span v-if="passagesError" class="passages-warning">{{ passagesError }}</span>
        </div>

        <div v-if="passagesLoading" class="passages-loading">{{ t('common.loading') }}</div>

        <div v-else-if="passages.length === 0 && !passagesLoading" class="no-passages">
          <p>{{ t('version.noPassages') }}</p>
          <p class="no-passages-reason">{{ t('version.noPassagesReason') }}</p>
        </div>

        <div v-else class="passages-list">
          <div v-for="(p, idx) in passages" :key="p.id" :id="`passage-${p.id}`" class="passage-item">
            <div class="passage-order">{{ p.order ?? idx + 1 }}</div>
            <div class="passage-text">{{ p.content_text }}</div>
            <div v-if="p.translation" class="passage-translation">{{ p.translation }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import api from '@/api/client';

const { t } = useI18n();
const route = useRoute();

interface VersionDetail {
  id: string;
  book_id: string;
  version_name: string;
  era: string | null;
  year: number | null;
  repository: string | null;
  shelf_mark: string | null;
  editor: string | null;
  description: string | null;
  source_url: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface PassageBrief {
  id: string;
  chapter_id: string;
  version_id: string | null;
  content_text: string;
  translation: string | null;
  order: number;
}

const version = ref<VersionDetail | null>(null);
const passages = ref<PassageBrief[]>([]);
const loading = ref(false);
const passagesLoading = ref(false);
const error = ref<string | null>(null);
const passagesError = ref<string | null>(null);

async function fetchVersion() {
  const id = route.params.id as string;
  loading.value = true;
  error.value = null;
  try {
    const { data: d } = await api.get(`/api/v1/versions/${id}`);
    version.value = (d.data ?? d) as VersionDetail;
  } catch (e: unknown) {
    const msg = (e as any)?.response?.data?.detail ?? (e as Error).message ?? 'Failed to load version';
    error.value = msg;
  } finally {
    loading.value = false;
  }
}

async function fetchPassages() {
  const id = route.params.id as string;
  passagesLoading.value = true;
  passagesError.value = null;
  try {
    const { data: d } = await api.get(`/api/v1/versions/${id}/passages`, {
      params: { limit: 500 },
    });
    const items = d.data?.items ?? [];
    passages.value = items as PassageBrief[];
  } catch (e: unknown) {
    // Don't block the page — just show the error state
    const msg = (e as any)?.response?.data?.detail ?? (e as Error).message ?? 'Failed to load passages';
    passagesError.value = msg;
  } finally {
    passagesLoading.value = false;
  }
}

onMounted(() => {
  fetchVersion();
  fetchPassages().then(() => {
    // If navigated from search with ?passage=xxx, scroll to that passage
    const pid = route.query.passage as string | undefined;
    if (pid) {
      nextTick(() => {
        const el = document.getElementById(`passage-${pid}`);
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      });
    }
  });
});
</script>

<style scoped>
.version-detail-page {
  max-width: 860px;
  margin: 0 auto;
  padding: 32px 24px;
}

.detail-header {
  margin-bottom: 24px;
}

.btn-back-link {
  background: none;
  border: none;
  color: var(--color-accent, #2b6cb0);
  cursor: pointer;
  font-size: 14px;
  padding: 0;
  margin-bottom: 12px;
}

.btn-back-link:hover {
  text-decoration: underline;
}

.detail-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 12px;
}

.header-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-tag {
  font-size: 13px;
  padding: 3px 10px;
  background: var(--color-accent, #2b6cb0);
  color: white;
  border-radius: 4px;
}

.meta-tag.meta-id {
  background: var(--color-text-muted, #a0aec0);
  font-family: monospace;
  font-size: 11px;
}

.version-meta-card {
  background: var(--color-hover, #f7fafc);
  border-radius: 8px;
  padding: 20px;
  margin-bottom: 32px;
}

.info-row {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
  align-items: flex-start;
}

.info-row-block {
  flex-direction: column;
}

.info-label {
  font-weight: 600;
  min-width: 72px;
  color: var(--color-text-muted, #a0aec0);
  flex-shrink: 0;
}

.version-desc {
  margin: 0;
  line-height: 1.7;
}

.passages-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--color-accent, #2b6cb0);
}

.passages-header h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
}

.passages-warning {
  font-size: 12px;
  color: var(--color-warning, #dd6b20);
}

.no-passages {
  text-align: center;
  padding: 48px 20px;
  color: var(--color-text-muted, #a0aec0);
}

.no-passages-reason {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  margin-top: 8px;
}

.passage-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  font-size: 14px;
  line-height: 1.8;
}

.passage-item:last-child {
  border-bottom: none;
}

.passage-order {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted, #a0aec0);
  min-width: 28px;
  text-align: right;
  flex-shrink: 0;
}

.passage-text {
  color: var(--color-text-primary, #1a365d);
  flex: 1;
}

.passage-translation {
  color: var(--color-text-secondary, #4a5568);
  font-style: italic;
  margin-top: 4px;
}

.loading-state,
.error-state,
.passages-loading {
  text-align: center;
  padding: 80px 20px;
  color: var(--color-text-muted, #a0aec0);
  font-size: 14px;
}

.error-state {
  color: var(--color-error, #e53e3e);
}

.btn-back {
  margin-top: 12px;
  padding: 8px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 4px;
  background: white;
  cursor: pointer;
  font-size: 14px;
}
</style>
