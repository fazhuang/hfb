<template>
  <div class="research-page">
    <!-- Page Header -->
    <ResearchPageHeader
      title="研究课题"
      description="创建、查找并继续您的研究课题。"
      :breadcrumbs="[{ label: 'Research' }]"
    >
      <template #actions>
        <router-link
          v-if="allProjects.length > 0"
          :to="`/research/${allProjects[0]!.id}/workflow`"
          class="rpp-create-btn rpp-create-btn--secondary rpp-quick-start-btn"
          style="margin-right: 8px; text-decoration: none"
          aria-label="发起新研究"
        >
          ⚡ 发起新研究
        </router-link>
        <button
          ref="createBtnRef"
          class="rpp-create-btn"
          @click="showCreateDialog = true"
          aria-label="新建课题"
        >
          + 新建课题
        </button>
      </template>
    </ResearchPageHeader>

    <div class="rpp-body">
      <!-- Search & Filter Toolbar -->
      <ProjectListToolbar v-model="searchQuery" @search="onSearch" @clear="onClear" />

      <!-- Content Area -->
      <div class="rpp-content">
        <!-- Loading -->
        <LoadingState v-if="loading" :message="loadingMessage" />

        <!-- Error -->
        <ErrorState v-else-if="error" :message="error" @retry="loadProjects" />

        <!-- Empty: no projects at all -->
        <EmptyState
          v-else-if="allProjects.length === 0 && !searchActive"
          title="还没有研究课题"
          description="创建您的第一个研究课题，开始对《针灸甲乙经》等古籍进行可计算、可验证的证据研究。"
          icon="🔬"
        >
          <template #action>
            <button class="rpp-create-btn rpp-create-btn--inline" @click="showCreateDialog = true">
              + 新建课题
            </button>
          </template>
        </EmptyState>

        <!-- Empty: search returned no results -->
        <EmptyState
          v-else-if="filteredProjects.length === 0 && searchActive"
          title="未找到匹配的课题"
          :description="'没有课题与 “' + searchQuery.trim() + '” 匹配，请尝试其他关键词。'"
          icon="🔍"
        >
          <template #action>
            <button class="rpp-create-btn rpp-create-btn--inline" @click="onClear">清除筛选</button>
          </template>
        </EmptyState>

        <!-- Project List -->
        <div v-else class="rpp-list">
          <ProjectListItem
            v-for="project in paginatedProjects"
            :key="project.id"
            :project="project"
          />
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="totalPages > 1" class="rpp-pagination">
        <button :disabled="page <= 1" @click="goPage(page - 1)">
          {{ t('common.back') }}
        </button>
        <span class="rpp-page-info" :aria-label="`第 ${page} 页，共 ${totalPages} 页`"
          >{{ page }} / {{ totalPages }}</span
        >
        <button :disabled="page >= totalPages" @click="goPage(page + 1)">
          {{ t('common.next') }}
        </button>
      </div>
    </div>

    <!-- Create Dialog -->
    <CreateProjectDialog
      :open="showCreateDialog"
      :trigger-el="createBtnRef"
      @update:open="showCreateDialog = $event"
      @created="onProjectCreated"
    />

    <!-- Success toast (lightweight) -->
    <div v-if="successMessage" class="rpp-toast" role="status" aria-live="polite">
      {{ successMessage }}
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ProjectListPage — 研究课题列表页面
 *
 * Data source:
 *   GET /api/v1/workspace/sessions
 *   POST /api/v1/workspace/sessions (create)
 *
 * NOTE: The backend endpoint does NOT support server-side search,
 * pagination, or status filtering. This page applies client-side
 * filtering on the full result set and client-side pagination.
 *
 * The list_sessions endpoint returns at most 20 sessions per user.
 * This page fetches up to 100 by calling with a larger limit via
 * the query parameter approach (falling back to the default 20).
 *
 * ref: docs/20-product/2010-project-list-migration.md
 */
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import api, { getErrorMessage } from '@/api/client';
import type { ResearchProjectSummary } from '@/types/research';

import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import ProjectListToolbar from '@/components/research/ProjectListToolbar.vue';
import ProjectListItem from '@/components/research/ProjectListItem.vue';
import CreateProjectDialog from '@/components/research/CreateProjectDialog.vue';

const { t } = useI18n();

type CancelErrorLike = { code?: string; name?: string };

function isCanceled(e: unknown): boolean {
  const err = e as CancelErrorLike;
  return err?.code === 'ERR_CANCELED' || err?.name === 'CanceledError';
}

// ---- Single source of truth: all projects from API ----
const allProjects = ref<ResearchProjectSummary[]>([]);

// ---- UI state ----
const loading = ref(false);
const error = ref<string | null>(null);
const showCreateDialog = ref(false);
const createBtnRef = ref<HTMLButtonElement | null>(null);
const successMessage = ref('');

// ---- Search (client-side) ----
const searchQuery = ref('');
const searchActive = ref(false);

// ---- Pagination (client-side) ----
const page = ref(1);
const limit = ref(10);

const loadingMessage = computed(() => {
  if (searchActive.value) return '正在搜索...';
  return t('common.loading');
});

