<template>
  <div class="v4-research">
    <!-- Back to current research -->
    <div v-if="researchStore.hasActiveResearch" class="back-to-research">
      <router-link :to="{ name: 'research-home' }" class="back-link">
        {{ t('researchEntry.backToResearch') }}
      </router-link>
      <span class="back-context">{{ researchStore.currentTopic?.name }}</span>
    </div>

    <header class="v4-header">
      <div>
        <p class="eyebrow">{{ t('v4.eyebrow') }}</p>
        <h1>{{ t('v4.title') }}</h1>
      </div>
    </header>

    <div class="v4-tabs" role="tablist">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        role="tab"
        :aria-selected="activeTab === tab.key"
        :class="['tab-button', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Full Research Workflow -->
    <section v-if="activeTab === 'research'" class="v4-panel">
      <h2>{{ t('v4.researchTitle') }}</h2>

      <form v-if="!workflowRunId" @submit.prevent="runWorkflow" class="v4-form">
        <label for="v4-topic">{{ t('v4.topicLabel') }}</label>
        <input
          id="v4-topic"
          v-model="topic"
          type="text"
          :placeholder="t('v4.topicPlaceholder')"
          :disabled="loading"
        />
        <button
          class="button button--primary"
          :disabled="loading || !topic.trim()"
          data-testid="v4-run-workflow"
        >
          {{ loading ? t('v4.workflowRunning') : t('v4.runWorkflow') }}
        </button>
        <p v-if="loading" class="elapsed-hint" aria-live="polite">
          {{ t('v4.elapsed', { seconds: elapsedSeconds }) }}
        </p>
      </form>

      <div v-else class="workflow-result">
        <h3>
          {{ workflowSuccess ? t('v4.runComplete') : t('v4.runPartial') }}
          <span v-if="loading" class="loading-hint">{{ t('common.loading') }}...</span>
          <span v-if="!loading" class="elapsed-hint">{{ t('v4.completedIn', { seconds: elapsedSeconds }) }}</span>
        </h3>

        <!-- Five-step status -->
        <ol class="step-list">
          <li
            v-for="step in steps"
            :key="step.name"
            :class="['step-item', step.status]"
            data-testid="workflow-step"
          >
            <span class="step-name">{{ stepName(step.name) }}</span>
            <span class="step-status">{{ stepStatusLabel(step) }}</span>
            <template v-if="step.status === 'failed' && step.result?.error">
              <p class="step-error-detail">{{ step.result.error }}</p>
              <p v-if="step.result.error_code" class="step-error-code">{{ step.result.error_code }}</p>
            </template>
          </li>
        </ol>

        <!-- No-evidence state: workflow returned success=false with zero retrieval records -->
        <div
          v-if="!workflowSuccess && steps.find(s => s.name === 'literature_retrieval' && s.result?.records === 0)"
          class="no-evidence-state"
          data-testid="no-evidence-state"
        >
          <p class="no-evidence-message">{{ error }}</p>
        </div>

        <!-- Report content -->
        <div v-if="reportContent" class="report-body">
          <h4>{{ t('v4.reportPreview') }}</h4>
          <pre class="report-text">{{ reportPreview }}</pre>
        </div>

        <!-- Citations -->
        <div v-if="citations.length" class="citations-section" data-testid="citations-section">
          <h4>{{ t('v4.citations') }} ({{ citations.length }})</h4>
          <details v-for="(cit, i) in citations" :key="cit.trace_id || i" class="citation-detail">
            <summary>
              <span class="cit-index">#{{ i + 1 }}</span>
              <span class="cit-text">{{ cit.claim_text?.slice(0, 120) || cit.citation_text?.slice(0, 120) || cit.quote?.slice(0, 120) || t('v4.untitledCitation') }}</span>
            </summary>
            <div class="citation-body">
              <p v-if="cit.claim_text"><strong>{{ t('v4.claimText') }}:</strong> {{ cit.claim_text }}</p>
              <p v-if="cit.quote"><strong>{{ t('v4.quote') }}:</strong> {{ cit.quote }}</p>
              <p v-if="cit.citation_text"><strong>{{ t('v4.citationText') }}:</strong> <code>{{ cit.citation_text }}</code></p>
              <p><strong>Trace ID:</strong> <code>{{ cit.trace_id }}</code></p>
              <p v-if="cit.document_id"><strong>Document ID:</strong> <code>{{ cit.document_id }}</code></p>
              <p v-if="cit.source_ref_id"><strong>SourceRef ID:</strong> <code>{{ cit.source_ref_id }}</code></p>
              <!-- P2-⑤: Create note from citation — only for real citations -->
              <button
                v-if="cit.claim_text || cit.citation_text || cit.document_id"
                class="button button--secondary button--sm"
                @click="noteFromCitation(cit)"
              >
                📝 {{ t('v4.noteFromCitation') }}
              </button>
            </div>
          </details>
        </div>

        <!-- Actions row: export + notes -->
        <div v-if="!loading" class="actions-row">
          <button
            class="button button--secondary"
            :disabled="!reportContent || exporting"
            data-testid="v4-export"
            @click="exportRecord"
          >
            {{ exporting ? t('v4.exporting') : t('v4.export') }}
          </button>

          <button
            class="button button--secondary"
            :disabled="!canSaveNote"
            data-testid="v4-toggle-note"
            @click="showNoteEditor = !showNoteEditor"
          >
            {{ t('v4.saveNote') }}
          </button>
        </div>

        <!-- Note editor -->
        <div v-if="showNoteEditor" class="note-editor" data-testid="note-editor">
          <label for="v4-note">{{ t('v4.noteLabel') }}</label>
          <textarea
            id="v4-note"
            v-model="noteContent"
            rows="5"
            :placeholder="t('v4.notePlaceholder')"
          ></textarea>
          <div class="note-actions">
            <button
              class="button button--primary"
              :disabled="!noteContent.trim() || savingNote"
              data-testid="v4-save-note"
              @click="saveNote"
            >
              {{ savingNote ? t('v4.saving') : t('v4.save') }}
            </button>
            <span v-if="noteMessage" class="note-feedback" aria-live="polite" data-testid="note-feedback">{{ noteMessage }}</span>
          </div>
        </div>

        <!-- Note feedback (persists after editor closes) -->
        <p v-if="noteMessage && !showNoteEditor" class="note-feedback note-feedback--standalone" aria-live="polite" data-testid="note-feedback-standalone">{{ noteMessage }}</p>

        <!-- P1-⑥: Re-search from report -->
        <div v-if="reportContent" class="re-search-section">
          <button
            class="button button--secondary"
            @click="reSearchFromReport"
            data-testid="v4-re-search"
          >
            🔍 {{ t('v4.reSearch') }}
          </button>
        </div>

        <!-- Replay -->
        <div v-if="workflowRunId" class="replay-section">
          <button
            class="button button--secondary"
            :disabled="replaying"
            data-testid="v4-replay"
            @click="replayRun"
          >
            {{ replaying ? t('v4.replaying') : t('v4.replay') }}
          </button>

          <div v-if="replayResult !== null" class="replay-result" data-testid="replay-result">
            <p :class="['match-badge', replayResult.matched ? 'match-ok' : 'match-fail']">
              {{ replayResult.matched ? t('v4.matchedTrue') : t('v4.matchedFalse') }}
            </p>
            <p><small>{{ t('v4.originalHash') }}: {{ replayResult.original_output_sha256 }}</small></p>
            <p><small>{{ t('v4.replayHash') }}: {{ replayResult.replay_output_sha256 }}</small></p>
          </div>
        </div>

        <!-- Runs list -->
        <div v-if="runs.length" class="runs-list">
          <h4>{{ t('v4.runs') }}</h4>
          <div v-for="run in runs" :key="run.run_id" class="run-entry">
            <p><strong>Run:</strong> <code>{{ run.run_id?.slice(0, 8) }}...</code></p>
            <p><small>{{ run.completed_at }}</small></p>
          </div>
        </div>

        <button class="button text-button" @click="resetWorkflow">
          {{ t('v4.newWorkflow') }}
        </button>
      </div>

      <p v-if="error" class="message message--error" role="alert">{{ error }}</p>
      <p v-if="workflowMessage" class="message message--info" aria-live="polite">{{ workflowMessage }}</p>
    </section>

    <!-- Education Mode -->
    <section v-if="activeTab === 'education'" class="v4-panel">
      <h2>{{ t('v4.educationTitle') }}</h2>

      <form @submit.prevent="runEducation" class="v4-form">
        <label for="v4-edu-topic">{{ t('v4.topicLabel') }}</label>
        <input
          id="v4-edu-topic"
          v-model="eduTopic"
          type="text"
          :placeholder="t('v4.topicPlaceholder')"
          :disabled="eduLoading"
        />
        <label for="v4-edu-level">{{ t('v4.levelLabel') }}</label>
        <select id="v4-edu-level" v-model="eduLevel" :disabled="eduLoading">
          <option value="beginner">{{ t('v4.beginner') }}</option>
          <option value="intermediate">{{ t('v4.intermediate') }}</option>
          <option value="advanced">{{ t('v4.advanced') }}</option>
        </select>
        <button
          class="button button--primary"
          :disabled="eduLoading || !eduTopic.trim()"
          data-testid="v4-run-education"
        >
          {{ eduLoading ? t('common.loading') : t('v4.learn') }}
        </button>
      </form>

      <div v-if="eduResult" class="edu-result" data-testid="edu-result">
        <p><strong>{{ t('v4.citationCount') }}:</strong> {{ eduResult.citation_count }}</p>
        <p><strong>{{ t('v4.sourceCount') }}:</strong> {{ eduResult.source_count }}</p>

        <article v-for="concept in eduResult.concepts" :key="concept.concept" class="concept-card">
          <h4>{{ concept.concept }} <span class="level-tag">{{ concept.level }}</span></h4>
          <p v-for="(p, i) in concept.paragraphs" :key="i">{{ p }}</p>
          <small>{{ t('v4.evidenceCount') }}: {{ concept.citation_count }}</small>
        </article>

        <div v-if="eduError" class="lineage-error">
          {{ eduError }}
        </div>
      </div>

      <p v-if="error" class="message message--error" role="alert">{{ error }}</p>
    </section>

    <!-- Visualization Mode -->
    <section v-if="activeTab === 'visualization'" class="v4-panel">
      <h2>{{ t('v4.vizTitle') }}</h2>

      <form @submit.prevent="runViz" class="v4-form">
        <label for="v4-viz-labels">{{ t('v4.conceptLabels') }}</label>
        <input
          id="v4-viz-labels"
          v-model="vizLabels"
          type="text"
          :placeholder="t('v4.labelsPlaceholder')"
          :disabled="vizLoading"
        />
        <label for="v4-viz-type">{{ t('v4.graphType') }}</label>
        <select id="v4-viz-type" v-model="vizType" :disabled="vizLoading">
          <option value="concept">{{ t('v4.graphConcept') }}</option>
          <option value="citation">{{ t('v4.graphCitation') }}</option>
          <option value="timeline">{{ t('v4.graphTimeline') }}</option>
          <option value="document">{{ t('v4.graphDocument') }}</option>
        </select>
        <button
          class="button button--primary"
          :disabled="vizLoading || !vizLabels.trim()"
          data-testid="v4-run-viz"
        >
          {{ vizLoading ? t('common.loading') : t('v4.generateGraph') }}
        </button>
      </form>

      <div v-if="vizResult" class="viz-result" data-testid="viz-result">
        <p><strong>{{ t('v4.nodes') }}:</strong> {{ vizResult.nodes?.length || 0 }}</p>
        <p><strong>{{ t('v4.edges') }}:</strong> {{ vizResult.edges?.length || 0 }}</p>

        <div v-if="vizResult.edges?.length" class="edge-list" data-testid="viz-edges">
          <div v-for="(edge, i) in vizResult.edges.slice(0, 10)" :key="i" class="edge-entry">
            <span class="edge-type">{{ edge.type }}</span>
            {{ edge.source?.slice(0, 20) }} → {{ edge.target?.slice(0, 20) }}
            <small>({{ edge.evidence_ids?.length || 0 }} evidence)</small>
          </div>
        </div>

        <p v-else class="empty-state" data-testid="viz-empty">
          {{ t('v4.noEvidence') }}
        </p>
      </div>

      <p v-if="error" class="message message--error" role="alert">{{ error }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useResearchStore } from '@/stores/research';

