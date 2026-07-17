<template>
  <div class="research-page">
    <ResearchPageHeader
      :title="pageTitle"
      :breadcrumbs="[
        { label: '研究课题', to: '/research' },
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
          v-else-if="stepState === 'report'"
          :report="reportOrDefault"
          :project-id="projectId"
          @back-to-evidence="goToEvidence"
          @new-workflow="reset"
        />
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
import { computed, ref, watch, onMounted, nextTick } from 'vue';
import { useRoute } from 'vue-router';
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
import type { WorkflowReport } from '@/composables/useResearchWorkflow';

const route = useRoute();
const projectId = computed(() => String(route.params.projectId || ''));

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

// ---- Default report for when report is null ----
const reportOrDefault = computed<WorkflowReport>(() => {
  if (report.value) return report.value;
  return {
    run_id: '',
    topic: '',
    title: '',
    markdown: '',
    completed_at: null,
    evidence_count: 0,
    citation_count: 0,
  };
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
    });
  },
);
</script>

<style scoped>
.research-page {
  min-height: 100%;
}

.rwf-body {
  padding: 24px 32px;
  max-width: 880px;
}

/* ---- Error banner ---- */
.rwf-error-banner {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
  padding: 14px 18px;
  border: 1px solid #feb2b2;
  border-left: 4px solid #c53030;
  border-radius: 6px;
  background: #fff5f5;
  margin-bottom: 24px;
}

.rwf-error-banner-content {
  flex: 1;
  min-width: 0;
}

.rwf-error-banner-title {
  display: block;
  font-size: 14px;
  color: #c53030;
  margin-bottom: 4px;
}

.rwf-error-banner-message {
  margin: 0;
  font-size: 13px;
  color: #742a2a;
  line-height: 1.5;
}

.rwf-error-banner-actions {
  flex-shrink: 0;
}

.rwf-error-retry-btn {
  padding: 8px 18px;
  border: 1px solid #c53030;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  background: #fff;
  color: #c53030;
  transition: all 0.15s;
}

.rwf-error-retry-btn:hover {
  background: #c53030;
  color: #fff;
}

/* ---- Back link ---- */
.rwf-back-link {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
  transition: all 0.15s;
}

.rwf-back-link:hover {
  background: var(--color-accent, #2b6cb0);
  color: #fff;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rwf-body {
    padding: 16px 20px;
  }

  .rwf-error-banner {
    flex-direction: column;
  }
}
</style>
