<template>
  <div class="research-workflow">
    <!-- Back to current research -->
    <div v-if="researchStore.hasActiveResearch" class="back-to-research">
      <router-link :to="{ name: 'research-home' }" class="back-link">
        {{ t('researchEntry.backToResearch') }}
      </router-link>
      <span class="back-context">{{ researchStore.currentTopic?.name }}</span>
    </div>

    <header class="workflow-header">
      <div>
        <p class="eyebrow">{{ t('research.eyebrow') }}</p>
        <h1>{{ t('research.title') }}</h1>
      </div>
      <button
        class="button button--secondary"
        :disabled="!comparison || exporting"
        @click="exportRecord"
      >
        {{ exporting ? t('research.exporting') : t('research.export') }}
      </button>
    </header>

    <div v-if="showValidationBanner" class="validation-banner" role="status">
      <strong>{{ t('research.validationTitle') }}</strong>
      <span>{{ t('research.validationMessage') }}</span>
    </div>

    <ol class="workflow-steps" aria-label="Research workflow progress">
      <li :class="{ active: currentStep >= 1 }">1. {{ t('research.stepSearch') }}</li>
      <li :class="{ active: currentStep >= 2 }">2. {{ t('research.stepCompare') }}</li>
      <li :class="{ active: currentStep >= 3 }">3. {{ t('research.stepEvidence') }}</li>
      <li :class="{ active: currentStep >= 4 }">4. {{ t('research.stepRecord') }}</li>
    </ol>

    <p v-if="error" class="message message--error" role="alert">{{ error }}</p>
    <p v-if="message" class="message message--success" aria-live="polite">{{ message }}</p>

    <div class="workflow-grid">
      <section class="search-panel" aria-labelledby="passage-search-title">
        <div class="section-heading">
          <div>
            <p class="section-number">01</p>
            <h2 id="passage-search-title">{{ t('research.findPassage') }}</h2>
          </div>
          <span v-if="searchResults.length" class="result-count">
            {{ t('research.resultCount', { count: searchResults.length }) }}
          </span>
        </div>

        <form class="search-form" @submit.prevent="searchPassages">
          <label for="research-query">{{ t('research.searchLabel') }}</label>
          <div class="search-row">
            <input
              id="research-query"
              v-model="query"
              type="search"
              :placeholder="t('research.searchPlaceholder')"
            />
            <button
              data-testid="search-passages"
              class="button button--primary"
              :disabled="searching || !query.trim()"
            >
              {{ searching ? t('common.loading') : t('common.search') }}
            </button>
          </div>
        </form>

        <div v-if="searchResults.length" class="search-results">
          <article v-for="item in searchResults" :key="item.id" class="result-item">
            <div class="result-main">
              <div class="result-meta">
                <span>{{ item.metadata.version_name || t('research.unknownVersion') }}</span>
                <span>{{ item.metadata.chapter_title || t('research.unknownChapter') }}</span>
              </div>
              <p>{{ item.snippet || item.title }}</p>
              <small>
                {{ provenanceLabel(item) }}
              </small>
            </div>
            <div class="result-actions">
              <button
                class="button button--compact"
                :class="{ selected: sourcePassage?.id === item.id }"
                @click="selectPassage(item, 'source')"
              >
                {{ t('research.setSource') }}
              </button>
              <button
                class="button button--compact"
                :class="{ selected: targetPassage?.id === item.id }"
                @click="selectPassage(item, 'target')"
              >
                {{ t('research.setTarget') }}
              </button>
            </div>
          </article>
        </div>
        <div v-else-if="searched && !searching" class="empty-state">
          <p>{{ t('research.noPassages') }}</p>
          <p class="empty-hint">{{ t('onboarding.noPassagesHint') }}</p>
        </div>
      </section>

      <section class="selection-panel" aria-labelledby="selection-title">
        <div class="section-heading">
          <div>
            <p class="section-number">02</p>
            <h2 id="selection-title">{{ t('research.chooseVersions') }}</h2>
          </div>
        </div>

        <div class="selection-slots">
          <div class="selection-slot">
            <span class="slot-label">{{ t('research.source') }}</span>
            <template v-if="sourcePassage">
              <strong>{{ sourcePassage.metadata.version_name }}</strong>
              <p>{{ sourcePassage.title }}</p>
              <button class="text-button" @click="sourcePassage = null">
                {{ t('common.delete') }}
              </button>
            </template>
            <p v-else class="slot-empty">{{ t('research.selectSourceHint') }}</p>
          </div>

          <div class="selection-slot">
            <span class="slot-label">{{ t('research.target') }}</span>
            <template v-if="targetPassage">
              <strong>{{ targetPassage.metadata.version_name }}</strong>
              <p>{{ targetPassage.title }}</p>
              <button class="text-button" @click="targetPassage = null">
                {{ t('common.delete') }}
              </button>
            </template>
            <p v-else class="slot-empty">{{ t('research.selectTargetHint') }}</p>
          </div>
        </div>

        <p v-if="sameVersion" class="inline-warning">
          {{ t('research.differentVersionRequired') }}
        </p>
        <button
          data-testid="compare-passages"
          class="button button--primary button--wide"
          :disabled="!canCompare || comparing"
          @click="runComparison"
        >
          {{ comparing ? t('research.comparing') : t('research.compare') }}
        </button>
      </section>
    </div>

    <section v-if="comparison" class="comparison-panel" aria-labelledby="comparison-title">
      <div class="section-heading">
        <div>
          <p class="section-number">03</p>
          <h2 id="comparison-title">{{ t('research.comparisonResult') }}</h2>
        </div>
        <div class="comparison-metrics">
          <span>{{ t('research.differenceCount', { count: comparison.comparison.differences }) }}</span>
          <span>{{ formatSimilarity(comparison.comparison.similarity_ratio) }}</span>
        </div>
      </div>

      <div class="passage-columns">
        <article class="passage-column">
          <div class="passage-heading">
            <span>{{ t('research.source') }}</span>
            <strong>{{ comparison.source.version.name }}</strong>
          </div>
          <p class="passage-text">{{ comparison.source.text }}</p>
          <p class="citation">{{ comparison.source.citation }}</p>
        </article>

        <article class="passage-column">
          <div class="passage-heading">
            <span>{{ t('research.target') }}</span>
            <strong>{{ comparison.target.version.name }}</strong>
          </div>
          <p class="passage-text">{{ comparison.target.text }}</p>
          <p class="citation">{{ comparison.target.citation }}</p>
        </article>
      </div>

      <div v-if="comparison.comparison.operations.length" class="diff-table-wrap">
        <table class="diff-table">
          <thead>
            <tr>
              <th>{{ t('research.diffType') }}</th>
              <th>{{ t('research.sourceText') }}</th>
              <th>{{ t('research.targetText') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(operation, index) in comparison.comparison.operations" :key="index">
              <td><span class="diff-type">{{ operation.op }}</span></td>
              <td>{{ operation.source_text || '—' }}</td>
              <td>{{ operation.target_text || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="empty-state">{{ t('research.noDifferences') }}</p>
    </section>

    <div v-if="comparison" class="workflow-grid workflow-grid--lower">
      <section class="evidence-panel" aria-labelledby="evidence-title">
        <div class="section-heading">
          <div>
            <p class="section-number">04</p>
            <h2 id="evidence-title">{{ t('research.verifyEvidence') }}</h2>
          </div>
        </div>

        <div
          v-for="item in [comparison.source, comparison.target]"
          :key="item.passage_id"
          class="evidence-row"
        >
          <div>
            <strong>{{ item.version.name }}</strong>
            <p>{{ item.version.repository || t('research.missingRepository') }}</p>
            <small>{{ item.version.shelf_mark || t('research.missingShelfMark') }}</small>
          </div>
          <span :class="['evidence-status', { complete: item.evidence_complete }]">
            {{ item.evidence_complete ? t('research.complete') : t('research.incomplete') }}
          </span>
        </div>
      </section>

      <section class="note-panel" aria-labelledby="note-title">
        <div class="section-heading">
          <div>
            <p class="section-number">05</p>
            <h2 id="note-title">{{ t('research.writeNote') }}</h2>
          </div>
        </div>
        <label for="research-note">{{ t('research.noteLabel') }}</label>
        <textarea
          id="research-note"
          v-model="noteContent"
          rows="7"
          :placeholder="t('research.notePlaceholder')"
        ></textarea>
        <button
          class="button button--primary"
          :disabled="!noteContent.trim() || savingNote"
          @click="saveNote"
        >
          {{ savingNote ? t('research.saving') : t('research.saveNote') }}
        </button>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { useResearchStore } from '@/stores/research';

import api from '@/api/client';

const { t } = useI18n();
const researchStore = useResearchStore();

interface PassageSearchResult {
  id: string;
  title: string;
  snippet: string | null;
  metadata: {
    version_id?: string;
    version_name?: string;
    repository?: string | null;
    shelf_mark?: string | null;
    chapter_title?: string;
  };
}

interface EvidenceSnapshot {
  passage_id: string;
  text: string;
  citation: string;
  evidence_complete: boolean;
  version: {
    id: string;
    name: string;
    repository: string | null;
    shelf_mark: string | null;
  };
}

interface ComparisonState {
  workflow_type: string;
  corpus_status: 'validation' | 'approved';
  source: EvidenceSnapshot;
  target: EvidenceSnapshot;
  comparison: {
    differences: number;
    similarity_ratio: number;
    operations: Array<{
      op: string;
      source_text: string;
      target_text: string;
    }>;
  };
}

interface ResearchSession {
  id: string;
  title: string;
}

const query = ref('');
const searchResults = ref<PassageSearchResult[]>([]);
const sourcePassage = ref<PassageSearchResult | null>(null);
const targetPassage = ref<PassageSearchResult | null>(null);
const comparison = ref<ComparisonState | null>(null);
const sessionId = ref<string | null>(null);
const noteContent = ref('');
const searching = ref(false);
const searched = ref(false);
const comparing = ref(false);
const savingNote = ref(false);
const exporting = ref(false);
const noteSaved = ref(false);
const error = ref('');
const message = ref('');

const sameVersion = computed(
  () =>
    Boolean(sourcePassage.value?.metadata.version_id) &&
    sourcePassage.value?.metadata.version_id === targetPassage.value?.metadata.version_id,
);
const canCompare = computed(
  () => Boolean(sourcePassage.value && targetPassage.value && !sameVersion.value),
);
const currentStep = computed(() => {
  if (noteSaved.value || noteContent.value.trim()) return 4;
  if (comparison.value) return 3;
  if (sourcePassage.value && targetPassage.value) return 2;
  return 1;
});

const showValidationBanner = computed(() => {
  // Hide the banner only when a comparison exists AND corpus_status is 'approved'
  if (comparison.value && comparison.value.corpus_status === 'approved') {
    return false;
  }
  return true;
});

async function searchPassages() {
  if (!query.value.trim()) return;
  searching.value = true;
  searched.value = true;
  error.value = '';
  try {
    const { data } = await api.get('/api/v1/search', {
      params: { q: query.value.trim(), types: 'passage', limit: 50 },
    });
    searchResults.value = (data.data?.items ?? []) as PassageSearchResult[];
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('research.searchFailed'));
  } finally {
    searching.value = false;
  }
}

function selectPassage(item: PassageSearchResult, side: 'source' | 'target') {
  if (side === 'source') sourcePassage.value = item;
  else targetPassage.value = item;
  comparison.value = null;
  noteSaved.value = false;
  message.value = '';
}

async function ensureSession(): Promise<string> {
  if (sessionId.value) return sessionId.value;
  const { data } = await api.post('/api/v1/workspace/sessions', {
    title: t('research.sessionTitle'),
  });
  sessionId.value = data.data.id as string;
  return sessionId.value;
}

async function runComparison() {
  if (!sourcePassage.value || !targetPassage.value || !canCompare.value) return;
  comparing.value = true;
  error.value = '';
  message.value = '';
  try {
    const id = await ensureSession();
    const { data } = await api.put(
      `/api/v1/research/sessions/${id}/version-comparison`,
      {
        source_passage_id: sourcePassage.value.id,
        target_passage_id: targetPassage.value.id,
      },
    );
    comparison.value = data.data as ComparisonState;
    noteSaved.value = false;
    message.value = t('research.comparisonSaved');
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('research.compareFailed'));
  } finally {
    comparing.value = false;
  }
}

async function saveNote() {
  if (!sessionId.value || !noteContent.value.trim()) return;
  savingNote.value = true;
  error.value = '';
  try {
    await api.post(`/api/v1/workspace/sessions/${sessionId.value}/notes`, {
      content: noteContent.value.trim(),
      entity_type: 'version_comparison',
      entity_id: comparison.value?.source.passage_id,
      tags: '版本比较',
    });
    noteSaved.value = true;
    message.value = t('research.noteSaved');
    noteContent.value = '';
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('research.noteFailed'));
  } finally {
    savingNote.value = false;
  }
}

async function exportRecord() {
  if (!sessionId.value || !comparison.value) return;
  exporting.value = true;
  error.value = '';
  try {
    const response = await api.get(
      `/api/v1/research/sessions/${sessionId.value}/export`,
      { responseType: 'blob' },
    );
    const url = URL.createObjectURL(response.data as Blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `hfb-research-record-${sessionId.value}.md`;
    link.click();
    URL.revokeObjectURL(url);
    message.value = t('research.exported');
  } catch (err: unknown) {
    error.value = getErrorMessage(err, t('research.exportFailed'));
  } finally {
    exporting.value = false;
  }
}

async function restoreLatestWorkflow() {
  try {
    const { data } = await api.get('/api/v1/workspace/sessions');
    const sessions = (data.data ?? []) as ResearchSession[];
    for (const researchSession of sessions.slice(0, 10)) {
      try {
        const response = await api.get(
          `/api/v1/research/sessions/${researchSession.id}/version-comparison`,
        );
        const comparisonData = response.data?.data;
        // null / undefined means no comparison has been configured for this
        // session — skip it silently (backend returns 200 with data: null).
        if (!comparisonData) {
          continue;
        }
        comparison.value = comparisonData as ComparisonState;
        sessionId.value = researchSession.id;
        return;
      } catch {
        // The session may belong to another workflow or not exist.
      }
    }
  } catch {
    // Authentication guard handles unauthenticated access.
  }
}

function provenanceLabel(item: PassageSearchResult): string {
  const parts = [
    item.metadata.repository,
    item.metadata.shelf_mark,
  ].filter(Boolean);
  return parts.length ? parts.join(' · ') : t('research.provenancePending');
}

function formatSimilarity(value: number): string {
  return t('research.similarity', { value: `${Math.round(value * 100)}%` });
}

function getErrorMessage(errorValue: unknown, fallback: string): string {
  if (
    typeof errorValue === 'object' &&
    errorValue !== null &&
    'response' in errorValue
  ) {
    const response = (errorValue as { response?: { data?: { detail?: string } } }).response;
    return response?.data?.detail || fallback;
  }
  return errorValue instanceof Error ? errorValue.message : fallback;
}

onMounted(restoreLatestWorkflow);
</script>

<style scoped>
/* --- Back to research --- */
.back-to-research {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-2-5) 20px;
  background: var(--color-page-bg);
  border-bottom: 1px solid var(--color-border);
  margin-bottom: 0;
}

.back-link {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent);
  text-decoration: none;
}

