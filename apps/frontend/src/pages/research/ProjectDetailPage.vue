<template>
  <div class="project-detail-page">
    <header class="pdp-header">
      <h1>Project Header</h1>
    </header>

    <section class="pdp-section">
      <h2>Project Metadata</h2>
      <p>Placeholder</p>
    </section>

    <section class="pdp-section">
      <h2>Research Sessions</h2>
      <p>Placeholder</p>
    </section>

    <section class="pdp-section">
      <h2>Reports</h2>
      <p>Placeholder</p>
    </section>

    <section class="pdp-section">
      <h2>Notes</h2>
      <p>Placeholder</p>
    </section>
  </div>
</template>

<script setup lang="ts">
// Scaffold — no business logic, no API, no store
</script>

<style scoped>
.project-detail-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 20px;
}

.pdp-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.pdp-section {
  margin-bottom: 24px;
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
}
</style>
