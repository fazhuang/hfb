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
        <router-link
          v-if="project"
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
      <!-- Page-level states -->
      <LoadingState v-if="pageLoading" message="正在加载工作区..." />

      <ErrorState
        v-else-if="pageError"
        :title="errorTitle"
        :message="pageErrorMessage"
        @retry="loadSession"
      />

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

      <!-- Main content -->
      <template v-else-if="project">
        <main class="rwp-main">
          <!-- 1. Recent Research (merged runs + history) -->
          <RecentReports
            :project-id="project.id"
            :items="mergedResearch"
            :loading="mergedLoading"
            :error="mergedError"
            @retry="retryMergedResearch"
          />

          <!-- 2. Recent Notes -->
          <RecentNotes
            :notes="notes"
            :loading="notesLoading"
            :error="notesError"
            @retry="retryNotes"
          />

          <!-- 3. Research Resources -->
          <ResearchResources
            :citations="citations"
            :loading="citationsLoading"
            :error="citationsError"
            @retry="retryCitations"
          />
        </main>

        <!-- 4. AI Research Assistant sidebar -->
        <ResearchAssistantEntry :project-id="project.id" />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ResearchWorkspacePage — 研究工作台页面
 *
 * Page is the single data owner for all sections:
 *   1. RecentReports (merged runs + history) — controlled via props
 *   2. RecentNotes — controlled via props
 *   3. ResearchResources — controlled via props
 *   4. ResearchAssistantEntry — sidebar
 *
 * Route param :projectId === ResearchSession.id
 *
 * ref: docs/superpowers/specs/2026-08-03-c2-1-workspace-convergence-design.md
 */
import { ref, computed, watch, onBeforeUnmount } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/api/client';
import { toProjectDetail } from '@/types/research';
import type { ResearchProjectDetail, ResearchCitationSummary } from '@/types/research';

import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import RecentReports from '@/components/research/RecentReports.vue';
import RecentNotes from '@/components/research/RecentNotes.vue';
import ResearchResources from '@/components/research/ResearchResources.vue';
import ResearchAssistantEntry from '@/components/research/ResearchAssistantEntry.vue';

const route = useRoute();

// ---- Merged research item ----
interface MergedResearchItem {
  id: string;
  type: 'run' | 'activity';
  title: string;
  timestamp: string;
  // run-specific
  stepTrace?: Array<{ name: string; status: string }>;
  runId?: string;
  completedAt?: string | null;
  // activity-specific
  queryType?: string;
  citationCount?: number;
}

// ---- Run item from API ----
interface RunItem {
  run_id: string;
  topic?: string;
  started_at?: string | null;
  completed_at?: string | null;
  step_execution_trace?: Array<{ name: string; status: string }>;
}

// ---- Activity item from API ----
interface ActivityItem {
  query_id: string;
  query_text: string;
  query_type: string;
  citation_count: number;
  trace_count: number;
  created_at: string | null;
}

// ---- Note item ----
interface NoteItem {
  id: string;
  session_id: string;
  entity_type?: string | null;
  entity_id?: string | null;
  content: string;
  tags?: string | null;
  created_at: string | null;
  updated_at: string | null;
}

// ---- Session detail (single source of truth) ----
const project = ref<ResearchProjectDetail | null>(null);
const pageLoading = ref(false);
const pageError = ref(false);
const pageErrorMessage = ref('');
const notFound = ref(false);

// ---- Merged research state ----
const mergedResearch = ref<MergedResearchItem[]>([]);
const mergedLoading = ref(false);
const mergedError = ref<string | null>(null);

// ---- Notes state ----
const notes = ref<NoteItem[]>([]);
const notesLoading = ref(false);
const notesError = ref<string | null>(null);

// ---- Citations state ----
const citations = ref<ResearchCitationSummary[]>([]);
const citationsLoading = ref(false);
const citationsError = ref<string | null>(null);

// ---- Derived ----
const projectId = computed(() => String(route.params.projectId || ''));
const pageTitle = computed(() => project.value?.title || '研究工作区');

const errorTitle = computed(() => {
  const msg = pageErrorMessage.value;
  if (msg.includes('403') || msg.includes('Forbidden')) {
    return '权限不足';
  }
  return '加载失败';
});

// ---- Request dedup (per-section reqIds) ----
// Each section owns its own reqId so retrying one does not invalidate
// in-flight requests from sibling sections.
let sessionReqId = 0;
let mergedReqId = 0;
let notesReqId = 0;
let citationsReqId = 0;

// ---- Session gate ----
async function loadSession() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') {
    notFound.value = true;
    return;
  }

  const myReqId = ++sessionReqId;

  // Immediately invalidate all in-flight section requests from any prior project.
  // Must happen BEFORE the async session fetch so old section responses
  // cannot write back during the window between project switch and session resolve.
  ++mergedReqId;
  ++notesReqId;
  ++citationsReqId;

  pageLoading.value = true;
  pageError.value = false;
  pageErrorMessage.value = '';
  notFound.value = false;
  project.value = null;

  // Clear all section data on session reload
  clearAllSectionData();

  try {
    const { data } = await api.get(`/api/v1/workspace/sessions/${id}`);
    if (myReqId !== sessionReqId) return;
    const raw = (data.data ?? data) as Record<string, unknown>;
    project.value = toProjectDetail(raw);

    // Session gate passed — load all section data concurrently
    // Use fresh reqIds (already bumped above; bump again for clean generation)
    loadMergedResearch(++mergedReqId);
    loadNotes(++notesReqId);
    loadCitations(++citationsReqId);
  } catch (e: unknown) {
    if (myReqId !== sessionReqId) return;
    const status = (e as any)?.response?.status;
    const msg =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '加载失败，请检查网络连接后重试。';
    if (status === 404) {
      notFound.value = true;
    } else {
      pageError.value = true;
      pageErrorMessage.value = msg;
    }
  } finally {
    if (myReqId === sessionReqId) {
      pageLoading.value = false;
    }
  }
}

