<template>
  <section class="ral-section" aria-labelledby="ral-heading">
    <h2 id="ral-heading" class="ral-heading">研究活动</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载研究活动..." />

    <!-- Error -->
    <ErrorState
      v-else-if="error"
      :message="error"
      title="活动加载失败"
      @retry="fetchActivities"
    />

    <!-- Empty -->
    <EmptyState
      v-else-if="activities.length === 0"
      title="暂无研究活动"
      description="在此课题中执行研究查询后，活动记录将显示在这里。"
      icon="📋"
    />

    <!-- Activity list -->
    <ul v-else class="ral-list" role="list">
      <li v-for="item in activities" :key="item.query_id" class="ral-item">
        <div class="ral-item-main">
          <span class="ral-type-badge">{{ typeLabel(item.query_type) }}</span>
          <span class="ral-text">{{ item.query_text }}</span>
        </div>
        <div class="ral-item-meta">
          <span v-if="item.citation_count > 0" class="ral-stat">
            {{ item.citation_count }} 条引用
          </span>
          <time :datetime="item.created_at ?? undefined" class="ral-time">
            {{ formatDate(item.created_at) }}
          </time>
        </div>
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

interface ActivityItem {
  query_id: string;
  query_text: string;
  query_type: string;
  citation_count: number;
  trace_count: number;
  created_at: string | null;
}

const activities = ref<ActivityItem[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);

const TYPE_LABELS: Record<string, string> = {
  research: '研究',
  report: '报告',
  synthesis: '综合',
  education: '教育',
  graph: '图谱',
  search: '搜索',
  workflow_step: '工作流',
};

function typeLabel(t: string): string {
  return TYPE_LABELS[t] || t;
}

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

async function fetchActivities() {
  const myReqId = ++reqId;
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get(
      `/api/v4/research/session/${props.projectId}/history`,
      { params: { limit: 50 } },
    );
    if (myReqId !== reqId) return;
    const body = data.data ?? data;
    activities.value = (body.history ?? []) as ActivityItem[];
  } catch (e: unknown) {
    if (myReqId !== reqId) return;
    const msg =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '加载活动失败';
    error.value = msg;
  } finally {
    if (myReqId === reqId) {
      loading.value = false;
    }
  }
}

onMounted(() => {
  fetchActivities();
});

onBeforeUnmount(() => {
  reqId = -1;
});
</script>

<style scoped>
.ral-section {
  margin-bottom: 28px;
}

.ral-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.ral-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ral-item {
  padding: 12px 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  flex-wrap: wrap;
}

.ral-item-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.ral-type-badge {
  display: inline-block;
  padding: 1px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: var(--color-hover, #edf2f7);
  color: var(--color-text-secondary, #4a5568);
  white-space: nowrap;
  flex-shrink: 0;
  margin-top: 1px;
}

.ral-text {
  font-size: 13px;
  color: var(--color-text-primary, #1a365d);
  line-height: 1.5;
  word-break: break-word;
}

.ral-item-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.ral-stat {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.ral-time {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  white-space: nowrap;
}
</style>
