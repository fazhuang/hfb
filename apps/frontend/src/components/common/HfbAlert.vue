<template>
  <div
    :class="alertClass"
    :role="variant === 'error' ? 'alert' : 'status'"
    :aria-live="variant === 'error' ? 'assertive' : 'polite'"
  >
    <span v-if="showIcon" class="hfb-alert__icon" aria-hidden="true">{{ alertIcon }}</span>
    <div class="hfb-alert__content">
      <div v-if="title || $slots.title" class="hfb-alert__title">
        <slot name="title">{{ title }}</slot>
      </div>
      <div v-if="$slots.default" class="hfb-alert__body">
        <slot />
      </div>
      <div v-if="$slots.actions" class="hfb-alert__actions">
        <slot name="actions" />
      </div>
    </div>
    <button
      v-if="closable"
      class="hfb-alert__close"
      type="button"
      aria-label="Close alert"
      @click="$emit('close')"
    >
      ✕
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

const props = withDefaults(
  defineProps<{
    variant?: 'info' | 'success' | 'warning' | 'error';
    title?: string;
    closable?: boolean;
    icon?: boolean;
  }>(),
  {
    variant: 'info',
    closable: false,
    icon: true,
  },
);

defineEmits<{
  close: [];
}>();

const showIcon = computed(
  () => props.icon && ['info', 'success', 'warning', 'error'].includes(props.variant),
);

const alertIcon = computed(() => {
  const icons: Record<string, string> = {
    info: 'ℹ',
    success: '✓',
    warning: '⚠',
    error: '✕',
  };
  return icons[props.variant] || '';
});

const alertClass = computed(() => ['hfb-alert', `hfb-alert--${props.variant}`].join(' '));
</script>

<style scoped>
@import '../../styles/base/alert.css';
</style>