import api from '@/api/client';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const researchStore = useResearchStore();

// =========================================================================
// Tab state
// =========================================================================

const activeTab = ref<'research' | 'education' | 'visualization'>('research');
const tabs = [
  { key: 'research' as const, label: t('v4.tabResearch') },
  { key: 'education' as const, label: t('v4.tabEducation') },
  { key: 'visualization' as const, label: t('v4.tabViz') },
];

// =========================================================================
// Research workflow
// =========================================================================

const topic = ref('');
const loading = ref(false);
const error = ref('');
const workflowMessage = ref('');
const sessionId = ref('');
const workflowRunId = ref('');
const workflowSuccess = ref(false);
const steps = ref<Array<{ name: string; status: string; result?: Record<string, unknown> }>>([]);
const reportContent = ref('');
const citations = ref<Array<{ trace_id: string; claim_text: string; quote: string; citation_text: string; document_id: string; source_ref_id?: string }>>([]);
const elapsedSeconds = ref(0);
let elapsedTimer: ReturnType<typeof setInterval> | null = null;

// Export
const exporting = ref(false);

// Notes
const showNoteEditor = ref(false);
const noteContent = ref('');
const savingNote = ref(false);
const noteMessage = ref('');

const replaying = ref(false);
const replayResult = ref<{
  matched: boolean;
  original_output_sha256: string;
  replay_output_sha256: string;
} | null>(null);
const runs = ref<Array<{ run_id?: string; completed_at?: string; output_artifacts?: Record<string, unknown>; replay_manifest?: Record<string, unknown>; step_execution_trace?: Array<{ trace_ids?: string[] }> }>>([]);

