<template>
  <div class="research-page">
    <ResearchPageHeader
      title="Research"
      description="研究项目列表"
      :breadcrumbs="[{ label: 'Research' }]"
    />

    <div class="rpp-body">
      <div class="rpp-search">
        <input
          type="text"
          placeholder="搜索项目..."
          class="rpp-search-input"
        />
      </div>

      <div class="rpp-list">
        <p>项目列表占位</p>
      </div>

      <div class="rpp-pagination">
        <p>分页区域占位</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
</script>

<style scoped>
.rpp-body {
  padding: 24px 32px;
}

.rpp-search {
  margin-bottom: 24px;
}

.rpp-search-input {
  width: 100%;
  max-width: 480px;
  padding: 10px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 14px;
}

.rpp-list {
  margin-bottom: 24px;
  padding: 32px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
  text-align: center;
}

.rpp-pagination {
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
  text-align: center;
}

@media (max-width: 768px) {
  .rpp-body {
    padding: 16px 20px;
  }
}
</style>
