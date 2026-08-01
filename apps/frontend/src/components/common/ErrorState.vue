<template>
  <div class="error-state" role="alert" aria-live="assertive">
    <HfbIcon icon="lucide:circle-alert" :size="36" class="error-icon" />
    <h3 class="error-title">{{ title || t('common.error') }}</h3>
    <p v-if="message" class="error-message">{{ message }}</p>
    <button v-if="retryLabel || showRetry" class="error-retry-btn" @click="$emit('retry')">
      {{ retryLabel || t('common.retry') }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import HfbIcon from './HfbIcon.vue';

const { t } = useI18n();

withDefaults(
  defineProps<{
    title?: string;
    message?: string;
    showRetry?: boolean;
    retryLabel?: string;
  }>(),
  {
    showRetry: true,
  },
);

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
  padding: var(--space-15) var(--space-5);
  text-align: center;
}

.error-icon {
  font-size: 36px;
  margin-bottom: var(--space-3);
}

.error-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-error-text);
  margin: 0 0 var(--space-2);
}

.error-message {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-4);
  max-width: 420px;
  line-height: var(--leading-normal);
  word-break: break-word;
}

.error-retry-btn {
  padding: var(--btn-padding-md);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  font-size: var(--text-sm);
  cursor: pointer;
  color: var(--color-accent);
  transition: all var(--transition-base);
}

.error-retry-btn:hover {
  background: var(--color-hover);
  border-color: var(--color-accent);
}

.error-retry-btn:focus-visible {
  background: var(--color-hover);
  border-color: var(--color-accent);
}
</style>
