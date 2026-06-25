<template>
  <div class="status-card" :class="{ connected, disconnected: !connected }">
    <span class="status-icon">{{ connected ? '✓' : '✗' }}</span>
    <div class="status-body">
      <span class="status-label">{{ label }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  connected: boolean;
}>();
</script>

<style scoped>
.status-card {
  display: flex;
  align-items: center;
  padding: 14px 20px;
  border-radius: 8px;
  border: 1px solid var(--color-border, #e2e8f0);
  gap: 12px;
  transition: all 0.2s;
}

.status-card.connected {
  background: var(--color-success-bg, #f0fff4);
  border-color: var(--color-success, #68d391);
}

.status-card.disconnected {
  background: var(--color-error-bg, #fff5f5);
  border-color: var(--color-error, #fc8181);
}

.status-icon {
  font-size: 18px;
  font-weight: 700;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}

.connected .status-icon {
  color: #22543d;
  background: var(--color-success-icon-bg, #c6f6d5);
}

.disconnected .status-icon {
  color: #742a2a;
  background: var(--color-error-icon-bg, #fed7d7);
}

.status-label {
  font-size: 15px;
  color: var(--color-text-primary, #2d3748);
}
</style>