.back-link:hover {
  text-decoration: underline;
}

.back-context {
  font-size: 12px;
  color: var(--color-text-muted);
}

/* --- existing styles unchanged --- */
.research-workflow {
  width: min(1440px, 100%);
  margin: 0 auto;
  padding: var(--space-6);
  color: var(--color-text-primary, var(--color-page-bg));
}

.workflow-header,
.section-heading,
.search-row,
.result-item,
.result-actions,
.passage-heading,
.evidence-row,
.comparison-metrics {
  display: flex;
  align-items: center;
}

.workflow-header {
  justify-content: space-between;
  gap: var(--space-6);
  margin-bottom: 16px;
}

.eyebrow,
.section-number {
  margin: 0 0 var(--space-1);
  color: var(--color-error-light-text);
  font-size: 12px;
  font-weight: 700;
  text-transform: uppercase;
}

h1 {
  margin: 0;
  font-size: 26px;
  letter-spacing: 0;
}

h2 {
  margin: 0;
  font-size: 17px;
  letter-spacing: 0;
}

.validation-banner {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2-5) 14px;
  border-left: 4px solid var(--color-warning-text);
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
  font-size: 13px;
}

.workflow-steps {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin: var(--space-4-5) 0 24px;
  padding: 0;
  list-style: none;
  border-bottom: 1px solid var(--color-border);
}

