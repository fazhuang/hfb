<template>
  <div class="research-page">
    <ResearchPageHeader
      :title="pageTitle"
      :description="project?.context_notes ?? undefined"
      :breadcrumbs="[
        { label: 'Research', to: '/research' },
        { label: pageTitle, to: `/research/${projectId}` },
        { label: '研究工作区' },
      ]"
    >
      <template #actions>
        <!-- CTA hidden during global empty state -->
        <router-link
          v-if="project && !isGlobalEmpty"
          :to="`/research/${project.id}/workflow`"
          class="rwp-action-btn rwp-action-btn--primary"
        >
          开始新研究
        </router-link>
        <router-link
          v-if="project"
          :to="`/research/${project.id}`"
          class="rwp-action-btn rwp-action-btn--secondary"
        >
          查看课题详情
        </router-link>
      </template>
    </ResearchPageHeader>

    <div class="rwp-body">
      <!-- Page-level skeleton -->
      <div v-if="showSkeleton" class="rwp-skeleton" role="status" aria-busy="true" aria-label="正在加载工作区...">
        <div class="rwp-skeleton-section">
          <HfbSkeleton variant="text" width="30%" height="1.2em" />
          <div class="rwp-skeleton-cards">
            <HfbSkeleton variant="rect" height="48px" />
            <HfbSkeleton variant="rect" height="48px" />
            <HfbSkeleton variant="rect" height="48px" />
          </div>
        </div>
        <div class="rwp-skeleton-section">
          <HfbSkeleton variant="text" width="25%" height="1.2em" />
          <div class="rwp-skeleton-cards">
            <HfbSkeleton variant="rect" height="56px" />
            <HfbSkeleton variant="rect" height="56px" />
          </div>
        </div>
        <div class="rwp-skeleton-section">
          <HfbSkeleton variant="text" width="25%" height="1.2em" />
          <div class="rwp-skeleton-cards">
            <HfbSkeleton variant="rect" height="56px" />
            <HfbSkeleton variant="rect" height="56px" />
          </div>
        </div>
      </div>

      <!-- Not found -->
      <EmptyState
        v-else-if="notFound"
        title="课题不存在"
        description="该课题可能已被删除，或您没有访问权限。"
        icon="🔍"
      >
        <template #action>
          <router-link to="/research" class="rwp-back-link"> 返回研究课题列表 </router-link>
        </template>
      </EmptyState>

      <!-- Page error (session gate failure) -->
      <ErrorState
        v-else-if="pageError"
        :title="errorTitle"
        :message="pageErrorMessage"
        @retry="loadSession"
      />

      <!-- All three logical sections failed -->
      <div v-else-if="allSectionsFailed" class="rwp-all-failed">
        <ErrorState
          title="加载失败"
          message="无法加载工作区数据，请检查网络连接后重试。"
          @retry="retryAllSections"
        />
      </div>

      <!-- Global empty → WelcomeCard -->
      <template v-else-if="isGlobalEmpty && project">
        <main class="rwp-main">
          <div class="rwp-welcome-card">
            <div class="rwp-welcome-icon" aria-hidden="true">🚀</div>
            <h2 class="rwp-welcome-title">开始您的研究</h2>
            <p class="rwp-welcome-desc">
              提出研究问题，系统将自动检索古籍文献并生成循证报告。
            </p>
            <div class="rwp-welcome-form">
              <ResearchAssistantEntry :project-id="project.id" mode="inline" />
            </div>
            <router-link
              :to="`/research/${project.id}/workflow`"
              class="rwp-welcome-secondary"
            >
              进入完整工作流
            </router-link>
          </div>
        </main>
      </template>

      <!-- Normal content -->
      <template v-else-if="project">
        <main class="rwp-main">
          <RecentReports
            :project-id="project.id"
            :items="mergedResearch"
            :loading="mergedLoading"
            :error="mergedError"
            :partial-type="mergedPartial"
            @retry="retryMergedResearch"
            @retry-runs="retryRunsOnly"
            @retry-history="retryHistoryOnly"
          />

          <RecentNotes
            :notes="notes"
            :loading="notesLoading"
            :error="notesError"
            @retry="retryNotes"
          />

          <ResearchResources
            :citations="citations"
            :loading="citationsLoading"
            :error="citationsError"
            @retry="retryCitations"
          />
        </main>

        <ResearchAssistantEntry
          v-if="!isGlobalEmpty"
          :project-id="project.id"
          :mode="raeMode"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ResearchWorkspacePage — 研究工作台页面
 *
 * C2-1C: Unified feedback-first loading with skeleton, session gate retry,
 * section partial states, WelcomeCard empty state, and responsive RAE modes.
 *
 * ref: docs/superpowers/specs/2026-08-03-c2-1-workspace-convergence-design.md
 */
