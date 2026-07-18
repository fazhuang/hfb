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
  padding: 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
}

.eed-section {
  margin-bottom: 12px;
}

.eed-label {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 700;
  margin-bottom: 6px;
}

.eed-label--claim {
  background: #ebf8ff;
  color: #2b6cb0;
  border: 1px solid #bee3f8;
}

.eed-label--quote {
  background: #f0fff4;
  color: #276749;
  border: 1px solid #c6f6d5;
}

.eed-label--cit {
  background: var(--color-page-bg, #fafafa);
  color: var(--color-text-muted, #a0aec0);
  border: 1px solid var(--color-border, #e2e8f0);
}

.eed-claim-text {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--color-text-primary, #1a365d);
  line-height: 1.6;
}

.eed-quote-text {
  margin: 4px 0 0;
  padding: 10px 14px;
  border-left: 3px solid #38a169;
  background: #f0fff4;
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  font-size: 14px;
  color: #276749;
  line-height: 1.9;
  border-radius: 0 6px 6px 0;
}

.eed-citation-code {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  background: var(--color-page-bg, #fafafa);
  padding: 4px 10px;
  border-radius: 4px;
  word-break: break-all;
  color: var(--color-text-secondary, #4a5568);
}

/* Metadata */
.eed-meta {
  margin-top: 12px;
  padding-top: 10px;
  border-top: 1px solid var(--color-border, #e2e8f0);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.eed-meta-row {
  display: flex;
  align-items: baseline;
  gap: 8px;
  font-size: 11px;
}

.eed-meta-label {
  color: var(--color-text-muted, #a0aec0);
  flex-shrink: 0;
  min-width: 72px;
}

.eed-meta-value {
  color: var(--color-text-secondary, #4a5568);
}

.eed-meta-value--incomplete {
  color: #d69e2e;
}

.eed-meta-note {
  color: #d69e2e;
  font-style: italic;
}
</style>