.workflow-steps li {
  padding: var(--space-2-5) 8px;
  color: var(--color-text-muted, var(--color-text-secondary));
  font-size: 13px;
  border-bottom: 3px solid transparent;
}

.workflow-steps li.active {
  color: var(--color-accent-hover);
  border-bottom-color: var(--color-accent-hover);
  font-weight: 700;
}

.workflow-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(320px, 0.8fr);
  gap: var(--space-6);
}

.workflow-grid--lower {
  margin-top: 24px;
  grid-template-columns: 1fr 1fr;
}

.search-panel,
.selection-panel,
.comparison-panel,
.evidence-panel,
.note-panel {
  min-width: 0;
  padding-top: 16px;
  border-top: 2px solid var(--color-text-primary, var(--color-page-bg));
}

.section-heading {
  justify-content: space-between;
  gap: var(--space-4);
  margin-bottom: 16px;
}

.result-count,
.comparison-metrics {
  color: var(--color-text-muted);
  font-size: 12px;
}

.comparison-metrics {
  gap: var(--space-3);
}

.search-form label,
.note-panel label {
  display: block;
  margin-bottom: 6px;
  font-size: 12px;
  font-weight: 700;
}

.search-row {
  gap: var(--space-2);
}

input,
textarea {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-page-bg, var(--color-surface));
  color: var(--color-text-primary, var(--color-page-bg));
  font: inherit;
}

