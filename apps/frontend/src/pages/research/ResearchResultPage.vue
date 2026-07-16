<template>
  <div class="research-page">
    <ResearchPageHeader
      title="研究结果"
      description="研究报告与证据审查"
      :breadcrumbs="[
        { label: 'Research', to: '/research' },
        { label: '项目名称', to: '/research/1' },
        { label: '结果' },
      ]"
    />

    <div class="rrp-body">
      <section class="rrp-section">
        <h2>摘要</h2>
        <p>占位</p>
      </section>

      <section class="rrp-section">
        <h2>证据</h2>
        <p>占位</p>
      </section>

      <section class="rrp-section">
        <h2>引用</h2>
        <p>占位</p>
      </section>

      <section class="rrp-section">
        <h2>导出</h2>
        <p>占位</p>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
</script>

<style scoped>
.rrp-body {
  padding: 24px 32px;
}

.rrp-section {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
}

@media (max-width: 768px) {
  .rrp-body {
    padding: 16px 20px;
  }
}
</style>
