<template>
  <HfbBadge :variant="badgeVariant" :dot="needsAttention">
    {{ badgeText }}
  </HfbBadge>
</template>

<script lang="ts">
export interface EvidenceBadgeProps {
  sourceType: 'primary_source' | 'edition' | 'annotation' | 'modern_scholarship';
  verificationStatus: 'verified' | 'unverified' | 'disputed';
  locatorCompleteness: 'complete' | 'partial' | 'missing';
}
</script>

<script setup lang="ts">
import { computed } from 'vue';
import HfbBadge from '@/components/common/HfbBadge.vue';

const props = defineProps<EvidenceBadgeProps>();

const sourceTypeLabel = computed((): string => {
  switch (props.sourceType) {
    case 'primary_source':
      return '一手文献';
    case 'edition':
      return '版本';
    case 'annotation':
      return '注疏';
    case 'modern_scholarship':
      return '现代研究';
  }
});

const verificationLabel = computed((): string => {
  switch (props.verificationStatus) {
    case 'verified':
      return '来源可追溯';
    case 'unverified':
      return '未核验';
    case 'disputed':
      return '存疑';
  }
});

/**
 * v4.2 映射表 → HfbBadge variant:
 *   verified  → info (严禁 success/绿色)
 *   unverified → neutral
 *   disputed  → error
 */
const badgeVariant = computed((): 'warning' | 'error' | 'info' | 'neutral' => {
  switch (props.verificationStatus) {
    case 'verified':
      return 'info';
    case 'unverified':
      return 'neutral';
    case 'disputed':
      return 'error';
  }
});

/** dot indicator when attention is needed: disputed status or incomplete locator */
const needsAttention = computed(
  (): boolean =>
    props.verificationStatus === 'disputed' || props.locatorCompleteness !== 'complete',
);

const badgeText = computed((): string => {
  const parts: Array<string> = [sourceTypeLabel.value, `· ${verificationLabel.value}`];
  if (props.locatorCompleteness === 'partial') {
    parts.push('· 定位不完整');
  } else if (props.locatorCompleteness === 'missing') {
    parts.push('· 无定位');
  }
  return parts.join(' ');
});
</script>
