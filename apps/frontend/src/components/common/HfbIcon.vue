<template>
  <Icon
    :icon="icon"
    :width="size"
    :height="size"
    :color="color"
    :class="iconClass"
    :aria-hidden="ariaHidden"
    :aria-label="ariaLabel"
    role="img"
  />
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Icon } from '@iconify/vue';

const props = withDefaults(
  defineProps<{
    /** Iconify icon id, e.g. "lucide:book-open" or "mdi:home" */
    icon: string;
    /** Icon size in px (applied to both width & height) */
    size?: number | string;
    /** CSS color (token or hex), passed to SVG fill/stroke */
    color?: string;
    /** Accessible label for standalone icon buttons or icon-only controls */
    ariaLabel?: string;
    /** Hide from screen readers; default true per icon-only convention */
    ariaHidden?: boolean;
  }>(),
  {
    size: 20,
    color: 'currentColor',
    ariaHidden: true,
  },
);

const ariaHidden = computed(() =>
  props.ariaLabel ? undefined : props.ariaHidden,
);

const iconClass = computed(() => ['hfb-icon', props.ariaLabel ? '' : 'hfb-icon--decorative'].filter(Boolean).join(' '));
</script>

<style scoped>
.hfb-icon {
  display: inline-block;
  vertical-align: middle;
  flex-shrink: 0;
}
</style>
