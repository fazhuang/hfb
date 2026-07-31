<template>
  <div class="research-page">
    <ResearchPageHeader
      :title="pageTitle"
      :breadcrumbs="[
        { label: 'Research', to: '/research' },
        { label: session?.title || '加载中...', to: `/research/${projectId}` },
        { label: '版本比较' },
      ]"
    >
      <template v-if="comparison" #actions>
        <button class="button button--secondary" :disabled="exporting" @click="exportRecord">
          {{ exporting ? '导出中...' : '导出 Markdown' }}
        </button>
      </template>
    </ResearchPageHeader>

    <div class="vc-body">
      <!-- ============================================================ -->
      <!-- Page-level states -->
      <!-- ============================================================ -->
      <LoadingState v-if="sessionLoading" message="正在加载研究课题..." />

      <EmptyState
        v-else-if="notFound"
        title="课题不存在"
        description="该课题可能已被删除，或您没有访问权限。"
        icon="🔍"
      >
        <template #action>
          <router-link to="/research" class="vc-back-link"> 返回研究课题列表 </router-link>
        </template>
      </EmptyState>

      <ErrorState
        v-else-if="sessionError"
        title="加载失败"
        :message="sessionError"
        @retry="loadSession"
      />

      <!-- ============================================================ -->
      <!-- Validation banner (corpus_status !== 'approved') -->
      <!-- ============================================================ -->
      <div v-else-if="showValidationBanner && session" class="vc-validation-banner" role="status">
        <strong>语料验证状态</strong>
        <span>当前比较结果的语料证据仍在验证中，结果可能不完整。</span>
      </div>

      <!-- ============================================================ -->
      <!-- Step navigation -->
      <!-- ============================================================ -->
      <template v-if="session">
        <ol class="vc-step-nav" aria-label="版本比较进度">
          <li :class="{ active: currentStep >= 1 }">1. 检索条文</li>
          <li :class="{ active: currentStep >= 2 }">2. 选择版本</li>
          <li :class="{ active: currentStep >= 3 }">3. 比较差异</li>
          <li :class="{ active: currentStep >= 4 }">4. 验证语料</li>
        </ol>

        <p v-if="error" class="message message--error" role="alert">{{ error }}</p>
        <p v-if="message" class="message message--success" aria-live="polite">{{ message }}</p>

        <!-- ============================================================ -->
        <!-- Step 1 + 2: Search + Select (always visible before comparison) -->
        <!-- ============================================================ -->
        <div v-if="currentStep < 3" class="vc-workflow-grid">
          <PassageSearchStep
            :query="query"
            :results="searchResults"
            :searching="searching"
            :searched="searched"
            :source-passage="sourcePassage"
            :target-passage="targetPassage"
            @update:query="query = $event"
            @search="searchPassages"
            @select="selectPassage"
          />

          <VersionSelectStep
            :source-passage="sourcePassage"
            :target-passage="targetPassage"
            :same-version="sameVersion"
            :can-compare="canCompare"
            :comparing="comparing"
            @clear-source="sourcePassage = null"
            @clear-target="targetPassage = null"
            @compare="runComparison"
          />
        </div>

        <!-- ============================================================ -->
        <!-- Step 3: Diff Results -->
        <!-- ============================================================ -->
        <DiffResultStep v-if="currentStep >= 3" :comparison="comparison" />

        <!-- ============================================================ -->
        <!-- Step 3-4: Evidence verify + Notes -->
        <!-- ============================================================ -->
        <EvidenceVerifyStep
          v-if="currentStep >= 3"
          :comparison="comparison"
          :note-content="noteContent"
          :saving-note="savingNote"
          @update:note-content="noteContent = $event"
          @save-note="saveNote"
        />
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * VersionComparisonPage — 4-step version comparison workflow
 *
 * Route: /research/:projectId/version-comparison
 *
 * Step flow:
 *   1. Passage Search — full-text search for classical text passages
 *   2. Version Select — choose source and target versions
 *   3. Diff Result — diff engine output (differences, similarity, operations)
 *   4. Evidence Verify + Note — corpus evidence audit + research notes
 *
 * Contract:
 *   - projectId === ResearchSession.id (route param)
 *   - Auto-restore: probes 10 most recent sessions for existing comparison
 *   - Null skip: sessions returning data:null silently skipped
 *   - Network errors during restore: caught, UI renders step 1
 *   - Empty session list: UI renders step 1 without crash
 *   - Source === target blocked (sameVersion check)
 *   - Validation banner shown until corpus_status === 'approved'
 *   - Export: GET /api/v1/research/sessions/{id}/export (blob, markdown)
 *   - Per-projectId isolation
 *
 * ref: docs/20-product/phase3-migration-contract.md §2.2
 */
import { computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import PassageSearchStep from '@/components/research/version-comparison/PassageSearchStep.vue';
import VersionSelectStep from '@/components/research/version-comparison/VersionSelectStep.vue';
import DiffResultStep from '@/components/research/version-comparison/DiffResultStep.vue';
import EvidenceVerifyStep from '@/components/research/version-comparison/EvidenceVerifyStep.vue';
import { useVersionComparison } from '@/composables/useVersionComparison';

const route = useRoute();
const projectId = computed(() => String(route.params.projectId || ''));

const {
  session,
  sessionLoading,
  sessionError,
  notFound,
  loadSession,
  query,
  searchResults,
  searching,
  searched,
  searchPassages,
  sourcePassage,
  targetPassage,
  sameVersion,
  canCompare,
  selectPassage,
  comparison,
  comparing,
  runComparison,
  restoreLatestWorkflow,
  noteContent,
  savingNote,
  saveNote,
  exporting,
  exportRecord,
  currentStep,
  showValidationBanner,
  error,
  message,
} = useVersionComparison(() => projectId.value);

const pageTitle = computed(() => session.value?.title || '版本比较');

onMounted(async () => {
  await loadSession();
  await restoreLatestWorkflow();
});
</script>

<style scoped>
.vc-body {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-6) var(--space-8);
}

.vc-validation-banner {
  background: var(--color-warning-light, #fff8e1);
  border: 1px solid var(--color-warning, #ffc107);
  border-radius: 8px;
  padding: var(--space-3) var(--space-4);
  margin-bottom: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.vc-step-nav {
  display: flex;
  gap: var(--space-4);
  list-style: none;
  padding: 0;
  margin: 0 0 var(--space-6);
  font-size: 0.9rem;
  color: var(--color-text-muted);
  flex-wrap: wrap;
}

.vc-step-nav li {
  padding: var(--space-1) var(--space-3);
  border-radius: 20px;
  background: var(--color-bg-muted);
  transition: background 0.2s;
}

.vc-step-nav li.active {
  background: var(--color-primary);
  color: #fff;
}

.vc-workflow-grid {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: var(--space-6);
}

@media (max-width: 768px) {
  .vc-body {
    padding: var(--space-4);
  }
  .vc-workflow-grid {
    grid-template-columns: 1fr;
  }
  .vc-step-nav {
    gap: var(--space-2);
    font-size: 0.8rem;
  }
}
</style>

<!-- Globally scoped styles for step components (vue test-utils compatibility) -->
<style>
.vc-step-heading {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.vc-step-number {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: var(--color-text-muted);
  margin: 0 0 var(--space-1);
}

.vc-step-heading h2 {
  margin: 0;
  font-size: 1.25rem;
}

.vc-search-row {
  display: flex;
  gap: var(--space-2);
}

.vc-search-row input {
  flex: 1;
}

.vc-result-item {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-3);
  margin-bottom: var(--space-3);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.vc-result-meta span {
  display: inline-block;
  font-size: 0.8rem;
  background: var(--color-bg-muted);
  padding: 2px 8px;
  border-radius: 4px;
  margin-right: var(--space-2);
  margin-bottom: var(--space-1);
}

.vc-result-actions {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
  flex-shrink: 0;
}

.button--compact {
  padding: 4px 12px;
  font-size: 0.8rem;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg);
  cursor: pointer;
}

.button--compact.selected {
  background: var(--color-primary);
  color: #fff;
  border-color: var(--color-primary);
}

.vc-selection-slots {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}

.vc-selection-slot {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-3);
}

.vc-slot-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
  margin-bottom: var(--space-1);
}

.vc-slot-empty {
  color: var(--color-text-muted);
  font-style: italic;
}

.vc-text-button {
  background: none;
  border: none;
  color: var(--color-danger, #dc3545);
  cursor: pointer;
  padding: 0;
  font-size: 0.85rem;
}

.vc-inline-warning {
  color: var(--color-danger, #dc3545);
  font-size: 0.9rem;
  margin-bottom: var(--space-3);
}

.vc-diff-metrics {
  display: flex;
  gap: var(--space-3);
  font-size: 0.9rem;
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.vc-passage-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.vc-passage-column {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-3);
}

.vc-passage-heading {
  margin-bottom: var(--space-2);
}

.vc-passage-heading span {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--color-text-muted);
}

.vc-passage-text {
  font-size: 1.1rem;
  line-height: 1.6;
  margin-bottom: var(--space-2);
}

.vc-citation {
  font-size: 0.85rem;
  color: var(--color-text-muted);
}

.vc-diff-table-wrap {
  overflow-x: auto;
}

.vc-diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.9rem;
}

.vc-diff-table th,
.vc-diff-table td {
  border: 1px solid var(--color-border);
  padding: var(--space-2) var(--space-3);
  text-align: left;
}

.vc-diff-type {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--color-bg-muted);
  font-size: 0.8rem;
  font-weight: 600;
}

.vc-evidence-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: var(--space-3);
  margin-bottom: var(--space-3);
}

.vc-evidence-status {
  font-size: 0.8rem;
  padding: 2px 10px;
  border-radius: 12px;
  background: var(--color-warning-light, #fff8e1);
  color: #856404;
  flex-shrink: 0;
}

.vc-evidence-status.complete {
  background: var(--color-success-light, #d4edda);
  color: #155724;
}

.vc-back-link {
  color: var(--color-primary);
  text-decoration: none;
}

.vc-empty-state {
  text-align: center;
  padding: var(--space-6);
  color: var(--color-text-muted);
}

.vc-empty-hint {
  font-size: 0.85rem;
}

.vc-note-step textarea {
  width: 100%;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  resize: vertical;
  margin-bottom: var(--space-3);
}

.vc-note-step label {
  display: block;
  margin-bottom: var(--space-2);
  font-weight: 600;
}
</style>
