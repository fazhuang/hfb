<template>
  <div class="research-page">
    <!-- Loading skeleton -->
    <div v-if="status === 'loading'" class="rpage-loading">
      <div class="rpage-spinner" aria-label="加载中..." />
      <p class="rpage-loading-text">加载研究结果...</p>
    </div>

    <!-- Error / non-ready states -->
    <ResearchResultErrorState
      v-else-if="status !== 'ready'"
      :status="status"
      :message="statusMessage"
      :project-id="currentProjectId"
      @retry="retry"
    />

    <!-- Ready: full result display -->
    <template v-else>
      <ResearchResultHeader
        :project-id="currentProjectId"
        :run-id="currentRunId"
        :session="session"
        :report="report"
        :evidence="evidenceList"
        :raw-run="rawRun"
        :exporting="exporting"
        :has-report="hasReport"
        @export="handleExport"
      />

      <!-- Quick stats bar for report-missing but ready -->
      <div v-if="!hasReport && hasEvidence" class="rpage-notice">
        <span class="rpage-notice-icon" aria-hidden="true">📄</span>
        <p>报告正文尚未生成，但以下显示了已检索到的证据和引用。</p>
      </div>

      <div class="rpage-body">
        <!-- Report section -->
        <ResearchReportViewer
          v-if="hasReport"
          :report="report!"
          :selected-citation-trace-id="selectedCitationTraceId"
          :valid-citation-trace-ids="validCitationTraceIds"
          @select-citation="selectCitation"
        />

        <!-- Export error -->
        <div v-if="exportError" class="rpage-export-error" role="alert">
          {{ exportError }}
        </div>

        <!-- Citation & Evidence panel -->
        <CitationPanel
          v-if="hasCitations || hasEvidence"
          class="rpage-citations"
          :citations="citationList"
          :evidence="evidenceList"
          :selected-trace-id="selectedCitationTraceId"
          @select="selectCitation"
        />

        <!-- No evidence or citations -->
        <div v-if="!hasEvidence && !hasCitations && hasReport" class="rpage-empty-section">
          <span class="rpage-empty-icon" aria-hidden="true">🔍</span>
          <p>此报告暂无关联证据与引用。</p>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { useRoute } from 'vue-router';
import { useResearchResult } from '@/composables/useResearchResult';
import ResearchResultHeader from '@/components/research/result/ResearchResultHeader.vue';
import ResearchReportViewer from '@/components/research/result/ResearchReportViewer.vue';
import CitationPanel from '@/components/research/result/CitationPanel.vue';
import ResearchResultErrorState from '@/components/research/result/ResearchResultErrorState.vue';

const route = useRoute();

const currentProjectId = computed(() => (route.params.projectId as string) || '');
const currentRunId = computed(() => (route.params.runId as string) || '');

const {
  status,
  statusMessage,
  session,
  report,
  evidenceList,
  citationList,
  rawRun,
  hasReport,
  hasEvidence,
  hasCitations,
  validCitationTraceIds,
  exporting,
  exportError,
  selectedCitationTraceId,
  load,
  retry,
  exportMarkdown,
  selectCitation,
  releaseExportBlob,
} = useResearchResult(
  () => currentProjectId.value,
  () => currentRunId.value,
);

// Load on mount and on route change
let lastProjectId = '';
let lastRunId = '';


onMounted(async () => {
  lastProjectId = currentProjectId.value;
  lastRunId = currentRunId.value;
  await load();
});

// Watch route params — full reload on change
watch(
  [() => route.params.projectId, () => route.params.runId],
  async ([newPid, newRid]) => {
    const pid = (newPid as string) || '';
    const rid = (newRid as string) || '';
    if (pid !== lastProjectId || rid !== lastRunId) {
      lastProjectId = pid;
      lastRunId = rid;
      await load();
    }
  },
);

async function handleExport() {
  await exportMarkdown();
}

// Release any export Blob URL on unmount
onBeforeUnmount(() => {
  releaseExportBlob();
});
</script>

<style scoped>
.research-page {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8);
}

@media (max-width: 768px) {
  .research-page {
    padding: var(--space-4) var(--space-5);
  }
}

/* Loading */
.rpage-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-4);
  padding: var(--space-20) 0;
}

.rpage-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: hfb-spin var(--transition-spinner) linear infinite;
}

.rpage-loading-text {
  font-size: var(--text-base);
  color: var(--color-text-muted);
  margin: 0;
}

/* Notice */
.rpage-notice {
  display: flex;
  gap: var(--space-3);
  align-items: center;
  padding: var(--space-3-5) var(--space-4);
  border: 1px solid var(--color-warning);
  border-left: 4px solid var(--color-warning);
  border-radius: var(--radius-md);
  background: var(--color-warning-bg);
  margin-top: var(--space-5);
}

.rpage-notice-icon {
  font-size: 18px;
  flex-shrink: 0;
}

.rpage-notice p {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-warning-text);
}

/* Body */
.rpage-body {
  margin-top: var(--space-7);
  display: flex;
  flex-direction: column;
  gap: var(--space-8);
}

/* Export error */
.rpage-export-error {
  padding: var(--space-2-5) 14px;
  border: 1px solid var(--color-error-icon-bg);
  border-radius: var(--radius-md);
  background: var(--color-error-bg);
  color: var(--color-error-light-text);
  font-size: var(--text-sm);
}

/* Empty section */
.rpage-empty-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-10) var(--space-5);
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
}

.rpage-empty-icon {
  font-size: 32px;
}

.rpage-empty-section p {
  margin: 0;
  font-size: var(--text-base);
}
</style>
