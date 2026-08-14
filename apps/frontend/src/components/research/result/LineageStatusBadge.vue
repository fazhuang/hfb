<template>
  <div :class="['els-badge', badgeClass]">
    <HfbIcon :icon="icon" :size="14" class="els-icon" />
    <span class="els-text">{{ badgeText }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { ResultEvidence } from '@/composables/useResearchResult';
import HfbIcon from '@/components/common/HfbIcon.vue';
import type { LucideIconName } from '@/components/common/HfbIcon.vue';

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
  icon: LucideIconName;
  text: string;
}

const lineage = computed((): LineageState => {
  const { evidence: ev } = props;

  // Must have basic identifiers
  if (!ev.trace_id || !ev.document_id) {
    return { status: 'minimal', icon: 'x-circle', text: '证据链不完整 — 缺少基本标识符' };
  }

  // Must have content
  if (!ev.claim_text && !ev.quote) {
    return { status: 'minimal', icon: 'triangle-alert', text: '证据链不完整 — 缺少内容' };
  }

  const hasSourceRef = !!ev.source_ref_title;
  const hasPassage = !!ev.passage_id;

  if (hasSourceRef && hasPassage) {
    return { status: 'full', icon: 'check-circle', text: '证据链完整' };
  }

  // Partial: missing one or both of source_ref_title and passage_id
  const missing: string[] = [];
  if (!hasSourceRef) missing.push('来源文献');
  if (!hasPassage) missing.push('Passage 定位');

  return {
    status: 'partial',
    icon: 'triangle-alert',
    text: `证据链不完整 — 缺少${missing.join('、')}`,
  };
});

const badgeClass = computed(() => {
  switch (lineage.value.status) {
    case 'full':
      return 'els-badge--full';
    case 'partial':
      return 'els-badge--partial';
    case 'minimal':
      return 'els-badge--minimal';
  }
});

const icon = computed(() => lineage.value.icon);
const badgeText = computed(() => lineage.value.text);
</script>

<style scoped>
.els-badge {
  display: flex;
  gap: var(--space-1-5);
  align-items: center;
  padding: var(--space-2) 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  margin-top: 10px;
}

.els-badge--full {
  border: 1px solid var(--color-success-icon-bg);
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.els-badge--partial {
  border: 1px solid var(--color-warning);
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.els-badge--minimal {
  border: 1px solid var(--color-error-icon-bg);
  background: var(--color-error-bg);
  color: var(--color-error-light-text);
}

.els-icon {
  flex-shrink: 0;
  font-size: 14px;
}

.els-text {
  line-height: 1.4;
}
</style>
