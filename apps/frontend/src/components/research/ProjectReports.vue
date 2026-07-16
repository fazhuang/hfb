<template>
  <section class="pr-section" aria-labelledby="pr-heading">
    <h2 id="pr-heading" class="pr-heading">报告</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载报告..." />

    <!-- Error -->
    <ErrorState
      v-else-if="error"
      :message="error"
      title="报告加载失败"
      @retry="fetchReports"
    />

    <!-- Empty -->
    <EmptyState
      v-else-if="reports.length === 0"
      title="暂无报告"
      description="在此课题中运行研究工作流后，生成的报告将显示在这里。"
      icon="📄"
    />

    <!-- Report list -->
    <ul v-else class="pr-list" role="list">
      <li v-for="report in reports" :key="report.run_id" class="pr-item">
        <div class="pr-item-main">
          <h3 class="pr-title">{{ report.topic || '未命名报告' }}</h3>
          <div class="pr-steps">
            <span
              v-for="step in (report.step_execution_trace || [])"
              :key="step.name"
              class="pr-step-badge"
              :class="'pr-step--' + step.status"
            >
              {{ stepLabel(step.name) }}
            </span>
          </div>
        </div>
        <div class="pr-item-meta">
          <time :datetime="report.completed_at ?? undefined" class="pr-time">
            {{ formatDate(report.completed_at || report.started_at) }}
          </time>
          <router-link
            :to="`/research/${projectId}/result/${report.run_id}`"
            class="pr-view-link"
          >
            查看
          </router-link>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import api from '@/api/client';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

const props = defineProps<{
  projectId: string;
}>();

interface ReportItem {
  run_id: string;
  topic?: string;
  started_at?: string | null;
  completed_at?: string | null;
  step_execution_trace?: Array<{ name: string; status: string }>;
}

const reports = ref<ReportItem[]>([]);
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

async function fetchReports() {
  const myReqId = ++reqId;
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get(
      `/api/v4/research/session/${props.projectId}/runs`,
    );
    if (myReqId !== reqId) return;
    const body = data.data ?? data;
    reports.value = (body.runs ?? []) as ReportItem[];
  } catch (e: unknown) {
    if (myReqId !== reqId) return;
    const msg =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '加载报告失败';
    error.value = msg;
  } finally {
    if (myReqId === reqId) {
      loading.value = false;
    }
  }
}

onMounted(() => {
  fetchReports();
});

onBeforeUnmount(() => {
  reqId = -1;
});
</script>

<style scoped>
.pr-section {
  margin-bottom: 28px;
}

.pr-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.pr-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pr-item {
  padding: 12px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.pr-item-main {
  flex: 1;
  min-width: 0;
}

.pr-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 6px;
}

.pr-steps {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.pr-step-badge {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
  background: var(--color-hover, #edf2f7);
  color: var(--color-text-muted, #a0aec0);
}

.pr-step--completed {
  background: rgba(56, 161, 105, 0.12);
  color: #276749;
}

.pr-step--failed {
  background: rgba(197, 48, 48, 0.1);
  color: #9b2c2c;
}

.pr-step--pending {
  background: rgba(160, 174, 192, 0.12);
  color: #718096;
}

.pr-item-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.pr-time {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  white-space: nowrap;
}

.pr-view-link {
  display: inline-flex;
  align-items: center;
  padding: 4px 14px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
  white-space: nowrap;
  transition: all 0.15s;
}

.pr-view-link:hover {
  background: var(--color-accent, #2b6cb0);
  color: #fff;
}
</style>
