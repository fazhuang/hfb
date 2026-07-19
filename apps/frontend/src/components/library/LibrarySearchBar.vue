<template>
  <div class="lib-search-bar">
    <div class="lib-search-input-wrap">
      <input
        v-model="query"
        type="text"
        :placeholder="t('common.search') + '...'"
        @keyup.enter="emitSearch"
      />
      <button class="lib-search-btn" @click="emitSearch">{{ t('common.search') }}</button>
    </div>
    <div class="lib-filter-chips">
      <select v-model="copyrightStatus" class="lib-filter-select" @change="emitSearch">
        <option value="">— 版权 —</option>
        <option v-for="cs in COPYRIGHT_STATUSES" :key="cs" :value="cs">{{ COPYRIGHT_LABELS[cs] || cs }}</option>
      </select>
      <select v-model="reviewStatus" class="lib-filter-select" @change="emitSearch">
        <option value="">— 审核 —</option>
        <option v-for="rs in REVIEW_STATUSES" :key="rs" :value="rs">{{ REVIEW_LABELS[rs] || rs }}</option>
      </select>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import { COPYRIGHT_STATUSES, COPYRIGHT_LABELS, REVIEW_STATUSES, REVIEW_LABELS } from '@/types/library';

const { t } = useI18n();

const emit = defineEmits<{
  (e: 'search', filters: { query: string; copyrightStatus: string; reviewStatus: string }): void;
}>();

const query = ref('');
const copyrightStatus = ref('');
const reviewStatus = ref('');

function emitSearch() {
  emit('search', {
    query: query.value.trim(),
    copyrightStatus: copyrightStatus.value,
    reviewStatus: reviewStatus.value,
  });
}
</script>

<style scoped>
.lib-search-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.lib-search-input-wrap {
  display: flex;
  gap: 8px;
}

.lib-search-input-wrap input {
  padding: 8px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 14px;
  min-width: 220px;
  background: var(--color-page-bg, #f7fafc);
  color: var(--color-text-primary, #1a365d);
}

.lib-search-btn {
  padding: 8px 16px;
  background: var(--color-accent, #2b6cb0);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
}

.lib-filter-select {
  padding: 8px 12px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 13px;
  background: var(--color-navbar-bg, #fff);
  color: var(--color-text-primary, #1a365d);
}
</style>
