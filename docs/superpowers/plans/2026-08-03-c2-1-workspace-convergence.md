# C2-1 Workspace 高保真收敛 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ResearchWorkspacePage 及其子组件重构为受控展示架构，合并重复 section，实现统一加载/错误/重试体验。

**Architecture:** Page 层成为唯一数据所有者，4 个子组件纯受控（props in, emit retry out）。两请求聚合为一个逻辑 section"最近研究"。所有数据请求通过 `Promise.allSettled` 并发，骨架屏统一管理。空项目显示引导卡而非 4 个空状态。

**Tech Stack:** Vue 3 `<script setup>` + TypeScript, vitest + @vue/test-utils, vue-router, axios (via `@/api/client`)

## Global Constraints

- 禁止修改研究流程、引文逻辑、后端和 V4
- 禁止修改现有 API 端点签名与返回值结构
- 375×812 与 200% zoom 验证
- 键盘、焦点、加载/空态/错误重试
- 真实登录、真实 API、项目隔离
- 不提取 `formatDate` 为共享 util（触及 8+ 非 workspace 文件）
- 不引入新依赖

---

### Task 0: 创建 fetchWithRetry helper（预约路径）

**Files:**
- Create: `apps/frontend/src/utils/fetchWithRetry.ts`

**Interfaces:**
- Produces: `fetchWithRetry(fetcher, options?): Promise<AxiosResponse>` — Task 3 使用

- [ ] **Step 1: Write fetchWithRetry**

```typescript
// apps/frontend/src/utils/fetchWithRetry.ts
import type { AxiosResponse } from 'axios';

export interface FetchWithRetryOptions {
  maxRetries?: number;
  delays?: number[];
  signal?: AbortSignal;
}

/**
 * Retry a GET fetcher with exponential backoff.
 * Only for idempotent reads. Does NOT retry on 4xx responses.
 */
export async function fetchWithRetry<T = AxiosResponse>(
  fetcher: () => Promise<T>,
  options: FetchWithRetryOptions = {},
): Promise<T> {
  const { maxRetries = 3, delays = [1000, 2000, 4000], signal } = options;

  let lastError: unknown;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    if (signal?.aborted) {
      throw new DOMException('Aborted', 'AbortError');
    }

    try {
      if (attempt > 0) {
        await new Promise<void>((resolve, reject) => {
          const timeout = setTimeout(resolve, delays[attempt - 1] || 1000);
          const onAbort = () => {
            clearTimeout(timeout);
            reject(new DOMException('Aborted', 'AbortError'));
          };
          signal?.addEventListener('abort', onAbort, { once: true });
          // Cleanup if timeout fires normally
          if (signal) {
            setTimeout(() => signal.removeEventListener('abort', onAbort), delays[attempt - 1] || 1000);
          }
        });
      }
      return await fetcher();
    } catch (e: unknown) {
      lastError = e;
      // Don't retry on 4xx — client errors are not transient
      const status = (e as any)?.response?.status;
      if (status && status >= 400 && status < 500) {
        throw e;
      }
    }
  }

  throw lastError;
}
```

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/utils/fetchWithRetry.ts
git commit -m "feat: add fetchWithRetry utility for C2-1"
```

---

### Task 1: RecentNotes.vue → 受控展示组件

**Files:**
- Modify: `apps/frontend/src/components/research/RecentNotes.vue`

**Interfaces:**
- Consumes: `NoteItem` (local interface, id/session_id/content/tags/created_at/updated_at)
- Produces: Props `notes: NoteItem[]`, `loading: boolean`, `error: string | null`; Emits `retry: []`

**Removes:**
- `import api from '@/api/client'`
- `watch(() => props.projectId, ...)` 自动请求
- `fetchNotes()` 方法
- `onBeforeUnmount` reqId 失效代码（页面层统一管理）
- `projectId` prop（不再需要，数据由页面 fetch 后传入）
- `MAX_ITEMS` 常量 + `slice(0, MAX_ITEMS)`（页面层负责截断）

- [ ] **Step 1: Rewrite template — loading/error/data from props**

`apps/frontend/src/components/research/RecentNotes.vue` `<script setup>` 替换为：

```typescript
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

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

defineProps<{
  notes: NoteItem[];
  loading: boolean;
  error: string | null;
}>();

defineEmits<{
  retry: [];
}>();

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
```

Template: LoadingState 使用 `v-if="loading"`（移除 `message` prop，用 `正在加载笔记...`），ErrorState 使用 `v-else-if="error"` + `@retry="$emit('retry')"`，列表使用 `v-else` + `notes.length === 0` 时显示 EmptyState。

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/components/research/RecentNotes.vue
git commit -m "refactor: RecentNotes — controlled display component, no self-fetch"
```

---

### Task 2: ResearchResources.vue → 受控展示组件

**Files:**
- Modify: `apps/frontend/src/components/research/ResearchResources.vue`

**Interfaces:**
- Consumes: `ResearchCitationSummary` from `@/types/research`
- Produces: Props `citations: ResearchCitationSummary[]`, `loading: boolean`, `error: string | null`; Emits `retry: []`

