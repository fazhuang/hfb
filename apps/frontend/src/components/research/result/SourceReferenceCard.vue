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

      <!-- Internal passage link (preferred) -->
      <div v-if="hasInternalRoute" class="esrc-field">
        <span class="esrc-field-label">查看原文</span>
        <router-link
          v-if="internalRoute"
          :to="internalRoute"
          class="esrc-link esrc-link--internal"
        >
          打开原文 →
        </router-link>
      </div>

      <!-- External link (fallback, only when no internal route) -->
      <div v-else-if="safeSourceUrl" class="esrc-field">
        <span class="esrc-field-label">原文链接</span>
        <a
          :href="safeSourceUrl"
          target="_blank"
          rel="noopener noreferrer"
          class="esrc-link"
        >
          打开原文 →
        </a>
      </div>
    </template>

    <!-- No SourceRef -->
    <template v-else>
      <div class="esrc-missing">
        <span class="esrc-missing-icon" aria-hidden="true">⚠️</span>
        <p>此证据缺少文献来源信息。</p>
      </div>
    </template>

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
 * Build an internal app route when we have enough evidence identifiers.
 *
 * Priority:
 *  1. document_id + passage_id → /versions/:versionId?passage=:passageId
 *     (passage-level deep link to the version reader)
 *  2. document_id only → /versions/:versionId
 *     (document-level fallback)
 *  3. No document_id → no internal route (use external link or hide)
 *
 * document_id from retrieval_snapshot/hf_chunks is a version ID
 * in the current data model. We route to the existing VersionDetailView
 * which supports ?passage= query param for scroll-to-passage.
 */
const internalRoute = computed((): RouteLocationRaw | null => {
  const docId = props.evidence.document_id;
  if (!docId) return null;

  if (props.evidence.passage_id) {
    return {
      path: `/versions/${docId}`,
      query: { passage: props.evidence.passage_id },
    };
  }

  return { path: `/versions/${docId}` };
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
  padding: 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-page-bg, #fafafa);
}

.esrc-header {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.esrc-icon {
  font-size: 14px;
}

.esrc-label {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-text-secondary, #4a5568);
}

.esrc-field {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-bottom: 4px;
  font-size: 12px;
}

.esrc-field-label {
  color: var(--color-text-muted, #a0aec0);
  flex-shrink: 0;
  min-width: 52px;
}

.esrc-field-value {
  color: var(--color-text-primary, #1a365d);
}

.esrc-field-value--incomplete {
  color: #d69e2e;
  font-style: italic;
}

.esrc-field-code {
  font-size: 11px;
  color: var(--color-text-secondary, #4a5568);
  background: var(--color-navbar-bg, #fff);
  padding: 1px 4px;
  border-radius: 3px;
}

.esrc-field-note {
  color: #276749;
  font-style: italic;
  font-size: 11px;
}

.esrc-link {
  color: var(--color-accent, #4299e1);
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
  color: #2b6cb0;
}

.esrc-missing {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 8px 10px;
  border: 1px dashed #d69e2e;
  border-radius: 4px;
  background: #fffff0;
}

.esrc-missing-icon {
  font-size: 13px;
  flex-shrink: 0;
}

.esrc-missing p {
  margin: 0;
  font-size: 12px;
  color: #975a16;
}
</style>
