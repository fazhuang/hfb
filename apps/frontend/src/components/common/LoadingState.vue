<template>
  <div class="loading-state" role="status" aria-live="polite">
    <span class="loading-spinner" aria-hidden="true"></span>
    <p class="loading-text">{{ message || t('common.loading') }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

defineProps<{
  message?: string;
}>();
</script>

<style scoped>
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-15) var(--space-5);
  text-align: center;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: hfb-spin var(--transition-spinner) linear infinite;
}

.loading-text {
  margin: var(--space-4) 0 0;
  font-size: var(--text-base);
  color: var(--color-text-muted);
}
</style>
