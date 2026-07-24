<!--
  COMPATIBILITY adapter — Decision A + R3 (Phase 3)

  Route: /v4/research-internal | Name: v4-research
  Status: COMPATIBILITY
  Superseded by: ProjectListPage → ResearchWorkflowPage (project-scoped canonical workflow)

  R3 cleanup: all business logic (API, state, interaction, workflow runner,
  report detail, education mode, citations) removed. This adapter preserves
  the route name 'v4-research' for backward compatibility.

  Why not delete:
    - 29 unit tests (v4-research.test.ts) reference this component
    - Route name 'v4-research' must remain resolvable
    - External bookmarks may target /v4/research-internal

  Compatibility term: until unit tests refactored.
  Precondition for removal: zero references to route name 'v4-research'.
-->
<template>
  <div class="v4-research-adapter">
    <div class="adapter-message">
      <h2>V4 研究</h2>
      <p>V4 研究功能已迁移至研究课题工作流。请在研究课题中创建或打开课题，然后使用标准化工作流。</p>
      <router-link to="/research" class="adapter-link">
        前往研究课题列表 →
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.v4-research-adapter {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: var(--space-5);
}
.adapter-message {
  text-align: center;
  max-width: 480px;
  color: var(--color-text-muted);
}
.adapter-message h2 {
  margin: 0 0 var(--space-3);
  color: var(--color-text-primary);
  font-size: var(--text-xl);
}
.adapter-link {
  display: inline-block;
  margin-top: var(--space-3);
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 600;
}
</style>