input {
  min-height: 40px;
  padding: var(--space-2) 10px;
}

textarea {
  padding: var(--space-2-5);
  resize: vertical;
  line-height: 1.6;
}

.button {
  min-height: 36px;
  padding: var(--space-1-75) 13px;
  border: 1px solid transparent;
  border-radius: var(--radius-sm);
  font: inherit;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
}

.button--primary {
  background: var(--color-accent-hover);
  color: var(--color-surface);
}

.button--secondary,
.button--compact {
  border-color: var(--color-border);
  background: transparent;
  color: var(--color-text-primary, var(--color-page-bg));
}

.button--compact {
  min-height: 30px;
  padding: var(--space-1) 8px;
  font-size: 12px;
}

.button--compact.selected {
  border-color: var(--color-accent-hover);
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.button--wide {
  width: 100%;
  margin-top: 14px;
}

.button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.search-results {
  margin-top: 14px;
  border-top: 1px solid var(--color-border);
}

.result-item {
  justify-content: space-between;
  gap: var(--space-4-5);
  padding: var(--space-3-5) 0;
  border-bottom: 1px solid var(--color-border);
}

.result-main {
  min-width: 0;
}

.result-main p {
  margin: var(--space-1-75) 0;
  line-height: 1.65;
}

.result-main small {
  color: var(--color-text-muted);
}

.result-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1-5);
  color: var(--color-error-light-text);
  font-size: 12px;
  font-weight: 700;
}

