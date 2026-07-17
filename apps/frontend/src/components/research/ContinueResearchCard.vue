<template>
  <section class="crc-section" aria-labelledby="crc-heading">
    <h2 id="crc-heading" class="crc-heading">继续研究</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在检查可恢复的研究..." />

    <!-- Error -->
    <ErrorState
      v-else-if="error"
      :message="error"
      title="检查失败"
      @retry="checkResumable"
    />

    <!-- No resumable run — show Start New Research -->
    <div v-else-if="!resumableRun" class="crc-empty">
      <p class="crc-empty-text">当前没有可继续的研究运行。</p>
      <router-link
        :to="`/research/${projectId}/workflow`"
        class="crc-start-btn"
      >
        开始新研究
      </router-link>
    </div>

    <!-- Resumable run found -->
    <div v-else class="crc-card">
      <div class="crc-card-main">
        <h3 class="crc-topic">{{ resumableRun.topic || '未命名研究' }}</h3>
        <p class="crc-step-info">
          当前步骤：{{ stepLabel(resumableRun.currentStep) }}
        </p>
        <time
          v-if="resumableRun.updatedAt"
          :datetime="resumableRun.updatedAt"
          class="crc-time"
        >
          {{ formatDate(resumableRun.updatedAt) }}
        </time>
      </div>
      <router-link
        :to="`/research/${projectId}/workflow`"
        class="crc-resume-btn"
      >
        继续研究
      </router-link>
    </div>
  </section>
</template>

<script setup lang="ts">
/**
 * ContinueResearchCard — 可恢复研究运行卡片
 *
 * Checks GET /api/v4/research/session/{projectId}/runs for the most recent
 * run with incomplete steps. The current backend executes workflows
 * synchronously in a single request — runs are either fully completed or
 * failed. There is no resume API. This component therefore shows "开始新研究"
 * as the default and only falls through to "继续研究" when a run with
 * non-terminal step status exists (future-proofing).
 *
 * ref: docs/20-product/2013-research-workspace-migration.md
 */
import { ref, onMounted, onBeforeUnmount } from 'vue';
import api from '@/api/client';
import LoadingState from '@/components/common/LoadingState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

const props = defineProps<{
  projectId: string;
}>();

interface RunItem {
  run_id: string;
  topic?: string;
  started_at?: string | null;
  completed_at?: string | null;
  step_execution_trace?: Array<{ name: string; status: string }>;
}

interface ResumableRun {
  runId: string;
  topic: string;
  currentStep: string;
  updatedAt: string | null;
}

const resumableRun = ref<ResumableRun | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const STEP_LABELS: Record<string, string> = {
  topic_selection: '选题',
  literature_retrieval: '文献检索',
  evidence_synthesis: '证据综合',
  report_generation: '报告生成',
  citation_export: '引文导出',
};

function stepLabel(name: string): string {
  return STEP_LABELS[name] || name;
}

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

let reqId = 0;

async function checkResumable() {
  const myReqId = ++reqId;
  loading.value = true;
  error.value = null;
  resumableRun.value = null;

  try {
    const { data } = await api.get(
      `/api/v4/research/session/${props.projectId}/runs`,
    );
    if (myReqId !== reqId) return;
    const body = data.data ?? data;
    const runs: RunItem[] = (body.runs ?? []) as RunItem[];

    // Find the most recent run with incomplete steps.
    // The workflow runs synchronously so normally all runs are either
    // completed or failed. Check for pending/running steps as future-proof.
    for (const run of runs) {
      const trace = run.step_execution_trace ?? [];
      const incomplete = trace.find(
        (s) => s.status === 'pending' || s.status === 'running',
      );
      if (incomplete) {
        resumableRun.value = {
          runId: run.run_id,
          topic: run.topic ?? '未命名研究',
          currentStep: incomplete.name,
          updatedAt: run.completed_at ?? run.started_at ?? null,
        };
        break; // first incomplete run
      }
    }
  } catch (e: unknown) {
    if (myReqId !== reqId) return;
    const msg =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '检查可恢复研究失败';
    error.value = msg;
  } finally {
    if (myReqId === reqId) {
      loading.value = false;
    }
  }
}

onMounted(() => {
  checkResumable();
});

onBeforeUnmount(() => {
  reqId = -1;
});
</script>

<style scoped>
.crc-section {
  margin-bottom: 28px;
}

.crc-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

/* Empty — no resumable run */
.crc-empty {
  padding: 24px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  text-align: center;
}

.crc-empty-text {
  font-size: 14px;
  color: var(--color-text-muted, #718096);
  margin: 0 0 16px;
}

.crc-start-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  background: var(--color-accent, #4299e1);
  color: #fff;
  transition: background 0.15s;
}

.crc-start-btn:hover {
  background: var(--color-accent-hover, #3182ce);
}

/* Card — resumable run */
.crc-card {
  padding: 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 16px;
}

.crc-card-main {
  flex: 1;
  min-width: 0;
}

.crc-topic {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 6px;
}

.crc-step-info {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 4px;
}

.crc-time {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.crc-resume-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  background: var(--color-accent, #4299e1);
  color: #fff;
  white-space: nowrap;
  flex-shrink: 0;
  transition: background 0.15s;
}

.crc-resume-btn:hover {
  background: var(--color-accent-hover, #3182ce);
}
</style>
