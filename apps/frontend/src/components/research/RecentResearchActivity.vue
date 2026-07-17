<template>
  <section class="rra-section" aria-labelledby="rra-heading">
    <h2 id="rra-heading" class="rra-heading">最近活动</h2>

    <!-- Loading -->
    <LoadingState v-if="loading" message="正在加载最近活动..." />

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

    <!-- Activity list — max 5 items -->
    <ul v-else class="rra-list" role="list">
      <li v-for="item in activities" :key="item.query_id" class="rra-item">
        <div class="rra-item-main">
          <span class="rra-type-badge">{{ typeLabel(item.query_type) }}</span>
          <span class="rra-text">{{ item.query_text }}</span>
        </div>
        <div class="rra-item-meta">
          <span v-if="item.citation_count > 0" class="rra-stat">
            {{ item.citation_count }} 条引用
          </span>
          <time :datetime="item.created_at ?? undefined" class="rra-time">
            {{ formatDate(item.created_at) }}
          </time>
        </div>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
/**
 * RecentResearchActivity — 最近研究活动列表
 *
 * Data source: GET /api/v4/research/session/{projectId}/history?limit=5
 * Backend supports `limit` query parameter — we request exactly 5.
 * Sorted by created_at DESC on the server.
 *
 * ref: docs/20-product/2013-research-workspace-migration.md
 */
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

const MAX_ITEMS = 5;

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
    // Backend supports ?limit= — use exactly MAX_ITEMS
    const { data } = await api.get(
      `/api/v4/research/session/${props.projectId}/history`,
      { params: { limit: MAX_ITEMS } },
    );
    if (myReqId !== reqId) return;
    const body = data.data ?? data;
    // Backend respects ?limit= but we client-side truncate as safety net
    activities.value = ((body.history ?? []) as ActivityItem[]).slice(0, MAX_ITEMS);
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
.rra-section {
  margin-bottom: 28px;
}

.rra-heading {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.rra-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rra-item {
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

.rra-item-main {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  flex: 1;
  min-width: 0;
}

.rra-type-badge {
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

.rra-text {
  font-size: 13px;
  color: var(--color-text-primary, #1a365d);
  line-height: 1.5;
  word-break: break-word;
}

.rra-item-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.rra-stat {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.rra-time {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  white-space: nowrap;
}
</style>
