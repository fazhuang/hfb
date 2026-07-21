<template>
  <div class="research-page">
    <ResearchPageHeader
      :title="pageTitle"
      :breadcrumbs="[
        { label: 'Research', to: '/research' },
        { label: session?.title || '加载中...', to: `/research/${projectId}` },
        { label: '研究工作流' },
      ]"
    />

    <div class="rwf-body">
      <!-- ============================================================ -->
      <!-- Page-level states -->
      <!-- ============================================================ -->
      <LoadingState
        v-if="sessionLoading"
        message="正在加载研究课题..."
      />

      <EmptyState
        v-else-if="notFound"
        title="课题不存在"
        description="该课题可能已被删除，或您没有访问权限。"
        icon="🔍"
      >
        <template #action>
          <router-link to="/research" class="rwf-back-link">
            返回研究课题列表
          </router-link>
        </template>
      </EmptyState>

      <ErrorState
        v-else-if="sessionError"
        title="加载失败"
        :message="sessionError"
        @retry="loadSession"
      />

      <!-- ============================================================ -->
      <!-- Main workflow content -->
      <!-- ============================================================ -->
      <template v-else-if="session">
        <!-- Step navigation -->
        <WorkflowStepNavigation
          :steps="navSteps"
          :current-index="currentStepIndex"
          :submitting="submitting"
        />

        <!-- Error banner -->
        <div
          v-if="submitError"
          ref="errorBannerRef"
          class="rwf-error-banner"
          role="alert"
          tabindex="-1"
        >
          <div class="rwf-error-banner-content">
            <strong class="rwf-error-banner-title">
              {{ submitStatusCode ? errorTitleForCode(submitStatusCode) : '工作流错误' }}
            </strong>
            <p class="rwf-error-banner-message">{{ submitError }}</p>
          </div>
          <div class="rwf-error-banner-actions">
            <button
              type="button"
              class="rwf-error-retry-btn"
              @click="retry"
            >
              返回修改
            </button>
          </div>
        </div>

        <!-- ============================================================ -->
        <!-- Step 1: Research Question -->
        <!-- ============================================================ -->
        <ResearchQuestionStep
          v-if="stepState === 'question'"
          :question="question"
          :disabled="submitting"
          @update:question="question = $event"
          @next="goToSelection"
        />

        <!-- ============================================================ -->
        <!-- Step 2: Document Selection -->
        <!-- ============================================================ -->
        <DocumentSelectionStep
          v-else-if="stepState === 'selection'"
          :question="question"
          :disabled="submitting"
          @back="goToQuestion"
          @submit="submitWorkflow"
        />

        <!-- ============================================================ -->
        <!-- Step 3: AI Analysis (submitting) -->
        <!-- ============================================================ -->
        <AnalysisPendingState
          v-else-if="stepState === 'submitting'"
          :active="submitting"
        />

        <!-- ============================================================ -->
        <!-- Step 4: Evidence Review -->
        <!-- ============================================================ -->
        <EvidenceReviewStep
          v-else-if="stepState === 'evidence'"
          :evidence="evidenceList"
          :citations="citationList"
          :citation-save-state="citationSaveState"
          @save-citation="saveCitation"
          @go-to-report="goToReport"
        />

        <!-- ============================================================ -->
        <!-- Step 5: Research Report -->
        <!-- ============================================================ -->
        <ResearchReportStep
          v-else-if="stepState === 'report' && report !== null"
          :report="report"
          :project-id="projectId"
          @back-to-evidence="goToEvidence"
          @new-workflow="reset"
        />
      </template>

      <!-- ══════════════════════════════════════════════════════════ -->
      <!-- Past Research Results (existing completed runs) -->
      <!-- ══════════════════════════════════════════════════════════ -->
      <template v-if="session && !sessionLoading">
        <!-- Loading past runs -->
        <LoadingState
          v-if="pastRunsLoading"
          message="正在加载历史报告..."
        />

        <!-- Past runs list -->
        <div
          v-else-if="pastRuns.length > 0"
          class="rwf-past-runs"
        >
          <h2 class="rwf-past-heading">历史研究报告</h2>
          <ul class="rwf-past-list" role="list">
            <li v-for="run in pastRuns" :key="run.run_id" class="rwf-past-item">
              <div class="rwf-past-main">
                <h3 class="rwf-past-title">{{ run.topic || '未命名报告' }}</h3>
                <time v-if="run.completed_at || run.started_at" class="rwf-past-time">
                  {{ formatPastRunDate(run.completed_at || run.started_at) }}
                </time>
              </div>
              <router-link
                :to="`/research/${projectId}/result/${run.run_id}`"
                class="rwf-result-link"
              >
                查看结果
              </router-link>
            </li>
          </ul>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * ResearchWorkflowPage — 五步研究工作流页面
 *
 * Route: /research/:projectId/workflow
 *
 * Step flow:
 *   1. Research Question — user enters topic
 *   2. Document Selection — system auto-retrieves (no manual selection)
 *   3. AI Analysis — single synchronous POST /api/v4/research/workflow
 *   4. Evidence Review — evidence/citations from run artifacts
 *   5. Research Report — markdown + "查看完整结果" link
 *
 * Contract:
 *   - projectId === ResearchSession.id (route param)
 *   - Exactly ONE workflow request per submission
 *   - Backend workflow is synchronous — all 5 steps in one HTTP response
 *   - No fake percentages, no setTimeout-simulated progress
 *   - No pause/resume (not supported by backend)
 *   - Document selection is not supported — system auto-retrieves by topic
 *   - sessionStorage key includes projectId for isolation
 *   - Sensitive data never enters URL or console
 *
 * Does NOT:
 *   - Implement ResearchResultPage (only navigation link)
 *   - Modify backend API
 *   - Create independent Project entity
 *   - Delete old pages or routes
 *
 * ref: docs/20-product/2014-research-workflow-migration.md
 */
