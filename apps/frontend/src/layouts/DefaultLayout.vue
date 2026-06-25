<template>
  <div class="default-layout">
    <AppNavbar />
    <AppMain>
      <router-view />
    </AppMain>
    <AppFooter />
  </div>
</template>

<script setup lang="ts">
import AppNavbar from '@/components/layout/AppNavbar.vue';
import AppMain from '@/components/layout/AppMain.vue';
import AppFooter from '@/components/layout/AppFooter.vue';
</script>

<style scoped>
.default-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
</style>
