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
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
  padding-bottom: 10px;
  border-bottom: 2px solid var(--color-accent, #4299e1);
}

.rcp-subheading {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 12px;
}

.rcp-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
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
  gap: 10px;
}

.rcp-citation-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 12px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  cursor: pointer;
  transition: all 0.15s;
}

.rcp-citation-item:hover {
  border-color: var(--color-accent, #4299e1);
  box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.2);
}

.rcp-citation-item:focus-visible {
  border-color: var(--color-accent, #4299e1);
  box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.2);
}

.rcp-citation-item--selected {
  border-color: var(--color-accent);
  box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.3);
  background: var(--color-accent-light);
}

.rcp-citation-header {
  display: flex;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 6px;
}

.rcp-citation-number {
  font-size: 12px;
  font-weight: 700;
  color: #8a3b2f;
}

.rcp-citation-id {
  font-size: 11px;
  color: var(--color-text-muted, #a0aec0);
}

.rcp-citation-text {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-primary, #1a365d);
  line-height: 1.5;
}

.rcp-citation-text--quote {
  font-family: 'Songti SC', 'STSong', 'Noto Serif CJK SC', serif;
  color: var(--color-text-secondary, #4a5568);
  font-style: italic;
}

/* Evidence area */
.rcp-evidence-area {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rcp-no-evidence,
.rcp-select-prompt {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px 16px;
  border: 2px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
  color: var(--color-text-muted, #a0aec0);
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
  gap: 12px;
  padding: 48px 20px;
  border: 2px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
  color: var(--color-text-muted, #a0aec0);
}

.rcp-empty-icon {
  font-size: 32px;
}

.rcp-empty p {
  margin: 0;
  font-size: 14px;
}
</style>
