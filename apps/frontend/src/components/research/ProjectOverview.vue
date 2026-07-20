<template>
  <section class="po-section" aria-labelledby="po-heading">
    <h2 id="po-heading" class="po-heading">课题信息</h2>

    <dl class="po-grid">
      <div class="po-field">
        <dt class="po-label">课题名称</dt>
        <dd class="po-value">{{ project.title }}</dd>
      </div>

      <div v-if="project.context_notes" class="po-field po-field--wide">
        <dt class="po-label">课题说明</dt>
        <dd class="po-value po-value--notes">{{ project.context_notes }}</dd>
      </div>

      <div class="po-field">
        <dt class="po-label">创建时间</dt>
        <dd class="po-value">
          <time :datetime="project.created_at ?? undefined">
            {{ formatDate(project.created_at) }}
          </time>
        </dd>
      </div>

      <div class="po-field">
        <dt class="po-label">更新时间</dt>
        <dd class="po-value">
          <time :datetime="project.updated_at ?? undefined">
            {{ formatDate(project.updated_at) }}
          </time>
        </dd>
      </div>
    </dl>
  </section>
</template>

<script setup lang="ts">
import type { ResearchProjectDetail } from '@/types/research';

defineProps<{
  project: ResearchProjectDetail;
}>();

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
</script>

<style scoped>
.po-section {
  margin-bottom: var(--space-7);
}

.po-heading {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.po-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--space-4);
}

.po-field {
  min-width: 0;
}

.po-field--wide {
  grid-column: 1 / -1;
}

.po-label {
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: var(--space-1);
}

.po-value {
  font-size: var(--text-base);
  color: var(--color-text-primary);
  margin: 0;
  line-height: var(--leading-normal);
  word-break: break-word;
}

.po-value--notes {
  white-space: pre-wrap;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

@media (max-width: 600px) {
  .po-grid {
    grid-template-columns: 1fr;
  }
}
</style>
