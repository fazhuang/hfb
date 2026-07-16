<template>
  <div class="research-workspace-page">
    <header class="rwp-header">
      <h1>Research Header</h1>
    </header>

    <div class="rwp-body">
      <main class="rwp-main">
        <section class="rwp-section">
          <h2>Continue Research</h2>
          <p>Placeholder</p>
        </section>

        <section class="rwp-section">
          <h2>Recent Projects</h2>
          <p>Placeholder</p>
        </section>

        <section class="rwp-section">
          <h2>Recent Reports</h2>
          <p>Placeholder</p>
        </section>

        <section class="rwp-section">
          <h2>Recent Notes</h2>
          <p>Placeholder</p>
        </section>
      </main>

      <aside class="rwp-sidebar">
        <h2>AI Research Assistant</h2>
        <p>Placeholder</p>
      </aside>
    </div>
  </div>
</template>

<script setup lang="ts">
// Scaffold — no business logic, no API, no store
</script>

<style scoped>
.research-workspace-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 20px;
}

.rwp-header {
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.rwp-body {
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
</style>
