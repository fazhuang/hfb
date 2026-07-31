<template>
  <template v-if="variant === 'text' && (lines ?? 1) > 1">
    <div class="hfb-skeleton__lines" role="status" aria-busy="true" aria-label="Loading...">
      <div
        v-for="i in lines"
        :key="i"
        :class="[
          'hfb-skeleton__line',
          animation !== 'none' ? `hfb-skeleton__line--${animation}` : '',
        ]"
      />
    </div>
  </template>
  <div
    v-else
    class="hfb-skeleton"
    :class="[`hfb-skeleton--${variant}`, animation !== 'none' ? `hfb-skeleton--${animation}` : '']"
    :style="skeletonStyle"
    role="status"
    aria-busy="true"
    :aria-label="ariaLabel"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    variant?: 'text' | 'circle' | 'rect';
    width?: string | number;
    height?: string | number;
    /** Number of lines (text variant only, >1 renders a multi-line block) */
    lines?: number;
    animation?: 'pulse' | 'wave' | 'none';
  }>(),
  {
    variant: 'text',
    lines: 1,
    animation: 'pulse',
  },
);

const widthValue = computed((): string => {
  if (props.width !== undefined)
    return typeof props.width === 'number' ? `${props.width}px` : props.width;
  if (props.variant === 'circle')
    return props.height !== undefined ? cssValue(props.height) : '40px';
  return '100%';
});

const heightValue = computed((): string => {
  if (props.height !== undefined) return cssValue(props.height);
  if (props.variant === 'circle') return widthValue.value;
  if (props.variant === 'rect') return '100px';
  return '1em';
});

function cssValue(v: string | number): string {
  return typeof v === 'number' ? `${v}px` : v;
}

const skeletonStyle = computed(() => ({
  width: widthValue.value,
  height: heightValue.value,
}));

const ariaLabel = computed(() => {
  const labels = {
    text: 'Loading text...',
    circle: 'Loading avatar...',
    rect: 'Loading content...',
  };
  return labels[props.variant];
});
</script>

<style scoped>
@import '../../styles/base/skeleton.css';
</style>
