<template>
  <router-view />
  <HfbToastProvider />
</template>

<script setup lang="ts">
import { useTheme } from '@/composables/useTheme';
import HfbToastProvider from '@/components/common/HfbToastProvider.vue';

// Initialize theme on app mount
useTheme();
</script>

<style>
/* Router-view root element — layout pages handle their own structure */
</style>
