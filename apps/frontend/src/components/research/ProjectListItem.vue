<template>
  <article class="pli-card">
    <div class="pli-body">
      <div class="pli-main">
        <h3 class="pli-name">
          <router-link
            :to="`/research/${project.id}`"
            class="pli-name-link"
          >
            {{ project.title }}
          </router-link>
        </h3>
        <p v-if="project.description" class="pli-description">{{ project.description }}</p>
      </div>
      <div class="pli-meta">
        <span class="pli-date">
          {{ t('common.created') }}: {{ formatDate(project.created_at) }}
        </span>
        <span class="pli-date">
          {{ t('common.updated') }}: {{ formatDate(project.updated_at) }}
        </span>
      </div>
    </div>
    <div class="pli-action">
      <router-link
        :to="`/research/${project.id}`"
        class="pli-enter-btn"
        :aria-label="`${t('researchEntry.newResearch')} ${project.title}`"
      >
        {{ t('researchEntry.newResearch') }}
      </router-link>
    </div>
  </article>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import type { ResearchProjectSummary } from '@/types/research';

const { t } = useI18n();

defineProps<{
  project: ResearchProjectSummary;
}>();

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('zh-CN');
  } catch {
    return iso;
  }
}
</script>

<style scoped>
.pli-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  background: var(--color-navbar-bg, #fff);
  transition: border-color 0.15s, box-shadow 0.15s;
}

.pli-card:hover {
  border-color: var(--color-accent, #2b6cb0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.pli-body {
  flex: 1;
  min-width: 0;
}

.pli-main {
  margin-bottom: 8px;
}

.pli-name {
  font-size: 16px;
  font-weight: 600;
  margin: 0 0 6px;
}

.pli-name-link {
  color: var(--color-text-primary, #1a365d);
  text-decoration: none;
  transition: color 0.15s;
}

.pli-name-link:hover {
  color: var(--color-accent, #2b6cb0);
  text-decoration: underline;
}

.pli-description {
  font-size: 13px;
  color: var(--color-text-muted, #718096);
  margin: 0;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pli-meta {
  display: flex;
  gap: 16px;
  flex-wrap: wrap;
}

.pli-date {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.pli-action {
  flex-shrink: 0;
}

.pli-enter-btn {
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 8px;
  background: transparent;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  text-decoration: none;
  cursor: pointer;
  transition: all 0.15s;
  white-space: nowrap;
}

.pli-enter-btn:hover {
  background: var(--color-accent, #2b6cb0);
  color: #fff;
}
</style>
