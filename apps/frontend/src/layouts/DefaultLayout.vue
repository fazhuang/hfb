<template>
  <div class="default-layout">
    <AppNavbar v-if="!isResearchApp" />
    <AppMain>
      <router-view />
    </AppMain>
    <AppFooter v-if="!isResearchApp" />
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import AppNavbar from '@/components/layout/AppNavbar.vue';
import AppMain from '@/components/layout/AppMain.vue';
import AppFooter from '@/components/layout/AppFooter.vue';

const route = useRoute();
const isResearchApp = computed(() => route.meta.appShell === 'research');
</script>

<style scoped>
.default-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
