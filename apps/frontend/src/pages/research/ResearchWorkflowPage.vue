<template>
  <div class="research-workflow-page">
    <h1>Research Workflow</h1>

    <div class="rwf-steps">
      <div class="rwf-step">
        <div class="rwf-step-number">1</div>
        <div class="rwf-step-content">
          <h2>Research Question</h2>
          <p>Placeholder</p>
        </div>
      </div>

      <div class="rwf-step-connector">
        <span>&darr;</span>
      </div>

      <div class="rwf-step">
        <div class="rwf-step-number">2</div>
        <div class="rwf-step-content">
          <h2>Document Selection</h2>
          <p>Placeholder</p>
        </div>
      </div>

      <div class="rwf-step-connector">
        <span>&darr;</span>
      </div>

      <div class="rwf-step">
        <div class="rwf-step-number">3</div>
        <div class="rwf-step-content">
          <h2>AI Analysis</h2>
          <p>Placeholder</p>
        </div>
      </div>

      <div class="rwf-step-connector">
        <span>&darr;</span>
      </div>

      <div class="rwf-step">
        <div class="rwf-step-number">4</div>
        <div class="rwf-step-content">
          <h2>Evidence Review</h2>
          <p>Placeholder</p>
        </div>
      </div>

      <div class="rwf-step-connector">
        <span>&darr;</span>
      </div>

      <div class="rwf-step">
        <div class="rwf-step-number">5</div>
        <div class="rwf-step-content">
          <h2>Research Report</h2>
          <p>Placeholder</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
// Scaffold — no business logic, no API, no store
</script>

<style scoped>
.research-workflow-page {
  max-width: 720px;
  margin: 0 auto;
  padding: 24px 20px;
}

.rwf-steps {
  margin-top: 24px;
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
</style>