import { ref, computed, watch, onBeforeUnmount, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { fetchWithRetry } from '@/utils/fetchWithRetry';
import { toProjectDetail } from '@/types/research';
import type { ResearchProjectDetail, ResearchCitationSummary } from '@/types/research';

import HfbSkeleton from '@/components/common/HfbSkeleton.vue';
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import RecentReports from '@/components/research/RecentReports.vue';
import RecentNotes from '@/components/research/RecentNotes.vue';
import ResearchResources from '@/components/research/ResearchResources.vue';
import ResearchAssistantEntry from '@/components/research/ResearchAssistantEntry.vue';

const route = useRoute();

// ---- Interfaces ----
interface MergedResearchItem {
  id: string;
  type: 'run' | 'activity';
  title: string;
  timestamp: string;
  stepTrace?: Array<{ name: string; status: string }>;
  runId?: string;
  completedAt?: string | null;
  queryType?: string;
  citationCount?: number;
}

interface RunItem {
  run_id: string;
  topic?: string;
  started_at?: string | null;
  completed_at?: string | null;
  step_execution_trace?: Array<{ name: string; status: string }>;
}

interface ActivityItem {
  query_id: string;
  query_text: string;
  query_type: string;
  citation_count: number;
  trace_count: number;
  created_at: string | null;
}

interface NoteItem {
  id: string;
  session_id: string;
  content: string;
  tags?: string | null;
  created_at: string | null;
  updated_at: string | null;
}

// ---- Session state ----
const project = ref<ResearchProjectDetail | null>(null);
const notFound = ref(false);
const pageError = ref(false);
const pageErrorMessage = ref('');

// ---- Section state ----
const mergedResearch = ref<MergedResearchItem[]>([]);
const mergedLoading = ref(false);
const mergedError = ref<string | null>(null);
const mergedPartial = ref<'runs' | 'history' | null>(null);

const notes = ref<NoteItem[]>([]);
const notesLoading = ref(false);
const notesError = ref<string | null>(null);

const citations = ref<ResearchCitationSummary[]>([]);
const citationsLoading = ref(false);
const citationsError = ref<string | null>(null);

// ---- Skeleton state ----
const minSkeletonDone = ref(false);
let skeletonTimer: ReturnType<typeof setTimeout> | null = null;

// ---- Section settled tracking (for skeleton dismissal) ----
const mergedSettled = ref(false);
const notesSettled = ref(false);
const citationsSettled = ref(false);

const allSectionsSettled = computed(
  () => mergedSettled.value && notesSettled.value && citationsSettled.value,
);

const showSkeleton = computed(() => {
  if (notFound.value || pageError.value) return false;
  if (!project.value) return true; // session still loading
  if (!allSectionsSettled.value) return true; // sections still loading
  if (!minSkeletonDone.value) return true; // minimum 300ms not elapsed
  return false;
});

// ---- Derived ----
const projectId = computed(() => String(route.params.projectId || ''));
const pageTitle = computed(() => project.value?.title || '研究工作区');

const errorTitle = computed(() => {
  const msg = pageErrorMessage.value;
  if (msg.includes('403') || msg.includes('Forbidden')) return '权限不足';
  return '加载失败';
});

const isGlobalEmpty = computed(() => {
  if (!allSectionsSettled.value) return false;
  // All three must be success (no partial, no failed)
  if (mergedPartial.value !== null || mergedError.value !== null) return false;
  if (notesError.value !== null) return false;
  if (citationsError.value !== null) return false;
  // All data must be empty
  return (
    mergedResearch.value.length === 0 &&
    notes.value.length === 0 &&
    citations.value.length === 0
  );
});

const allSectionsFailed = computed(() => {
  if (!allSectionsSettled.value) return false;
  if (!mergedError.value && mergedPartial.value === null) return false;
  if (mergedError.value === null && mergedPartial.value !== null) return false; // partial
  if (!notesError.value) return false;
  if (!citationsError.value) return false;
  return !!mergedError.value;
});

// ---- RAE mode ----
const windowWidth = ref(typeof window !== 'undefined' ? window.innerWidth : 1024);
const raeMode = computed<'sidebar' | 'sheet'>(() =>
  windowWidth.value >= 769 ? 'sidebar' : 'sheet',
);

function onResize() {
  windowWidth.value = window.innerWidth;
}

// ---- Request dedup ----
let sessionReqId = 0;
let mergedReqId = 0;
let notesReqId = 0;
let citationsReqId = 0;

// ---- Abort controllers ----
let sessionAbort: AbortController | null = null;
let sectionsAbort: AbortController | null = null;

function abortAll() {
  if (sessionAbort) { sessionAbort.abort(); sessionAbort = null; }
  if (sectionsAbort) { sectionsAbort.abort(); sectionsAbort = null; }
  if (skeletonTimer) { clearTimeout(skeletonTimer); skeletonTimer = null; }
}

function resetSkeletonTimer() {
  if (skeletonTimer) clearTimeout(skeletonTimer);
  minSkeletonDone.value = false;
  skeletonTimer = setTimeout(() => {
    minSkeletonDone.value = true;
  }, 300);
}

// ---- Session gate ----
async function loadSession() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') {
    notFound.value = true;
    return;
  }

  // Cancel everything from prior load
  abortAll();
  sessionAbort = new AbortController();
  const signal = sessionAbort.signal;

  const myReqId = ++sessionReqId;
  ++mergedReqId;
  ++notesReqId;
  ++citationsReqId;

  // Reset states
  notFound.value = false;
  pageError.value = false;
  pageErrorMessage.value = '';
  project.value = null;
  clearAllSectionData();
  mergedSettled.value = false;
  notesSettled.value = false;
  citationsSettled.value = false;
  resetSkeletonTimer();

  try {
    const res = await fetchWithRetry<Record<string, unknown>>(
      `/api/v1/workspace/sessions/${id}`,
      undefined,
      { signal },
    );
    if (myReqId !== sessionReqId || signal.aborted) return;
    const body = res.data as Record<string, unknown>;
    const raw = (body.data ?? body) as Record<string, unknown>;
    project.value = toProjectDetail(raw);

    // Session gate passed — load sections concurrently
    sectionsAbort = new AbortController();
    loadMergedResearch(++mergedReqId, sectionsAbort.signal);
    loadNotes(++notesReqId, sectionsAbort.signal);
    loadCitations(++citationsReqId, sectionsAbort.signal);
  } catch (e: unknown) {
    if (myReqId !== sessionReqId || signal.aborted) return;
    const status = (e as any)?.response?.status;
    if (status === 404) {
      notFound.value = true;
      return;
    }
    if (status === 403) {
      pageError.value = true;
      pageErrorMessage.value = (e as any)?.response?.data?.message || '权限不足';
      return;
    }
    // Network/5xx — fetchWithRetry already exhausted retries
    pageError.value = true;
    pageErrorMessage.value =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '加载失败，请检查网络连接后重试。';
  }
}