const reportPreview = computed(() => {
  if (!reportContent.value) return '';
  return reportContent.value.length > 2000
    ? reportContent.value.slice(0, 2000) + '...'
    : reportContent.value;
});

const canSaveNote = computed(() => Boolean(sessionId.value && reportContent.value));

function startElapsedTimer() {
  elapsedSeconds.value = 0;
  stopElapsedTimer();
  elapsedTimer = setInterval(() => {
    elapsedSeconds.value += 1;
  }, 1000);
}

function stopElapsedTimer() {
  if (elapsedTimer !== null) {
    clearInterval(elapsedTimer);
    elapsedTimer = null;
  }
}

onBeforeUnmount(stopElapsedTimer);

// Load a specific run when navigated with ?run=xxx
onMounted(async () => {
  const runId = route.query.run as string | undefined;
  if (!runId) return;

  // Derive session_id from run_id: runs are keyed as {session_id}/{run_id_node}
  // We must search across the user's workspace sessions
  try {
    const sessionsResp = await api.get('/api/v1/workspace/sessions');
    const sessionsList = (sessionsResp.data.data ?? []) as Array<{ id: string; title: string }>;

    for (const s of sessionsList) {
      try {
        const runsResp = await api.get(`/api/v4/research/session/${s.id}/runs`);
        const runList = (runsResp.data.data?.runs ?? []) as Array<Record<string, unknown>>;
        const found = runList.find((r: Record<string, unknown>) => r.run_id === runId);
        if (found) {
          sessionId.value = s.id;
          workflowRunId.value = found.run_id as string;
          topic.value = (found.topic as string) || '';
          workflowSuccess.value = true;
          steps.value = (found.step_execution_trace || []) as Array<{ name: string; status: string; result?: Record<string, unknown> }>;
          runs.value = runList as Array<{ run_id?: string; completed_at?: string; output_artifacts?: Record<string, unknown>; replay_manifest?: Record<string, unknown>; step_execution_trace?: Array<{ trace_ids?: string[] }> }>;

          // Populate reportContent and citations
          const artifacts = found.output_artifacts as Record<string, unknown> | undefined;
          reportContent.value = (artifacts?.markdown as string) || '';
          citations.value = extractCitationsFromRuns(runs.value);
          workflowMessage.value = t('v4.workflowCompleted');
          break;
        }
      } catch { /* skip session */ }
    }

    if (!workflowRunId.value) {
      workflowMessage.value = `未找到运行记录: ${runId}`;
    }
  } catch { /* ignore */ }
});