**Removes:**
- `import api from '@/api/client'`
- `watch(() => props.projectId, ...)` 自动请求
- `fetchResources()` 方法
- `onBeforeUnmount` reqId 失效代码
- `projectId` prop
- `MAX_ITEMS` + `slice(0, MAX_ITEMS)`
- `session_id` 过滤逻辑（页面层负责）

- [ ] **Step 1: Rewrite script to controlled props**

```typescript
import { toCitationSummary } from '@/types/research';
import type { ResearchCitationSummary } from '@/types/research';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

defineProps<{
  citations: ResearchCitationSummary[];
  loading: boolean;
  error: string | null;
}>();

defineEmits<{
  retry: [];
}>();

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
```

Template: `v-if="loading"` LoadingState; `v-else-if="error"` ErrorState + `@retry`; `v-else` + `citations.length === 0` EmptyState; else list.

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/components/research/ResearchResources.vue
git commit -m "refactor: ResearchResources — controlled display component, no self-fetch"
```

---

### Task 3: ResearchWorkspacePage.vue — 核心重构（数据并发 + 合并列表 + CTA 互斥）

**Files:**
- Modify: `apps/frontend/src/pages/research/ResearchWorkspacePage.vue`
- Delete: `apps/frontend/src/components/research/ContinueResearchCard.vue`
- Delete: `apps/frontend/src/components/research/RecentResearchActivity.vue`

**Interfaces:**
- Consumes: `toProjectDetail` / `ResearchProjectDetail` from `@/types/research`; `fetchWithRetry` from `@/utils/fetchWithRetry`; `api` from `@/api/client`
- Produces: 页面级 data/loading/error/retry 传递给子组件; `MergedResearchItem[]` 传递给 RecentReports

- [ ] **Step 1: Remove imports of deleted components + add MergedResearchItem type**

```typescript
// Remove these imports:
// import ContinueResearchCard from '@/components/research/ContinueResearchCard.vue';
// import RecentResearchActivity from '@/components/research/RecentResearchActivity.vue';

// Add type:
interface MergedResearchItem {
  id: string;
  type: 'run' | 'activity';
  title: string;
  timestamp: string;
  // type === 'run' 专属:
  stepTrace?: Array<{ name: string; status: string }>;
  runId?: string;
  // type === 'activity' 专属:
  queryType?: string;
  citationCount?: number;
}
```

- [ ] **Step 2: Replace independent loading with unified loadAll()**

Replace `loadSession()` + `loadRuns()` + individual child watches with:

```typescript
// Shared state
const project = ref<ResearchProjectDetail | null>(null);
const sessionLoading = ref(false);
const sessionError = ref<string | null>(null);
const notFound = ref(false);

// Section states
const mergedItems = ref<MergedResearchItem[]>([]);
const researchLoading = ref(false);
const researchError = ref<string | null>(null);
const isPartial = ref(false);       // true when only one of runs/history succeeded
const partialMessage = ref('');     // "活动记录暂不可用" or "运行记录暂不可用"

const notes = ref<NoteItem[]>([]);
const notesLoading = ref(false);
const notesError = ref<string | null>(null);

const citations = ref<ResearchCitationSummary[]>([]);
const citationsLoading = ref(false);
const citationsError = ref<string | null>(null);

// Skeleton state
const showSkeleton = ref(true);
const skeletonMinTimeMs = 300;

// Retry counters per logical section
let researchRetryCount = 0;
let notesRetryCount = 0;
let citationsRetryCount = 0;
const MAX_RETRIES = 3;
const RETRY_DELAYS = [1000, 2000, 4000];

// Check whether page is globally empty AND all sections success
const isGloballyEmpty = computed(() =>
  mergedItems.value.length === 0 &&
  notes.value.length === 0 &&
  citations.value.length === 0 &&
  !researchError.value &&
  !notesError.value &&
  !citationsError.value
);
```

- [ ] **Step 3: Write loadAll() — unified fetch with gate + concurrent sections**

```typescript
let pageReqId = 0;