function clearAllSectionData() {
  mergedResearch.value = [];
  mergedLoading.value = false;
  mergedError.value = null;
  mergedPartial.value = null;
  notes.value = [];
  notesLoading.value = false;
  notesError.value = null;
  citations.value = [];
  citationsLoading.value = false;
  citationsError.value = null;
}

// ---- Normalize helpers ----
function normalizeRuns(runItems: RunItem[]): MergedResearchItem[] {
  return runItems.map((r) => ({
    id: r.run_id,
    type: 'run' as const,
    title: r.topic || '',
    timestamp: r.completed_at || r.started_at || '',
    stepTrace: r.step_execution_trace ?? [],
    runId: r.run_id,
    completedAt: r.completed_at ?? null,
  }));
}

function normalizeActivities(activityItems: ActivityItem[]): MergedResearchItem[] {
  return activityItems.map((a) => ({
    id: a.query_id,
    type: 'activity' as const,
    title: a.query_text,
    timestamp: a.created_at ?? '',
    queryType: a.query_type,
    citationCount: a.citation_count,
  }));
}

function mergeAndSort(runItems: MergedResearchItem[], activityItems: MergedResearchItem[]): MergedResearchItem[] {
  const merged = [...runItems, ...activityItems];
  merged.sort((a, b) => {
    if (!a.timestamp && !b.timestamp) return 0;
    if (!a.timestamp) return 1;
    if (!b.timestamp) return -1;
    return b.timestamp.localeCompare(a.timestamp);
  });
  return merged.slice(0, 5);
}

