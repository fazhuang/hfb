<template>
  <div class="empty-state" role="status">
    <span class="empty-icon" aria-hidden="true">{{ icon }}</span>
    <h3 class="empty-title">{{ title }}</h3>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <div v-if="$slots.action" class="empty-action">
      <slot name="action" />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(defineProps<{
  icon?: string;
  title: string;
  description?: string;
}>(), {
  icon: '📭',
});
</script>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 36px;
  margin-bottom: 12px;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 8px;
}

.empty-description {
  font-size: 14px;
  color: var(--color-text-muted, #718096);
  margin: 0;
  max-width: 360px;
  line-height: 1.5;
}

.empty-action {
  margin-top: 20px;
}
</style>
