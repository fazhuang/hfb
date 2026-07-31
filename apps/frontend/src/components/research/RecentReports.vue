<template>
  <section class="rr-section" aria-labelledby="rr-heading">
    <h2 id="rr-heading" class="rr-heading">最近研究运行</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载..." />

    <!-- Error -->
    <ErrorState v-else-if="error" :message="error" title="加载失败" @retry="$emit('retry')" />

    <!-- Empty -->
    <EmptyState
      v-else-if="displayRuns.length === 0"
      title="暂无研究运行记录"
      description="在此课题中运行研究工作流后，运行记录将显示在这里。"
      icon="📄"
    />

    <!-- Run list — max 5 items -->
    <ul v-else class="rr-list" role="list">
      <li v-for="run in displayRuns" :key="run.run_id" class="rr-item">
        <div class="rr-item-main">
          <h3 class="rr-title">{{ run.topic || '未命名研究' }}</h3>
          <div class="rr-steps">
            <span
              v-for="step in run.step_execution_trace || []"
              :key="step.name"
              class="rr-step-badge"
              :class="'rr-step--' + step.status"
            >
              {{ stepLabel(step.name) }}
            </span>
          </div>
        </div>
        <div class="rr-item-meta">
          <time v-if="run.completed_at" :datetime="run.completed_at" class="rr-time">
            {{ formatDate(run.completed_at) }}
          </time>
          <router-link
            v-if="run.run_id && hasResultRoute(run)"
            :to="`/research/${projectId}/result/${run.run_id}`"
            class="rr-view-link"
          >
            查看
          </router-link>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
/**
 * RecentReports — 最近研究运行列表
 *
 * Receives shared runs data from parent page (single-source-of-truth).
 * Does NOT make its own API call.
 *
 * Only displays completed runs with report artifacts.
 * View link only shown when run_id is real and steps include report_generation completed.
 *
 * ref: docs/20-product/2013-research-workspace-migration.md
 */
import { computed } from 'vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

interface RunItem {
  run_id: string;
  topic?: string;
  started_at?: string | null;
  completed_at?: string | null;
  step_execution_trace?: Array<{ name: string; status: string }>;
}

const props = defineProps<{
  projectId: string;
  loading?: boolean;
  error?: string | null;
  runs?: RunItem[];
}>();

defineEmits<{
  retry: [];
}>();

const MAX_ITEMS = 5;

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

/** Only runs with report artifacts (completed report_generation) OR runs that have
 * at least some completed steps. This prevents hiding runs that had partial
 * completion — the workspace should display the same runs visible in
 * ProjectDetailPage's ProjectReports component.
 *
 * See ProjectReports.vue for the canonical unfiltered display.
 * Minimum bar: run has a run_id, topic, and completed at least one step.
 * This avoids the discrepancy where ProjectReports shows runs that
 * RecentReports hides due to aggressive filter.
 */
function hasReportArtifact(run: RunItem): boolean {
  const trace = run.step_execution_trace ?? [];
  if (trace.length === 0) return false;
  // Show runs with completed report_generation OR any completed step
  // (matches ProjectReports behavior where all runs are shown)
  return trace.some((s) => s.status === 'completed');
}

/** Result route exists when run_id is truthy and has at least one completed step. */
function hasResultRoute(run: RunItem): boolean {
  return !!run.run_id && hasReportArtifact(run);
}

const displayRuns = computed(() => {
  const raw = props.runs ?? [];
  // Only completed runs with report artifacts
  const completed = raw.filter(hasReportArtifact);
  // Sort by completed_at DESC; missing completed_at goes last
  const sorted = [...completed].sort((a, b) => {
    const da = a.completed_at ?? '';
    const db = b.completed_at ?? '';
    if (!da && !db) return 0;
    if (!da && db) return 1; // a has no time → a after b
    if (da && !db) return -1; // b has no time → b after a
    return db.localeCompare(da); // DESC
  });
  return sorted.slice(0, MAX_ITEMS);
});
</script>

<style scoped>
.rr-section {
  margin-bottom: var(--space-7);
}

.rr-heading {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.rr-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.rr-item {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
  flex-wrap: wrap;
}

.rr-item-main {
  flex: 1;
  min-width: 0;
}

.rr-title {
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1-5);
}

.rr-steps {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.rr-step-badge {
  display: inline-block;
  padding: var(--space-0-25) 6px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: var(--font-medium);
  background: var(--color-hover);
  color: var(--color-text-muted);
}

.rr-step--completed {
  background: var(--color-success-alpha-12);
  color: var(--color-success-text);
}

.rr-step--failed {
  background: var(--color-error-alpha-10);
  color: var(--color-error-light-text);
}

.rr-step--pending {
  background: var(--color-muted-alpha-12);
  color: var(--color-text-muted);
}

.rr-item-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.rr-time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
}

.rr-view-link {
  display: inline-flex;
  align-items: center;
  padding: var(--space-1) 14px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
  text-decoration: none;
  white-space: nowrap;
  transition: all var(--transition-base);
}

.rr-view-link:hover {
  background: var(--color-accent);
  color: var(--color-surface);
}

.rr-view-link:focus-visible {
  background: var(--color-accent);
  color: var(--color-surface);
}
</style>
