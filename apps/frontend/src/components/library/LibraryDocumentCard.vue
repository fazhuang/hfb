<template>
  <router-link :to="`/library/${doc.id}`" class="lib-list-item">
    <!-- 朝代/类别视觉锚点 -->
    <div class="lib-item-anchor" aria-hidden="true">
      <HfbIcon :icon="categoryIcon" :size="20" />
    </div>

    <div class="lib-item-main">
      <div class="lib-item-title-row">
        <div class="lib-item-title">{{ doc.title }}</div>
        <span v-if="doc.rag_enabled" class="lib-badge lib-badge-rag">RAG</span>
        <span v-if="doc.withdrawn_at" class="lib-badge lib-badge-withdrawn">已撤回</span>
      </div>
      <div class="lib-item-meta">
        <span v-if="doc.dynasty" class="lib-meta-tag">{{ doc.dynasty }}</span>
        <span v-if="doc.category" class="lib-meta-tag lib-meta-tag--category">{{ doc.category }}</span>
        <span v-if="doc.source_name" class="lib-meta-tag lib-meta-tag--source">{{ doc.source_name }}</span>
      </div>
    </div>

    <div class="lib-item-right">
      <div class="lib-item-badges">
        <span class="lib-badge lib-badge-copyright">{{
          COPYRIGHT_LABELS[doc.copyright_status] || doc.copyright_status
        }}</span>
        <span class="lib-badge" :class="`lib-badge-review-${doc.review_status}`">{{
          REVIEW_LABELS[doc.review_status] || doc.review_status
        }}</span>
      </div>
      <div v-if="doc.created_at" class="lib-item-date">{{ formatDate(doc.created_at) }}</div>
    </div>
  </router-link>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import HfbIcon from '@/components/common/HfbIcon.vue';
import type { LucideIconName } from '@/components/common/HfbIcon.vue';
import type { LibraryDocument } from '@/types/library';
import { COPYRIGHT_LABELS, REVIEW_LABELS } from '@/types/library';

const props = defineProps<{ doc: LibraryDocument }>();

const categoryIcon = computed((): LucideIconName => {
  const c = props.doc.category ?? '';
  if (/医|药|针灸|经/.test(c)) return 'book-marked';
  if (/史|传|记/.test(c)) return 'scroll-text';
  if (/版|本/.test(c)) return 'landmark';
  return 'book-open';
});

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('zh-CN');
}
</script>

<style scoped>
.lib-list-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  background: var(--color-surface);
  text-decoration: none;
  color: inherit;
  box-shadow: var(--shadow-card-xs);
  transition:
    border-color var(--transition-base),
    box-shadow var(--transition-base);
  cursor: pointer;
}

.lib-list-item:hover {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-card-hover);
}

.lib-list-item:focus-visible {
  border-color: var(--color-accent);
  box-shadow: var(--shadow-card-hover);
}

.lib-item-anchor {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-md);
  background: var(--color-accent-light);
  color: var(--color-accent);
}

.lib-item-main {
  flex: 1;
  min-width: 0;
}

.lib-item-title-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-1-5);
}

.lib-item-title {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  font-family: var(--font-serif);
  letter-spacing: 0.02em;
}

.lib-item-meta {
  display: flex;
  gap: var(--space-1-5);
  flex-wrap: wrap;
}

.lib-meta-tag {
  font-size: var(--text-xs);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--color-accent);
  color: var(--color-on-accent);
}

.lib-meta-tag--category {
  background: var(--color-accent-light);
  color: var(--color-accent);
}

.lib-meta-tag--source {
  background: var(--color-hover);
  color: var(--color-text-secondary);
}

.lib-item-right {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: var(--space-1-5);
}

.lib-item-badges {
  display: flex;
  gap: var(--space-1-5);
  flex-wrap: wrap;
  justify-content: flex-end;
}

.lib-badge {
  font-size: 11px;
  padding: 2px 8px;
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
  background: var(--color-info-bg);
  color: var(--color-info-text);
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
  background: var(--color-info-bg);
  color: var(--color-info-text);
}

.lib-badge-withdrawn {
  background: var(--color-border);
  color: var(--color-text-muted);
}

.lib-item-date {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .lib-item-right {
    align-items: flex-start;
  }

  .lib-item-badges {
    justify-content: flex-start;
  }
}
</style>