function stepName(name: string): string {
  const map: Record<string, string> = {
    topic_selection: t('v4.stepTopic'),
    literature_retrieval: t('v4.stepRetrieval'),
    evidence_synthesis: t('v4.stepSynthesis'),
    report_generation: t('v4.stepReport'),
    citation_export: t('v4.stepCitation'),
  };
  return map[name] || name;
}

function stepStatusLabel(step: { name: string; status: string; result?: Record<string, unknown> }): string {
  if (step.status === 'completed') {
    const result = step.result;
    if (result) {
      if (step.name === 'topic_selection' && result.sub_questions !== undefined) {
        return `${t('v4.completed')} (${result.sub_questions} sub-questions)`;
      }
      if (step.name === 'literature_retrieval' && result.records !== undefined) {
        return `${t('v4.completed')} (${result.themes} themes, ${result.records} records)`;
      }
      if (step.name === 'evidence_synthesis' && result.claims !== undefined) {
        return `${t('v4.completed')} (${result.sections} sections, ${result.claims} claims)`;
      }
      if (step.name === 'report_generation' && result.sections !== undefined) {
        return `${t('v4.completed')} (${result.sections} sections)`;
      }
      if (step.name === 'citation_export' && result.total_citations !== undefined) {
        return `${t('v4.completed')} (${result.total_citations} citations)`;
      }
    }
    return t('v4.completed');
  }
  if (step.status === 'failed') return t('v4.failed');
  return step.status;
}