// ---- Derived: filtered projects ----
const filteredProjects = computed<ResearchProjectSummary[]>(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return allProjects.value;
  return allProjects.value.filter((p) => {
    const title = (p.title || '').toLowerCase();
    const desc = (p.description || '').toLowerCase();
    return title.includes(q) || desc.includes(q);
  });
});

// ---- Derived: paginated slice ----
const totalPages = computed(() =>
  Math.max(1, Math.ceil(filteredProjects.value.length / limit.value)),
);

const paginatedProjects = computed<ResearchProjectSummary[]>(() => {
  const start = (page.value - 1) * limit.value;
  return filteredProjects.value.slice(start, start + limit.value);
});

// ---- Request deduplication (race condition guard) ----
let reqId = 0;
let pendingController: AbortController | null = null;
let pendingTimeoutId: ReturnType<typeof setTimeout> | null = null;

const ABORT_TIMEOUT_MS = 10_000;

function clearPendingRequest() {
  if (pendingTimeoutId !== null) {
    clearTimeout(pendingTimeoutId);
    pendingTimeoutId = null;
  }
  if (pendingController) {
    pendingController.abort();
    pendingController = null;
  }
}

// ---- Load projects from API ----
async function loadProjects() {
  const myReqId = ++reqId;

  clearPendingRequest();

  const controller = new AbortController();
  pendingController = controller;
  pendingTimeoutId = setTimeout(() => controller.abort(), ABORT_TIMEOUT_MS);

  loading.value = true;
  error.value = null;

  try {
    const { data } = await api.get('/api/v1/workspace/sessions', {
      params: { limit: 100 },
      signal: controller.signal,
    });
    // Guard against stale responses
    if (myReqId !== reqId) return;
    const rawItems = (data.data ?? []) as Record<string, unknown>[];
    allProjects.value = rawItems.map(toProjectSummary);
  } catch (e: unknown) {
    if (myReqId !== reqId) return;
    if (isCanceled(e)) {
      if (controller.signal.aborted) {
        error.value = '请求超时（10 秒），请重试。';
      }
      return;
    }
    error.value = getErrorMessage(e, '加载失败，请检查网络连接后重试。');
  } finally {
    if (myReqId === reqId) {
      loading.value = false;
      if (pendingController === controller) {
        pendingController = null;
      }
      if (pendingTimeoutId !== null) {
        clearTimeout(pendingTimeoutId);
        pendingTimeoutId = null;
      }
    }
  }
}

// ---- Map API response to ResearchProjectSummary ----
function toProjectSummary(raw: Record<string, unknown>): ResearchProjectSummary {
  return {
    id: String(raw.id || ''),
    title: String(raw.title || ''),
    created_at: typeof raw.created_at === 'string' ? raw.created_at : null,
    updated_at: typeof raw.updated_at === 'string' ? raw.updated_at : null,
  };
}

// ---- Search ----
function onSearch(_query: string) {
  searchActive.value = _query.trim().length > 0;
  page.value = 1; // reset to first page on search
}

function onClear() {
  searchQuery.value = '';
  searchActive.value = false;
  page.value = 1;
}

// ---- Pagination ----
function goPage(p: number) {
  if (p < 1 || p > totalPages.value) return;
  page.value = p;
}

// ---- Create ----
async function onProjectCreated() {
  successMessage.value = '课题创建成功';
  await loadProjects();
  // Auto-dismiss toast
  setTimeout(() => {
    successMessage.value = '';
  }, 3000);
}

// ---- Lifecycle ----
onMounted(() => {
  loadProjects();
});

// Cancel pending requests on unmount
onBeforeUnmount(() => {
  reqId = -1; // invalidates all pending request callbacks
  clearPendingRequest();
});
</script>

<style scoped>
.research-page {
  min-height: 100%;
}

.rpp-body {
  padding: var(--space-6) var(--space-8);
}

.rpp-content {
  min-height: 200px;
}

.rpp-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* ---- Create button ---- */
.rpp-create-btn {
  padding: var(--btn-padding-lg);
  border: none;
  border-radius: var(--btn-radius);
  background: var(--color-accent);
  color: var(--color-surface);
  font-size: var(--btn-font-lg);
  font-weight: var(--font-semibold);
  cursor: pointer;
  white-space: nowrap;
  transition: background var(--transition-base);
}

.rpp-create-btn:hover {
  background: var(--color-accent-hover);
}

.rpp-create-btn:focus-visible {
  outline-offset: 2px;
  background: var(--color-accent-hover);
}

.rpp-create-btn--inline {
  display: inline-flex;
  align-items: center;
}

/* ---- Pagination ---- */
.rpp-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  margin-top: var(--space-7);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.rpp-pagination button {
  padding: var(--btn-padding-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
}

.rpp-pagination button:hover:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.rpp-pagination button:focus-visible:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.rpp-pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.rpp-page-info {
  min-width: 60px;
  text-align: center;
}

/* ---- Toast ---- */
.rpp-toast {
  position: fixed;
  bottom: var(--space-6);
  left: 50%;
  transform: translateX(-50%);
  padding: var(--btn-padding-lg);
  border-radius: var(--radius-lg);
  background: var(--color-success-text);
  color: var(--color-surface);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  z-index: var(--z-toast);
  box-shadow: var(--shadow-toast);
  animation: hfb-toast-in var(--transition-slow) var(--ease-out);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rpp-body {
    padding: var(--space-4) var(--space-5);
  }
}
</style>
