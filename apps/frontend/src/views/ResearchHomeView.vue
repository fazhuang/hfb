<!--
  COMPATIBILITY adapter — Decision A (Phase 3 R3)

  Route: /research/home | Name: research-home
  Status: COMPATIBILITY
  Superseded by: ProjectListPage

  Decision A: Legacy URL is preserved — no router.replace / push.
  This adapter directly renders the canonical business implementation
  in the legacy URL context. No independent API, state, or interaction logic.

  Why not delete:
    - Router name 'research-home' must remain resolvable for external bookmarks.
    - External references may target /research/home.

  Compatibility term: indefinite — until zero external references confirmed.
  Precondition for removal: zero external references to route name 'research-home'.
-->
<template>
  <ProjectListPage />
</template>

<script setup lang="ts">
import ProjectListPage from '@/pages/research/ProjectListPage.vue';
</script>
