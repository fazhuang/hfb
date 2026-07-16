<template>
  <div class="error-state" role="alert" aria-live="assertive">
    <span class="error-icon" aria-hidden="true">⚠️</span>
    <h3 class="error-title">{{ title || t('common.error') }}</h3>
    <p v-if="message" class="error-message">{{ message }}</p>
    <button
      v-if="retryLabel || showRetry"
      class="error-retry-btn"
      @click="$emit('retry')"
    >
      {{ retryLabel || t('common.retry') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

withDefaults(defineProps<{
  title?: string;
  message?: string;
  showRetry?: boolean;
  retryLabel?: string;
}>(), {
  showRetry: true,
});

defineEmits<{
  retry: [];
}>();
</script>

<style scoped>
.error-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.error-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.error-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-error-text, #c53030);
  margin: 0 0 8px;
}

.error-message {
  font-size: 13px;
  color: var(--color-text-muted, #718096);
  margin: 0 0 16px;
  max-width: 420px;
  line-height: 1.5;
  word-break: break-word;
}

.error-retry-btn {
  padding: 8px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  background: var(--color-navbar-bg, #fff);
  font-size: 13px;
  cursor: pointer;
  color: var(--color-accent, #2b6cb0);
  transition: all 0.15s;
}

.error-retry-btn:hover {
  background: var(--color-hover, #edf2f7);
  border-color: var(--color-accent, #2b6cb0);
}
</style>
