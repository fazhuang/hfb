<template>
  <span :class="badgeClass" role="status" :aria-label="ariaLabel">
    <span v-if="dot" class="hfb-badge__dot" aria-hidden="true" />
    <slot />
  </span>
</template>

<script setup lang="ts">
import { computed, useSlots } from 'vue';

const props = withDefaults(
  defineProps<{
    variant?: 'success' | 'warning' | 'error' | 'info' | 'neutral';
    size?: 'sm' | 'md';
    pill?: boolean;
    dot?: boolean;
  }>(),
  {
    variant: 'neutral',
    size: 'sm',
    pill: false,
    dot: false,
  },
);

const slots = useSlots();

const badgeClass = computed(() =>
  [
    'hfb-badge',
    `hfb-badge--${props.variant}`,
    props.size !== 'sm' ? `hfb-badge--${props.size}` : '',
    props.pill ? 'hfb-badge--pill' : '',
    props.dot ? 'hfb-badge--dot' : '',
  ]
    .filter(Boolean)
    .join(' '),
);

const ariaLabel = computed(() => {
  const content =
    slots
      .default?.()
      ?.map((v) => {
        if (typeof v.children === 'string') return v.children;
        return '';
      })
      .join('') || '';
  return content || props.variant;
});
</script>

<style scoped>
@import '../../styles/base/badge.css';
</style>
