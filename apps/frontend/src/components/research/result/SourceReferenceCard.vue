<template>
  <div class="esrc-card" aria-label="来源参考">
    <div class="esrc-header">
      <span class="esrc-icon" aria-hidden="true">📚</span>
      <span class="esrc-label">文献来源</span>
    </div>

    <!-- With SourceRef -->
    <template v-if="evidence.source_ref_title">
      <div class="esrc-field">
        <span class="esrc-field-label">文献</span>
        <span class="esrc-field-value">{{ evidence.source_ref_title }}</span>
      </div>
      <div v-if="evidence.source_ref_id" class="esrc-field">
        <span class="esrc-field-label">来源 ID</span>
        <code class="esrc-field-code">{{ evidence.source_ref_id.slice(0, 16) }}...</code>
      </div>
    </template>

    <!-- No SourceRef title — fail-closed for source metadata, but internal route
         (reader / library) must still render when document_id exists -->
    <template v-else>
      <div class="esrc-missing">
        <span class="esrc-missing-icon" aria-hidden="true">⚠️</span>
        <p v-if="hasInternalRoute">来源信息未提供；可打开文档定位</p>
        <p v-else>此证据缺少文献来源信息。</p>
      </div>
    </template>

    <!-- Internal document route — renders ALWAYS when hasInternalRoute,
         regardless of source_ref_title -->
    <div v-if="hasInternalRoute" class="esrc-field">
      <span class="esrc-field-label">查看原文</span>
      <router-link v-if="internalRoute" :to="internalRoute" class="esrc-link esrc-link--internal">
        打开原文 →
      </router-link>
    </div>

    <!-- External link (fallback, only when no internal route) -->
    <div v-else-if="safeSourceUrl" class="esrc-field">
      <span class="esrc-field-label">原文链接</span>
      <a :href="safeSourceUrl" target="_blank" rel="noopener noreferrer" class="esrc-link">
        打开原文 →
      </a>
    </div>

    <!-- Passage locator -->
    <div v-if="evidence.passage_id" class="esrc-field esrc-field--passage">
      <span class="esrc-field-label">Passage</span>
      <code class="esrc-field-code">{{ evidence.passage_id.slice(0, 16) }}...</code>
      <span class="esrc-field-note">（精确段落定位可用）</span>
    </div>
    <div v-else-if="evidence.document_id" class="esrc-field esrc-field--no-passage">
      <span class="esrc-field-label">定位</span>
      <span class="esrc-field-value esrc-field-value--incomplete">
        仅文献级定位（无 passage 级定位）
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ResultEvidence } from '@/composables/useResearchResult';
import type { RouteLocationRaw } from 'vue-router';

const props = defineProps<{
  evidence: ResultEvidence;
}>();

/**
 * Build an internal app route when we have a document_id.
 *
 * Priority (readerAddressable → /reader, fallback → /library):
 *  1. document_id + chunk_id → /reader/:documentId#chunk-<chunk_id>
 *  2. document_id only → /library/:documentId
 *  3. No document_id → no internal route (use external link or hide)
 *
 * evidence.document_id is the primary key of the documents table.
 * Do NOT map it to /versions/ — that requires a real version_id field.
 */
const internalRoute = computed((): RouteLocationRaw | null => {
  const docId = props.evidence.document_id;
  if (!docId) return null;

  // readerAddressable: document_id + chunk_id → /reader/:id#chunk-<chunk_id>
  if (props.evidence.chunk_id) {
    const chunkFragment = props.evidence.chunk_id.startsWith('chunk-')
      ? props.evidence.chunk_id
      : `chunk-${props.evidence.chunk_id}`;
    return `/reader/${docId}#${encodeURIComponent(chunkFragment)}`;
  }

  // Fallback: no chunk_id → /library/:documentId
  return `/library/${docId}`;
});

const hasInternalRoute = computed(() => internalRoute.value !== null);

/**
 * Defense-in-depth: reject dangerous URL schemes even though source_ref_url
 * originates from the server-side SourceRef table (admin-seeded during ingestion).
 *
 * Allowed schemes: https?, ftp (for ctext.org variants). Rejected: javascript,
 * data, vbscript, file. Null return hides the link.
 */
const safeSourceUrl = computed(() => {
  const raw = props.evidence.source_ref_url;
  if (!raw) return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  const DANGEROUS = /^(javascript|data|vbscript|file):/i;
  if (DANGEROUS.test(trimmed)) return null;
  // Require at least an http/https scheme for outbound links
  const SAFE = /^https?:\/\//i;
  if (!SAFE.test(trimmed)) return null;
  return trimmed;
});
</script>

<style scoped>
.esrc-card {
  margin-top: 10px;
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
}

.esrc-header {
  display: flex;
  gap: var(--space-1-5);
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border);
}

.esrc-icon {
  font-size: 14px;
}

.esrc-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-secondary);
}

.esrc-field {
  display: flex;
  align-items: baseline;
  gap: var(--space-1-5);
  margin-bottom: 4px;
  font-size: 12px;
}

.esrc-field-label {
  color: var(--color-text-muted);
  flex-shrink: 0;
  min-width: 52px;
}

.esrc-field-value {
  color: var(--color-text-primary);
}

.esrc-field-value--incomplete {
  color: var(--color-warning);
  font-style: italic;
}

.esrc-field-code {
  font-size: 11px;
  color: var(--color-text-secondary);
  background: var(--color-navbar-bg);
  padding: var(--space-0-25) 4px;
  border-radius: var(--radius-sm);
}

.esrc-field-note {
  color: var(--color-success-text);
  font-style: italic;
  font-size: 11px;
}

.esrc-link {
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 600;
  font-size: 12px;
}

.esrc-link:hover {
  text-decoration: underline;
}

.esrc-link:focus-visible {
  text-decoration: underline;
}

.esrc-link--internal {
  color: var(--color-accent);
}

.esrc-missing {
  display: flex;
  gap: var(--space-1-5);
  align-items: center;
  padding: var(--space-2) 10px;
  border: 1px dashed var(--color-warning);
  border-radius: var(--radius-sm);
  background: var(--color-warning-bg);
}

.esrc-missing-icon {
  font-size: 13px;
  flex-shrink: 0;
}

.esrc-missing p {
  margin: 0;
  font-size: 12px;
  color: var(--color-warning-text);
}
</style>
