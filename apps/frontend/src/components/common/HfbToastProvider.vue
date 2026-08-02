<template>
  <Teleport to="body">
    <div
      v-if="toasts.length > 0"
      class="hfb-toast-container"
      aria-live="polite"
      aria-relevant="additions removals"
    >
      <div
        v-for="t in toasts"
        :key="t.id"
        :class="['hfb-toast', `hfb-toast--${t.variant}`]"
        :role="t.variant === 'error' ? 'alert' : 'status'"
        :aria-live="t.variant === 'error' ? 'assertive' : 'polite'"
      >
        <HfbIcon :icon="toastIconId(t.variant)" :size="18" class="hfb-toast__icon" />
        <div class="hfb-toast__content">
          <div v-if="t.title" class="hfb-toast__title">{{ t.title }}</div>
          <p class="hfb-toast__message">{{ t.message }}</p>
        </div>
        <button
          v-if="t.closable"
          class="hfb-toast__close"
          type="button"
          aria-label="Dismiss notification"
          @click="dismiss(t.id)"
        >
          <HfbIcon icon="x" :size="14" />
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast';
import HfbIcon from './HfbIcon.vue';
import type { LucideIconName } from './HfbIcon.vue';

const { toasts, dismiss } = useToast();

function toastIconId(variant: string): LucideIconName {
  const icons: Record<string, LucideIconName> = {
    info: 'info',
    success: 'check',
    warning: 'triangle-alert',
    error: 'x',
  };
  return icons[variant] || 'info';
}
</script>

<style scoped>
@import '../../styles/base/toast.css';
</style>
