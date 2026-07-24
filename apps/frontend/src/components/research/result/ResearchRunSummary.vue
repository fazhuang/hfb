<template>
  <div class="rrs-summary" role="status" aria-label="运行摘要">
    <div class="rrs-row">
      <span class="rrs-label">运行 ID</span>
      <code class="rrs-value rrs-value--code">{{ shortRunId }}</code>
    </div>
    <div class="rrs-row">
      <span class="rrs-label">状态</span>
      <span :class="['rrs-status', statusClass]">{{ statusText }}</span>
    </div>
    <div v-if="report?.completed_at" class="rrs-row">
      <span class="rrs-label">完成时间</span>
      <time class="rrs-value" :datetime="report.completed_at">{{ formatDate(report.completed_at) }}</time>
    </div>
    <div v-if="steps.length > 0" class="rrs-row rrs-row--steps">
      <span class="rrs-label">流程步骤</span>
      <div class="rrs-steps">
        <span
          v-for="(step, idx) in steps"
          :key="idx"
          :class="['rrs-step-badge', stepClass(step)]"
        >
          {{ stepLabels[step.name as string] || step.name }}
        </span>
      </div>
    </div>
    <div v-if="report" class="rrs-row">
      <span class="rrs-label">统计</span>
      <span class="rrs-value">
        证据 {{ report.evidence_count }} 条 · 引用 {{ report.citation_count }} 条
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ResultReport } from '@/composables/useResearchResult';

const props = defineProps<{
  run: Record<string, unknown>;
  report: ResultReport | null;
}>();

const stepLabels: Record<string, string> = {
  topic_selection: '主题选择',
  literature_retrieval: '文献检索',
  evidence_synthesis: '证据综合',
  report_generation: '报告生成',
  citation_export: '引文导出',
};

const shortRunId = computed(() => {
  const rid = props.run.run_id as string;
  return rid ? rid.slice(0, 12) + '...' : '—';
});

const steps = computed(() => {
  const trace = props.run.step_execution_trace as Array<Record<string, unknown>> | undefined;
  return trace || [];
});

const hasFailed = computed(() => steps.value.some((s) => s.status === 'failed'));
const allCompleted = computed(() =>
  steps.value.length > 0 && steps.value.every((s) => s.status === 'completed')
);

const statusClass = computed(() => {
  if (hasFailed.value) return 'rrs-status--failed';
  if (allCompleted.value) return 'rrs-status--completed';
  return 'rrs-status--pending';
});

const statusText = computed(() => {
  if (hasFailed.value) return '失败';
  if (allCompleted.value) return '已完成';
  return '进行中';
});

function stepClass(step: Record<string, unknown>) {
  if (step.status === 'completed') return 'rrs-step-badge--completed';
  if (step.status === 'failed') return 'rrs-step-badge--failed';
  return 'rrs-step-badge--pending';
}

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
</script>

<style scoped>
.rrs-summary {
  padding: 16px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rrs-row {
  display: flex;
  align-items: baseline;
  gap: 12px;
  font-size: 13px;
}

.rrs-row--steps {
  align-items: flex-start;
}

.rrs-label {
  font-weight: 500;
  color: var(--color-text-muted, #718096);
  min-width: 80px;
  flex-shrink: 0;
}

.rrs-value {
  color: var(--color-text-primary, #1a365d);
}

.rrs-value--code {
  font-size: 12px;
  background: var(--color-page-bg, #fafafa);
  padding: 2px 6px;
  border-radius: 3px;
}

.rrs-status {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 700;
}

.rrs-status--completed {
  background: var(--color-success-icon-bg);
  color: var(--color-success-text);
}

.rrs-status--failed {
  background: var(--color-error-icon-bg);
  color: var(--color-error-light-text);
}

.rrs-status--pending {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.rrs-steps {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.rrs-step-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.rrs-step-badge--completed {
  background: var(--color-success-icon-bg);
  color: var(--color-success-text);
}

.rrs-step-badge--failed {
  background: var(--color-error-icon-bg);
  color: var(--color-error-light-text);
}

.rrs-step-badge--pending {
  background: var(--color-page-bg);
  color: var(--color-text-muted);
}
</style>
