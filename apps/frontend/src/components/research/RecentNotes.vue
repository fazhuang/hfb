<template>
  <section class="rn-section" aria-labelledby="rn-heading">
    <h2 id="rn-heading" class="rn-heading">最近笔记</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载笔记..." />

    <!-- Error -->
    <ErrorState v-else-if="error" :message="error" title="笔记加载失败" @retry="fetchNotes" />

    <!-- Empty -->
    <EmptyState
      v-else-if="notes.length === 0"
      title="暂无笔记"
      description="在此课题中创建的研究笔记将显示在这里。"
      icon="📝"
    />

    <!-- Notes list — max 5 items -->
    <ul v-else class="rn-list" role="list">
      <li v-for="note in notes" :key="note.id" class="rn-item">
        <div class="rn-item-main">
          <p class="rn-content">{{ note.content }}</p>
          <div v-if="note.tags" class="rn-tags">
            <span class="rn-tag">{{ note.tags }}</span>
          </div>
        </div>
        <time :datetime="note.created_at ?? undefined" class="rn-time">
          {{ formatDate(note.created_at) }}
        </time>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
/**
 * RecentNotes — 最近笔记列表
 *
 * Data source: GET /api/v1/workspace/sessions/{projectId}/notes
 * Backend has a hard-coded limit of 50 and sorts by created_at DESC.
 * We request the full list and take the first 5.
 *
 * ref: docs/20-product/2013-research-workspace-migration.md
 */
import { ref, watch, onBeforeUnmount } from 'vue';
import api from '@/api/client';
import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

const props = defineProps<{
  projectId: string;
}>();

interface NoteItem {
  id: string;
  session_id: string;
  entity_type?: string | null;
  entity_id?: string | null;
  content: string;
  tags?: string | null;
  created_at: string | null;
  updated_at: string | null;
}

const notes = ref<NoteItem[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

const MAX_ITEMS = 5;

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

let reqId = 0;

async function fetchNotes() {
  const myReqId = ++reqId;
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get(`/api/v1/workspace/sessions/${props.projectId}/notes`);
    if (myReqId !== reqId) return;
    const body = data.data ?? data;
    const all = (Array.isArray(body) ? body : []) as NoteItem[];

    // Backend sorts by created_at DESC, hard limit 50.
    // Take first MAX_ITEMS — no need to re-sort.
    notes.value = all.slice(0, MAX_ITEMS);
  } catch (e: unknown) {
    if (myReqId !== reqId) return;
    const msg = (e as any)?.response?.data?.message || (e as any)?.message || '加载笔记失败';
    error.value = msg;
  } finally {
    if (myReqId === reqId) {
      loading.value = false;
    }
  }
}

// Watch projectId to reload on route change. Clear stale data immediately.
watch(
  () => props.projectId,
  (newId, oldId) => {
    if (newId !== oldId) {
      notes.value = [];
      error.value = null;
      loading.value = true;
      // Bump reqId so in-flight request for old projectId is discarded
      reqId++;
    }
    fetchNotes();
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  // Invalidate all pending requests
  reqId += 1000000;
});
</script>

<style scoped>
.rn-section {
  margin-bottom: var(--space-7);
}

.rn-heading {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
  padding-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-border);
}

.rn-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.rn-item {
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--space-3);
}

.rn-item-main {
  flex: 1;
  min-width: 0;
}

.rn-content {
  font-size: var(--text-base);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1-5);
  line-height: var(--leading-normal);
  white-space: pre-wrap;
  word-break: break-word;
}

.rn-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.rn-tag {
  font-size: 11px;
  padding: var(--space-0-25) 8px;
  border-radius: var(--radius-sm);
  background: var(--color-hover);
  color: var(--color-text-muted);
}

.rn-time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 2px;
}
</style>
