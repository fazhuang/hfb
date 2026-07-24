<template>
  <section class="rcp-section" aria-labelledby="rcp-heading">
    <h2 id="rcp-heading" class="rcp-heading">引用与证据</h2>

    <!-- No citations -->
    <div v-if="citations.length === 0" class="rcp-empty">
      <span class="rcp-empty-icon" aria-hidden="true">📎</span>
      <p>此报告暂无引用记录。</p>
    </div>

    <div v-else class="rcp-body">
      <!-- Citation list -->
      <nav class="rcp-citation-list" aria-label="引用列表">
        <h3 class="rcp-subheading">
          引用项（{{ citations.length }}）
        </h3>
        <div
          v-for="(citation, idx) in citations"
          :key="citation.trace_id"
          :class="['rcp-citation-item', { 'rcp-citation-item--selected': citation.trace_id === selectedTraceId }]"
          role="button"
          tabindex="0"
          :aria-selected="citation.trace_id === selectedTraceId"
          :aria-label="`引用 #[${idx + 1}]`"
          @click="$emit('select', citation.trace_id)"
          @keydown.enter="$emit('select', citation.trace_id)"
          @keydown.space.prevent="$emit('select', citation.trace_id)"
        >
          <div class="rcp-citation-header">
            <span class="rcp-citation-number">#[{{ idx + 1 }}]</span>
            <code class="rcp-citation-id">{{ citation.trace_id.slice(0, 16) }}...</code>
          </div>
          <p v-if="citation.citation_text" class="rcp-citation-text">
            {{ citation.citation_text }}
          </p>
          <p v-else-if="citation.quote" class="rcp-citation-text rcp-citation-text--quote">
            {{ citation.quote.slice(0, 120) }}{{ citation.quote.length > 120 ? '...' : '' }}
          </p>
        </div>
      </nav>

      <!-- Evidence detail for selected citation -->
      <div class="rcp-evidence-area">
        <template v-if="selectedTraceId">
          <h3 class="rcp-subheading">证据详情</h3>
          <EvidenceDetail
            v-for="ev in selectedEvidence"
            :key="ev.trace_id"
            :evidence="ev"
          />
          <div v-if="selectedEvidence.length === 0" class="rcp-no-evidence">
            <span class="rcp-empty-icon" aria-hidden="true">🔍</span>
            <p>此引用缺少证据关联。</p>
          </div>
        </template>
        <div v-else class="rcp-select-prompt">
          <span class="rcp-empty-icon" aria-hidden="true">👆</span>
          <p>请选择左侧引用项查看证据详情。</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ResultCitation, ResultEvidence } from '@/composables/useResearchResult';
import EvidenceDetail from './EvidenceDetail.vue';

const props = defineProps<{
  citations: ResultCitation[];
  evidence: ResultEvidence[];
  selectedTraceId: string | null;
}>();

defineEmits<{
  select: [traceId: string];
}>();

const selectedEvidence = computed(() => {
  if (!props.selectedTraceId) return [];
  return props.evidence.filter((e) => e.trace_id === props.selectedTraceId);
});
</script>

<style scoped>
.rcp-section {
  padding: 0;
}

.rcp-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  padding-bottom: 10px;
  border-bottom: 2px solid var(--color-accent);
}

.rcp-subheading {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-3);
}

.rcp-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-5);
  align-items: start;
}

@media (max-width: 768px) {
  .rcp-body {
    grid-template-columns: 1fr;
  }
}

/* Citation list */
.rcp-citation-list {
  display: flex;
  flex-direction: column;
  gap: var(--space-2-5);
}

.rcp-citation-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: var(--space-3) 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-navbar-bg, var(--color-surface));
  cursor: pointer;
  transition: all var(--transition-base);
}

.rcp-citation-item:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-focus-md);
}

.rcp-citation-item:focus-visible {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-focus-md);
}

.rcp-citation-item--selected {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-focus-lg);
  background: var(--color-accent-light);
}

.rcp-citation-header {
  display: flex;
  gap: var(--space-2);
  align-items: baseline;
  margin-bottom: 6px;
}

.rcp-citation-number {
  font-size: 12px;
  font-weight: 700;
  color: var(--color-error-light-text);
}

.rcp-citation-id {
  font-size: 11px;
  color: var(--color-text-muted);
}

.rcp-citation-text {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-primary);
  line-height: 1.5;
}

.rcp-citation-text--quote {
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  color: var(--color-text-secondary);
  font-style: italic;
}

/* Evidence area */
.rcp-evidence-area {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.rcp-no-evidence,
.rcp-select-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-8) 16px;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
}

.rcp-no-evidence p,
.rcp-select-prompt p {
  margin: 0;
  font-size: 13px;
}

/* Empty state */
.rcp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-12) 20px;
  border: 2px dashed var(--color-border);
  border-radius: var(--radius-lg);
  color: var(--color-text-muted);
}

.rcp-empty-icon {
  font-size: 32px;
}

.rcp-empty p {
  margin: 0;
  font-size: 14px;
}
</style>
