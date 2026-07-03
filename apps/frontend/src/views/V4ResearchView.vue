<template>
  <div class="v4-research">
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
          {{ loading ? t('common.loading') : t('v4.runWorkflow') }}
        </button>
      </form>

      <div v-else class="workflow-result">
        <h3>
          {{ t('v4.runComplete') }}
          <span v-if="loading" class="loading-hint">{{ t('common.loading') }}...</span>
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
            <span class="step-status">{{ step.status }}</span>
          </li>
        </ol>

        <!-- Report content -->
        <div v-if="reportContent" class="report-body">
          <h4>{{ t('v4.reportPreview') }}</h4>
          <pre class="report-text">{{ reportPreview }}</pre>
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
        <div class="runs-list">
          <h4>{{ t('v4.runs') }}</h4>
          <div v-for="run in runs" :key="run.run_id" class="run-entry">
            <p><strong>Run:</strong> {{ run.run_id?.slice(0, 8) }}...</p>
            <p><small>{{ run.completed_at }}</small></p>
          </div>
        </div>

        <button class="button text-button" @click="resetWorkflow">
          {{ t('v4.newWorkflow') }}
        </button>
      </div>

      <p v-if="error" class="message message--error" role="alert">{{ error }}</p>
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
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import api from '@/api/client';

const { t } = useI18n();

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
const sessionId = ref('');
const workflowRunId = ref('');
const steps = ref<Array<{ name: string; status: string }>>([]);
const reportContent = ref('');
const replaying = ref(false);
const replayResult = ref<{
  matched: boolean;
  original_output_sha256: string;
  replay_output_sha256: string;
} | null>(null);
const runs = ref<Array<{ run_id?: string; completed_at?: string; output_artifacts?: Record<string, unknown> }>>([]);

const reportPreview = computed(() => {
  if (!reportContent.value) return '';
  return reportContent.value.length > 2000
    ? reportContent.value.slice(0, 2000) + '...'
    : reportContent.value;
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
  try {
    const sid = await ensureSession();
    const { data } = await api.post('/api/v4/research/workflow', {
      session_id: sid,
      topic: topic.value.trim(),
      workflow_type: 'full_research_flow',
    });

    if (data.success) {
      workflowRunId.value = data.data.run_id as string;
      steps.value = (data.data.steps as Array<{ name: string; status: string }>) || [];
      reportContent.value = ''; // Markdown artifact is in runs
    } else {
      error.value = data.message || t('v4.workflowFailed');
    }

    // Fetch runs for the session
    const runsResp = await api.get(`/api/v4/research/session/${sid}/runs`);
    runs.value = (runsResp.data.data.runs as Array<Record<string, unknown>>) || [];
    const lastRun = runs.value[runs.value.length - 1];
    if (lastRun?.output_artifacts) {
      const artifacts = lastRun.output_artifacts as Record<string, unknown>;
      reportContent.value = (artifacts.markdown as string) || '';
    }
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('v4.workflowFailed'));
  } finally {
    loading.value = false;
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

function resetWorkflow() {
  workflowRunId.value = '';
  steps.value = [];
  reportContent.value = '';
  replayResult.value = null;
  runs.value = [];
  sessionId.value = '';
  topic.value = '';
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
  if (typeof err === 'object' && err !== null && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    return resp?.data?.detail || fallback;
  }
  return err instanceof Error ? err.message : fallback;
}
</script>

<style scoped>
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

input, select {
  min-height: 40px;
  padding: 8px 10px;
  border: 1px solid var(--color-border, #cfd6de);
  border-radius: 4px;
  font: inherit;
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

.step-list {
  padding: 0;
  list-style: none;
  display: grid;
  gap: 6px;
  margin: 12px 0;
}

.step-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 13px;
}

.step-item.completed { background: #e8f4ef; color: #1f5f55; }
.step-item.failed { background: #fff0ef; color: #8f2f25; }
.step-item.pending { background: #f5f5f5; color: #7b8794; }

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
  max-height: 300px;
  overflow-y: auto;
  background: #fafafa;
  padding: 8px;
}

.runs-list { margin-top: 16px; }
.run-entry { padding: 6px 0; border-bottom: 1px solid var(--color-border, #e8ecf0); }

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
}
</style>
