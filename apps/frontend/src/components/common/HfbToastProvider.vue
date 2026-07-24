<template>
  <Teleport to="body">
    <div v-if="toasts.length > 0" class="hfb-toast-container" aria-live="polite" aria-relevant="additions removals">
      <div
        v-for="t in toasts"
        :key="t.id"
        :class="['hfb-toast', `hfb-toast--${t.variant}`]"
        :role="t.variant === 'error' ? 'alert' : 'status'"
        :aria-live="t.variant === 'error' ? 'assertive' : 'polite'"
      >
        <span class="hfb-toast__icon" aria-hidden="true">{{ toastIcon(t.variant) }}</span>
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
          ✕
        </button>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToast } from '@/composables/useToast';

const { toasts, dismiss } = useToast();

function toastIcon(variant: string): string {
  const icons: Record<string, string> = {
    info: 'ℹ',
    success: '✓',
    warning: '⚠',
    error: '✕',
  };
  return icons[variant] || 'ℹ';
}
</script>

<style scoped>
@import '../../styles/base/toast.css';
</style>
