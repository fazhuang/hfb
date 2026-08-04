<template>
  <div class="empty-state" role="status" aria-live="polite">
    <HfbIcon :icon="emptyIconId" :size="36" class="empty-icon" />
    <h3 class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import HfbIcon from './HfbIcon.vue';
import type { LucideIconName } from './HfbIcon.vue';

const props = withDefaults(
  defineProps<{
    icon?: string;
    title: string;
    description?: string;
  }>(),
  {
    icon: '📭',
  },
);

const emptyIconId = computed((): LucideIconName => {
  const map: Record<string, LucideIconName> = {
    '📭': 'inbox',
    '🔍': 'search',
    '📄': 'file-text',
  };
  return map[props.icon] || 'inbox';
});
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-15) var(--space-5);
  text-align: center;
}

.empty-icon {
  font-size: 36px;
  margin-bottom: var(--space-3);
}

.empty-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.empty-description {
  font-size: var(--text-base);
  color: var(--color-text-muted);
  margin: 0;
  max-width: 360px;
  line-height: var(--leading-normal);
}

.empty-action {
  margin-top: var(--space-5);
}
</style>
