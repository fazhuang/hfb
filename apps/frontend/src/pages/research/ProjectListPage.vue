<template>
  <div class="project-list-page">
    <h1>Project List</h1>

    <div class="plp-search">
      <input
        type="text"
        placeholder="Search projects..."
        class="plp-search-input"
      />
    </div>

    <div class="plp-list">
      <p>Project list placeholder</p>
    </div>

    <div class="plp-pagination">
      <p>Pagination placeholder</p>
    </div>
  </div>
</template>

<script setup lang="ts">
// Scaffold — no business logic, no API, no store
</script>

<style scoped>
.project-list-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px 20px;
}

.plp-search {
  margin-bottom: 24px;
}

.plp-search-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 14px;
}

.plp-list {
  margin-bottom: 24px;
  padding: 32px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
  text-align: center;
}

.plp-pagination {
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
  text-align: center;
}
</style>
