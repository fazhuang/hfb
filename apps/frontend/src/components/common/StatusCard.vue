<template>
  <div class="status-card" :class="{ connected, disconnected: !connected }">
    <HfbIcon :icon="connected ? 'check-circle' : 'x-circle'" :size="20" class="status-icon" />
    <div class="status-body">
      <span class="status-label">{{ label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import HfbIcon from './HfbIcon.vue';

defineProps<{
  label: string;
  connected: boolean;
}>();
</script>

<style scoped>
.status-card {
  display: flex;
  align-items: center;
  padding: var(--space-3-5) var(--space-5);
  border-radius: var(--radius-lg);
  border: 1px solid var(--color-border);
  gap: var(--space-3);
  transition: all var(--transition-slow);
}

.status-card.connected {
  background: var(--color-success-bg);
  border-color: var(--color-success);
}

.status-card.disconnected {
  background: var(--color-error-bg);
  border-color: var(--color-error);
}

.status-icon {
  font-size: 18px;
  font-weight: var(--font-bold);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.connected .status-icon {
  color: var(--color-success-text);
  background: var(--color-success-icon-bg);
}

.disconnected .status-icon {
  color: var(--color-error-light-text);
  background: var(--color-error-icon-bg);
}

.status-label {
  font-size: 15px;
  color: var(--color-text-primary);
}
</style>
