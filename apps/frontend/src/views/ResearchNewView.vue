<!--
  COMPATIBILITY adapter — Decision A (Phase 3 R3)

  Route: /research/new | Name: research-new
  Status: COMPATIBILITY
  Superseded by: ProjectListPage (CreateProjectDialog inline)

  This view is a thin adapter that internally delegates to the canonical
  ProjectListPage. The URL, route name, and auth boundary are preserved
  for backward compatibility.

  Why not delete:
    - Referenced by: HomeView, DashboardView, AppNavbar (legacy links)
    - External bookmarks may still target /research/new
    - Router name 'research-new' must remain resolvable

  Compatibility term: indefinite — until all external references are updated.
  Precondition for removal: zero external references to route name 'research-new'.
-->
<template>
  <div class="research-new-adapter">
    <p class="adapter-notice" aria-live="polite">正在跳转到研究课题列表...</p>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

onMounted(() => {
  router.replace({ name: 'research-project-list' });
});
</script>

<style scoped>
.research-new-adapter {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
}
.adapter-notice {
  color: var(--color-text-muted);
  font-size: var(--text-base);
}
</style>
