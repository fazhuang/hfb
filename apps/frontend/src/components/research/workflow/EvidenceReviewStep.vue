<template>
  <section class="ers-step" aria-labelledby="ers-heading">
    <h2 id="ers-heading" class="ers-heading">第四步：证据审查</h2>

    <!-- No evidence warning -->
    <div v-if="evidence.length === 0" class="ers-warning" role="alert">
      <span class="ers-warning-icon" aria-hidden="true">⚠️</span>
      <div>
        <strong>未找到相关文献证据</strong>
        <p>
          系统未能检索到与您的研究问题相关的文献证据。您仍然可以查看系统生成的报告，但其中的结论缺乏证据支持。
        </p>
      </div>
    </div>

    <!-- Evidence list -->
    <div v-else class="ers-summary-bar">
      <span>共找到 {{ evidence.length }} 条证据，{{ citations.length }} 条引用</span>
      <button type="button" class="ers-action-btn" @click="$emit('go-to-report')">
        查看研究报告 →
      </button>
    </div>

    <ol v-if="evidence.length > 0" class="ers-list" role="list">
      <li v-for="(ev, idx) in evidence" :key="ev.trace_id" class="ers-item">
        <div class="ers-item-header">
          <span class="ers-item-index">#{{ idx + 1 }}</span>
          <span class="ers-item-source">{{ ev.document_id || '未知来源' }}</span>
        </div>

        <!-- Claim text (AI归纳) -->
        <div class="ers-claim" aria-label="AI 归纳结论">
          <span class="ers-label ers-label--ai">AI 归纳</span>
          <p class="ers-claim-text">{{ ev.claim_text || '暂无归纳' }}</p>
        </div>

        <!-- Original quote -->
        <div v-if="ev.quote" class="ers-quote" aria-label="原始文献内容">
          <span class="ers-label ers-label--source">原文</span>
          <blockquote class="ers-quote-text">{{ ev.quote }}</blockquote>
        </div>

        <!-- Citation -->
        <div v-if="ev.citation_text" class="ers-citation">
          <span class="ers-label ers-label--citation">引用标识</span>
          <code class="ers-citation-text">{{ ev.citation_text }}</code>
        </div>

        <!-- Locator info -->
        <div class="ers-locator">
          <span v-if="getLocatorText(ev)" class="ers-locator-hint">
            {{ getLocatorText(ev) }}
          </span>
          <span v-else class="ers-locator-hint ers-locator-hint--incomplete"> 来源定位不完整 </span>
        </div>

        <!-- Lineage completeness indicator -->
        <div v-if="!hasFullLineage(ev)" class="ers-lineage-warning">
          <span class="ers-lineage-warning-icon" aria-hidden="true">⚠️</span>
          该条目的证据链不完整，缺少部分来源追溯信息。
        </div>

        <!-- Actions -->
        <div class="ers-item-actions">
          <!-- Save citation (always available via real API) -->
          <button
            type="button"
            class="ers-item-action-btn"
            :disabled="
              citationSaveState[ev.trace_id] === 'saving' ||
              citationSaveState[ev.trace_id] === 'saved'
            "
            @click="$emit('save-citation', ev)"
          >
            {{
              citationSaveState[ev.trace_id] === 'saved'
                ? '已保存 ✓'
                : citationSaveState[ev.trace_id] === 'saving'
                  ? '保存中...'
                  : '保存引用'
            }}
          </button>
        </div>
      </li>
    </ol>
  </section>
</template>

<script setup lang="ts">
import type { WorkflowEvidence, WorkflowCitation } from '@/composables/useResearchWorkflow';

defineProps<{
  evidence: WorkflowEvidence[];
  citations: WorkflowCitation[];
  citationSaveState: Record<string, 'idle' | 'saving' | 'saved'>;
}>();

defineEmits<{
  'save-citation': [evidence: WorkflowEvidence];
  'go-to-report': [];
}>();

/**
 * Build a human-readable locator string from available evidence fields.
 *
 * Key invariants:
 *   - source_ref_title is a REAL source title from the backend (not document_id).
 *   - passage_id is a REAL passage UUID from traces (not chunk_id).
 *   - If source_ref_title is missing, we show "来源定位不完整" — we CANNOT
 *     fabricate it from document_id or any other field.
 *   - chunk_id is a chunk identifier, not a passage — it goes in the
 *     locator only when passage_id is missing.
 */
function getLocatorText(ev: WorkflowEvidence): string {
  const parts: string[] = [];
  // source_ref_title comes from retrieval_snapshot.source_ref_title — only present
  // when the backend has a real SourceRef record for this evidence.
  if ('source_ref_title' in ev && ev.source_ref_title) {
    parts.push(`来源: ${ev.source_ref_title}`);
  }
  // passage_id comes from manifests.traces[].passage_id (real passage UUID).
  // chunk_id is a fallback. Neither is a source title.
  if ('passage_id' in ev && ev.passage_id) {
    parts.push(`Passage: ${ev.passage_id.slice(0, 12)}...`);
  } else if (ev.chunk_id) {
    parts.push(`Chunk: ${ev.chunk_id.slice(0, 12)}...`);
  }
  // P2T2: When we only have a chunk_id (no source_ref_title or passage_id),
  // return empty string so the template renders "来源定位不完整" instead.
  if (parts.length === 1 && parts[0]?.startsWith('Chunk:')) return '';
  return parts.join(' · ');
}