import { computed, ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/api/client';
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import WorkflowStepNavigation from '@/components/research/workflow/WorkflowStepNavigation.vue';
import ResearchQuestionStep from '@/components/research/workflow/ResearchQuestionStep.vue';
import DocumentSelectionStep from '@/components/research/workflow/DocumentSelectionStep.vue';
import AnalysisPendingState from '@/components/research/workflow/AnalysisPendingState.vue';
import EvidenceReviewStep from '@/components/research/workflow/EvidenceReviewStep.vue';
import ResearchReportStep from '@/components/research/workflow/ResearchReportStep.vue';
import { useResearchWorkflow } from '@/composables/useResearchWorkflow';

const route = useRoute();
const projectId = computed(() => String(route.params.projectId || ''));

// ---- Past runs (historical completed runs with result links) ----
interface PastRunItem {
  run_id: string;
  topic?: string;
  started_at?: string | null;
  completed_at?: string | null;
}
const pastRuns = ref<PastRunItem[]>([]);
const pastRunsLoading = ref(false);
let pastRunsReqId = 0;

async function loadPastRuns() {
  const id = String(route.params.projectId || '');
  if (!id || id === 'undefined' || id === 'null') return;
  const myReqId = ++pastRunsReqId;
  pastRunsLoading.value = true;
  try {
    const { data } = await api.get(`/api/v4/research/session/${id}/runs`);
    if (myReqId !== pastRunsReqId) return;
    const body = data.data ?? data;
    const allRuns = (body.runs ?? []) as PastRunItem[];
    // Only show runs that have a run_id (all valid runs)
    pastRuns.value = allRuns.filter((r) => r.run_id);
  } catch {
    if (myReqId !== pastRunsReqId) return;
    // Silent failure — past runs are auxiliary, don't block workflow
    pastRuns.value = [];
  } finally {
    if (myReqId === pastRunsReqId) {
      pastRunsLoading.value = false;
    }
  }
}

function formatPastRunDate(iso?: string | null): string {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

const {
  session,
  sessionLoading,
  sessionError,
  notFound,
  loadSession,
  question,
  initPendingQuestion,
  stepState,
  currentStepIndex,
  submitting,
  submitError,
  submitStatusCode,
  submitWorkflow,
  retry,
  goToQuestion,
  goToSelection,
  goToEvidence,
  goToReport,
  reset,
  evidenceList,
  citationList,
  report,
  citationSaveState,
  saveCitation,
} = useResearchWorkflow(() => projectId.value);

// ---- Error banner focus ----
const errorBannerRef = ref<HTMLElement | null>(null);

// ---- Navigation steps ----
const navSteps = [
  { label: '研究问题' },
  { label: '文献选择' },
  { label: 'AI 分析' },
  { label: '证据审查' },
  { label: '研究报告' },
];

// ---- Page title ----
const pageTitle = computed(() => {
  if (session.value?.title) return `${session.value.title} · 研究工作流`;
  return '研究工作流';
});

// ---- Error title helper ----
function errorTitleForCode(code: number): string {
  switch (code) {
    case 400: return '输入错误';
    case 401: return '未登录';
    case 403: return '权限不足';
    case 404: return '未找到';
    case 409: return '状态冲突';
    case 422: return '校验失败';
    case 429: return '请求过多';
    default:
      if (code >= 500) return '服务端错误';
      return '请求失败';
  }
}

// ---- Focus management ----
// Move focus to error banner when submitError appears
watch(submitError, async (val) => {
  if (val) {
    await nextTick();
    errorBannerRef.value?.focus();
  }
});

// ---- Lifecycle ----
onMounted(async () => {
  await loadSession();
  if (session.value) {
    initPendingQuestion();
  }
  loadPastRuns();
});

// ---- Watch projectId changes ----
watch(
  () => route.params.projectId,
  () => {
    reset();
    loadSession().then(() => {
      if (session.value) {
        initPendingQuestion();
      }
      loadPastRuns();
    });
  },
);

onBeforeUnmount(() => {
  pastRunsReqId = -1;
});
</script>

<style scoped>
.research-page {
  min-height: 100%;
}

.rwf-body {
  padding: var(--space-6) var(--space-8);
  max-width: 880px;
}

/* ---- Error banner ---- */
.rwf-error-banner {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-4);
  padding: 14px 18px;
  border: 1px solid var(--color-error);
  border-left: 4px solid var(--color-error-text);
  border-radius: var(--radius-md);
  background: var(--color-error-bg);
  margin-bottom: var(--space-6);
}

.rwf-error-banner-content {
  flex: 1;
  min-width: 0;
}

.rwf-error-banner-title {
  display: block;
  font-size: var(--text-base);
  color: var(--color-error-text);
  margin-bottom: var(--space-1);
}

.rwf-error-banner-message {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-error-light-text);
  line-height: var(--leading-normal);
}

