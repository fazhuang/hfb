<template>
  <div class="placeholder-page">
    <ResearchPageHeader
      title="Library"
      description="古籍文献搜索与全文阅读"
      :breadcrumbs="[{ label: 'Library' }]"
    />
    <div class="placeholder-body">
      <p>功能迁移中 — Library Search、Document Detail、Document Reader 页面将在后续 Sprint 中实现。</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
</script>

<style scoped>
.placeholder-body {
  padding: 24px 32px;
  color: var(--color-text-muted, #718096);
}

@media (max-width: 768px) {
  .placeholder-body {
    padding: 16px 20px;
  }
}
</style>