/**
 * An evidence entry has full lineage when it has at least:
 *   trace_id + document_id + chunk_id + (claim_text OR quote)
 * No confidence score — just structural completeness.
 * Missing source_ref_title or passage_id means incomplete lineage.
 */
function hasFullLineage(ev: WorkflowEvidence): boolean {
  // Basic structural requirement
  if (!ev.trace_id || !ev.document_id || !ev.chunk_id) return false;
  if (!ev.claim_text && !ev.quote) return false;
  // SourceRef or passage locator is required for full lineage
  if (!('source_ref_title' in ev) || !ev.source_ref_title) return false;
  if (!('passage_id' in ev) || !ev.passage_id) return false;
  return true;
}
</script>

<style scoped>
.ers-step {
  padding: 0;
}

.ers-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
}

/* Warning */
.ers-warning {
  display: flex;
  gap: var(--space-2-5);
  padding: var(--space-3-5) 16px;
  border: 1px solid var(--color-warning);
  border-left: 4px solid var(--color-warning);
  border-radius: var(--radius-md);
  background: var(--color-warning-bg);
  margin-bottom: 20px;
}

.ers-warning-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

.ers-warning strong {
  display: block;
  font-size: 14px;
  color: var(--color-warning-text);
  margin-bottom: 4px;
}

.ers-warning p {
  margin: 0;
  font-size: 13px;
  color: var(--color-warning-text);
  line-height: 1.5;
}

/* Summary bar */
.ers-summary-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--space-2-5) 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--color-text-secondary);
}

.ers-action-btn {
  padding: var(--space-1-5) 14px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  background: transparent;
  color: var(--color-accent);
  transition: all var(--transition-base);
}

.ers-action-btn:hover {
  background: var(--color-accent);
  color: var(--color-surface);
}

.ers-action-btn:focus-visible {
  background: var(--color-accent);
  color: var(--color-surface);
}

/* Evidence list */
.ers-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
}

.ers-item {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-navbar-bg, var(--color-surface));
}

.ers-item-header {
  display: flex;
  gap: var(--space-2-5);
  align-items: baseline;
  margin-bottom: 12px;
  padding-bottom: 10px;
  border-bottom: 1px solid var(--color-border);
}

.ers-item-index {
  font-size: 13px;
  font-weight: 700;
  color: var(--color-error-light-text);
}

.ers-item-source {
  font-size: 12px;
  color: var(--color-text-muted);
  font-family: monospace;
}

/* Labels */
.ers-label {
  display: inline-block;
  padding: var(--space-0-5) 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 6px;
}

.ers-label--ai {
  background: var(--color-accent-light);
  color: var(--color-accent);
  border: 1px solid var(--color-info-text);
}

.ers-label--source {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-icon-bg);
}

.ers-label--citation {
  background: var(--color-page-bg);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}

/* Claim */
.ers-claim {
  margin-bottom: 12px;
}

.ers-claim-text {
  margin: 0;
  font-size: 14px;
  color: var(--color-text-primary);
  line-height: 1.6;
}

/* Quote */
.ers-quote {
  margin-bottom: 12px;
}

.ers-quote-text {
  margin: 0;
  padding: var(--space-2-5) 14px;
  border-left: 3px solid var(--color-success-text);
  background: var(--color-success-bg);
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 15px;
  color: var(--color-success-text);
  line-height: 1.9;
  border-radius: 0 6px 6px 0;
}

/* Citation */
.ers-citation {
  margin-bottom: 10px;
}

.ers-citation-text {
  font-size: 12px;
  background: var(--color-page-bg);
  padding: var(--space-0-75) 8px;
  border-radius: var(--radius-sm);
  word-break: break-all;
  color: var(--color-text-secondary);
}

/* Locator */
.ers-locator {
  margin-bottom: 12px;
  padding: var(--space-2) 12px;
  border-radius: var(--radius-sm);
  background: var(--color-page-bg);
}

.ers-locator-hint {
  font-size: 12px;
  color: var(--color-text-muted);
}

.ers-locator-hint--incomplete {
  color: var(--color-warning);
  font-style: italic;
}

/* Lineage warning */
.ers-lineage-warning {
  display: flex;
  gap: var(--space-1-5);
  padding: var(--space-2) 12px;
  border: 1px solid var(--color-warning);
  border-radius: var(--radius-sm);
  background: var(--color-warning-bg);
  font-size: 12px;
  color: var(--color-warning-text);
  margin-bottom: 10px;
}

.ers-lineage-warning-icon {
  flex-shrink: 0;
  font-size: 13px;
}

/* Actions */
.ers-item-actions {
  display: flex;
  gap: var(--space-2);
  padding-top: 10px;
  border-top: 1px solid var(--color-border);
}

.ers-item-action-btn {
  padding: var(--space-1-5) 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  background: var(--color-navbar-bg, var(--color-surface));
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
}

.ers-item-action-btn:hover:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.ers-item-action-btn:focus-visible:not(:disabled) {
  background: var(--color-hover);
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.ers-item-action-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
