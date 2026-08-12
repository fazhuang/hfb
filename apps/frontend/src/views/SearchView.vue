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
          <router-link :to="{ name: 'books' }" class="empty-link">{{
            t('onboarding.searchNoResultBrowseBooks')
          }}</router-link>
          <router-link :to="{ name: 'persons' }" class="empty-link">{{
            t('onboarding.searchNoResultBrowsePersons')
          }}</router-link>
        </div>
      </div>

      <!-- Initial State -->
      <div v-else-if="!hasSearched" class="empty-state">
        <span class="empty-icon">🔍</span>
        <p>{{ t('search.initialHint') }}</p>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="pagination">
        <button class="page-btn" :disabled="page <= 1" @click="goToPage(page - 1)">
          {{ t('common.back') }}
        </button>
        <span class="page-info">{{ page }} / {{ totalPages }}</span>
        <button class="page-btn" :disabled="page >= totalPages" @click="goToPage(page + 1)">
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
  const priority = [
    'dynasty',
    'era',
    'authors',
    'journal',
    'year',
    'category',
    'repository',
    'order',
  ];
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
  } else if (item.entity_type === 'version') {
    router.push(`/versions/${item.id}`);
  } else if (item.entity_type === 'document') {
    router.push(`/literature/${item.id}`);
  } else if (item.entity_type === 'passage') {
    // Passage results link to parent version detail with anchor
    const meta = item.metadata as Record<string, unknown> | undefined;
    const vid = meta?.version_id as string | undefined;
    if (vid) {
      router.push(`/versions/${vid}?passage=${item.id}`);
    }
  }
  // paper has no dedicated detail page yet — clicking shows nothing
}

// P1-①: Add search result as research topic
function addToTopic(item: SearchResultItem) {
  if (researchStore.hasActiveResearch) {
    const confirmed = window.confirm(
      `当前已有研究课题"${researchStore.currentTopic?.name}"，是否覆盖？`,
    );
    if (!confirmed) return;
  }
  researchStore.setTopic(item.title, item.snippet || item.subtitle || '');
  router.push({ name: 'research-project-list' });
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
  padding: var(--space-6) 20px 60px;
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
  border: 2px solid var(--color-border);
  border-radius: var(--radius-2xl);
  overflow: hidden;
  transition: border-color var(--transition-slow);
}

.search-input-wrapper:focus-within {
  border-color: var(--color-accent);
}

.search-icon {
  padding: 0 var(--space-4);
  font-size: 20px;
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  padding: var(--space-4) 0;
  border: none;
  font-size: 16px;
  background: transparent;
  color: var(--color-text-primary);
  outline: none;
}

.search-input::placeholder {
  color: var(--color-text-muted);
}

.search-submit-btn {
  padding: var(--space-3-5) 28px;
  border: none;
  background: var(--color-accent);
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity var(--transition-base);
}

.search-submit-btn:hover {
  opacity: 0.9;
}

.search-submit-btn:focus-visible {
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
  margin: var(--space-1) 0 0;
  padding: 0;
  list-style: none;
  background: var(--color-navbar-bg, var(--color-surface));
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-dropdown);
  z-index: var(--z-dropdown);
  overflow: hidden;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  padding: var(--space-2-5) 16px;
  cursor: pointer;
  transition: background var(--transition-fast);
}

.suggestion-item:hover {
  background: var(--color-hover);
}

.suggestion-type-badge {
  padding: var(--space-0-5) 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-accent);
  background: var(--color-accent);
  flex-shrink: 0;
}

.suggestion-text {
  font-size: 14px;
  color: var(--color-text-primary);
}

/* --- Filters --- */
.search-filters {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-4);
  margin-bottom: 24px;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.filter-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-text-muted);
  white-space: nowrap;
}

.filter-chips {
  display: flex;
  gap: var(--space-1-5);
  flex-wrap: wrap;
}

.filter-chip {
  padding: var(--space-1) 12px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: transparent;
  font-size: 12px;
  cursor: pointer;
  color: var(--color-text-secondary, var(--color-text-muted));
  transition: all var(--transition-base);
}

.filter-chip:hover {
  border-color: var(--color-accent);
}

.filter-chip:focus-visible {
  border-color: var(--color-accent);
}

.filter-chip--active {
  border-color: var(--color-accent);
  background: var(--color-accent);
  color: var(--color-accent);
}

/* --- Body --- */
.search-body {
  min-height: 300px;
}

.results-stats {
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--color-text-muted);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.result-card {
  padding: var(--space-4) 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-base);

  box-shadow: var(--shadow-card-xs, 0 2px 8px rgba(0, 0, 0, 0.05));}

.result-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-card-sm);
}

.result-card:focus-within {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-card-sm);
}

.result-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.result-type-badge {
  padding: var(--space-0-5) 10px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 600;
}

.badge--person {
  background: var(--color-accent-light);
  color: var(--color-accent);
}
.badge--book {
  background: var(--color-warning-bg);
  color: var(--color-warning);
}
.badge--passage {
  background: var(--color-accent-light);
  color: var(--color-accent);
}
.badge--version {
  background: var(--color-success-bg);
  color: var(--color-success);
}
.badge--paper {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}
.badge--document {
  background: var(--color-page-bg);
  color: var(--color-text-secondary);
}

.result-score {
  font-size: 11px;
  color: var(--color-text-muted);
}

.result-title {
  margin: 0 0 var(--space-1);
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.result-subtitle {
  margin: 0 0 var(--space-1-5);
  font-size: 13px;
  color: var(--color-text-secondary, var(--color-text-muted));
}

.result-snippet {
  margin: 0 0 var(--space-2);
  font-size: 13px;
  color: var(--color-text-secondary, var(--color-text-muted));
  line-height: 1.5;
}

.result-snippet :deep(mark) {
  background: var(--color-warning-bg);
  color: var(--color-text-primary);
  padding: 0 var(--space-0-5);
  border-radius: var(--radius-xs);
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1-5);
}

.meta-tag {
  padding: var(--space-0-5) 8px;
  background: var(--color-page-bg);
  border-radius: var(--radius-sm);
  font-size: 11px;
  color: var(--color-text-muted);
}

/* --- Empty State --- */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-15) 20px;
  color: var(--color-text-muted);
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
  color: var(--color-text-muted);
}

.empty-actions {
  display: flex;
  gap: var(--space-2-5);
  margin-top: 14px;
  flex-wrap: wrap;
  justify-content: center;
}

.empty-link {
  padding: var(--space-1-5) 16px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--color-text-secondary, var(--color-text-muted));
  text-decoration: none;
  transition: all var(--transition-base);
}

.empty-link:hover {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.empty-link:focus-visible {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

/* --- Pagination --- */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border);
}

.page-btn {
  padding: var(--space-2) 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 13px;
  cursor: pointer;
  color: var(--color-text-secondary, var(--color-text-muted));
  transition: all var(--transition-base);
}

.page-btn:hover:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.page-btn:focus-visible:not(:disabled) {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: var(--color-text-muted);
}

/* P1-①: Result actions */
.result-actions {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
}
.result-action-btn {
  padding: var(--space-1) 12px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: transparent;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  color: var(--color-accent);
  transition: all var(--transition-base);
}
.result-action-btn:hover {
  background: var(--color-accent);
  color: white;
}

.result-action-btn:focus-visible {
  background: var(--color-accent);
  color: white;
}
</style>