async function loadAll() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') {
    notFound.value = true;
    showSkeleton.value = false;
    return;
  }

  const myReqId = ++pageReqId;

  // Reset all
  project.value = null;
  notFound.value = false;
  sessionLoading.value = true;
  sessionError.value = null;
  showSkeleton.value = true;

  // Reset sections
  mergedItems.value = []; researchLoading.value = true; researchError.value = null; isPartial.value = false; partialMessage.value = '';
  notes.value = []; notesLoading.value = true; notesError.value = null;
  citations.value = []; citationsLoading.value = true; citationsError.value = null;
  researchRetryCount = 0; notesRetryCount = 0; citationsRetryCount = 0;

  const startTime = Date.now();

  // ---- Step 1: Session gate ----
  try {
    const { data } = await fetchWithRetry(() =>
      api.get(`/api/v1/workspace/sessions/${id}`),
      { maxRetries: 3, delays: RETRY_DELAYS },
    );
    if (myReqId !== pageReqId) return;
    const raw = (data.data ?? data) as Record<string, unknown>;
    project.value = toProjectDetail(raw);
    sessionLoading.value = false;
  } catch (e: unknown) {
    if (myReqId !== pageReqId) return;
    sessionLoading.value = false;
    const status = (e as any)?.response?.status;
    const name = (e as any)?.name;
    const msg = (e as any)?.response?.data?.message || (e as any)?.message || '加载失败，请检查网络连接后重试。';
    if (status === 404) {
      notFound.value = true;
      showSkeleton.value = false;
      return;
    }
    if (status === 403) {
      sessionError.value = msg;
      showSkeleton.value = false;
      return;
    }
    // Network/5xx/timeout/parse error — show retryable error
    sessionError.value = name === 'AbortError' ? '请求已取消' : msg;
    showSkeleton.value = false;
    return;
  }

  // ---- Step 2: Concurrent section fetches ----
  const [runsResult, historyResult, notesResult, citationsResult] = await Promise.allSettled([
    api.get(`/api/v4/research/session/${id}/runs`),
    api.get(`/api/v4/research/session/${id}/history`, { params: { limit: 5 } }),
    api.get(`/api/v1/workspace/sessions/${id}/notes`),
    api.get(`/api/v1/workspace/sessions/${id}/citations`),
  ]);

  if (myReqId !== pageReqId) return;

  // ---- Aggregate research section ----
  const runsOk = runsResult.status === 'fulfilled';
  const historyOk = historyResult.status === 'fulfilled';

  const runItems: MergedResearchItem[] = runsOk
    ? ((runsResult.value.data.data?.runs ?? []) as RunItem[]).map(r => ({
        id: r.run_id,
        type: 'run' as const,
        title: r.topic || '未命名研究',
        timestamp: r.completed_at || r.started_at || '',
        stepTrace: r.step_execution_trace,
        runId: r.run_id,
      }))
    : [];

  const activityItems: MergedResearchItem[] = historyOk
    ? ((historyResult.value.data.data?.history ?? []) as ActivityItem[]).map(a => ({
        id: a.query_id,
        type: 'activity' as const,
        title: a.query_text,
        timestamp: a.created_at || '',
        queryType: a.query_type,
        citationCount: a.citation_count,
      }))
    : [];

  if (runsOk && historyOk) {
    // Both success
    mergedItems.value = [...runItems, ...activityItems].sort(mergedItemSort).slice(0, 5);
    researchError.value = null;
    isPartial.value = false;
    partialMessage.value = '';
  } else if (runsOk && !historyOk) {
    // Partial: runs OK, history failed
    mergedItems.value = runItems.sort(mergedItemSort).slice(0, 5);
    researchError.value = null; // not an error
    isPartial.value = true;
    partialMessage.value = '活动记录暂不可用';
  } else if (!runsOk && historyOk) {
    // Partial: history OK, runs failed
    mergedItems.value = activityItems.sort(mergedItemSort).slice(0, 5);
    researchError.value = null; // not an error
    isPartial.value = true;
    partialMessage.value = '运行记录暂不可用';
  } else {
    // Both failed
    mergedItems.value = [];
    researchError.value = '加载研究记录失败';
    isPartial.value = false;
    partialMessage.value = '';
  }

  researchLoading.value = false;

  // ---- notes section ----
  if (notesResult.status === 'fulfilled') {
    const body = notesResult.value.data.data ?? notesResult.value.data;
    notes.value = (Array.isArray(body) ? (body as NoteItem[]) : []).slice(0, 5);
    notesError.value = null;
  } else {
    notes.value = [];
    notesError.value = '加载笔记失败';
  }
  notesLoading.value = false;

  // ---- citations section ----
  if (citationsResult.status === 'fulfilled') {
    const body = citationsResult.value.data.data ?? citationsResult.value.data;
    citations.value = ((Array.isArray(body) ? body : []) as Record<string, unknown>[])
      .map(toCitationSummary)
      .filter(c => c.session_id === id)
      .slice(0, 5);
    citationsError.value = null;
  } else {
    citations.value = [];
    citationsError.value = '加载研究资料失败';
  }
  citationsLoading.value = false;

  // ---- Skeleton minimum duration ----
  const elapsed = Date.now() - startTime;
  if (elapsed < skeletonMinTimeMs) {
    await new Promise(r => setTimeout(r, skeletonMinTimeMs - elapsed));
  }
  if (myReqId !== pageReqId) return;
  showSkeleton.value = false;
}

