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
  padding: 60px 20px;
  text-align: center;
}

.loading-spinner {
  width: 32px;
  height: 32px;
  border: 3px solid var(--color-border, #e2e8f0);
  border-top-color: var(--color-accent, #2b6cb0);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.loading-text {
  margin: 16px 0 0;
  font-size: 14px;
  color: var(--color-text-muted, #a0aec0);
}
</style>