// ---- Load merged research ----
async function loadMergedResearch(myReqId: number, signal: AbortSignal) {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;

  mergedLoading.value = true;
  mergedError.value = null;
  mergedPartial.value = null;
  mergedResearch.value = [];
  mergedSettled.value = false;

  let runsOk = false;
  let historyOk = false;
  let runItems: RunItem[] = [];
  let activityItems: ActivityItem[] = [];
  let runsErr = '';
  let historyErr = '';

  const [runsResult, historyResult] = await Promise.allSettled([
    fetchWithRetry(`/api/v4/research/session/${id}/runs`, undefined, { signal, maxRetries: 0 }).catch((e: unknown) => { throw e; }),
    fetchWithRetry(`/api/v4/research/session/${id}/history`, { limit: 5 }, { signal, maxRetries: 0 }).catch((e: unknown) => { throw e; }),
  ]);

  if (myReqId !== mergedReqId || signal.aborted) return;

  if (runsResult.status === 'fulfilled') {
    const body = (runsResult.value.data as any).data ?? runsResult.value.data;
    runItems = (body.runs ?? []) as RunItem[];
    runsOk = true;
  } else {
    const e = runsResult.reason;
    if ((e as any)?.name !== 'AbortError') {
      runsErr = (e as any)?.response?.data?.message || (e as any)?.message || '加载运行记录失败';
    }
  }

  if (historyResult.status === 'fulfilled') {
    const body = (historyResult.value.data as any).data ?? historyResult.value.data;
    activityItems = ((body.history ?? []) as ActivityItem[]).slice(0, 5);
    historyOk = true;
  } else {
    const e = historyResult.reason;
    if ((e as any)?.name !== 'AbortError') {
      historyErr = (e as any)?.response?.data?.message || (e as any)?.message || '加载活动记录失败';
    }
  }

  if (myReqId !== mergedReqId || signal.aborted) return;

  const normalizedRuns = runsOk ? normalizeRuns(runItems) : [];
  const normalizedActivities = historyOk ? normalizeActivities(activityItems) : [];
  mergedResearch.value = mergeAndSort(normalizedRuns, normalizedActivities);

  if (!runsOk && !historyOk) {
    mergedError.value = runsErr || historyErr || '加载研究记录失败';
  } else if (!runsOk && historyOk) {
    mergedPartial.value = 'runs';
  } else if (runsOk && !historyOk) {
    mergedPartial.value = 'history';
  }

  mergedLoading.value = false;
  mergedSettled.value = true;
}

// ---- Load notes ----
async function loadNotes(myReqId: number, signal: AbortSignal) {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;

  notesLoading.value = true;
  notesError.value = null;
  notes.value = [];
  notesSettled.value = false;

  try {
    const { data } = await fetchWithRetry<unknown>(
      `/api/v1/workspace/sessions/${id}/notes`,
      undefined,
      { signal, maxRetries: 0 },
    );
    if (myReqId !== notesReqId || signal.aborted) return;
    const body = (data as any).data ?? data;
    notes.value = (Array.isArray(body) ? body : []) as NoteItem[];
  } catch (e: unknown) {
    if (myReqId !== notesReqId || signal.aborted) return;
    if ((e as any)?.name !== 'AbortError') {
      notesError.value = (e as any)?.response?.data?.message || (e as any)?.message || '加载笔记失败';
    }
  } finally {
    if (myReqId === notesReqId) {
      notesLoading.value = false;
      notesSettled.value = true;
    }
  }
}