function mergedItemSort(a: MergedResearchItem, b: MergedResearchItem): number {
  if (!a.timestamp && !b.timestamp) return 0;
  if (!a.timestamp) return 1;
  if (!b.timestamp) return -1;
  return b.timestamp.localeCompare(a.timestamp);
}
```

- [ ] **Step 4: Write per-section retry functions**

```typescript
async function retryResearch() {
  if (researchRetryCount >= MAX_RETRIES) return;
  researchRetryCount++;
  const id = String(route.params.projectId || '');
  const myReqId = ++pageReqId;

  try {
    // Partial retry: only retry the failed endpoint
    if (isPartial.value) {
      if (partialMessage.value === '活动记录暂不可用') {
        // Retry history only
        const { data } = await api.get(`/api/v4/research/session/${id}/history`, { params: { limit: 5 } });
        if (myReqId !== pageReqId) return;
        const historyItems = ((data.data?.history ?? []) as ActivityItem[]).map(a => ({
          id: a.query_id, type: 'activity' as const, title: a.query_text,
          timestamp: a.created_at || '', queryType: a.query_type, citationCount: a.citation_count,
        }));
        mergedItems.value = [...mergedItems.value, ...historyItems].sort(mergedItemSort).slice(0, 5);
        isPartial.value = false;
        partialMessage.value = '';
      } else {
        // Retry runs only
        const { data } = await api.get(`/api/v4/research/session/${id}/runs`);
        if (myReqId !== pageReqId) return;
        const runItems = ((data.data?.runs ?? []) as RunItem[]).map(r => ({
          id: r.run_id, type: 'run' as const, title: r.topic || '未命名研究',
          timestamp: r.completed_at || r.started_at || '', stepTrace: r.step_execution_trace, runId: r.run_id,
        }));
        mergedItems.value = [...runItems, ...mergedItems.value].sort(mergedItemSort).slice(0, 5);
        isPartial.value = false;
        partialMessage.value = '';
      }
      researchRetryCount = 0; // reset on success
      return;
    }

    // Full retry: both endpoints failed, retry both
    const delay = RETRY_DELAYS[researchRetryCount - 1] || 4000;
    await new Promise(r => setTimeout(r, delay));
    const [runsResult, historyResult] = await Promise.allSettled([
      api.get(`/api/v4/research/session/${id}/runs`),
      api.get(`/api/v4/research/session/${id}/history`, { params: { limit: 5 } }),
    ]);
    if (myReqId !== pageReqId) return;

    // Same aggregation logic as loadAll...
    // (abbreviated — full logic mirrors Step 3 aggregation)
    // If successful: researchError = null, researchRetryCount = 0
    // If still failed: if retryCount >= MAX_RETRIES → show persistent error
  } catch {
    if (myReqId !== pageReqId) return;
    if (researchRetryCount >= MAX_RETRIES) {
      researchError.value = '研究记录加载失败，请稍后重试或联系支持';
    }
  }
}

// retryNotes / retryCitations follow same pattern with their own counters
```

- [ ] **Step 5: Rewrite template — CTA visibility + skeleton + welcome card**

```vue
<template>
  <div class="research-page">
    <ResearchPageHeader
      :title="pageTitle"
      :description="project?.context_notes ?? undefined"
      :breadcrumbs="[...]"
    >
      <template #actions>
        <!-- CTA visible only when NOT empty -->
        <router-link
          v-if="!isGloballyEmpty && !showSkeleton && !notFound && !sessionError"
          :to="`/research/${projectId}/workflow`"
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
      <!-- Session gate errors -->
      <LoadingState v-if="sessionLoading" message="正在加载工作区..." />
      <ErrorState v-else-if="sessionError" :title="errorTitle" :message="sessionErrorMessage" @retry="loadAll" />
      <EmptyState v-else-if="notFound" title="课题不存在" description="..." icon="🔍">
        ...
      </EmptyState>

      <!-- Skeleton -->
      <template v-else-if="showSkeleton">
        <div class="rwp-skeleton"> ... hfb-skeleton blocks ... </div>
      </template>

      <!-- Welcome card: global empty AND all sections success -->
      <template v-else-if="isGloballyEmpty">
        <div class="rwp-welcome">
          ... 引导卡 (inline ResearchAssistantEntry mode='inline') ...
        </div>
      </template>

      <!-- Content layout -->
      <template v-else>
        <main class="rwp-main">
          <RecentReports
            :project-id="projectId"
            :items="mergedItems"
            :loading="researchLoading"
            :error="researchError"
            :is-partial="isPartial"
            :partial-message="partialMessage"
            @retry="retryResearch"
            @retry-partial="retryResearch"
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
          :project-id="projectId"
          mode="sidebar"
        />
      </template>
    </div>
  </div>
</template>
```

- [ ] **Step 6: Add route/inactive watcher**

```typescript
// Watch route param changes — cancel everything and reload
watch(
  () => route.params.projectId,
  () => {
    pageReqId++; // invalidate all in-flight callbacks
    clearTimeout any pending retry timers (use refs)
    researchRetryCount = 0; notesRetryCount = 0; citationsRetryCount = 0;
    loadAll();
  },
);

// Initial load
loadAll();

