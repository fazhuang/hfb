<template>
  <section class="rrs-step" aria-labelledby="rrs-heading">
    <h2 id="rrs-heading" class="rrs-heading">第五步：研究报告</h2>

    <!-- Unpersisted warning -->
    <div v-if="!report.markdown" class="rrs-warning" role="alert">
      <AlertTriangle :size="16" class="rrs-warning-icon" aria-hidden="true" />
      <p>
        当前报告尚未持久化，刷新页面后可能丢失。建议通过"查看完整结果"进入独立结果页面查看已保存的报告。
      </p>
    </div>

    <!-- Report card -->
    <div v-if="report.run_id" class="rrs-card">
      <div class="rrs-card-header">
        <h3 class="rrs-card-title">{{ report.title }}</h3>
        <time v-if="report.completed_at" :datetime="report.completed_at" class="rrs-card-time">
          {{ formatDate(report.completed_at) }}
        </time>
      </div>

      <div class="rrs-stats">
        <div class="rrs-stat">
          <span class="rrs-stat-label">证据条数</span>
          <span class="rrs-stat-value">{{ report.evidence_count }}</span>
        </div>
        <div class="rrs-stat">
          <span class="rrs-stat-label">引用数量</span>
          <span class="rrs-stat-value">{{ report.citation_count }}</span>
        </div>
        <div v-if="report.artifact_id" class="rrs-stat">
          <span class="rrs-stat-label">产物 ID</span>
          <code class="rrs-stat-value rrs-stat-value--code"
            >{{ report.artifact_id.slice(0, 12) }}...</code
          >
        </div>
      </div>

      <!-- Report preview -->
      <div v-if="report.markdown" class="rrs-preview">
        <h4 class="rrs-preview-heading">报告预览</h4>
        <pre class="rrs-preview-text">{{ reportPreview }}</pre>
      </div>

      <!-- Actions -->
      <div class="rrs-actions">
        <button
          type="button"
          class="rrs-action-btn rrs-action-btn--secondary"
          @click="$emit('back-to-evidence')"
        >
          返回证据审查
        </button>
        <button
          type="button"
          class="rrs-action-btn rrs-action-btn--secondary"
          @click="$emit('new-workflow')"
        >
          开始新研究
        </button>
        <button
          v-if="report.topic"
          type="button"
          class="rrs-action-btn rrs-action-btn--secondary"
          @click="$emit('re-search')"
        >
          <Search :size="13" class="rrs-action-icon" aria-hidden="true" />
          基于报告重新搜索
        </button>
        <router-link
          v-if="report.run_id"
          :to="`/research/${projectId}/result/${report.run_id}`"
          class="rrs-action-btn rrs-action-btn--primary"
        >
          查看完整结果
        </router-link>
      </div>
    </div>

    <!-- Empty state -->
    <EmptyState
      v-else
      title="暂无报告"
      description="研究流尚未生成报告。请先完成 AI 分析。"
      icon="📄"
    >
      <template #action>
        <button
          type="button"
          class="rrs-action-btn rrs-action-btn--secondary"
          @click="$emit('back-to-evidence')"
        >
          返回证据审查
        </button>
      </template>
    </EmptyState>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { AlertTriangle, Search } from '@lucide/vue';
import type { WorkflowReport } from '@/composables/useResearchWorkflow';
import EmptyState from '@/components/common/EmptyState.vue';

const props = defineProps<{
  report: WorkflowReport;
  projectId: string;
}>();

defineEmits<{
  'back-to-evidence': [];
  'new-workflow': [];
  're-search': [];
}>();

const reportPreview = computed(() => {
  if (!props.report.markdown) return '';
  return props.report.markdown.length > 3000
    ? props.report.markdown.slice(0, 3000) + '\n\n...'
    : props.report.markdown;
});

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
/* ponytail: 18px/15px/11px retained — no exact --text-* token. Add --text-2xs (11px), --text-md (15px), --text-2xl (18px) when typography grid fills out */
.rrs-step {
  padding: 0;
}

.rrs-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
}

/* Warning */
.rrs-warning {
  display: flex;
  gap: var(--space-2-5);
  padding: var(--space-3) var(--space-3-5);
  border: 1px solid var(--color-warning);
  border-left: 4px solid var(--color-warning);
  border-radius: var(--radius-md);
  background: var(--color-warning-bg);
  margin-bottom: var(--space-5);
}

.rrs-warning-icon {
  flex-shrink: 0;
  margin-top: var(--space-0-25);
  color: var(--color-warning-text);
}

.rrs-warning p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-warning-text);
  line-height: 1.5;
}

/* Card */
.rrs-card {
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-navbar-bg, var(--color-surface));
  overflow: hidden;
}

.rrs-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.rrs-card-title {
  font-size: var(--text-lg);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.rrs-card-time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
}

/* Stats */
.rrs-stats {
  display: flex;
  gap: var(--space-6);
  padding: var(--space-3) var(--space-5);
  border-bottom: 1px solid var(--color-border);
  background: var(--color-page-bg);
}

.rrs-stat {
  display: flex;
  flex-direction: column;
  gap: var(--space-0-5);
}

.rrs-stat-label {
  font-size: 11px;
  color: var(--color-text-muted);
  text-transform: uppercase;
}

.rrs-stat-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.rrs-stat-value--code {
  font-size: var(--text-xs);
  font-weight: 400;
}

/* Preview */
.rrs-preview {
  padding: var(--space-4) var(--space-5);
  border-bottom: 1px solid var(--color-border);
}

.rrs-preview-heading {
  font-size: var(--text-sm);
  font-weight: 600;
  color: var(--color-text-muted);
  margin: 0 0 var(--space-2-5);
}

.rrs-preview-text {
  margin: 0;
  padding: var(--space-3-5);
  background: var(--color-page-bg);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  line-height: 1.7;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
  color: var(--color-text-primary);
}

/* Actions */
.rrs-actions {
  display: flex;
  gap: var(--space-2-5);
  padding: var(--space-4) var(--space-5);
  flex-wrap: wrap;
}

.rrs-action-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--space-2) var(--space-4-5);
  border-radius: var(--radius-lg);
  font-size: var(--text-sm);
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
  text-decoration: none;
}

.rrs-action-btn--primary {
  border: none;
  background: var(--color-accent);
  color: var(--color-surface);
}

.rrs-action-btn--primary:hover {
  background: var(--color-accent-hover, var(--color-info));
}

.rrs-action-btn--primary:focus-visible {
  background: var(--color-accent-hover, var(--color-info));
}

.rrs-action-btn--secondary {
  border: 1px solid var(--color-border);
  background: var(--color-navbar-bg, var(--color-surface));
  color: var(--color-text-secondary);
}

.rrs-action-btn--secondary:hover {
  background: var(--color-hover);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.rrs-action-btn--secondary:focus-visible {
  background: var(--color-hover);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.rrs-action-icon {
  margin-right: var(--space-1);
}

@media (max-width: 640px) {
  .rrs-stats {
    flex-wrap: wrap;
    gap: var(--space-3);
  }

  .rrs-preview-text {
    overflow-wrap: anywhere;
    overflow-x: auto;
  }
}
</style>