function extractCitationsFromRuns(runList: typeof runs.value): Array<{ trace_id: string; claim_text: string; quote: string; citation_text: string; document_id: string; source_ref_id?: string }> {
  const result: Array<{ trace_id: string; claim_text: string; quote: string; citation_text: string; document_id: string; source_ref_id?: string }> = [];
  const seen = new Set<string>();

  for (const run of runList) {
    // Build a trace_id → snapshot entry map from retrieval_snapshot
    const snapshotMap = new Map<string, Record<string, unknown>>();
    const manifest = run.replay_manifest;
    if (manifest?.retrieval_snapshot && Array.isArray(manifest.retrieval_snapshot)) {
      for (const rec of manifest.retrieval_snapshot as Array<Record<string, unknown>>) {
        const tid = rec.trace_id as string;
        if (tid) snapshotMap.set(tid, rec);
      }
    }

    // Try replay_manifest.traces first, cross-referencing with snapshot
    if (manifest?.traces && Array.isArray(manifest.traces)) {
      for (const tr of manifest.traces as Array<Record<string, unknown>>) {
        const tid = tr.trace_id as string;
        if (!tid || seen.has(tid)) continue;
        seen.add(tid);
        const snap = snapshotMap.get(tid) || {};
        result.push({
          trace_id: tid,
          claim_text: (snap.claim_text as string) || '',
          citation_text: (snap.citation_text as string) || (tr.citation_text as string) || '',
          quote: (snap.quote as string) || (tr.quote as string) || '',
          document_id: (snap.document_id as string) || (tr.document_id as string) || '',
          source_ref_id: (snap.source_ref_id as string) || (tr.source_ref_id as string) || undefined,
        });
      }
    }

    // Build directly from snapshot entries if no traces array present
    if (result.length === 0 && snapshotMap.size > 0) {
      for (const [tid, snap] of snapshotMap) {
        if (seen.has(tid)) continue;
        seen.add(tid);
        result.push({
          trace_id: tid,
          claim_text: (snap.claim_text as string) || '',
          citation_text: (snap.citation_text as string) || '',
          quote: (snap.quote as string) || '',
          document_id: (snap.document_id as string) || '',
          source_ref_id: (snap.source_ref_id as string) || undefined,
        });
      }
    }
  }
  return result;
}

async function ensureSession(): Promise<string> {
  if (sessionId.value) return sessionId.value;
  const { data } = await api.post('/api/v4/research/session', {
    title: `V4 研究 - ${topic.value || '未命名'}`,
  });
  sessionId.value = data.data.session_id as string;
  return sessionId.value;
}

async function runWorkflow() {
  loading.value = true;
  error.value = '';
  workflowMessage.value = t('v4.workflowRunning');
  startElapsedTimer();
  try {
    const sid = await ensureSession();

    // Use per-call timeout override: 120s for the long-running workflow
    const { data } = await api.post('/api/v4/research/workflow', {
      session_id: sid,
      topic: topic.value.trim(),
      workflow_type: 'full_research_flow',
    }, {
      timeout: 120000, // 2 minutes — backend takes ~14s for this flow
    });

    workflowSuccess.value = data.success === true;
    workflowRunId.value = data.data.run_id as string;
    steps.value = (data.data.steps as Array<{ name: string; status: string; result?: Record<string, unknown> }>) || [];
    reportContent.value = '';

    if (!data.success) {
      workflowMessage.value = '';
      error.value = data.message || t('v4.workflowFailed');
    } else {
      workflowMessage.value = t('v4.workflowCompleted');
    }

    // Fetch runs for the session
    const runsResp = await api.get(`/api/v4/research/session/${sid}/runs`);
    runs.value = (runsResp.data.data.runs as Array<Record<string, unknown>>) || [];
    const lastRun = runs.value[runs.value.length - 1];
    if (lastRun?.output_artifacts) {
      const artifacts = lastRun.output_artifacts as Record<string, unknown>;
      reportContent.value = (artifacts.markdown as string) || '';
    }

    // Extract citations
    citations.value = extractCitationsFromRuns(runs.value);
  } catch (err: unknown) {
    workflowMessage.value = '';
    error.value = getErrorMessage(err, t('v4.workflowFailed'));
    // Still try to show partial results if session was created
    if (sessionId.value) {
      try {
        const runsResp = await api.get(`/api/v4/research/session/${sessionId.value}/runs`);
        runs.value = (runsResp.data.data.runs as Array<Record<string, unknown>>) || [];
        const lastRun = runs.value[runs.value.length - 1];
        if (lastRun?.output_artifacts) {
          const artifacts = lastRun.output_artifacts as Record<string, unknown>;
          reportContent.value = (artifacts.markdown as string) || '';
          citations.value = extractCitationsFromRuns(runs.value);
          // If we have data despite the error, show a partial state
          if (reportContent.value || citations.value.length) {
            workflowRunId.value = (lastRun.run_id as string) || '';
            workflowMessage.value = t('v4.partialResults');
          }
        }
      } catch {
        // Ignore secondary failures
      }
    }
  } finally {
    loading.value = false;
    stopElapsedTimer();
  }
}