onBeforeUnmount(() => {
  pageReqId += 1_000_000;
  // Clear all retry timers
});
```

- [ ] **Step 7: Delete ContinueResearchCard.vue and RecentResearchActivity.vue**

```bash
git rm apps/frontend/src/components/research/ContinueResearchCard.vue
git rm apps/frontend/src/components/research/RecentResearchActivity.vue
```

- [ ] **Step 8: Commit**

```bash
git add apps/frontend/src/pages/research/ResearchWorkspacePage.vue
git commit -m "refactor: ResearchWorkspacePage — unified fetch, CTA gating, no ContinueResearchCard/RecentResearchActivity"
```

---

### Task 4: RecentReports.vue — 合并列表 + 标题 + partial 状态

**Files:**
- Modify: `apps/frontend/src/components/research/RecentReports.vue`

**Interfaces:**
- Consumes: `MergedResearchItem` (from page via props)
- Produces: Props `projectId: string`, `items: MergedResearchItem[]`, `loading: boolean`, `error: string | null`, `isPartial: boolean`, `partialMessage: string`; Emits `retry: []`, `retryPartial: []`

**Removes:**
- `RunItem` 本地接口（替换为 `MergedResearchItem`）
- `MAX_ITEMS` + `slice(0, MAX_ITEMS)`（页面层负责）
- `displayRuns` computed（替换为直接使用 `props.items`）
- 排序逻辑（页面层负责）
- `hasReportArtifact` / `hasResultRoute` — 页面层已过滤，组件仅展示

- [ ] **Step 1: Rewrite props + template**

Section heading: `"最近研究"`

Template 新增 partial 提示行:
```vue
<p v-if="isPartial && items.length === 0" class="rr-partial-hint">
  {{ partialMessage }}
  <button class="rr-partial-retry" @click="$emit('retryPartial')">重试</button>
</p>
<p v-else-if="isPartial" class="rr-partial-hint">
  {{ partialMessage }}
  <button class="rr-partial-retry" @click="$emit('retryPartial')">重试</button>
</p>
```

样式:
```css
.rr-partial-hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-2);
}

.rr-partial-retry {
  border: none;
  background: none;
  color: var(--color-accent);
  cursor: pointer;
  font-size: var(--text-xs);
  text-decoration: underline;
  padding: 0;
  margin-left: var(--space-1);
}
```

List items: iterate `props.items`, render differently by `item.type`:
- `type === 'run'`: show title, step badges, completed_at, view link
- `type === 'activity'`: show type badge, query_text, citation count, timestamp

- [ ] **Step 2: Commit**

```bash
git add apps/frontend/src/components/research/RecentReports.vue
git commit -m "refactor: RecentReports — merged research list, partial state, controlled props"
```

---

### Task 5: ResearchAssistantEntry.vue — mode prop + sheet a11y

**Files:**
- Modify: `apps/frontend/src/components/research/ResearchAssistantEntry.vue`

**Interfaces:**
- Consumes: `useRouter` from `vue-router`
- Produces: Props `projectId: string`, `mode: 'inline' | 'sidebar' | 'sheet'`

- [ ] **Step 1: Add mode prop + three render paths**

```typescript
const props = defineProps<{
  projectId: string;
  mode: 'inline' | 'sidebar' | 'sheet';
}>();
```

**mode='inline'**: Render as `<div class="rae-inline">` — input + button inline, no aside wrapper, no sidebar styling. For embedding in welcome card.

**mode='sidebar'**: Current sidebar rendering. Add toggle button with `aria-expanded` + `aria-controls`. Default collapsed.

```vue
<button
  class="rae-toggle"
  :aria-expanded="isOpen"
  aria-controls="rae-sidebar-panel"
  @click="isOpen = !isOpen"
>
  AI 助手
</button>
<aside v-if="isOpen" id="rae-sidebar-panel" class="rae-sidebar">...</aside>
```

**mode='sheet'**: Mobile slide-up panel.

```vue
<template v-if="mode === 'sheet'">
  <button
    class="rae-toggle"
    :aria-expanded="isOpen"
    aria-controls="rae-sheet-panel"
    @click="openSheet"
  >
    AI 助手
  </button>
  <Teleport to="body">
    <div
      v-if="isOpen"
      class="rae-backdrop"
      @click="closeSheet"
    />
    <div
      v-if="isOpen"
      id="rae-sheet-panel"
      ref="sheetRef"
      role="dialog"
      aria-modal="true"
      aria-label="AI 研究助手"
      class="rae-sheet"
      @keydown="trapFocus"
    >
      <form class="rae-form" @submit.prevent="onSubmit"> ... </form>
    </div>
  </Teleport>
</template>
```

- [ ] **Step 2: Implement sheet a11y: focus trap, Escape, body scroll lock**

```typescript
const isOpen = ref(false);
const sheetRef = ref<HTMLElement | null>(null);
let previousActiveElement: HTMLElement | null = null;

function openSheet() {
  previousActiveElement = document.activeElement as HTMLElement;
  isOpen.value = true;
  document.body.style.overflow = 'hidden';
  nextTick(() => {
    const input = sheetRef.value?.querySelector('input');
    input?.focus();
  });
}

function closeSheet() {
  isOpen.value = false;
  document.body.style.overflow = '';
  previousActiveElement?.focus();
}

function trapFocus(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    closeSheet();
    return;
  }
  if (e.key !== 'Tab') return;
  const panel = sheetRef.value;
  if (!panel) return;
  const focusable = panel.querySelectorAll<HTMLElement>(
    'input, button, [tabindex]:not([tabindex="-1"])'
  );
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (!first || !last) return;
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}
```

Sheet styles:
```css
.rae-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 100;
}

.rae-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-height: 70vh;
  background: var(--color-surface);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  z-index: 101;
  padding: var(--space-4);
  transform: translateY(100%);
  animation: rae-slide-up 300ms ease forwards;
  overflow-y: auto;
}

