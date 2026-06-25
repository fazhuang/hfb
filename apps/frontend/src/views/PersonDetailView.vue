<template>
  <div class="person-detail-page">
    <div v-if="loading" class="loading-state">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error-state">{{ error }}</div>
    <div v-else-if="person" class="person-content">
      <div class="detail-header">
        <h1>{{ person.name }}</h1>
        <p v-if="person.name_zh" class="name-alt">{{ person.name_zh }}</p>
        <div class="header-meta">
          <span v-if="person.dynasty" class="meta-tag">{{ person.dynasty }}</span>
          <span v-if="lifeSpan" class="meta-tag">{{ lifeSpan }}</span>
          <span v-if="person.expertise" class="meta-tag">{{ person.expertise }}</span>
        </div>
      </div>

      <div class="info-grid">
        <div v-if="person.courtesy_name" class="info-row">
          <span class="info-label">{{ t('person.courtesyName') }}</span>
          <span>{{ person.courtesy_name }}</span>
        </div>
        <div v-if="person.pseudonym" class="info-row">
          <span class="info-label">{{ t('person.pseudonym') }}</span>
          <span>{{ person.pseudonym }}</span>
        </div>
        <div v-if="person.birth_place" class="info-row">
          <span class="info-label">{{ t('person.birthPlace') }}</span>
          <span>{{ person.birth_place }}</span>
        </div>
      </div>

      <div v-if="person.biography" class="person-bio">
        <h3>{{ t('person.biography') }}</h3>
        <p>{{ person.biography }}</p>
        <span v-if="person.biography_source" class="bio-source">{{ person.biography_source }}</span>
      </div>

      <div v-if="person.notable_works" class="person-works">
        <h3>{{ t('person.notableWorks') }}</h3>
        <div class="works-list">
          <span v-for="work in workList" :key="work" class="work-item">{{ work }}</span>
        </div>
      </div>

      <div v-if="person.external_ref" class="external-ref">
        <a :href="person.external_ref" target="_blank" rel="noopener">{{ t('person.externalRef') }}</a>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute } from 'vue-router';
import { useEntityDetail } from '@/composables/useApi';

const { t } = useI18n();
const route = useRoute();

interface PersonDetail {
  id: string;
  name: string;
  name_zh: string | null;
  name_pinyin: string | null;
  courtesy_name: string | null;
  pseudonym: string | null;
  dynasty: string | null;
  birth_year: number | null;
  death_year: number | null;
  birth_place: string | null;
  biography: string | null;
  biography_source: string | null;
  notable_works: string | null;
  expertise: string | null;
  external_ref: string | null;
}

const { entity: person, loading, error, fetch } = useEntityDetail<PersonDetail>(
  (id) => `/api/v1/persons/${id}`,
);

const lifeSpan = computed(() => {
  if (!person.value) return null;
  const b = person.value.birth_year;
  const d = person.value.death_year;
  if (b && d) return `${b} - ${d}`;
  if (b) return `${b} - ?`;
  return null;
});

const workList = computed(() => {
  if (!person.value?.notable_works) return [];
  return person.value.notable_works.split(',').map((w: string) => w.trim()).filter(Boolean);
});

onMounted(() => fetch(route.params.id as string));
</script>

<style scoped>
.person-detail-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 32px 24px;
}

.detail-header {
  margin-bottom: 24px;
}

.detail-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
}

.name-alt {
  font-size: 16px;
  color: var(--color-text-muted, #a0aec0);
  margin: 4px 0 12px;
}

.header-meta {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.meta-tag {
  font-size: 13px;
  padding: 3px 10px;
  background: var(--color-accent, #2b6cb0);
  color: white;
  border-radius: 4px;
}

.info-grid {
  margin-bottom: 24px;
}

.info-row {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
}

.info-label {
  font-weight: 600;
  min-width: 64px;
  color: var(--color-text-muted, #a0aec0);
}

.person-bio {
  padding: 20px;
  background: var(--color-hover, #f7fafc);
  border-radius: 8px;
  margin-bottom: 24px;
}

.person-bio h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 8px;
  color: var(--color-text-primary, #1a365d);
}

.person-bio p {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 8px;
}

.bio-source {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.person-works {
  margin-bottom: 24px;
}

.person-works h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 12px;
}

.works-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.work-item {
  padding: 6px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 6px;
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  background: var(--color-navbar-bg, #fff);
}

.external-ref a {
  font-size: 13px;
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
}

.external-ref a:hover {
  text-decoration: underline;
}

.loading-state, .error-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--color-text-muted, #a0aec0);
  font-size: 14px;
}
</style>
