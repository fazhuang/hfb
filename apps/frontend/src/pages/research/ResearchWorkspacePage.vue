<template>
  <div class="research-page">
    <ResearchPageHeader
      title="研究工作台"
      description="AI 辅助研究空间"
      :breadcrumbs="[
        { label: 'Research', to: '/research' },
        { label: '项目名称', to: '/research/1' },
        { label: '工作台' },
      ]"
    />

    <div class="rwp-body">
      <main class="rwp-main">
        <section class="rwp-section">
          <h2>继续研究</h2>
          <p>占位</p>
        </section>

        <section class="rwp-section">
          <h2>最近项目</h2>
          <p>占位</p>
        </section>

        <section class="rwp-section">
          <h2>最近报告</h2>
          <p>占位</p>
        </section>

        <section class="rwp-section">
          <h2>最近笔记</h2>
          <p>占位</p>
        </section>
      </main>

      <aside class="rwp-sidebar">
        <h2>AI 研究助手</h2>
        <p>占位</p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
</script>

<style scoped>
.rwp-body {
  padding: 24px 32px;
  display: flex;
  gap: 24px;
}

.rwp-main {
  flex: 1;
}

.rwp-sidebar {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid var(--color-border, #e2e8f0);
  padding-left: 24px;
}

.rwp-section {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
}

@media (max-width: 768px) {
  .rwp-body {
    flex-direction: column;
    padding: 16px 20px;
  }

  .rwp-sidebar {
    width: 100%;
    border-left: none;
    border-top: 1px solid var(--color-border, #e2e8f0);
    padding-left: 0;
    padding-top: 16px;
  }
}
</style>