@keyframes rae-slide-up {
  to { transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .rae-sheet {
    animation: none;
    transform: translateY(0);
  }
}
```

- [ ] **Step 3: Commit**

```bash
git add apps/frontend/src/components/research/ResearchAssistantEntry.vue
git commit -m "feat: ResearchAssistantEntry — mode prop, sheet a11y, sidebar toggle"
```

---

### Task 6: ResearchWorkspacePage.vue — 骨架屏 + welcome card 样式

**Files:**
- Modify: `apps/frontend/src/pages/research/ResearchWorkspacePage.vue`

- [ ] **Step 1: Add skeleton markup to template**

```vue
<template v-else-if="showSkeleton">
  <div class="rwp-skeleton">
    <!-- Header row -->
    <div class="hfb-skeleton hfb-skeleton--wave hfb-skeleton--text" style="width: 40%; height: 24px; margin-bottom: var(--space-4);"></div>
    <!-- Section 1 -->
    <div class="hfb-skeleton hfb-skeleton--wave hfb-skeleton--text" style="width: 20%; height: 18px; margin-bottom: var(--space-3);"></div>
    <div class="hfb-skeleton hfb-skeleton--wave hfb-skeleton--rect" style="width: 100%; height: 60px; margin-bottom: var(--space-2);"></div>
    <div class="hfb-skeleton hfb-skeleton--wave hfb-skeleton--rect" style="width: 100%; height: 60px; margin-bottom: var(--space-2);"></div>
    <div class="hfb-skeleton hfb-skeleton--wave hfb-skeleton--rect" style="width: 100%; height: 40px; margin-bottom: var(--space-6);"></div>
    <!-- Section 2 -->
    <div class="hfb-skeleton hfb-skeleton--wave hfb-skeleton--text" style="width: 20%; height: 18px; margin-bottom: var(--space-3);"></div>
    <div class="hfb-skeleton hfb-skeleton--wave hfb-skeleton--rect" style="width: 100%; height: 40px;"></div>
  </div>
</template>
```

- [ ] **Step 2: Add welcome card markup**

```vue
<template v-else-if="isGloballyEmpty">
  <div class="rwp-welcome">
    <span class="rwp-welcome-icon">🚀</span>
    <h2 class="rwp-welcome-heading">开始您的研究</h2>
    <p class="rwp-welcome-desc">
      提出研究问题，系统将自动检索古籍文献并生成循证报告。
    </p>
    <form class="rwp-welcome-form" @submit.prevent="startFromWelcome">
      <input
        v-model.trim="welcomeQuestion"
        type="text"
        class="rwp-welcome-input"
        placeholder="输入您的研究问题..."
        autocomplete="off"
      />
      <button
        type="submit"
        class="rwp-welcome-submit"
        :disabled="!welcomeQuestion"
      >
        开始研究
      </button>
    </form>
    <span class="rwp-welcome-divider">或</span>
    <router-link
      :to="`/research/${projectId}/workflow`"
      class="rwp-welcome-secondary"
    >
      进入完整工作流
    </router-link>
  </div>
</template>
```

- [ ] **Step 3: Add welcome card styles**

```css
.rwp-welcome {
  max-width: 480px;
  margin: var(--space-10) auto;
  text-align: center;
  padding: var(--space-8) var(--space-6);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
}

.rwp-welcome-icon { font-size: 2.5rem; display: block; margin-bottom: var(--space-4); }
.rwp-welcome-heading { font-size: var(--text-xl); font-weight: var(--font-bold); margin: 0 0 var(--space-2); color: var(--color-text-primary); }
.rwp-welcome-desc { font-size: var(--text-base); color: var(--color-text-muted); margin: 0 0 var(--space-6); line-height: var(--leading-normal); }
.rwp-welcome-form { display: flex; gap: var(--space-2); margin-bottom: var(--space-4); }
.rwp-welcome-input { flex: 1; padding: var(--space-2-5) var(--space-3); border: 1px solid var(--color-border); border-radius: var(--radius-lg); font-size: var(--text-base); }
.rwp-welcome-input:focus { outline: none; border-color: var(--color-accent); box-shadow: var(--focus-ring-sm); }
.rwp-welcome-submit { padding: var(--space-2-5) var(--space-4); border: none; border-radius: var(--radius-lg); font-size: var(--text-base); font-weight: var(--font-semibold); background: var(--color-accent); color: var(--color-surface); cursor: pointer; white-space: nowrap; }
.rwp-welcome-submit:disabled { opacity: 0.5; cursor: not-allowed; }
.rwp-welcome-divider { display: block; font-size: var(--text-xs); color: var(--color-text-muted); margin-bottom: var(--space-4); }
.rwp-welcome-secondary { display: inline-block; padding: var(--space-2) var(--space-4); border: 1px solid var(--color-border); border-radius: var(--radius-lg); font-size: var(--text-base); color: var(--color-text-secondary); text-decoration: none; }
.rwp-welcome-secondary:hover { background: var(--color-hover); }

/* Mobile: 375px */
@media (max-width: 768px) {
  .rwp-welcome {
    margin: var(--space-6) var(--space-4);
    padding: var(--space-6) var(--space-4);
  }
  .rwp-welcome-form {
    flex-direction: column;
  }
}
```

- [ ] **Step 4: Add welcome card logic to `<script setup>`**

```typescript
const welcomeQuestion = ref('');

function startFromWelcome() {
  const q = welcomeQuestion.value;
  if (!q) return;
  try {
    sessionStorage.setItem(`hfb.research.${projectId.value}.pending-question`, q);
  } catch { /* unavailable */ }
  router.push(`/research/${projectId.value}/workflow`);
}
```

- [ ] **Step 5: Commit**

```bash
git add apps/frontend/src/pages/research/ResearchWorkspacePage.vue
git commit -m "feat: ResearchWorkspacePage — skeleton screen + welcome card for empty projects"
```

---

### Task 7: 测试 — 删除旧 stub + 添加新用例

**Files:**
- Modify: `apps/frontend/src/__tests__/research-workspace.test.ts`

**Removes:**
- `ContinueResearchCard` stub 和相关测试（test #821）
- `RecentResearchActivity` stub 和相关测试（test #1112）
- `RecentNotes` / `ResearchResources` 旧测试（test #1184, #1239 — 它们 watch projectId 的测试在受控模式失效）

**Adds:** 36 条新测试 (Batch A–G from spec §7)

- [ ] **Step 1: Remove old stub references from `setupDefaultMocks` and stubs**

Remove lines referencing `ContinueResearchCard` and `RecentResearchActivity` from the default stub map used in `mount()` calls throughout the file.

- [ ] **Step 2: Write Batch A — CTA visibility (tests 1-5)**

```typescript
describe('CTA visibility', () => {
  it('hides "开始新研究" in header when project is empty', async () => {
    setupDefaultMocks(makeSession(), [], []); // empty runs, history, notes, citations
    // mount, verify rwp-action-btn--primary not rendered
  });

  it('shows "开始新研究" in header when project has data', async () => {
    setupDefaultMocks(makeSession(), [makeRun()]); // has runs
    // mount, verify rwp-action-btn--primary is rendered
  });

  it('renders welcome card when globally empty', async () => {
    setupDefaultMocks(makeSession(), [], []); // all empty
    // mount, verify .rwp-welcome exists
  });

  it('does not render welcome card when project has data', async () => {
    setupDefaultMocks(makeSession(), [makeRun()]);
    // mount, verify .rwp-welcome does not exist
  });

  it('welcome card link points to correct workflow route', async () => {
    setupDefaultMocks(makeSession(), [], []);
    // mount, verify routerLink to /research/${PROJ_A}/workflow
  });
});
```

- [ ] **Step 3: Write Batch B — controlled subcomponent contract (tests 6-10)**

```typescript
describe('Controlled subcomponents', () => {
  it('RecentNotes does NOT call API on its own', async () => {
    // Mount RecentNotes directly with props, verify mockApiGet not called
  });

  it('ResearchResources does NOT call API on its own', async () => {
    // Mount ResearchResources directly with props, verify mockApiGet not called
  });

  it('RecentNotes renders from props (loading)', async () => {
    // Mount with notes=[], loading=true → verify LoadingState rendered
  });

  it('RecentNotes renders from props (data)', async () => {
    // Mount with notes=[makeNote()], loading=false → verify content rendered
  });

  it('RecentNotes emits retry from error state', async () => {
    // Mount with error='test err', click retry → verify emit
  });
});
```

- [ ] **Step 4: Write Batch C — merged sort + truncate (tests 11-13)**

```typescript
describe('Merged research items', () => {
  it('merges runs and activities into max 5 items', async () => {
    // setup runs=3, history=3 → verify mergedItems.length <= 5
  });

  it('sorts by timestamp DESC, empties last', async () => {
    // runs: [{completed_at:'2026-01'},{completed_at:''},{completed_at:'2026-03'}]
    // verify order
  });

  it('normalizes run and activity fields correctly', async () => {
    // verify MergedResearchItem.type, title, timestamp for both types
  });
});
```

- [ ] **Step 5: Write Batch D — gate + concurrent + stale guard (tests 14-17)**

```typescript
describe('Session gate and concurrency', () => {
  it('does not fire section requests after session 404', async () => {
    // mock session 404 → wait → count mockApiGet calls, should be 1 (session only)
  });

  it('does not fire section requests after session 403', async () => {
    // mock session 403 → same as above
  });

  it('stale response from old projectId does not overwrite new', async () => {
    // existing test adapted: navigate A→B quickly, verify B's data shown
  });

  it('no state writes after unmount', async () => {
    // existing test adapted
  });
});
```

- [ ] **Step 6: Write Batch D-2 — session retry/recovery (tests 18-22)**

```typescript
describe('Session gate recovery', () => {
  it('does not fire section requests when session returns 500', async () => {
    // mock session 500 → wait → count mockApiGet === 1
  });

  it('enters auto-retry on session network error', async () => {
    // mock session: first 2 fail ERR_NETWORK, 3rd success
    // verify session finally loads, sections are fetched
  });

  it('shows reload button after auto-retry exhausted', async () => {
    // mock session: always ECONNABORTED
    // verify error state with retry button visible after 3 attempts
  });

  it('cancels session retry timers on project switch', async () => {
    // start load on A (slow session), navigate to B → verify B loads correctly
  });

  it('cancels session retry timers on unmount', async () => {
    // mount, immediately unmount → no state writes after unmount
  });
});
```

- [ ] **Step 7: Write Batch E — skeleton (tests 23-25)**

```typescript
describe('Skeleton screen', () => {
  it('renders skeleton during initial load', async () => {
    // mount → verify .rwp-skeleton exists before settled
  });

  it('holds skeleton for minimum 300ms', async () => {
    // mock fast responses (<300ms) → verify skeleton visible at 200ms, gone by 350ms
  });

  it('switches immediately when responses take >300ms', async () => {
    // mock slow responses (500ms) → verify skeleton gone right after settled
  });
});
```

- [ ] **Step 8: Write Batch F — partial + retry + all-failed (tests 26-32)**

```typescript
describe('Partial failure and retry', () => {
  it('shows data from successful sections when one section fails', async () => {
    // mock notes reject, runs/history/citations succeed
    // verify RecentReports rendered, error banner for notes
  });

  it('per-section retry button is visible and triggers refetch', async () => {
    // mock notes reject → click retry → verify API called again
  });

  it('shows persistent error after 3 retry failures', async () => {
    // mock notes always reject → trigger 3 retries → verify "联系支持" text
  });

  it('resets retry counter on project switch', async () => {
    // trigger 2 retries on A, switch to B → verify counters reset
  });

  it('shows summary error (not welcome card) when all sections fail', async () => {
    // reject runs, history, notes, citations → verify welcome card NOT rendered
  });

  it('shows partial hint and retry when runs succeed but history fails', async () => {
    // runs=[makeRun()], history reject, notes/citations empty
    // verify: partial hint visible, welcome card NOT rendered, retry button for history
  });

  it('partial retry only re-fetches the failed endpoint', async () => {
    // runs success, history reject → click partial retry
    // verify: only history API called, not runs
  });
});
```

- [ ] **Step 9: Write Batch G — deleted component checks (tests 33-36)**

```typescript
describe('Deleted component cleanup', () => {
  it('does not import ContinueResearchCard', async () => {
    const src = await import('@/pages/research/ResearchWorkspacePage.vue');
    // verify ContinueResearchCard not in component list
  });

  it('does not import RecentResearchActivity', async () => {
    // same as above
  });

  it('does not render ContinueResearchCard markup', async () => {
    // mount, verify .crc-section does not exist
  });

  it('does not render RecentResearchActivity markup', async () => {
    // mount, verify .rra-section does not exist
  });
});
```

- [ ] **Step 10: Run tests to verify (initial failure expected for new tests)**

```bash
cd apps/frontend && npx vitest run src/__tests__/research-workspace.test.ts 2>&1 | tail -30
```

- [ ] **Step 11: Commit**

```bash
git add apps/frontend/src/__tests__/research-workspace.test.ts
git commit -m "test: C2-1 workspace — 36 new test cases, remove deleted component tests"
```

---

### Task 8: 运行 typecheck + lint + 全部测试

**Files:**
- No new files — validation only

- [ ] **Step 1: Run vue-tsc**

```bash
cd apps/frontend && npx vue-tsc --noEmit 2>&1 | tail -20
```
Expected: zero errors.

- [ ] **Step 2: Run vitest full suite**

```bash
cd apps/frontend && npx vitest run 2>&1 | tail -30
```
Expected: ALL GREEN. Fix any failures.

- [ ] **Step 3: Run existing E2E tests for workspace**

```bash
cd apps/frontend && npx playwright test --grep "workspace" 2>&1 | tail -20
```

- [ ] **Step 4: Fix any issues, re-run until green, commit**

```bash
git commit -am "chore: C2-1 — typecheck + test suite green"
```

---

### Task 9: E2E 手动验证清单

**No file changes.** Manual verification against real API.

- [ ] **Step 1: 空项目引导卡** — login → create new empty session → navigate to workspace → verify welcome card renders → type question → click "开始研究" → verify navigated to workflow

- [ ] **Step 2: 非空项目** — navigate to workspace with data → verify welcome card hidden → sections display → "开始新研究" visible in header

- [ ] **Step 3: 375×812 viewport** — resize to 375×812 → verify sidebar hidden → click AI 助手 toggle → verify sheet slides up → Escape to close → focus returns to toggle

- [ ] **Step 4: 200% zoom** — set zoom to 200% → verify content does not overflow → verify skeleton does not break

- [ ] **Step 5: Keyboard** — Tab through all interactive elements → Enter/Space activate buttons → sidebar toggle responds to keyboard

- [ ] **Step 6: Error recovery** — disconnect network → navigate to workspace → verify skeleton → error state → reconnect → click retry → verify content loads

- [ ] **Step 7: Project isolation** — open project A in tab 1, project B in tab 2 → verify each shows correct data
