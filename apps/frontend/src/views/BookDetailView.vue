<template>
  <div class="book-detail-page">
    <div v-if="loading" class="loading-state" aria-busy="true">{{ t('common.loading') }}</div>

    <ErrorState v-else-if="error" :message="error" @retry="fetchBook" />

    <div v-else-if="book" class="book-content">
      <!-- 面包屑 -->
      <nav class="detail-breadcrumb" aria-label="面包屑">
        <router-link :to="{ name: 'books' }" class="crumb-link">
          {{ t('nav.books') }}
        </router-link>
        <HfbIcon icon="chevron-right" :size="12" class="crumb-sep" />
        <span class="crumb-current">{{ book.title }}</span>
      </nav>

      <div class="detail-header">
        <h1>{{ book.title }}</h1>
        <div class="header-meta">
          <span v-if="book.dynasty" class="meta-tag">{{ book.dynasty }}</span>
          <span v-if="book.category" class="meta-tag meta-tag--category">{{ book.category }}</span>
          <span v-if="book.year" class="meta-tag meta-tag--year">{{ book.year }} 年</span>
        </div>
      </div>

      <div v-if="book.title_pinyin || book.title_english" class="info-group">
        <div v-if="book.title_pinyin" class="info-row">
          <span class="info-label">拼音</span>
          <span>{{ book.title_pinyin }}</span>
        </div>
        <div v-if="book.title_english" class="info-row">
          <span class="info-label">英文</span>
          <span>{{ book.title_english }}</span>
        </div>
      </div>

      <div v-if="book.abstract" class="book-abstract">
        <h3><HfbIcon icon="scroll-text" :size="16" /> {{ t('book.abstract') }}</h3>
        <p>{{ book.abstract }}</p>
      </div>

      <!-- Chapters -->
      <section v-if="chapters.length" class="book-chapters">
        <h3>
          {{ t('book.chapters') }}
          <span class="section-count">{{ chapters.length }}</span>
        </h3>
        <div v-for="ch in chapters" :key="ch.id" class="chapter-item">
          <span class="chapter-order">{{ String(ch.order).padStart(2, '0') }}</span>
          <span class="chapter-title">{{ ch.title }}</span>
          <span v-if="ch.description" class="chapter-desc">{{ ch.description }}</span>
        </div>
      </section>

      <!-- Versions -->
      <section v-if="versions.length" class="book-versions">
        <h3>
          {{ t('book.versions') }}
          <span class="section-count">{{ versions.length }}</span>
        </h3>
        <div
          v-for="v in versions"
          :key="v.id"
          class="version-item"
          role="button"
          tabindex="0"
          @click="$router.push(`/versions/${v.id}`)"
          @keydown.enter="$router.push(`/versions/${v.id}`)"
        >
          <HfbIcon icon="landmark" :size="16" class="version-icon" />
          <div class="version-main">
            <strong>{{ v.version_name }}</strong>
            <span v-if="v.era || v.repository" class="version-sub">
              {{ [v.era, v.repository].filter(Boolean).join(' · ') }}
            </span>
          </div>
          <HfbIcon icon="chevron-right" :size="16" class="version-arrow" />
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import HfbIcon from '@/components/common/HfbIcon.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import api, { getErrorMessage } from '@/api/client';

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
    const { data: ch } = await api.get('/api/v1/chapters', { params: { limit: 100 } });
    const allCh = (ch.data?.items ?? []) as Array<ChapterBrief>;
    chapters.value = allCh.filter((c) => (c as ChapterBrief).book_id === id);

    // Fetch versions
    const { data: ver } = await api.get('/api/v1/versions', { params: { limit: 100 } });
    const allVer = (ver.data?.items ?? []) as Array<VersionBrief>;
    versions.value = allVer.filter((v) => (v as VersionBrief).book_id === id);
  } catch (e: unknown) {
    error.value = getErrorMessage(e, '加载古籍详情失败');
  } finally {
    loading.value = false;
  }
}

onMounted(fetchBook);
</script>

<style scoped>
.book-detail-page {
  width: 100%;
  max-width: 800px;
  margin: 0 auto;
  padding: var(--space-8) 24px;
}

.detail-breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  margin-bottom: var(--space-4);
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.crumb-link {
  color: var(--color-accent);
  text-decoration: none;
}

.crumb-link:hover {
  text-decoration: underline;
}

.crumb-sep {
  color: var(--color-text-muted);
}

.crumb-current {
  color: var(--color-text-secondary);
}

.detail-header {
  margin-bottom: var(--space-6);
}

.detail-header h1 {
  font-size: var(--text-3xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
  font-family: var(--font-serif);
  letter-spacing: 0.02em;
}

.header-meta {
  display: flex;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.meta-tag {
  font-size: var(--text-xs);
  font-weight: var(--font-medium);
  padding: 3px 10px;
  background: var(--color-accent);
  color: var(--color-on-accent);
  border-radius: var(--radius-sm);
}

.meta-tag--category {
  background: var(--color-accent-light);
  color: var(--color-accent);
}

.meta-tag--year {
  background: var(--color-hover);
  color: var(--color-text-secondary);
}

.info-group {
  margin-bottom: var(--space-2);
}

.info-row {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  font-size: var(--text-base);
  color: var(--color-text-secondary);
}

.info-label {
  font-weight: var(--font-semibold);
  min-width: 48px;
  color: var(--color-text-muted);
}

.book-abstract {
  margin-top: var(--space-6);
  padding: var(--space-5);
  background: var(--color-page-bg);
  border: 1px solid var(--color-border);
  border-left: 3px solid var(--color-accent);
  border-radius: var(--radius-lg);
}

.book-abstract h3 {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  margin: 0 0 var(--space-2);
  color: var(--color-text-primary);
  font-family: var(--font-serif);
}

.book-abstract p {
  font-size: var(--text-base);
  line-height: 1.8;
  color: var(--color-text-secondary);
  margin: 0;
}

.book-chapters h3,
.book-versions h3 {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: var(--space-8) 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--color-accent);
  font-family: var(--font-serif);
}

.section-count {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
  background: var(--color-accent-light);
  padding: 1px 8px;
  border-radius: var(--radius-full);
}

.chapter-item {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
  padding: var(--space-2-5) 12px;
  border-bottom: 1px solid var(--color-border);
  font-size: var(--text-base);
}

.chapter-order {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  font-family: var(--font-mono);
}

.chapter-title {
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.chapter-desc {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.version-item {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  margin-bottom: 8px;
  cursor: pointer;
  box-shadow: var(--shadow-card-xs);
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base);
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  background: var(--color-surface);
}

.version-item:hover,
.version-item:focus-visible {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-card-hover);
  outline: none;
}

.version-icon {
  color: var(--color-accent);
  flex-shrink: 0;
}

.version-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.version-item strong {
  color: var(--color-text-primary);
  font-family: var(--font-serif);
  letter-spacing: 0.02em;
}

.version-sub {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.version-arrow {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.loading-state {
  text-align: center;
  padding: var(--space-20) 20px;
  color: var(--color-text-muted);
  font-size: var(--text-base);
}
</style>
