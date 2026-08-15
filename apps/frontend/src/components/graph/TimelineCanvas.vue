<template>
  <div class="timeline-strip">
    <div v-if="loading" class="ts-state">
      <span class="spinner"></span>
    </div>
    <div v-else-if="error" class="ts-state ts-state--error">
      <span class="ts-error-text">{{ error }}</span>
      <button class="ts-retry" @click="$emit('retry')">{{ t('common.retry') }}</button>
    </div>
    <div v-else-if="events.length === 0" class="ts-state">{{ emptyText }}</div>
    <div v-else class="ts-track">
      <div
        v-for="ev in events"
        :key="ev.id"
        class="ts-item"
        :class="[
          `ts-item--${ev.category}`,
          { 'ts-item--active': activeId === ev.id },
        ]"
        :tabindex="0"
        role="button"
        @click="$emit('select', ev)"
        @keydown.enter="$emit('select', ev)"
      >
        <div class="ts-top">
          <span class="ts-year">{{ ev.year ?? '—' }}</span>
          <span v-if="ev.era" class="ts-era">{{ ev.era }}</span>
        </div>
        <div class="ts-dot"></div>
        <div class="ts-label">{{ ev.label }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import type { TimelineEvent } from '@/types/graph';

const { t } = useI18n();

defineProps<{
  events: Array<TimelineEvent>;
  loading?: boolean;
  error?: string | null;
  emptyText?: string;
  activeId?: string | null;
}>();

defineEmits<{
  (e: 'select', event: TimelineEvent): void;
  (e: 'retry'): void;
}>();
</script>

<style scoped>
.timeline-strip {
  flex-shrink: 0;
  position: relative;
  width: 100%;
  min-height: 96px;
  border-bottom: 1px solid var(--color-border);
  background: var(--color-navbar-bg, var(--color-surface));
  overflow-x: auto;
  overflow-y: hidden;
}

.ts-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  height: 96px;
  color: var(--color-text-muted);
  font-size: 13px;
  white-space: nowrap;
  padding: 0 var(--space-4);
}

.ts-state--error {
  color: var(--color-error, var(--color-error-text));
}

.ts-retry {
  padding: var(--space-1) 12px;
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-accent);
  cursor: pointer;
  font-size: 12px;
}

.ts-track {
  display: flex;
  align-items: stretch;
  min-width: 100%;
  padding: var(--space-3) var(--space-4);
  position: relative;
}

/* Horizontal axis line through the dots */
.ts-track::before {
  content: '';
  position: absolute;
  top: 40px;
  left: var(--space-4);
  right: var(--space-4);
  height: 2px;
  background: var(--color-border);
}

.ts-item {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 104px;
  max-width: 160px;
  padding: 0 var(--space-2);
  cursor: pointer;
  text-align: center;
  flex-shrink: 0;
}

.ts-top {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: var(--space-1-5);
  min-height: 30px;
}

.ts-year {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-secondary, var(--color-text-muted));
  font-variant-numeric: tabular-nums;
}

.ts-era {
  font-size: 10px;
  color: var(--color-text-muted);
}

.ts-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-accent);
  border: 2px solid var(--color-navbar-bg, var(--color-surface));
  box-shadow: 0 0 0 2px var(--color-border);
  z-index: 1;
}

.ts-item--book .ts-dot {
  background: var(--color-warning);
}

.ts-item--version .ts-dot {
  background: var(--color-success);
}

.ts-item--active .ts-dot {
  box-shadow: 0 0 0 3px var(--color-accent);
}

.ts-item:hover .ts-label {
  color: var(--color-text-primary);
}

.ts-label {
  margin-top: var(--space-1-5);
  font-size: 12px;
  color: var(--color-text-secondary, var(--color-text-muted));
  line-height: 1.3;
  word-break: break-all;
  max-width: 100%;
}

.ts-item--active .ts-label {
  color: var(--color-accent);
  font-weight: 600;
}

.spinner {
  width: 18px;
  height: 18px;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-accent);
  border-radius: 50%;
  animation: spin var(--transition-spinner) linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
