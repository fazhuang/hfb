<template>
  <router-view />
</template>

<script setup lang="ts">
import { useTheme } from '@/composables/useTheme';

// Initialize theme on app mount
useTheme();
</script>

<style>
/* Router-view root element — layout pages handle their own structure */
</style>
