<template>
  <div class="research-page">
    <ResearchPageHeader
      title="研究流程"
      description="五步研究工作流"
      :breadcrumbs="[
        { label: 'Research', to: '/research' },
        { label: '项目名称', to: '/research/1' },
        { label: '工作流' },
      ]"
    />

    <div class="rwf-body">
      <div class="rwf-steps">
        <div class="rwf-step">
          <div class="rwf-step-number">1</div>
          <div class="rwf-step-content">
            <h2>研究问题</h2>
            <p>占位</p>
          </div>
        </div>

        <div class="rwf-step-connector"><span>&darr;</span></div>

        <div class="rwf-step">
          <div class="rwf-step-number">2</div>
          <div class="rwf-step-content">
            <h2>文献选择</h2>
            <p>占位</p>
          </div>
        </div>

        <div class="rwf-step-connector"><span>&darr;</span></div>

        <div class="rwf-step">
          <div class="rwf-step-number">3</div>
          <div class="rwf-step-content">
            <h2>AI 分析</h2>
            <p>占位</p>
          </div>
        </div>

        <div class="rwf-step-connector"><span>&darr;</span></div>

        <div class="rwf-step">
          <div class="rwf-step-number">4</div>
          <div class="rwf-step-content">
            <h2>证据审查</h2>
            <p>占位</p>
          </div>
        </div>

        <div class="rwf-step-connector"><span>&darr;</span></div>

        <div class="rwf-step">
          <div class="rwf-step-number">5</div>
          <div class="rwf-step-content">
            <h2>研究报告</h2>
            <p>占位</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';
</script>

<style scoped>
.rwf-body {
  padding: 24px 32px;
}

.rwf-steps {
  max-width: 720px;
}

.rwf-step {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
}

.rwf-step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-accent, #4299e1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 14px;
  flex-shrink: 0;
}

.rwf-step-content {
  flex: 1;
}

.rwf-step-content h2 {
  margin: 0 0 4px;
  font-size: 16px;
}

.rwf-step-content p {
  margin: 0;
  color: var(--color-text-muted, #718096);
}

.rwf-step-connector {
  text-align: center;
  padding: 8px 0;
  color: var(--color-text-muted, #a0aec0);
  font-size: 20px;
}

@media (max-width: 768px) {
  .rwf-body {
    padding: 16px 20px;
  }
}
</style>