.rwf-error-banner-actions {
  flex-shrink: 0;
}

.rwf-error-retry-btn {
  padding: var(--space-2) 18px;
  border: 1px solid var(--color-error-text);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  background: #fff;
  color: var(--color-error-text);
  transition: all var(--transition-base);
}

.rwf-error-retry-btn:hover {
  background: var(--color-error-text);
  color: #fff;
}

/* ---- Back link ---- */
.rwf-back-link {
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

.rwf-back-link:hover {
  background: var(--color-accent);
  color: #fff;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rwf-body {
    padding: var(--space-4) var(--space-5);
  }

  .rwf-error-banner {
    flex-direction: column;
  }
}

/* ---- Past runs section ---- */
.rwf-past-runs {
  margin-top: var(--space-8);
  padding-top: var(--space-6);
  border-top: 2px solid var(--color-border);
}

.rwf-past-heading {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
}

.rwf-past-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.rwf-past-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.rwf-past-main {
  flex: 1;
  min-width: 0;
}

.rwf-past-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.rwf-past-time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.rwf-result-link {
  display: inline-flex;
  align-items: center;
  padding: 4px 14px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
  text-decoration: none;
  white-space: nowrap;
  transition: all var(--transition-base);
  flex-shrink: 0;
}

.rwf-result-link:hover {
  background: var(--color-accent);
  color: #fff;
}
</style>
