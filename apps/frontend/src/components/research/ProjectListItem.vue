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
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  transition: border-color var(--transition-base), box-shadow var(--transition-base);
}

.pli-card:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-sm);
}

.pli-card:focus-within {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-sm);
}

.pli-body {
  flex: 1;
  min-width: 0;
}

.pli-main {
  margin-bottom: var(--space-2);
}

.pli-name {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  margin: 0 0 6px;
}

.pli-name-link {
  color: var(--color-text-primary);
  text-decoration: none;
  transition: color var(--transition-base);
}

.pli-name-link:hover {
  color: var(--color-accent);
  text-decoration: underline;
}

.pli-name-link:focus-visible {
  color: var(--color-accent);
  text-decoration: underline;
}

.pli-description {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0;
  line-height: var(--leading-normal);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.pli-meta {
  display: flex;
  gap: var(--space-4);
  flex-wrap: wrap;
}

.pli-date {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.pli-action {
  flex-shrink: 0;
}

.pli-enter-btn {
  display: inline-flex;
  align-items: center;
  padding: var(--btn-padding-md);
  border: 1px solid var(--color-accent);
  border-radius: var(--btn-radius);
  background: transparent;
  font-size: var(--btn-font-md);
  font-weight: var(--font-semibold);
  color: var(--color-accent);
  text-decoration: none;
  cursor: pointer;
  transition: all var(--transition-base);
  white-space: nowrap;
}

.pli-enter-btn:hover {
  background: var(--color-accent);
  color: #fff;
}

.pli-enter-btn:focus-visible {
  background: var(--color-accent);
  color: #fff;
}
</style>
