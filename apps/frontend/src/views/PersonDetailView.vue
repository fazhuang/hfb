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
  padding: var(--space-8) 24px;
}

.detail-header {
  margin-bottom: 24px;
}

.detail-header h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0;
}

.name-alt {
  font-size: 16px;
  color: var(--color-text-muted);
  margin: var(--space-1) 0 12px;
}

.header-meta {
  display: flex;
  gap: var(--space-2);
  margin-top: 12px;
}

.meta-tag {
  font-size: 13px;
  padding: var(--space-0-75) 10px;
  background: var(--color-accent);
  color: white;
  border-radius: var(--radius-sm);
}

.info-grid {
  margin-bottom: 24px;
}

.info-row {
  display: flex;
  gap: var(--space-3);
  padding: var(--space-2) 0;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.info-label {
  font-weight: 600;
  min-width: 64px;
  color: var(--color-text-muted);
}

.person-bio {
  padding: var(--space-5);
  background: var(--color-hover, var(--color-page-bg));
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
}

.person-bio h3 {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 var(--space-2);
  color: var(--color-text-primary);
}

.person-bio p {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-2);
}

.bio-source {
  font-size: 12px;
  color: var(--color-text-muted);
}

.person-works {
  margin-bottom: 24px;
}

.person-works h3 {
  font-size: 15px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
}

.works-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.work-item {
  padding: var(--space-1-5) 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--color-text-secondary);
  background: var(--color-navbar-bg, var(--color-surface));
}

.external-ref a {
  font-size: 13px;
  color: var(--color-accent);
  text-decoration: none;
}

.external-ref a:hover {
  text-decoration: underline;
}

.loading-state, .error-state {
  text-align: center;
  padding: var(--space-20) 20px;
  color: var(--color-text-muted);
  font-size: 14px;
}
</style>
