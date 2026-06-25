<template>
  <EntityListPage
    endpoint="/api/v1/books"
    :title="t('nav.documents')"
    route-prefix="/books"
    :get-title="(b) => b.title as string"
    :get-meta="(b) => [b.dynasty as string, b.category as string].filter(Boolean)"
    :get-subtitle="(b) => b.abstract as string | null"
  />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import EntityListPage from '@/components/common/EntityListPage.vue';
const { t } = useI18n();
</script>
