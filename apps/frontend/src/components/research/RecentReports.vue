<template>
  <section class="rr-section" aria-labelledby="rr-heading">
    <h2 id="rr-heading" class="rr-heading">最近研究</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载..." />

    <!-- Error -->
    <ErrorState v-else-if="error" :message="error" title="加载失败" @retry="$emit('retry')" />

    <!-- Empty -->
    <EmptyState
      v-else-if="props.items.length === 0"
      title="暂无研究记录"
      description="在此课题中执行研究查询或运行研究工作流后，记录将显示在这里。"
      icon="📄"
    />

    <!-- Merged research list -->
    <ul v-else class="rr-list" role="list">
      <li v-for="item in props.items" :key="`${item.type}-${item.id}`" class="rr-item">
        <!-- Run item -->
        <template v-if="item.type === 'run'">
          <div class="rr-item-main">
            <h3 class="rr-title">{{ item.title || '未命名研究' }}</h3>
            <div v-if="item.stepTrace && item.stepTrace.length > 0" class="rr-steps">
              <span
                v-for="step in item.stepTrace"
                :key="step.name"
                class="rr-step-badge"
                :class="'rr-step--' + step.status"
              >
                {{ stepLabel(step.name) }}
              </span>
            </div>
          </div>
          <div class="rr-item-meta">
            <time v-if="item.completedAt" :datetime="item.completedAt" class="rr-time">
              {{ formatDate(item.completedAt) }}
            </time>
            <router-link
              v-if="item.runId && hasCompletedStep(item)"
              :to="`/research/${projectId}/result/${item.runId}`"
              class="rr-view-link"
            >
              查看
            </router-link>
          </div>
        </template>

        <!-- Activity item -->
        <template v-else>
          <div class="rr-item-main rr-item-main--inline">
            <span class="rr-type-badge">{{ typeLabel(item.queryType || '') }}</span>
            <span class="rr-text">{{ item.title }}</span>
          </div>
          <div class="rr-item-meta">
            <span v-if="(item.citationCount ?? 0) > 0" class="rr-stat">
              {{ item.citationCount }} 条引用
            </span>
            <time :datetime="item.timestamp || undefined" class="rr-time">
              {{ formatDate(item.timestamp) }}
            </time>
          </div>
        </template>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
/**
 * RecentReports — 最近研究列表（受控展示组件）
 *
 * Receives merged research items from parent page (single source of truth).
 * Does NOT make its own API calls, sort, or filter — purely displays what it receives.
 *
 * Supports two item types:
 *   run — from /api/v4/research/session/{id}/runs
 *   activity — from /api/v4/research/session/{id}/history
 */
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

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

const props = defineProps<{
  projectId: string;
  items: MergedResearchItem[];
  loading?: boolean;
  error?: string | null;
}>();

defineEmits<{
  retry: [];
}>();

const STEP_LABELS: Record<string, string> = {
  topic_selection: '选题',
  literature_retrieval: '文献检索',
  evidence_synthesis: '证据综合',
  report_generation: '报告生成',
  citation_export: '引文导出',
};

const TYPE_LABELS: Record<string, string> = {
  research: '研究',
  report: '报告',
  synthesis: '综合',
  education: '教育',
  graph: '图谱',
  search: '搜索',
  workflow_step: '工作流',
};

function stepLabel(name: string): string {
  return STEP_LABELS[name] || name;
}

function typeLabel(t: string): string {
  return TYPE_LABELS[t] || t;
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

function hasCompletedStep(item: MergedResearchItem): boolean {
  const trace = item.stepTrace ?? [];
  if (trace.length === 0) return false;
  return trace.some((s) => s.status === 'completed');
}
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

.rr-item-main--inline {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
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

/* Activity item styles */
.rr-type-badge {
  display: inline-block;
  padding: var(--space-0-25) 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: var(--font-semibold);
  background: var(--color-hover);
  color: var(--color-text-secondary);
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 1px;
}

.rr-text {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
  line-height: var(--leading-normal);
  word-break: break-word;
}

.rr-stat {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}
</style>
