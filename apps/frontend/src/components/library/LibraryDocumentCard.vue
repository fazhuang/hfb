<template>
  <router-link :to="`/library/${doc.id}`" class="lib-list-item">
    <div class="lib-item-title">{{ doc.title }}</div>
    <div class="lib-item-meta">
      <span v-if="doc.dynasty" class="lib-meta-tag">{{ doc.dynasty }}</span>
      <span v-if="doc.category" class="lib-meta-tag">{{ doc.category }}</span>
      <span v-if="doc.source_name" class="lib-meta-tag lib-meta-tag--source">{{ doc.source_name }}</span>
    </div>
    <div class="lib-item-badges">
      <span class="lib-badge lib-badge-copyright">{{ COPYRIGHT_LABELS[doc.copyright_status] || doc.copyright_status }}</span>
      <span class="lib-badge" :class="`lib-badge-review-${doc.review_status}`">{{ REVIEW_LABELS[doc.review_status] || doc.review_status }}</span>
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
  padding: 16px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 10px;
  background: var(--color-navbar-bg, #fff);
  text-decoration: none;
  color: inherit;
  transition: box-shadow 0.15s, border-color 0.15s;
  cursor: pointer;
}

.lib-list-item:hover {
  border-color: var(--color-accent, #2b6cb0);
  box-shadow: 0 2px 8px rgba(43, 108, 176, 0.1);
}

.lib-list-item:focus-visible {
  border-color: var(--color-accent, #2b6cb0);
  box-shadow: 0 2px 8px rgba(43, 108, 176, 0.1);
}

.lib-item-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin-bottom: 6px;
}

.lib-item-meta {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.lib-meta-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--color-accent, #2b6cb0);
  color: white;
}

.lib-meta-tag--source {
  background: var(--color-tag-bg, #edf2f7);
  color: var(--color-text-secondary, #4a5568);
}

.lib-item-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 4px;
}

.lib-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}

.lib-badge-copyright {
  background: var(--color-tag-bg, #edf2f7);
  color: var(--color-text-secondary, #4a5568);
}

.lib-badge-review-pending_review { background: #fefcbf; color: #975a16; }
.lib-badge-review-under_review { background: #bee3f8; color: #2a4365; }
.lib-badge-review-approved { background: #c6f6d5; color: #276749; }
.lib-badge-review-rejected { background: #fed7d7; color: #c53030; }

.lib-badge-rag {
  background: #bee3f8;
  color: #2a4365;
}

.lib-badge-withdrawn {
  background: #e2e8f0;
  color: #718096;
}

.lib-item-date {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  margin-top: 4px;
}
</style>
