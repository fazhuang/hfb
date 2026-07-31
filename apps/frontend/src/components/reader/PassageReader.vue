<template>
  <div class="passage-reader">
    <div v-if="loading" class="loading-state" role="status" aria-live="polite">
      {{ t('common.loading') }}
    </div>
    <div v-else-if="error" class="error-state" role="alert" aria-live="assertive">{{ error }}</div>
    <div v-else-if="passage" class="passage-content">
      <div class="passage-header">
        <span class="passage-order">#{{ passage.order }}</span>
        <span v-if="passage.tags" class="passage-tags">
          <span v-for="tag in tagList" :key="tag" class="tag">{{ tag }}</span>
        </span>
      </div>

      <div class="passage-text">{{ passage.content_text }}</div>

      <div v-if="passage.translation" class="passage-translation">
        <h4>{{ t('passage.translation') }}</h4>
        <p>{{ passage.translation }}</p>
      </div>

      <div v-if="passage.notes" class="passage-notes">
        <h4>{{ t('passage.notes') }}</h4>
        <p>{{ passage.notes }}</p>
      </div>

      <div v-if="passage.version_id" class="passage-meta">
        <span class="meta-label">{{ t('passage.versionLinked') }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useEntityDetail } from '@/composables/useApi';

const { t } = useI18n();

const props = defineProps<{ passageId: string }>();

interface PassageDetail {
  id: string;
  chapter_id: string;
  version_id: string | null;
  content_text: string;
  translation: string | null;
  notes: string | null;
  order: number;
  tags: string | null;
}

const {
  entity: passage,
  loading,
  error,
  fetch,
} = useEntityDetail<PassageDetail>((id) => `/api/v1/passages/${id}`);

const tagList = computed(() => {
  if (!passage.value?.tags) return [];
  return passage.value.tags
    .split(',')
    .map((t: string) => t.trim())
    .filter(Boolean);
});

onMounted(() => fetch(props.passageId));
</script>

<style scoped>
.passage-reader {
  padding: var(--space-6);
}

.passage-content {
  max-width: 720px;
  margin: 0 auto;
}

.passage-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: 20px;
}

.passage-order {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent);
  padding: var(--space-0-5) 8px;
  background: var(--color-accent-light);
  border-radius: var(--radius-sm);
}

.passage-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.tag {
  font-size: 11px;
  padding: var(--space-0-25) 6px;
  background: var(--color-hover);
  border-radius: var(--radius-sm);
  color: var(--color-text-muted);
}

.passage-text {
  font-size: 18px;
  line-height: 2;
  color: var(--color-text-primary);
  padding: var(--space-5) 0;
  border-top: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  overflow-wrap: break-word;
  word-break: break-word;
}

.passage-translation {
  margin-top: 24px;
  padding: var(--space-4);
  background: var(--color-hover, var(--color-page-bg));
  border-radius: var(--radius-lg);
}

.passage-translation h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-2);
}

.passage-translation p {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary);
  margin: 0;
}

.passage-notes {
  margin-top: 16px;
  padding: var(--space-4);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-lg);
}

.passage-notes h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-2);
}

.passage-notes p {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin: 0;
}

.passage-meta {
  margin-top: 12px;
}

.meta-label {
  font-size: 12px;
  color: var(--color-text-muted);
}

.loading-state,
.error-state {
  text-align: center;
  padding: var(--space-15) 20px;
  color: var(--color-text-muted);
  font-size: 14px;
}
</style>