// ---- Load citations ----
async function loadCitations(myReqId: number, signal: AbortSignal) {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;

  citationsLoading.value = true;
  citationsError.value = null;
  citations.value = [];
  citationsSettled.value = false;

  try {
    const { data } = await fetchWithRetry<unknown>(
      `/api/v1/workspace/sessions/${id}/citations`,
      undefined,
      { signal, maxRetries: 0 },
    );
    if (myReqId !== citationsReqId || signal.aborted) return;
    const body = (data as any).data ?? data;
    const { toCitationSummary } = await import('@/types/research');
    citations.value = ((Array.isArray(body) ? body : []) as Record<string, unknown>[]).map(
      toCitationSummary,
    );
  } catch (e: unknown) {
    if (myReqId !== citationsReqId || signal.aborted) return;
    if ((e as any)?.name !== 'AbortError') {
      citationsError.value = (e as any)?.response?.data?.message || (e as any)?.message || '加载研究资料失败';
    }
  } finally {
    if (myReqId === citationsReqId) {
      citationsLoading.value = false;
      citationsSettled.value = true;
    }
  }
}

// ---- Section retry (with retry for manual retries) ----
async function retryMergedResearch() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;
  const myReqId = ++mergedReqId;
  const signal = sectionsAbort?.signal ?? new AbortController().signal;

  mergedLoading.value = true;
  mergedError.value = null;
  mergedPartial.value = null;
  mergedResearch.value = [];
  mergedSettled.value = false;

  let runsOk = false;
  let historyOk = false;
  let runItems: RunItem[] = [];
  let activityItems: ActivityItem[] = [];
  let runsErr = '';
  let historyErr = '';

  const [runsResult, historyResult] = await Promise.allSettled([
    fetchWithRetry(`/api/v4/research/session/${id}/runs`, undefined, { signal }),
    fetchWithRetry(`/api/v4/research/session/${id}/history`, { limit: 5 }, { signal }),
  ]);

  if (myReqId !== mergedReqId || signal.aborted) return;

  if (runsResult.status === 'fulfilled') {
    const body = (runsResult.value.data as any).data ?? runsResult.value.data;
    runItems = (body.runs ?? []) as RunItem[];
    runsOk = true;
  } else {
    const e = runsResult.reason;
    if ((e as any)?.name !== 'AbortError') {
      runsErr = (e as any)?.response?.data?.message || (e as any)?.message || '加载运行记录失败';
    }
  }
  if (historyResult.status === 'fulfilled') {
    const body = (historyResult.value.data as any).data ?? historyResult.value.data;
    activityItems = ((body.history ?? []) as ActivityItem[]).slice(0, 5);
    historyOk = true;
  } else {
    const e = historyResult.reason;
    if ((e as any)?.name !== 'AbortError') {
      historyErr = (e as any)?.response?.data?.message || (e as any)?.message || '加载活动记录失败';
    }
  }

  if (myReqId !== mergedReqId || signal.aborted) return;

  mergedResearch.value = mergeAndSort(
    runsOk ? normalizeRuns(runItems) : [],
    historyOk ? normalizeActivities(activityItems) : [],
  );

  if (!runsOk && !historyOk) {
    mergedError.value = runsErr || historyErr || '加载研究记录失败';
  } else if (!runsOk) {
    mergedPartial.value = 'runs';
  } else if (!historyOk) {
    mergedPartial.value = 'history';
  }

  mergedLoading.value = false;
  mergedSettled.value = true;
}

async function retryRunsOnly() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;
  const signal = sectionsAbort?.signal ?? new AbortController().signal;

  mergedPartial.value = null;

  try {
    const { data } = await fetchWithRetry(`/api/v4/research/session/${id}/runs`, undefined, { signal });
    const body = (data as any).data ?? data;
    const runItems = (body.runs ?? []) as RunItem[];
    const normalizedRuns = normalizeRuns(runItems);
    // Re-merge: keep existing history (activity items) from current display
    const historyItems = mergedResearch.value.filter((m) => m.type === 'activity');
    mergedResearch.value = mergeAndSort(normalizedRuns, historyItems);
    mergedError.value = null;
  } catch (e: unknown) {
    if ((e as any)?.name !== 'AbortError') {
      mergedPartial.value = 'runs';
    }
  }
}

async function retryHistoryOnly() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;
  const signal = sectionsAbort?.signal ?? new AbortController().signal;

  mergedPartial.value = null;

  try {
    const { data } = await fetchWithRetry(`/api/v4/research/session/${id}/history`, { limit: 5 }, { signal });
    const body = (data as any).data ?? data;
    const activityItems = ((body.history ?? []) as ActivityItem[]).slice(0, 5);
    const normalizedActivities = normalizeActivities(activityItems);
    const runItems = mergedResearch.value.filter((m) => m.type === 'run');
    mergedResearch.value = mergeAndSort(runItems, normalizedActivities);
    mergedError.value = null;
  } catch (e: unknown) {
    if ((e as any)?.name !== 'AbortError') {
      mergedPartial.value = 'history';
    }
  }
}

