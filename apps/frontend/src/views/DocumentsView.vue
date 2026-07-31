<template>
  <PlaceholderPage
    icon="📚"
    :title="t('nav.documents')"
    :description="$t('onboarding.comingSoon')"
    type="coming-soon"
  />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import PlaceholderPage from '@/components/common/PlaceholderPage.vue';
const { t } = useI18n();
</script>