async function replayRun() {
  if (!workflowRunId.value) return;
  replaying.value = true;
  replayResult.value = null;
  try {
    const { data } = await api.post(`/api/v4/research/runs/${workflowRunId.value}/replay`);
    replayResult.value = {
      matched: data.data.matched as boolean,
      original_output_sha256: data.data.original_output_sha256 as string,
      replay_output_sha256: data.data.replay_output_sha256 as string,
    };
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('v4.replayFailed'));
  } finally {
    replaying.value = false;
  }
}

async function exportRecord() {
  if (!reportContent.value) return;
  exporting.value = true;
  error.value = '';
  try {
    // P1-⑥: Append session notes to the report before export
    let content = reportContent.value;
    if (sessionId.value) {
      try {
        const notesResp = await api.get(`/api/v1/workspace/sessions/${sessionId.value}/notes`);
        const notesList = (notesResp.data.data ?? []) as Array<{ content: string; created_at: string; tags?: string }>;
        if (notesList.length > 0) {
          content += '\n\n---\n\n## 研究笔记\n\n';
          for (const note of notesList) {
            const date = note.created_at ? new Date(note.created_at).toLocaleString('zh-CN') : '';
            content += `> ${date}\n\n${note.content}\n\n---\n\n`;
          }
        }
      } catch { /* notes fetch failed, export without notes */ }
    }

    const blob = new Blob([content], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `hfb-research-report-${workflowRunId.value?.slice(0, 8) || 'report'}.md`;
    link.click();
    URL.revokeObjectURL(url);
    workflowMessage.value = t('v4.exported');
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('v4.exportFailed'));
  } finally {
    exporting.value = false;
  }
}

async function saveNote() {
  if (!sessionId.value || !noteContent.value.trim()) return;
  savingNote.value = true;
  noteMessage.value = '';
  error.value = '';
  try {
    const resp = await api.post(`/api/v1/workspace/sessions/${sessionId.value}/notes`, {
      content: noteContent.value.trim(),
      entity_type: 'v4_research_workflow',
      entity_id: workflowRunId.value || sessionId.value,
      tags: 'V4研究',
    });
    if (resp.data?.success !== false) {
      noteMessage.value = t('v4.noteSaved');
      noteContent.value = '';
      showNoteEditor.value = false;
    } else {
      noteMessage.value = resp.data?.message || t('v4.noteFailed');
    }
  } catch (err: unknown) {
    noteMessage.value = getErrorMessage(err, t('v4.noteFailed'));
  } finally {
    savingNote.value = false;
  }
}

// P1-⑥: Re-search from report — extract keywords and navigate to search
function reSearchFromReport() {
  if (!reportContent.value) return;
  // Extract first heading or first meaningful line as search query
  const lines = reportContent.value.split('\n').filter(l => l.trim() && !l.startsWith('#') && l.length > 10);
  const query = topic.value || lines[0]?.slice(0, 60) || '';
  router.push({ name: 'search', query: { q: encodeURIComponent(query) } });
}

// P2-⑤: Create a note from a citation in V4ResearchView
async function noteFromCitation(cit: { trace_id: string; claim_text: string; quote: string; citation_text: string; document_id: string }) {
  // Reject citations with no real content
  if (!cit.trace_id || (!cit.claim_text && !cit.citation_text && !cit.quote && !cit.document_id)) return;
  if (!sessionId.value) {
    try {
      const { data } = await api.post('/api/v1/workspace/sessions', { title: `研究 - ${topic.value || '未命名'}` });
      sessionId.value = data.data?.id as string;
    } catch { return; }
  }
  try {
    await api.post(`/api/v1/workspace/sessions/${sessionId.value}/notes`, {
      content: `引用: ${cit.citation_text || cit.claim_text || cit.quote || '—'}\n\n---\n\n`,
      entity_type: 'citation',
      entity_id: cit.trace_id,
      tags: '引用笔记',
    });
    noteMessage.value = t('v4.noteSaved');
  } catch { noteMessage.value = t('v4.noteFailed'); }
}

function resetWorkflow() {
  workflowRunId.value = '';
  workflowSuccess.value = false;
  steps.value = [];
  reportContent.value = '';
  citations.value = [];
  replayResult.value = null;
  runs.value = [];
  sessionId.value = '';
  topic.value = '';
  error.value = '';
  workflowMessage.value = '';
  elapsedSeconds.value = 0;
  showNoteEditor.value = false;
  noteContent.value = '';
  noteMessage.value = '';
}

// =========================================================================
// Education
// =========================================================================

