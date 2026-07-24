<template>
  <header class="rrh-header">
    <div class="rrh-top">
      <nav class="rrh-breadcrumbs" aria-label="面包屑导航">
        <router-link :to="backToWorkspace" class="rrh-breadcrumb-link">← 返回工作区</router-link>
        <span class="rrh-breadcrumb-sep">/</span>
        <router-link
          v-if="session"
          :to="backToWorkflow"
          class="rrh-breadcrumb-link"
        >
          返回研究流程
        </router-link>
        <span v-if="session" class="rrh-breadcrumb-sep">/</span>
        <span class="rrh-breadcrumb-current">研究结果</span>
      </nav>

      <div class="rrh-actions">
        <button
          type="button"
          class="rrh-btn rrh-btn--export"
          :disabled="exportDisabled"
          @click="$emit('export')"
        >
          {{ exporting ? '导出中...' : '导出 Markdown' }}
        </button>
      </div>
    </div>

    <div class="rrh-info">
      <h1 class="rrh-title">{{ sessionTitle }}</h1>
      <p v-if="report?.topic" class="rrh-topic">研究问题：{{ report.topic }}</p>
    </div>

    <ResearchRunSummary v-if="rawRun" :run="rawRun" :report="report" />
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ResultSession, ResultReport, ResultEvidence } from '@/composables/useResearchResult';
import ResearchRunSummary from './ResearchRunSummary.vue';

const props = defineProps<{
  projectId: string;
  runId: string;
  session: ResultSession | null;
  report: ResultReport | null;
  evidence: ResultEvidence[];
  rawRun: Record<string, unknown> | null;
  exporting: boolean;
  hasReport: boolean;
}>();

defineEmits<{
  export: [];
}>();

const sessionTitle = computed(() => props.session?.title || '研究结果');

const backToWorkspace = computed(() => `/research/${props.projectId}/workspace`);
const backToWorkflow = computed(() => `/research/${props.projectId}/workflow`);

const exportDisabled = computed(() => props.exporting || !props.hasReport);
</script>

<style scoped>
.rrh-header {
  padding: 0;
}

.rrh-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.rrh-breadcrumbs {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 13px;
  color: var(--color-text-muted);
}

.rrh-breadcrumb-link {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 500;
}

.rrh-breadcrumb-link:hover {
  text-decoration: underline;
}

.rrh-breadcrumb-link:focus-visible {
  text-decoration: underline;
}

.rrh-breadcrumb-sep {
  color: var(--color-border);
}

.rrh-breadcrumb-current {
  color: var(--color-text-secondary);
  font-weight: 600;
}

.rrh-actions {
  display: flex;
  gap: var(--space-2);
}

.rrh-btn {
  padding: var(--space-2) 18px;
  border-radius: var(--radius-lg);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--transition-base);
  border: none;
}

.rrh-btn--export {
  background: var(--color-accent);
  color: var(--color-surface);
}

.rrh-btn--export:hover:not(:disabled) {
  background: var(--color-accent-hover, var(--color-info));
}

.rrh-btn--export:focus-visible:not(:disabled) {
  background: var(--color-accent-hover, var(--color-info));
}

.rrh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.rrh-info {
  margin-bottom: 16px;
}

.rrh-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.rrh-topic {
  font-size: 14px;
  color: var(--color-text-secondary);
  margin: 0;
}
</style>