async function retryNotes() {
  const signal = sectionsAbort?.signal ?? new AbortController().signal;
  notesSettled.value = false;
  await loadNotes(++notesReqId, signal);
}

async function retryCitations() {
  const signal = sectionsAbort?.signal ?? new AbortController().signal;
  citationsSettled.value = false;
  await loadCitations(++citationsReqId, signal);
}

function retryAllSections() {
  if (!project.value) return;
  sectionsAbort = new AbortController();
  const signal = sectionsAbort.signal;
  mergedSettled.value = false;
  notesSettled.value = false;
  citationsSettled.value = false;
  resetSkeletonTimer();
  loadMergedResearch(++mergedReqId, signal);
  loadNotes(++notesReqId, signal);
  loadCitations(++citationsReqId, signal);
}

// ---- Watch route ----
watch(
  () => route.params.projectId,
  () => {
    loadSession();
  },
);

// ---- Lifecycle ----
onMounted(() => {
  window.addEventListener('resize', onResize);
});

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize);
  abortAll();
  sessionReqId += 1000000;
  mergedReqId += 1000000;
  notesReqId += 1000000;
  citationsReqId += 1000000;
});

loadSession();
</script>

<style scoped>
.research-page {
  min-height: 100%;
}

.rwp-body {
  padding: var(--space-6) var(--space-8);
  display: flex;
  gap: var(--space-6);
}

.rwp-main {
  flex: 1;
  min-width: 0;
}

/* ---- Skeleton ---- */
.rwp-skeleton {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-7);
}

.rwp-skeleton-section {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.rwp-skeleton-cards {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

/* ---- All-failed ---- */
.rwp-all-failed {
  flex: 1;
}

/* ---- WelcomeCard ---- */
.rwp-welcome-card {
  text-align: center;
  padding: var(--space-10) var(--space-6);
  max-width: 480px;
  margin: var(--space-10) auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
}

.rwp-welcome-icon {
  font-size: 2.5rem;
  margin-bottom: var(--space-4);
}

.rwp-welcome-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
}

.rwp-welcome-desc {
  font-size: var(--text-base);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-6);
  line-height: var(--leading-normal);
}

.rwp-welcome-form {
  margin-bottom: var(--space-4);
}

.rwp-welcome-secondary {
  display: inline-flex;
  align-items: center;
  padding: var(--btn-padding-md);
  border: 1px solid var(--color-border);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-md);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
  text-decoration: none;
  transition: all var(--transition-base);
}

.rwp-welcome-secondary:hover {
  background: var(--color-hover);
}

/* ---- Action buttons ---- */
.rwp-action-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--btn-padding-md);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-md);
  font-weight: var(--font-semibold);
  cursor: pointer;
  text-decoration: none;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.rwp-action-btn--primary {
  border: none;
  background: var(--color-accent);
  color: var(--color-surface);
}

.rwp-action-btn--primary:hover {
  background: var(--color-accent-hover);
}

.rwp-action-btn--primary:focus-visible {
  background: var(--color-accent-hover);
}

.rwp-action-btn--secondary {
  border: 1px solid var(--color-border);
  background: var(--color-surface);
  color: var(--color-text-secondary);
}

.rwp-action-btn--secondary:hover {
  background: var(--color-hover);
}

.rwp-action-btn--secondary:focus-visible {
  background: var(--color-hover);
}

/* ---- Back link ---- */
.rwp-back-link {
  display: inline-flex;
  align-items: center;
  padding: var(--btn-padding-md);
  border: 1px solid var(--color-accent);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-md);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
  text-decoration: none;
  transition: all var(--transition-base);
}

.rwp-back-link:hover {
  background: var(--color-accent);
  color: var(--color-surface);
}

.rwp-back-link:focus-visible {
  background: var(--color-accent);
  color: var(--color-surface);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rwp-body {
    flex-direction: column;
    padding: var(--space-4) var(--space-5);
  }
}
</style>