// ---- Clear all section data ----
function clearAllSectionData() {
  mergedResearch.value = [];
  mergedLoading.value = false;
  mergedError.value = null;
  notes.value = [];
  notesLoading.value = false;
  notesError.value = null;
  citations.value = [];
  citationsLoading.value = false;
  citationsError.value = null;
}

// ---- Merge runs + history into MergedResearchItem[] ----
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

// ---- Load merged research (runs + history, concurrent) ----
async function loadMergedResearch(myReqId: number) {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;

  mergedLoading.value = true;
  mergedError.value = null;
  mergedResearch.value = [];

  let runsOk = false;
  let historyOk = false;
  let runItems: RunItem[] = [];
  let activityItems: ActivityItem[] = [];
  let runsErr = '';
  let historyErr = '';

  // fetch runs and history concurrently
  const [runsResult, historyResult] = await Promise.allSettled([
    api.get(`/api/v4/research/session/${id}/runs`),
    api.get(`/api/v4/research/session/${id}/history`, { params: { limit: 5 } }),
  ]);

  if (myReqId !== mergedReqId) return;

  if (runsResult.status === 'fulfilled') {
    const body = runsResult.value.data.data ?? runsResult.value.data;
    runItems = (body.runs ?? []) as RunItem[];
    runsOk = true;
  } else {
    runsErr = (runsResult.reason as any)?.response?.data?.message ||
      (runsResult.reason as any)?.message || '加载运行记录失败';
  }

  if (historyResult.status === 'fulfilled') {
    const body = historyResult.value.data.data ?? historyResult.value.data;
    activityItems = ((body.history ?? []) as ActivityItem[]).slice(0, 5);
    historyOk = true;
  } else {
    historyErr = (historyResult.reason as any)?.response?.data?.message ||
      (historyResult.reason as any)?.message || '加载活动记录失败';
  }

  const normalizedRuns = runsOk ? normalizeRuns(runItems) : [];
  const normalizedActivities = historyOk ? normalizeActivities(activityItems) : [];
  mergedResearch.value = mergeAndSort(normalizedRuns, normalizedActivities);

  if (!runsOk && !historyOk) {
    mergedError.value = runsErr || historyErr || '加载研究记录失败';
  }

  mergedLoading.value = false;
}

// ---- Load notes ----
async function loadNotes(myReqId: number) {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;

  notesLoading.value = true;
  notesError.value = null;
  notes.value = [];

  try {
    const { data } = await api.get(`/api/v1/workspace/sessions/${id}/notes`);
    if (myReqId !== notesReqId) return;
    const body = data.data ?? data;
    notes.value = (Array.isArray(body) ? body : []) as NoteItem[];
  } catch (e: unknown) {
    if (myReqId !== notesReqId) return;
    const msg = (e as any)?.response?.data?.message || (e as any)?.message || '加载笔记失败';
    notesError.value = msg;
  } finally {
    if (myReqId === notesReqId) {
      notesLoading.value = false;
    }
  }
}

// ---- Load citations ----
async function loadCitations(myReqId: number) {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;

  citationsLoading.value = true;
  citationsError.value = null;
  citations.value = [];

  try {
    const { data } = await api.get(`/api/v1/workspace/sessions/${id}/citations`);
    if (myReqId !== citationsReqId) return;
    const body = data.data ?? data;
    const { toCitationSummary } = await import('@/types/research');
    citations.value = ((Array.isArray(body) ? body : []) as Record<string, unknown>[]).map(
      toCitationSummary,
    );
  } catch (e: unknown) {
    if (myReqId !== citationsReqId) return;
    const msg = (e as any)?.response?.data?.message || (e as any)?.message || '加载研究资料失败';
    citationsError.value = msg;
  } finally {
    if (myReqId === citationsReqId) {
      citationsLoading.value = false;
    }
  }
}

// ---- Retry wrappers — bump section reqId on manual retry ----
function retryMergedResearch() {
  loadMergedResearch(++mergedReqId);
}
function retryNotes() {
  loadNotes(++notesReqId);
}
function retryCitations() {
  loadCitations(++citationsReqId);
}

// ---- Watch route param changes ----
watch(
  () => route.params.projectId,
  () => {
    loadSession();
  },
);

// ---- Lifecycle ----
loadSession();

onBeforeUnmount(() => {
  // Invalidate all in-flight requests permanently
  sessionReqId += 1000000;
  mergedReqId += 1000000;
  notesReqId += 1000000;
  citationsReqId += 1000000;
});
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

/* ---- Sidebar (ResearchAssistantEntry wrapper) ---- */
.rwp-main + :deep(.rae-sidebar),
.rwp-body > :deep(.rae-sidebar) {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid var(--color-border);
  padding-left: var(--space-6);
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

  .rwp-main + :deep(.rae-sidebar),
  .rwp-body > :deep(.rae-sidebar) {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--color-border);
    padding-left: 0;
    padding-top: var(--space-4);
  }
}
</style>
