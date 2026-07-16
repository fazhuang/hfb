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
  margin-bottom: 28px;
}

.po-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.po-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

.po-field {
  min-width: 0;
}

.po-field--wide {
  grid-column: 1 / -1;
}

.po-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted, #a0aec0);
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-bottom: 4px;
}

.po-value {
  font-size: 14px;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
  line-height: 1.5;
  word-break: break-word;
}

.po-value--notes {
  white-space: pre-wrap;
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
}

@media (max-width: 600px) {
  .po-grid {
    grid-template-columns: 1fr;
  }
}
</style>
