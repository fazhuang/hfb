<template>
  <div class="eed-card" role="article" aria-label="证据详情">
    <!-- Claim text -->
    <div v-if="evidence.claim_text" class="eed-section">
      <span class="eed-label eed-label--claim">AI 归纳</span>
      <p class="eed-claim-text">{{ evidence.claim_text }}</p>
    </div>

    <!-- Original quote -->
    <div v-if="evidence.quote" class="eed-section">
      <span class="eed-label eed-label--quote">原文</span>
      <blockquote class="eed-quote-text">{{ evidence.quote }}</blockquote>
    </div>

    <!-- Citation text -->
    <div v-if="evidence.citation_text" class="eed-section">
      <span class="eed-label eed-label--cit">引用标识</span>
      <code class="eed-citation-code">{{ evidence.citation_text }}</code>
    </div>

    <!-- Metadata -->
    <div class="eed-meta">
      <div class="eed-meta-row">
        <span class="eed-meta-label">证据 ID</span>
        <code class="eed-meta-value">{{ evidence.trace_id.slice(0, 16) }}...</code>
      </div>
      <div class="eed-meta-row">
        <span class="eed-meta-label">文档 ID</span>
        <code class="eed-meta-value">{{ evidence.document_id || '—' }}</code>
      </div>
      <div v-if="evidence.passage_id" class="eed-meta-row">
        <span class="eed-meta-label">Passage ID</span>
        <code class="eed-meta-value">{{ evidence.passage_id.slice(0, 16) }}...</code>
      </div>
      <div v-else-if="evidence.chunk_id" class="eed-meta-row">
        <span class="eed-meta-label">Chunk ID</span>
        <code class="eed-meta-value eed-meta-value--incomplete">{{ evidence.chunk_id.slice(0, 16) }}...</code>
        <span class="eed-meta-note">（无 passage 映射）</span>
      </div>
    </div>

    <!-- Lineage --><LineageStatusBadge :evidence="evidence" />

    <!-- SourceRef -->
    <SourceReferenceCard :evidence="evidence" />
  </div>
</template>

<script setup lang="ts">
import type { ResultEvidence } from '@/composables/useResearchResult';
import LineageStatusBadge from './LineageStatusBadge.vue';
import SourceReferenceCard from './SourceReferenceCard.vue';

defineProps<{
  evidence: ResultEvidence;
}>();
</script>

<style scoped>
.eed-card {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-navbar-bg, var(--color-surface));
}

.eed-section {
  margin-bottom: 12px;
}

.eed-label {
  display: inline-block;
  padding: var(--space-0-5) 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 6px;
}

.eed-label--claim {
  background: var(--color-active);
  color: var(--color-accent);
  border: 1px solid var(--color-info);
}

.eed-label--quote {
  background: var(--color-success-bg);
  color: var(--color-success-text);
  border: 1px solid var(--color-success-icon-bg);
}

.eed-label--cit {
  background: var(--color-page-bg);
  color: var(--color-text-muted);
  border: 1px solid var(--color-border);
}

.eed-claim-text {
  margin: var(--space-1) 0 0;
  font-size: 13px;
  color: var(--color-text-primary);
  line-height: 1.6;
}

.eed-quote-text {
  margin: var(--space-1) 0 0;
  padding: var(--space-2-5) 14px;
  border-left: 3px solid var(--color-success);
  background: var(--color-success-bg);
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 14px;
  color: var(--color-success-text);
  line-height: 1.9;
  border-radius: 0 6px 6px 0;
}

.eed-citation-code {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  background: var(--color-page-bg);
  padding: var(--space-1) 10px;
  border-radius: var(--radius-sm);
  word-break: break-all;
  color: var(--color-text-secondary);
}

/* Metadata */
.eed-meta {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.eed-meta-row {
  display: flex;
  align-items: baseline;
  gap: var(--space-2);
  font-size: 11px;
}

.eed-meta-label {
  color: var(--color-text-muted);
  flex-shrink: 0;
  min-width: 72px;
}

.eed-meta-value {
  color: var(--color-text-secondary);
}

.eed-meta-value--incomplete {
  color: var(--color-warning);
}

.eed-meta-note {
  color: var(--color-warning);
  font-style: italic;
}
</style>
