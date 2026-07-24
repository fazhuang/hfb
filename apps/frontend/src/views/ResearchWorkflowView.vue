<!--
  COMPATIBILITY adapter — Decision A + R3 (Phase 3)

  No direct route — previously embedded in ResearchWorkspaceView.
  R3 cleanup: all business logic (API, state, interaction) removed.
  This adapter delegates users to the canonical research project list,
  where the project-scoped workflow page is accessible.

  Why not delete:
    - 7 unit tests (research-workflow.test.ts) reference this component
    - Embedded stub in evidence-to-graph-e2e.test.ts

  Compatibility term: until unit tests refactored to canonical flow.
  Precondition for removal: zero source/test references.
-->
<template>
  <div class="research-workflow-adapter">
    <div class="adapter-message">
      <p>版本研究已迁移至研究课题工作流。</p>
      <router-link to="/research" class="adapter-link">
        前往研究课题列表
      </router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.research-workflow-adapter {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  padding: var(--space-5);
}
.adapter-message {
  text-align: center;
  color: var(--color-text-muted);
}
.adapter-link {
  display: inline-block;
  margin-top: var(--space-3);
  color: var(--color-accent);
  text-decoration: none;
  font-weight: 600;
}
</style>
