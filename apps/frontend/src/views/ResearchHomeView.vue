<!--
  COMPATIBILITY adapter — Decision A (Phase 3 R3)

  Route: /research/home | Name: research-home
  Status: COMPATIBILITY
  Superseded by: ProjectListPage + ProjectDetailPage

  This view is a thin adapter that internally delegates to the canonical
  ProjectListPage. The URL, route name, and auth boundary are preserved
  for backward compatibility.

  Why not delete:
    - Highest fan-in of any legacy view: 9 references across:
      ResearchWorkspaceView, V4ResearchView, ResearchWorkflowView,
      ResearchNewView, SearchView, DashboardView, HomeView, AppNavbar,
      and router tests
    - External bookmarks may target /research/home
    - Router name 'research-home' must remain resolvable

  Compatibility term: indefinite — until all external references are updated.
  Precondition for removal: zero external references to route name 'research-home'.
-->
<template>
  <div class="research-home-adapter" />
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
.research-home-adapter {
  min-height: 0;
}
</style>
