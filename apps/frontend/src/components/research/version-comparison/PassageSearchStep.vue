<template>
  <section class="vc-step vc-search-step" aria-labelledby="vc-search-title">
    <div class="vc-step-heading">
      <p class="vc-step-number">01</p>
      <h2 id="vc-search-title">检索条文</h2>
    </div>

    <form class="vc-search-form" @submit.prevent="$emit('search')">
      <label for="vc-search-input">搜索经文</label>
      <div class="vc-search-row">
        <input
          id="vc-search-input"
          v-model="queryModel"
          type="search"
          placeholder="输入关键词搜索经文..."
          :disabled="searching"
        />
        <button
          type="submit"
          class="button button--primary"
          :disabled="searching || !queryModel.trim()"
        >
          {{ searching ? '搜索中...' : '搜索' }}
        </button>
      </div>
    </form>

    <div v-if="results.length" class="vc-search-results">
      <article v-for="item in results" :key="item.id" class="vc-result-item">
        <div class="vc-result-main">
          <div class="vc-result-meta">
            <span>{{ item.metadata.version_name || '未知版本' }}</span>
            <span>{{ item.metadata.chapter_title || '未知章节' }}</span>
          </div>
          <p>{{ item.snippet || item.title }}</p>
          <small>{{ provenanceLabel(item) }}</small>
        </div>
        <div class="vc-result-actions">
          <button
            class="button button--compact"
            :class="{ selected: sourcePassage?.id === item.id }"
            @click="$emit('select', item, 'source')"
          >
            设为源版本
          </button>
          <button
            class="button button--compact"
            :class="{ selected: targetPassage?.id === item.id }"
            @click="$emit('select', item, 'target')"
          >
            设为目标版本
          </button>
        </div>
      </article>
    </div>

    <div v-else-if="searched && !searching" class="vc-empty-state">
      <p>未找到匹配的经文。</p>
      <p class="vc-empty-hint">请尝试不同的关键词。</p>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import type { PassageSearchResult } from '@/composables/useVersionComparison';

const props = defineProps<{
  query: string;
  results: PassageSearchResult[];
  searching: boolean;
  searched: boolean;
  sourcePassage: PassageSearchResult | null;
  targetPassage: PassageSearchResult | null;
}>();

const emit = defineEmits<{
  'update:query': [value: string];
  search: [];
  select: [item: PassageSearchResult, side: 'source' | 'target'];
}>();

const queryModel = computed({
  get: () => props.query,
  set: (v) => emit('update:query', v),
});

function provenanceLabel(item: PassageSearchResult): string {
  const parts = [item.metadata.repository, item.metadata.shelf_mark].filter(Boolean);
  return parts.length ? parts.join(' · ') : '来源信息待补';
}
</script>
