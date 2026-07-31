<template>
  <router-link :to="`/library/${doc.id}`" class="lib-list-item">
    <div class="lib-item-title">{{ doc.title }}</div>
    <div class="lib-item-meta">
      <span v-if="doc.dynasty" class="lib-meta-tag">{{ doc.dynasty }}</span>
      <span v-if="doc.category" class="lib-meta-tag">{{ doc.category }}</span>
      <span v-if="doc.source_name" class="lib-meta-tag lib-meta-tag--source">{{
        doc.source_name
      }}</span>
    </div>
    <div class="lib-item-badges">
      <span class="lib-badge lib-badge-copyright">{{
        COPYRIGHT_LABELS[doc.copyright_status] || doc.copyright_status
      }}</span>
      <span class="lib-badge" :class="`lib-badge-review-${doc.review_status}`">{{
        REVIEW_LABELS[doc.review_status] || doc.review_status
      }}</span>
      <span v-if="doc.rag_enabled" class="lib-badge lib-badge-rag">RAG</span>
      <span v-if="doc.withdrawn_at" class="lib-badge lib-badge-withdrawn">已撤回</span>
    </div>
    <div v-if="doc.created_at" class="lib-item-date">{{ formatDate(doc.created_at) }}</div>
  </router-link>
</template>

<script setup lang="ts">
import type { LibraryDocument } from '@/types/library';
import { COPYRIGHT_LABELS, REVIEW_LABELS } from '@/types/library';

defineProps<{ doc: LibraryDocument }>();

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN');
}
</script>

<style scoped>
.lib-list-item {
  display: block;
  padding: var(--space-4) 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-navbar-bg, var(--color-surface));
  text-decoration: none;
  color: inherit;
  transition:
    box-shadow var(--transition-base),
    border-color 0.15s;
  cursor: pointer;
}

.lib-list-item:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-accent-sm);
}

.lib-list-item:focus-visible {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-accent-sm);
}

.lib-item-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin-bottom: 6px;
}

.lib-item-meta {
  display: flex;
  gap: var(--space-1-5);
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.lib-meta-tag {
  font-size: 12px;
  padding: var(--space-0-5) 8px;
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: white;
}

.lib-meta-tag--source {
  background: var(--color-hover);
  color: var(--color-text-secondary);
}

.lib-item-badges {
  display: flex;
  gap: var(--space-1-5);
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.lib-badge {
  font-size: 11px;
  padding: var(--space-0-5) 8px;
  border-radius: var(--radius-sm);
  white-space: nowrap;
}

.lib-badge-copyright {
  background: var(--color-hover);
  color: var(--color-text-secondary);
}

.lib-badge-review-pending_review {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}
.lib-badge-review-under_review {
  background: var(--color-info-text);
  color: var(--color-accent-light);
}
.lib-badge-review-approved {
  background: var(--color-success-icon-bg);
  color: var(--color-success-text);
}
.lib-badge-review-rejected {
  background: var(--color-error-icon-bg);
  color: var(--color-error-text);
}

.lib-badge-rag {
  background: var(--color-info-text);
  color: var(--color-accent-light);
}

.lib-badge-withdrawn {
  background: var(--color-border);
  color: var(--color-text-muted);
}

.lib-item-date {
  font-size: 12px;
  color: var(--color-text-muted);
  margin-top: 4px;
}
</style>
