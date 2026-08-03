<template>
  <section class="rres-section" aria-labelledby="rres-heading">
    <h2 id="rres-heading" class="rres-heading">研究资料</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载研究资料..." />

    <!-- Error -->
    <ErrorState
      v-else-if="error"
      :message="error"
      title="研究资料加载失败"
      @retry="$emit('retry')"
    />

    <!-- Empty -->
    <EmptyState
      v-else-if="displayCitations.length === 0"
      title="尚未保存研究资料"
      description="在研究过程中保存的引用文献将显示在这里。"
      icon="📚"
    />

    <!-- Citation list — max 5 items -->
    <ul v-else class="rres-list" role="list">
      <li v-for="cite in displayCitations" :key="cite.id" class="rres-item">
        <div class="rres-item-main">
          <p class="rres-citation-text">{{ cite.citation_text }}</p>
          <p class="rres-source">{{ cite.source_document }}</p>
          <div v-if="cite.tags" class="rres-tags">
            <span class="rres-tag">{{ cite.tags }}</span>
          </div>
        </div>
        <time :datetime="cite.created_at ?? undefined" class="rres-time">
          {{ formatDate(cite.created_at) }}
        </time>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
/**
 * ResearchResources — 研究资料（引文集合，受控展示组件）
 *
 * Receives citations data from parent page. Does NOT make its own API calls.
 */
import { computed } from 'vue';
import type { ResearchCitationSummary } from '@/types/research';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

const props = defineProps<{
  citations: ResearchCitationSummary[];
  loading: boolean;
  error: string | null;
}>();

defineEmits<{
  retry: [];
}>();

const MAX_ITEMS = 5;

const displayCitations = computed(() => props.citations.slice(0, MAX_ITEMS));

function formatDate(iso?: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('zh-CN', {
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
.rres-section {
  margin-bottom: var(--space-7);
}

.rres-heading {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.rres-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.rres-item {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.rres-item-main {
  flex: 1;
  min-width: 0;
}

.rres-citation-text {
  font-size: var(--text-base);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1);
  line-height: var(--leading-normal);
  word-break: break-word;
}

.rres-source {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-1);
}

.rres-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.rres-tag {
  font-size: 11px;
  padding: var(--space-0-25) 8px;
  border-radius: var(--radius-sm);
  background: var(--color-hover);
  color: var(--color-text-muted);
}

.rres-time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 2px;
}
</style>