const eduTopic = ref('');
const eduLevel = ref<'beginner' | 'intermediate' | 'advanced'>('beginner');
const eduLoading = ref(false);
const eduResult = ref<{
  concepts: Array<{ concept: string; level: string; paragraphs: string[]; citation_count: number }>;
  citation_count: number;
  source_count: number;
} | null>(null);
const eduError = ref('');

async function runEducation() {
  eduLoading.value = true;
  eduResult.value = null;
  eduError.value = '';
  error.value = '';
  try {
    const sid = await ensureSession();
    const { data } = await api.post('/api/v4/education/learn', {
      session_id: sid,
      topic: eduTopic.value.trim(),
      level: eduLevel.value,
    });

    if (data.success) {
      eduResult.value = data.data;
    } else {
      eduError.value = data.message || data.data?.detail || t('v4.educationFailed');
    }
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('v4.educationFailed'));
  } finally {
    eduLoading.value = false;
  }
}

// =========================================================================
// Visualization
// =========================================================================

const vizLabels = ref('');
const vizType = ref<'concept' | 'citation' | 'timeline' | 'document'>('concept');
const vizLoading = ref(false);
const vizResult = ref<{ nodes: Array<Record<string, unknown>>; edges: Array<{ type?: string; source?: string; target?: string; evidence_ids?: unknown[] }> } | null>(null);

async function runViz() {
  vizLoading.value = true;
  vizResult.value = null;
  error.value = '';
  try {
    const sid = await ensureSession();
    const labels = vizLabels.value
      .split(/[,，、]/)
      .map((s) => s.trim())
      .filter(Boolean);

    const { data } = await api.post('/api/v4/visualization/graph', {
      session_id: sid,
      concept_labels: labels.length ? labels : ['针灸'],
      graph_type: vizType.value,
    });

    if (data.success) {
      vizResult.value = data.data;
    } else {
      error.value = data.message || t('v4.vizFailed');
    }
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('v4.vizFailed'));
  } finally {
    vizLoading.value = false;
  }
}

// =========================================================================
// Helpers
// =========================================================================

function getErrorMessage(err: unknown, fallback: string): string {
  if (typeof err === 'object' && err !== null) {
    const e = err as Record<string, unknown>;
    // Axios timeout
    if (e.code === 'ECONNABORTED' || e.code === 'ETIMEDOUT') {
      return t('v4.timeoutError');
    }
    // Axios network error
    if (e.code === 'ERR_NETWORK' || e.message === 'Network Error') {
      return t('v4.networkError');
    }
    // Axios response error
    if ('response' in e) {
      const resp = (e as { response?: { status?: number; data?: { detail?: string; message?: string } } }).response;
      if (resp?.data?.detail) return resp.data.detail;
      if (resp?.data?.message) return resp.data.message;
      if (resp?.status) return `${t('v4.httpError')} ${resp.status}`;
    }
    if (e.message && typeof e.message === 'string') return e.message;
  }
  return err instanceof Error ? err.message : fallback;
}
</script>

<style scoped>
/* --- Back to research --- */
.back-to-research {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  margin-bottom: 4px;
}

