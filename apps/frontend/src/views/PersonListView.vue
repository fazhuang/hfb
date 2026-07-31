<template>
  <EntityListPage
    endpoint="/api/v1/persons"
    :title="t('nav.persons')"
    route-prefix="/persons"
    :get-title="(p) => p.name as string"
    :get-meta="
      (p) =>
        [
          p.dynasty as string,
          p.birth_year ? `${p.birth_year} - ${p.death_year || '?'}` : '',
        ].filter(Boolean)
    "
    :get-subtitle="(p) => p.expertise as string | null"
  />
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import EntityListPage from '@/components/common/EntityListPage.vue';
const { t } = useI18n();
</script>
