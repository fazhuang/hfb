<template>
  <div class="research-result-page">
    <header class="rrp-header">
      <h1>Report Header</h1>
    </header>

    <section class="rrp-section">
      <h2>Summary</h2>
      <p>Placeholder</p>
    </section>

    <section class="rrp-section">
      <h2>Evidence</h2>
      <p>Placeholder</p>
    </section>

    <section class="rrp-section">
      <h2>Citation</h2>
      <p>Placeholder</p>
    </section>

    <section class="rrp-section">
      <h2>Export</h2>
      <p>Placeholder</p>
    </section>
  </div>
</template>

<script setup lang="ts">
// Scaffold — no business logic, no API, no store
</script>

<style scoped>
.research-result-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 20px;
}

.rrp-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.rrp-section {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
}
</style>
