<template>
  <div class="research-page">
    <ResearchPageHeader
      title="项目详情"
      description="研究项目概览与工具入口"
      :breadcrumbs="[
        { label: 'Research', to: '/research' },
        { label: '项目详情' },
      ]"
    />

    <div class="pdp-body">
      <section class="pdp-section">
        <h2>项目元数据</h2>
        <p>占位</p>
      </section>

      <section class="pdp-section">
        <h2>研究会话</h2>
        <p>占位</p>
      </section>

      <section class="pdp-section">
        <h2>报告</h2>
        <p>占位</p>
      </section>

      <section class="pdp-section">
        <h2>笔记</h2>
        <p>占位</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
</script>

<style scoped>
.pdp-body {
  padding: 24px 32px;
}

.pdp-section {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
}

@media (max-width: 768px) {
  .pdp-body {
    padding: 16px 20px;
  }
}
</style>
