<template>
  <div class="book-detail-page">
    <div v-if="loading" class="loading-state">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else-if="book" class="book-content">
      <div class="detail-header">
        <h1>{{ book.title }}</h1>
        <div class="header-meta">
          <span v-if="book.dynasty" class="meta-tag">{{ book.dynasty }}</span>
          <span v-if="book.category" class="meta-tag">{{ book.category }}</span>
          <span v-if="book.year" class="meta-tag">{{ book.year }}</span>
        </div>
      </div>

      <div v-if="book.title_pinyin" class="info-row">
        <span class="info-label">拼音</span>
        <span>{{ book.title_pinyin }}</span>
      </div>

      <div v-if="book.title_english" class="info-row">
        <span class="info-label">英文</span>
        <span>{{ book.title_english }}</span>
      </div>

      <div v-if="book.abstract" class="book-abstract">
        <h3>{{ t('book.abstract') }}</h3>
        <p>{{ book.abstract }}</p>
      </div>

      <!-- Chapters -->
      <div v-if="chapters.length" class="book-chapters">
        <h3>{{ t('book.chapters') }} ({{ chapters.length }})</h3>
        <div v-for="ch in chapters" :key="ch.id" class="chapter-item">
          <span class="chapter-order">{{ ch.order }}</span>
          <span class="chapter-title">{{ ch.title }}</span>
          <span v-if="ch.description" class="chapter-desc">{{ ch.description }}</span>
        </div>
      </div>

      <!-- Versions -->
      <div v-if="versions.length" class="book-versions">
        <h3>{{ t('book.versions') }} ({{ versions.length }})</h3>
        <div v-for="v in versions" :key="v.id" class="version-item" @click="$router.push(`/versions/${v.id}`)">
          <strong>{{ v.version_name }}</strong>
          <span v-if="v.era">{{ v.era }}</span>
          <span v-if="v.repository">{{ v.repository }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import api from '@/api/client';

const { t } = useI18n();
const route = useRoute();

interface BookDetail {
  id: string;
  title: string;
  title_pinyin: string | null;
  title_english: string | null;
  dynasty: string | null;
  year: number | null;
  category: string | null;
  abstract: string | null;
  author_id: string | null;
}

interface ChapterBrief {
  id: string;
  title: string;
  order: number;
  description: string | null;
  book_id: string;
}

interface VersionBrief {
  id: string;
  version_name: string;
  era: string | null;
  repository: string | null;
  book_id: string;
}

const book = ref<BookDetail | null>(null);
const chapters = ref<Array<ChapterBrief>>([]);
const versions = ref<Array<VersionBrief>>([]);
const loading = ref(false);
const error = ref<string | null>(null);

async function fetchBook() {
  const id = route.params.id as string;
  loading.value = true;
  try {
    const { data: d } = await api.get(`/api/v1/books/${id}`);
    book.value = d.data ?? d;

    // Fetch chapters
    const { data: ch } = await api.get('/api/v1/chapters', { params: { limit: 500 } });
    const allCh = (ch.data?.items ?? []) as Array<ChapterBrief>;
    chapters.value = allCh.filter((c) => (c as ChapterBrief).book_id === id);

    // Fetch versions
    const { data: ver } = await api.get('/api/v1/versions', { params: { limit: 500 } });
    const allVer = (ver.data?.items ?? []) as Array<VersionBrief>;
    versions.value = allVer.filter((v) => (v as VersionBrief).book_id === id);
  } catch (e: unknown) {
    error.value = (e as Error).message ?? 'Failed to load book';
  } finally {
    loading.value = false;
  }
}

onMounted(fetchBook);
</script>

<style scoped>
.book-detail-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 32px 24px;
}

.detail-header {
  margin-bottom: 24px;
}

.detail-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 12px;
}

.header-meta {
  display: flex;
  gap: 8px;
}

.meta-tag {
  font-size: 13px;
  padding: 3px 10px;
  background: var(--color-accent, #2b6cb0);
  color: white;
  border-radius: 4px;
}

.info-row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
}

.info-label {
  font-weight: 600;
  min-width: 48px;
  color: var(--color-text-muted, #a0aec0);
}

.book-abstract {
  margin-top: 24px;
  padding: 20px;
  background: var(--color-hover, #f7fafc);
  border-radius: 8px;
}

.book-abstract h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--color-text-primary, #1a365d);
}

.book-abstract p {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary, #4a5568);
  margin: 0;
}

.book-chapters h3, .book-versions h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 32px 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--color-accent, #2b6cb0);
}

.chapter-item {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 10px 12px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  font-size: 14px;
}

.chapter-order {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted, #a0aec0);
}

.chapter-title {
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
}

.chapter-desc {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.version-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
}

.version-item:hover {
  border-color: var(--color-accent, #2b6cb0);
}

.version-item strong {
  color: var(--color-text-primary, #1a365d);
}

.loading-state, .error-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--color-text-muted, #a0aec0);
  font-size: 14px;
}
</style>
