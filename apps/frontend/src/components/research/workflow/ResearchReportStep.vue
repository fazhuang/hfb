<template>
  <section class="rrs-step" aria-labelledby="rrs-heading">
    <h2 id="rrs-heading" class="rrs-heading">第五步：研究报告</h2>

    <!-- Unpersisted warning -->
    <div v-if="!report.markdown" class="rrs-warning" role="alert">
      <span class="rrs-warning-icon" aria-hidden="true">⚠️</span>
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
          <code class="rrs-stat-value rrs-stat-value--code">{{ report.artifact_id.slice(0, 12) }}...</code>
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
import type { WorkflowReport } from '@/composables/useResearchWorkflow';
import EmptyState from '@/components/common/EmptyState.vue';

const props = defineProps<{
  report: WorkflowReport;
  projectId: string;
}>();

defineEmits<{
  'back-to-evidence': [];
  'new-workflow': [];
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
.rrs-step {
  padding: 0;
}

.rrs-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
}

/* Warning */
.rrs-warning {
  display: flex;
  gap: 10px;
  padding: 12px 14px;
  border: 1px solid #d69e2e;
  border-left: 4px solid #d69e2e;
  border-radius: 6px;
  background: #fffff0;
  margin-bottom: 20px;
}

.rrs-warning-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

.rrs-warning p {
  margin: 0;
  font-size: 13px;
  color: #975a16;
  line-height: 1.5;
}

/* Card */
.rrs-card {
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  overflow: hidden;
}

.rrs-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.rrs-card-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
}

.rrs-card-time {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  white-space: nowrap;
}

/* Stats */
.rrs-stats {
  display: flex;
  gap: 24px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-page-bg, #fafafa);
}

.rrs-stat {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.rrs-stat-label {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
  text-transform: uppercase;
}

.rrs-stat-value {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
}

.rrs-stat-value--code {
  font-size: 12px;
  font-weight: 400;
}

/* Preview */
.rrs-preview {
  padding: 16px 20px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.rrs-preview-heading {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-muted, #718096);
  margin: 0 0 10px;
}

.rrs-preview-text {
  margin: 0;
  padding: 14px;
  background: var(--color-page-bg, #fafafa);
  border-radius: 6px;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  max-height: 400px;
  overflow-y: auto;
  color: var(--color-text-primary, #1a365d);
}

/* Actions */
.rrs-actions {
  display: flex;
  gap: 10px;
  padding: 16px 20px;
  flex-wrap: wrap;
}

.rrs-action-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 18px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
  text-decoration: none;
}

.rrs-action-btn--primary {
  border: none;
  background: var(--color-accent, #4299e1);
  color: #fff;
}

.rrs-action-btn--primary:hover {
  background: var(--color-accent-hover, #3182ce);
}

.rrs-action-btn--primary:focus-visible {
  background: var(--color-accent-hover, #3182ce);
}

.rrs-action-btn--secondary {
  border: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-navbar-bg, #fff);
  color: var(--color-text-secondary, #4a5568);
}

.rrs-action-btn--secondary:hover {
  background: var(--color-hover, #edf2f7);
  border-color: var(--color-accent, #4299e1);
  color: var(--color-accent, #2b6cb0);
}

.rrs-action-btn--secondary:focus-visible {
  background: var(--color-hover, #edf2f7);
  border-color: var(--color-accent, #4299e1);
  color: var(--color-accent, #2b6cb0);
}
</style>