.back-link {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent, #4299e1);
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.back-context {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.v4-research {
  width: min(1200px, 100%);
  margin: 0 auto;
  padding: 24px;
  color: var(--color-text-primary, #17202a);
}

.v4-header { margin-bottom: 16px; }

.eyebrow {
  margin: 0 0 4px;
  color: #8a3b2f;
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

h1 { margin: 0; font-size: 26px; }
h2 { font-size: 18px; margin: 16px 0 12px; }
h3 { font-size: 16px; margin: 12px 0 8px; }
h4 { font-size: 14px; margin: 8px 0 4px; }

.v4-tabs {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--color-border, #d8dee6);
  margin-bottom: 20px;
}

.tab-button {
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: var(--color-text-muted, #7b8794);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}

.tab-button.active {
  color: #1f5f55;
  border-bottom-color: #1f5f55;
}

.v4-form {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 520px;
}

.v4-form label {
  font-size: 12px;
  font-weight: 700;
  margin-bottom: -6px;
}

input, select, textarea {
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid var(--color-border, #cfd6de);
  border-radius: 4px;
  font: inherit;
}

textarea {
  min-height: 80px;
  resize: vertical;
  line-height: 1.6;
}

.button {
  min-height: 36px;
  padding: 7px 13px;
  border: 1px solid transparent;
  border-radius: 4px;
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.button--primary { background: #1f5f55; color: #fff; }
.button--secondary { border-color: var(--color-border, #bcc6d0); background: transparent; color: var(--color-text-primary); }

.button:disabled { opacity: 0.45; cursor: not-allowed; }
.text-button { border: none; background: none; color: #8a3b2f; padding: 4px 0; cursor: pointer; }

.elapsed-hint {
  color: var(--color-text-muted, #687482);
  font-size: 12px;
  margin-top: 2px;
}

.step-list {
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
  margin: 12px 0;
}

.step-item {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: flex-start;
  padding: 8px 10px;
  border-radius: 4px;
  font-size: 13px;
  gap: 4px 12px;
}

.step-item.completed { background: #e8f4ef; color: #1f5f55; }
.step-item.failed { background: #fff0ef; color: #8f2f25; }
.step-item.pending { background: #f5f5f5; color: #7b8794; }

.step-error-detail {
  width: 100%;
  margin: 4px 0 0;
  font-size: 12px;
  color: #8f2f25;
}

.step-error-code {
  width: 100%;
  margin: 2px 0 0;
  font-size: 11px;
  font-family: monospace;
  color: #a04036;
}

.replay-section {
  margin: 16px 0;
  padding: 12px;
  border: 1px solid var(--color-border, #d8dee6);
  border-radius: 4px;
}

.replay-result { margin-top: 8px; }

.match-badge {
  display: inline-block;
  padding: 4px 10px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 700;
}

.match-ok { background: #e8f4ef; color: #1f5f55; }
.match-fail { background: #fff0ef; color: #8f2f25; }

.report-body {
  margin: 12px 0;
  padding: 12px;
  border: 1px solid var(--color-border, #d8dee6);
  border-radius: 4px;
}

.report-text {
  white-space: pre-wrap;
  font-size: 12px;
  max-height: 400px;
  overflow-y: auto;
  background: #fafafa;
  padding: 8px;
  line-height: 1.7;
}

/* Citations */
.citations-section {
  margin: 16px 0;
  padding: 12px;
  border: 1px solid var(--color-border, #d8dee6);
  border-radius: 4px;
}

.citation-detail {
  margin: 6px 0;
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border, #e8ecf0);
}

.citation-detail summary {
  cursor: pointer;
  display: flex;
  gap: 8px;
  align-items: baseline;
  font-size: 13px;
  padding: 4px 0;
}

.cit-index {
  flex-shrink: 0;
  color: #8a3b2f;
  font-weight: 700;
  font-size: 12px;
}

.cit-text {
  color: var(--color-text-primary, #17202a);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.citation-body {
  padding: 8px 12px;
  margin-top: 4px;
  background: #fafafa;
  border-radius: 4px;
  font-size: 12px;
  line-height: 1.7;
}

.citation-body code {
  font-size: 11px;
  background: #eee;
  padding: 1px 4px;
  border-radius: 2px;
}

/* Actions & Notes */
.actions-row {
  display: flex;
  gap: 10px;
  margin: 16px 0;
}

.note-editor {
  margin: 12px 0;
  padding: 12px;
  border: 1px solid var(--color-border, #d8dee6);
  border-radius: 4px;
}

.note-editor label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
}

.note-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
}

.note-feedback {
  font-size: 12px;
  color: #1f5f55;
}

.note-feedback--standalone {
  margin-top: 8px;
  padding: 6px 10px;
  background: #e8f4ef;
  border-radius: 4px;
}

.runs-list { margin-top: 16px; }
.run-entry {
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border, #e8ecf0);
  font-size: 13px;
}
.run-entry code {
  font-size: 12px;
  background: #f5f5f5;
  padding: 1px 4px;
  border-radius: 2px;
}

.concept-card {
  padding: 12px;
  margin: 8px 0;
  border: 1px solid var(--color-border, #d8dee6);
  border-radius: 4px;
}

.level-tag {
  font-size: 11px;
  background: #1f5f55;
  color: #fff;
  padding: 1px 6px;
  border-radius: 3px;
}

.lineage-error {
  padding: 10px;
  margin: 8px 0;
  background: #fff0ef;
  color: #8f2f25;
  font-size: 13px;
}

.edge-list { margin-top: 10px; }

.edge-entry {
  padding: 6px 0;
  border-bottom: 1px solid var(--color-border, #e8ecf0);
  font-size: 13px;
}

.edge-type {
  display: inline-block;
  padding: 1px 6px;
  border-radius: 3px;
  margin-right: 6px;
  background: #e8f4ef;
  color: #1f5f55;
  font-size: 11px;
  font-weight: 700;
}

.empty-state, .loading-hint {
  color: var(--color-text-muted, #7b8794);
  font-size: 13px;
}

.message--error {
  padding: 9px 11px;
  background: #fff0ef;
  color: #8f2f25;
  border-radius: 4px;
  margin: 8px 0;
}

.message--info {
  padding: 9px 11px;
  background: #e8f4ef;
  color: #1f5f55;
  border-radius: 4px;
  margin: 8px 0;
}
</style>
