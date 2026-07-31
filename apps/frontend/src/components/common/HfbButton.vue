<template>
  <button
    :class="buttonClass"
    :type="type"
    :disabled="disabled || loading"
    :aria-disabled="disabled || loading"
    :aria-busy="loading ? true : undefined"
  >
    <span v-if="loading" class="hfb-button__spinner" aria-hidden="true" />
    <span v-if="$slots.icon && !loading" class="hfb-button__icon">
      <slot name="icon" />
    </span>
    <span v-if="$slots.default" class="hfb-button__label">
      <slot />
    </span>
    <span v-if="$slots['icon-after']" class="hfb-button__icon-after">
      <slot name="icon-after" />
    </span>
  </button>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
    size?: 'sm' | 'md' | 'lg';
    disabled?: boolean;
    loading?: boolean;
    type?: 'button' | 'submit' | 'reset';
    block?: boolean;
  }>(),
  {
    variant: 'primary',
    size: 'md',
    disabled: false,
    loading: false,
    type: 'button',
    block: false,
  },
);

const buttonClass = computed(() =>
  [
    'hfb-button',
    `hfb-button--${props.variant}`,
    `hfb-button--${props.size}`,
    props.block ? 'hfb-button--block' : '',
    props.loading ? 'hfb-button--loading' : '',
  ]
    .filter(Boolean)
    .join(' '),
);
</script>

<style scoped>
@import '../../styles/base/button.css';
</style>
