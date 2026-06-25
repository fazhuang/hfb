<template>
  <div class="placeholder-page">
    <div class="placeholder-icon">{{ icon }}</div>
    <h2 class="placeholder-title">{{ title }}</h2>
    <p class="placeholder-desc">{{ description }}</p>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  icon: string;
  title: string;
  description: string;
}>();
</script>

<style scoped>
.placeholder-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  flex: 1;
}

.placeholder-icon {
  font-size: 56px;
  margin-bottom: 16px;
  opacity: 0.6;
}

.placeholder-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 8px;
}

.placeholder-desc {
  font-size: 14px;
  color: var(--color-text-muted, #a0aec0);
  max-width: 400px;
  margin: 0;
}
</style>
