<template>
  <div class="passage-reader">
    <div v-if="loading" class="loading-state" role="status" aria-live="polite">{{ t('common.loading') }}</div>
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

const { entity: passage, loading, error, fetch } = useEntityDetail<PassageDetail>(
  (id) => `/api/v1/passages/${id}`,
);

const tagList = computed(() => {
  if (!passage.value?.tags) return [];
  return passage.value.tags.split(',').map((t: string) => t.trim()).filter(Boolean);
});

onMounted(() => fetch(props.passageId));
</script>

<style scoped>
.passage-reader {
  padding: 24px;
}

.passage-content {
  max-width: 720px;
  margin: 0 auto;
}

.passage-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.passage-order {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-accent, #2b6cb0);
  padding: 2px 8px;
  background: var(--color-active, #ebf8ff);
  border-radius: 4px;
}

.passage-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.tag {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--color-tag-bg, #edf2f7);
  border-radius: 3px;
  color: var(--color-text-muted, #718096);
}

.passage-text {
  font-size: 18px;
  line-height: 2;
  color: var(--color-text-primary, #1a365d);
  padding: 20px 0;
  border-top: 1px solid var(--color-border, #e2e8f0);
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  overflow-wrap: break-word;
  word-break: break-word;
}

.passage-translation {
  margin-top: 24px;
  padding: 16px;
  background: var(--color-hover, #f7fafc);
  border-radius: 8px;
}

.passage-translation h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 8px;
}

.passage-translation p {
  font-size: 14px;
  line-height: 1.8;
  color: var(--color-text-secondary, #4a5568);
  margin: 0;
}

.passage-notes {
  margin-top: 16px;
  padding: 16px;
  border: 1px dashed var(--color-border, #e2e8f0);
  border-radius: 8px;
}

.passage-notes h4 {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 8px;
}

.passage-notes p {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  margin: 0;
}

.passage-meta {
  margin-top: 12px;
}

.meta-label {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.loading-state, .error-state {
  text-align: center;
  padding: 60px 20px;
  color: var(--color-text-muted, #a0aec0);
  font-size: 14px;
}
</style>
