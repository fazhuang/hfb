<template>
  <section class="pn-section" aria-labelledby="pn-heading">
    <h2 id="pn-heading" class="pn-heading">笔记</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载笔记..." />

    <!-- Error -->
    <ErrorState
      v-else-if="error"
      :message="error"
      title="笔记加载失败"
      @retry="fetchNotes"
    />

    <!-- Empty -->
    <EmptyState
      v-else-if="notes.length === 0"
      title="暂无笔记"
      description="在此课题中创建的研究笔记将显示在这里。"
      icon="📝"
    />

    <!-- Notes list -->
    <ul v-else class="pn-list" role="list">
      <li v-for="note in notes" :key="note.id" class="pn-item">
        <div class="pn-item-main">
          <p class="pn-content">{{ note.content }}</p>
          <div v-if="note.tags" class="pn-tags">
            <span class="pn-tag">{{ note.tags }}</span>
          </div>
        </div>
        <time :datetime="note.created_at ?? undefined" class="pn-time">
          {{ formatDate(note.created_at) }}
        </time>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
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
    const { data } = await api.get(
      `/api/v1/workspace/sessions/${props.projectId}/notes`,
    );
    if (myReqId !== reqId) return;
    const body = data.data ?? data;
    notes.value = (Array.isArray(body) ? body : []) as NoteItem[];
  } catch (e: unknown) {
    if (myReqId !== reqId) return;
    const msg =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '加载笔记失败';
    error.value = msg;
  } finally {
    if (myReqId === reqId) {
      loading.value = false;
    }
  }
}

onMounted(() => {
  fetchNotes();
});

onBeforeUnmount(() => {
  reqId = -1;
});
</script>

<style scoped>
.pn-section {
  margin-bottom: 28px;
}

.pn-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.pn-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.pn-item {
  padding: 12px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
}

.pn-item-main {
  flex: 1;
  min-width: 0;
}

.pn-content {
  font-size: 14px;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 6px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}

.pn-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.pn-tag {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 4px;
  background: var(--color-hover, #edf2f7);
  color: var(--color-text-muted, #718096);
}

.pn-time {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 2px;
}
</style>
