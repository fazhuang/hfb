<template>
  <div :class="['els-badge', badgeClass]">
    <span class="els-icon" aria-hidden="true">{{ icon }}</span>
    <span class="els-text">{{ badgeText }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ResultEvidence } from '@/composables/useResearchResult';

const props = defineProps<{
  evidence: ResultEvidence;
}>();

/**
 * Lineage completeness rules:
 *
 * Full lineage requires:
 *   - trace_id present
 *   - document_id present
 *   - (claim_text OR quote) present
 *   - source_ref_title present
 *   - passage_id present
 *
 * Partial lineage:
 *   - trace_id + document_id + content present
 *   - BUT source_ref_title OR passage_id missing
 *
 * Minimal lineage:
 *   - Only trace_id + document_id, missing content
 *
 * The known defect test_query_unmapped_passage_fail_closed means some
 * evidence entries legitimately lack passage_id. This component displays
 * that gap honestly rather than hiding it.
 */

interface LineageState {
  status: 'full' | 'partial' | 'minimal';
  icon: string;
  text: string;
}

const lineage = computed((): LineageState => {
  const { evidence: ev } = props;

  // Must have basic identifiers
  if (!ev.trace_id || !ev.document_id) {
    return { status: 'minimal', icon: '❌', text: '证据链不完整 — 缺少基本标识符' };
  }

  // Must have content
  if (!ev.claim_text && !ev.quote) {
    return { status: 'minimal', icon: '⚠️', text: '证据链不完整 — 缺少内容' };
  }

  const hasSourceRef = !!ev.source_ref_title;
  const hasPassage = !!ev.passage_id;

  if (hasSourceRef && hasPassage) {
    return { status: 'full', icon: '✅', text: '证据链完整' };
  }

  // Partial: missing one or both of source_ref_title and passage_id
  const missing: string[] = [];
  if (!hasSourceRef) missing.push('来源文献');
  if (!hasPassage) missing.push('Passage 定位');

  return {
    status: 'partial',
    icon: '⚠️',
    text: `证据链不完整 — 缺少${missing.join('、')}`,
  };
});

const badgeClass = computed(() => {
  switch (lineage.value.status) {
    case 'full': return 'els-badge--full';
    case 'partial': return 'els-badge--partial';
    case 'minimal': return 'els-badge--minimal';
  }
});

const icon = computed(() => lineage.value.icon);
const badgeText = computed(() => lineage.value.text);
</script>

<style scoped>
.els-badge {
  display: flex;
  gap: 6px;
  align-items: center;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 12px;
  margin-top: 10px;
}

.els-badge--full {
  border: 1px solid #c6f6d5;
  background: #f0fff4;
  color: #276749;
}

.els-badge--partial {
  border: 1px solid #d69e2e;
  background: #fffff0;
  color: #975a16;
}

.els-badge--minimal {
  border: 1px solid #fed7d7;
  background: #fff5f5;
  color: #9b2c2c;
}

.els-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.els-text {
  line-height: 1.4;
}
</style>