.result-actions {
  flex-shrink: 0;
  gap: var(--space-1-5);
}

.selection-slots {
  display: grid;
  gap: var(--space-3);
}

.selection-slot {
  min-height: 128px;
  padding: var(--space-3-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
}

.selection-slot p {
  margin: var(--space-2) 0;
  line-height: 1.55;
}

.slot-label {
  display: block;
  margin-bottom: 8px;
  color: var(--color-text-muted);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
}

.slot-empty,
.empty-state {
  color: var(--color-text-muted, var(--color-text-secondary));
}

.empty-hint {
  margin-top: 4px;
  font-size: 13px;
  opacity: 0.75;
}

.text-button {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--color-error-light-text);
  cursor: pointer;
}

.inline-warning,
.message {
  padding: var(--space-2-25) 11px;
  font-size: 13px;
}

.inline-warning,
.message--error {
  background: var(--color-error-bg);
  color: var(--color-error-text);
}

.message--success {
  background: var(--color-success-bg);
  color: var(--color-accent-hover);
}

.comparison-panel {
  margin-top: 28px;
}

.passage-columns {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-0-25);
  background: var(--color-border);
  border: 1px solid var(--color-border);
}

.passage-column {
  padding: var(--space-4-5);
  background: var(--color-page-bg, var(--color-surface));
}

.passage-heading {
  justify-content: space-between;
  gap: var(--space-3);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
  font-size: 13px;
}

.passage-text {
  min-height: 88px;
  margin: var(--space-4) 0;
  font-family: "Songti SC", "STSong", serif;
  font-size: 18px;
  line-height: 2;
}

.citation {
  margin: 0;
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.diff-table-wrap {
  margin-top: 16px;
  overflow-x: auto;
}

.diff-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.diff-table th,
.diff-table td {
  padding: var(--space-2-25) 10px;
  border-bottom: 1px solid var(--color-border);
  text-align: left;
}

.diff-type {
  color: var(--color-error-light-text);
  font-weight: 700;
}

.evidence-row {
  justify-content: space-between;
  gap: var(--space-4);
  padding: var(--space-3) 0;
  border-bottom: 1px solid var(--color-border);
}

.evidence-row p {
  margin: var(--space-1) 0;
}

.evidence-status {
  flex-shrink: 0;
  color: var(--color-error-text);
  font-size: 12px;
  font-weight: 700;
}

.evidence-status.complete {
  color: var(--color-accent-hover);
}

.note-panel .button {
  margin-top: 10px;
}

@media (max-width: 900px) {
  .research-workflow {
    padding: var(--space-4);
  }

  .workflow-grid,
  .workflow-grid--lower,
  .passage-columns {
    grid-template-columns: 1fr;
  }

  .workflow-steps {
    grid-template-columns: 1fr 1fr;
  }

  .result-item,
  .workflow-header {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
