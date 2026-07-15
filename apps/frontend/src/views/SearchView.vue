<template>
  <div class="search-view">
    <!-- Search Header -->
    <header class="search-header">
      <div class="search-input-wrapper">
        <span class="search-icon">🔍</span>
        <input
          ref="searchInputRef"
          v-model="query"
          type="text"
          class="search-input"
          :placeholder="t('search.placeholder')"
          @keyup.enter="search"
          @input="onQueryInput"
        />
        <button class="search-submit-btn" @click="search" :disabled="loading">
          {{ t('common.search') }}
        </button>
      </div>

      <!-- Autocomplete -->
      <ul v-if="suggestions.length > 0 && query.length > 0" class="suggestions-list">
        <li
          v-for="s in suggestions"
          :key="s.text"
          class="suggestion-item"
          @click="selectSuggestion(s)"
        >
          <span class="suggestion-type-badge">{{ getTypeLabel(s.entity_type) }}</span>
          <span class="suggestion-text">{{ s.text }}</span>
        </li>
      </ul>
    </header>

    <!-- Filters -->
    <div class="search-filters">
      <!-- Entity type chips -->
      <div class="filter-group">
        <span class="filter-label">{{ t('search.filterByType') }}</span>
        <div class="filter-chips">
          <button
            v-for="et in entityTypes"
            :key="et.value"
            class="filter-chip"
            :class="{ 'filter-chip--active': selectedTypes.includes(et.value) }"
            @click="toggleType(et.value)"
          >
            {{ et.label }}
          </button>
        </div>
      </div>

      <!-- Dynasty filter -->
      <div v-if="dynastyFacets.length > 0" class="filter-group">
        <span class="filter-label">{{ t('search.filterByDynasty') }}</span>
        <div class="filter-chips">
          <button
            v-for="d in dynastyFacets"
            :key="d.value"
            class="filter-chip"
            :class="{ 'filter-chip--active': selectedDynasty === d.value }"
            @click="toggleDynasty(d.value)"
          >
            {{ d.value }} ({{ d.count }})
          </button>
        </div>
      </div>
    </div>

    <!-- Results -->
    <div class="search-body">
      <!-- Stats -->
      <div v-if="hasSearched" class="results-stats">
        <span v-if="loading">{{ t('common.loading') }}</span>
        <span v-else>
          {{ t('search.resultsFound', { count: total, query: lastQuery }) }}
        </span>
      </div>

      <!-- Results List -->
      <div v-if="results.length > 0" class="results-list">
        <article
          v-for="item in results"
          :key="`${item.entity_type}:${item.id}`"
          class="result-card"
          @click="navigateToItem(item)"
        >
          <div class="result-header">
            <span class="result-type-badge" :class="`badge--${item.entity_type}`">
              {{ getTypeLabel(item.entity_type) }}
            </span>
            <span class="result-score" v-if="item.score > 0">
              {{ Math.round(item.score * 100) }}%
            </span>
          </div>

          <h3 class="result-title">{{ item.title }}</h3>

          <p v-if="item.subtitle" class="result-subtitle">{{ item.subtitle }}</p>

          <p v-if="item.snippet" class="result-snippet">
            <template v-for="(segment, index) in highlightSnippet(item.snippet)" :key="index">
              <mark v-if="segment.highlighted">{{ segment.text }}</mark>
              <template v-else>{{ segment.text }}</template>
            </template>
          </p>

          <div v-if="item.metadata" class="result-meta">
            <span v-for="(val, key) in visibleMeta(item.metadata)" :key="key" class="meta-tag">
              {{ key }}: {{ val }}
            </span>
          </div>

          <!-- P1-①: Quick actions -->
          <div class="result-actions" @click.stop>
            <button
              class="result-action-btn"
              @click="addToTopic(item)"
              :title="t('search.addToTopic')"
            >
              📌 {{ t('search.addToTopic') }}
            </button>
          </div>
        </article>
      </div>

      <!-- Empty State -->
      <div v-else-if="hasSearched && !loading" class="empty-state">
        <span class="empty-icon">📭</span>
        <p>{{ t('search.noResults') }}</p>
        <p class="empty-hint">{{ t('onboarding.searchNoResultHint') }}</p>
        <div class="empty-actions">
          <router-link :to="{ name: 'books' }" class="empty-link">{{ t('onboarding.searchNoResultBrowseBooks') }}</router-link>
          <router-link :to="{ name: 'persons' }" class="empty-link">{{ t('onboarding.searchNoResultBrowsePersons') }}</router-link>
        </div>
      </div>

      <!-- Initial State -->
      <div v-else-if="!hasSearched" class="empty-state">
        <span class="empty-icon">🔍</span>
        <p>{{ t('search.initialHint') }}</p>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="pagination">
        <button
          class="page-btn"
          :disabled="page <= 1"
          @click="goToPage(page - 1)"
        >
          {{ t('common.back') }}
        </button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button
          class="page-btn"
          :disabled="page >= totalPages"
          @click="goToPage(page + 1)"
        >
          {{ t('common.next') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter, useRoute } from 'vue-router';
import { useResearchStore } from '@/stores/research';
import api from '@/api/client';

const { t } = useI18n();
const router = useRouter();
const route = useRoute();
const researchStore = useResearchStore();

// --- State ---
const query = ref('');
const lastQuery = ref('');
const page = ref(1);
const limit = 20;
const loading = ref(false);
const hasSearched = ref(false);
const results = ref<SearchResultItem[]>([]);
const total = ref(0);
const totalPages = ref(1);
const suggestions = ref<SuggestItem[]>([]);
const dynastyFacets = ref<{ value: string; count: number }[]>([]);
const selectTimer = ref<ReturnType<typeof setTimeout> | null>(null);

interface SearchResultItem {
  id: string;
  entity_type: string;
  title: string;
  subtitle?: string | null;
  snippet?: string | null;
  url?: string | null;
  metadata: Record<string, unknown>;
  score: number;
}

interface SuggestItem {
  text: string;
  entity_type: string;
  entity_id?: string | null;
}

// --- Filters ---
const entityTypes = [
  { value: 'person', label: '👤 ' + t('nav.persons') },
  { value: 'book', label: '📚 ' + t('nav.books') },
  { value: 'passage', label: '📜 ' + t('graph.passages') },
  { value: 'version', label: '📖 ' + t('graph.versions') },
  { value: 'paper', label: '📄 ' + t('search.papers') },
];
const selectedTypes = ref<string[]>(['person', 'book', 'passage', 'version', 'paper']);
const selectedDynasty = ref<string | null>(null);

function toggleType(type: string) {
  const idx = selectedTypes.value.indexOf(type);
  if (idx >= 0) {
    selectedTypes.value.splice(idx, 1);
  } else {
    selectedTypes.value.push(type);
  }
}

function toggleDynasty(dynasty: string) {
  selectedDynasty.value = selectedDynasty.value === dynasty ? null : dynasty;
}

// --- Computed ---
const searchInputRef = ref<HTMLInputElement | null>(null);

// --- Methods ---
const TYPE_LABELS: Record<string, string> = {
  person: '👤 ' + t('nav.persons'),
  book: '📚 ' + t('nav.books'),
  passage: '📜 ' + t('graph.passages'),
  version: '📖 ' + t('graph.versions'),
  paper: '📄 ' + t('search.papers'),
  document: '📁 ' + t('nav.documents'),
  image: '🖼️ ' + 'Image',
};

function getTypeLabel(type: string): string {
  return TYPE_LABELS[type] || type;
}

function visibleMeta(meta: Record<string, unknown>): Record<string, string> {
  // Filter to show only the most relevant meta fields
  const priority = ['dynasty', 'era', 'authors', 'journal', 'year', 'category', 'repository', 'order'];
  const visible: Record<string, string> = {};
  for (const key of priority) {
    if (meta[key] != null && meta[key] !== '') {
      visible[key] = String(meta[key]);
    }
  }
  return visible;
}

function highlightSnippet(text: string): Array<{ text: string; highlighted: boolean }> {
  if (!lastQuery.value) return [{ text, highlighted: false }];
  const escapedQuery = lastQuery.value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const matcher = new RegExp(`(${escapedQuery})`, 'gi');
  return text
    .split(matcher)
    .filter(Boolean)
    .map((segment) => ({
      text: segment,
      highlighted: segment.toLocaleLowerCase() === lastQuery.value.toLocaleLowerCase(),
    }));
}

async function search() {
  if (selectedTypes.value.length === 0) return;

  loading.value = true;
  hasSearched.value = true;
  suggestions.value = [];
  lastQuery.value = query.value.trim();

  try {
    const typesParam = selectedTypes.value.join(',');
    const params: Record<string, unknown> = {
      q: lastQuery.value,
      types: typesParam,
      page: page.value,
      limit,
    };
    if (selectedDynasty.value) {
      params.dynasty = selectedDynasty.value;
    }

    const { data } = await api.get('/api/v1/search', { params });
    const body = data.data ?? data;

    results.value = (body.items ?? []) as SearchResultItem[];
    total.value = (body.total ?? 0) as number;
    totalPages.value = (body.total_pages ?? 1) as number;

    // Update dynasty facets
    if (body.facets?.dynasty) {
      dynastyFacets.value = body.facets.dynasty;
    }
  } catch (e: unknown) {
    console.error('Search failed:', e);
    results.value = [];
  } finally {
    loading.value = false;
  }
}

async function fetchSuggestions() {
  const q = query.value.trim();
  if (q.length < 1) {
    suggestions.value = [];
    return;
  }

  try {
    const { data } = await api.get('/api/v1/search/suggest', {
      params: { q, limit: 5 },
    });
    suggestions.value = (data.data ?? []) as SuggestItem[];
  } catch {
    suggestions.value = [];
  }
}

function onQueryInput() {
  if (selectTimer.value) clearTimeout(selectTimer.value);
  selectTimer.value = setTimeout(fetchSuggestions, 200);
}

function selectSuggestion(s: SuggestItem) {
  query.value = s.text;
  suggestions.value = [];
  search();
}

function goToPage(p: number) {
  page.value = p;
  search();
}

function navigateToItem(item: SearchResultItem) {
  if (item.url) {
    router.push(item.url);
  } else if (item.entity_type === 'book') {
    router.push(`/books/${item.id}`);
  } else if (item.entity_type === 'person') {
    router.push(`/persons/${item.id}`);
  }
  // Other types have no dedicated detail page yet
}

// P1-①: Add search result as research topic
function addToTopic(item: SearchResultItem) {
  researchStore.setTopic(item.title, item.snippet || item.subtitle || '');
  router.push({ name: 'research-home' });
}

// Watch filters — re-search on change
watch([selectedTypes, selectedDynasty], () => {
  page.value = 1;
  if (hasSearched.value) search();
});

onMounted(() => {
  nextTick(() => searchInputRef.value?.focus());

  // P1-⑥: Accept ?q= param from re-search navigation
  const qParam = route.query.q as string | undefined;
  if (qParam) {
    query.value = decodeURIComponent(qParam);
    search();
  }
});
</script>

<style scoped>
.search-view {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 20px 60px;
}

/* --- Header --- */
.search-header {
  position: relative;
  margin-bottom: 20px;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 0;
  border: 2px solid var(--color-border, #e2e8f0);
  border-radius: 12px;
  overflow: hidden;
  transition: border-color 0.2s;
}

.search-input-wrapper:focus-within {
  border-color: var(--color-accent, #2b6cb0);
}

.search-icon {
  padding: 0 16px;
  font-size: 20px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  padding: 16px 0;
  border: none;
  font-size: 16px;
  background: transparent;
  color: var(--color-text-primary, #1a365d);
  outline: none;
}

.search-input::placeholder {
  color: var(--color-text-muted, #a0aec0);
}

.search-submit-btn {
  padding: 14px 28px;
  border: none;
  background: var(--color-accent, #2b6cb0);
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.15s;
}

.search-submit-btn:hover {
  opacity: 0.9;
}

.search-submit-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* --- Autocomplete --- */
.suggestions-list {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  margin: 4px 0 0;
  padding: 0;
  list-style: none;
  background: var(--color-navbar-bg, #fff);
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
  z-index: 50;
  overflow: hidden;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  cursor: pointer;
  transition: background 0.1s;
}

.suggestion-item:hover {
  background: var(--color-hover, #edf2f7);
}

.suggestion-type-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  background: rgba(43, 108, 176, 0.1);
  flex-shrink: 0;
}

.suggestion-text {
  font-size: 14px;
  color: var(--color-text-primary, #1a365d);
}

/* --- Filters --- */
.search-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 24px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-muted, #a0aec0);
  white-space: nowrap;
}

.filter-chips {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-chip {
  padding: 4px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 20px;
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  color: var(--color-text-secondary, #718096);
  transition: all 0.15s;
}

.filter-chip:hover {
  border-color: var(--color-accent, #2b6cb0);
}

.filter-chip--active {
  border-color: var(--color-accent, #2b6cb0);
  background: rgba(43, 108, 176, 0.1);
  color: var(--color-accent, #2b6cb0);
}

/* --- Body --- */
.search-body {
  min-height: 300px;
}

.results-stats {
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--color-text-muted, #a0aec0);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.result-card {
  padding: 16px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.15s;
}

.result-card:hover {
  border-color: var(--color-accent, #2b6cb0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.result-type-badge {
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.badge--person { background: #E8F4FD; color: #2196F3; }
.badge--book { background: #FEF3E2; color: #FF9800; }
.badge--passage { background: #F3E5F5; color: #9C27B0; }
.badge--version { background: #E8F5E9; color: #4CAF50; }
.badge--paper { background: #FFF3E0; color: #EF6C00; }
.badge--document { background: #ECEFF1; color: #607D8B; }

.result-score {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
}

.result-title {
  margin: 0 0 4px;
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
}

.result-subtitle {
  margin: 0 0 6px;
  font-size: 13px;
  color: var(--color-text-secondary, #718096);
}

.result-snippet {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--color-text-secondary, #718096);
  line-height: 1.5;
}

.result-snippet :deep(mark) {
  background: #FFF9C4;
  color: var(--color-text-primary, #1a365d);
  padding: 0 2px;
  border-radius: 2px;
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.meta-tag {
  padding: 2px 8px;
  background: var(--color-page-bg, #fafafa);
  border-radius: 4px;
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
}

/* --- Empty State --- */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  color: var(--color-text-muted, #a0aec0);
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
}

.empty-state p {
  margin: 0;
  font-size: 15px;
}

.empty-hint {
  margin-top: 6px !important;
  font-size: 13px !important;
  color: var(--color-text-muted, #a0aec0);
}

.empty-actions {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  flex-wrap: wrap;
  justify-content: center;
}

.empty-link {
  padding: 6px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  font-size: 13px;
  color: var(--color-text-secondary, #718096);
  text-decoration: none;
  transition: all 0.15s;
}

.empty-link:hover {
  border-color: var(--color-accent, #2b6cb0);
  color: var(--color-accent, #2b6cb0);
}

/* --- Pagination --- */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border, #e2e8f0);
}

.page-btn {
  padding: 8px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  color: var(--color-text-secondary, #718096);
  transition: all 0.15s;
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-accent, #2b6cb0);
  color: var(--color-accent, #2b6cb0);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: var(--color-text-muted, #a0aec0);
}

/* P1-①: Result actions */
.result-actions {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border, #e2e8f0);
}
.result-action-btn {
  padding: 4px 12px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 6px;
  background: transparent;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  color: var(--color-accent, #2b6cb0);
  transition: all 0.15s;
}
.result-action-btn:hover {
  background: var(--color-accent, #2b6cb0);
  color: white;
}
</style>
