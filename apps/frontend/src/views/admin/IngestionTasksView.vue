<template>
  <div class="ingestion-page">
    <div class="page-header">
      <h1>采集任务记录</h1>
    </div>

    <div class="filter-bar">
      <select v-model="actionFilter" class="filter-select" @change="fetchPage(1)">
        <option value="">— 操作类型 —</option>
        <option v-for="a in ACTIONS" :key="a" :value="a">{{ ACTION_LABELS[a] || a }}</option>
      </select>
      <select v-model="statusFilter" class="filter-select" @change="fetchPage(1)">
        <option value="">— 状态 —</option>
        <option v-for="s in STATUSES" :key="s" :value="s">{{ STATUS_LABELS[s] || s }}</option>
      </select>
      <select v-model="sourceFilter" class="filter-select" @change="fetchPage(1)">
        <option value="">— 来源 —</option>
        <option v-for="sn in SOURCES" :key="sn" :value="sn">{{ sn }}</option>
      </select>
    </div>

    <DataTable
      :columns="columns"
      :rows="items as unknown as Record<string, unknown>[]"
      :loading="loading"
      :error="error"
    />

    <div v-if="total > limit" class="pagination">
      <button :disabled="page <= 1" @click="fetchPage(page - 1)">{{ t('common.back') }}</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="fetchPage(page + 1)">{{ t('common.next') }}</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/api/client';
import DataTable, { type TableColumn } from '@/components/common/DataTable.vue';

const { t } = useI18n();

interface AuditRecord {
  id: string;
  created_at: string | null;
  action: string;
  status: string;
  source_url: string | null;
  source_name: string | null;
  copyright_status: string | null;
  license_type: string | null;
  review_status: string | null;
  result_entity_type: string | null;
  result_entity_id: string | null;
  reject_reason: string | null;
  skipped_reason: string | null;
  actor_id: string | null;
  details: Record<string, unknown> | null;
}

const ACTIONS = ['fulltext_ingest', 'reject', 'skip', 'withdraw', 'chunk_delete', 'rag_disabled'];
const ACTION_LABELS: Record<string, string> = {
  fulltext_ingest: '全文摄入', reject: '拒绝', skip: '跳过', withdraw: '撤回', chunk_delete: '删除已处理片段', rag_disabled: '停用智能检索',
};
const STATUSES = ['success', 'skipped', 'rejected', 'withdrawn'];
const STATUS_LABELS: Record<string, string> = { success: '成功', skipped: '已跳过', rejected: '已拒绝', withdrawn: '已撤回' };
const SOURCES = ['openalex', 'crossref', 'core', 'pubmed', 'internet_archive', 'user_upload'];

const items = ref<AuditRecord[]>([]);
const total = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const page = ref(1);
const limit = ref(20);
const actionFilter = ref('');
const statusFilter = ref('');
const sourceFilter = ref('');

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)));

const columns: TableColumn[] = [
  { key: 'created_at', label: '时间', width: '150px', render: (r) => r.created_at ? new Date(r.created_at as string).toLocaleString('zh-CN') : '—' },
  { key: 'action', label: '操作', width: '100px', render: (r) => String(ACTION_LABELS[r.action as string] || r.action) },
  { key: 'status', label: '状态', width: '80px', render: (r) => `<span class="badge badge-status-${r.status}">${STATUS_LABELS[r.status as string] || r.status}</span>` },
  { key: 'source_name', label: '来源', width: '90px' },
  { key: 'copyright_status', label: '版权', width: '80px' },
  { key: 'result_entity_type', label: '结果类型', width: '80px' },
  { key: 'details', label: '详情', width: '200px', render: (r) => {
    const d = r.details as Record<string, unknown> | null | undefined;
    return String(d?.title || r.reject_reason || r.skipped_reason || '—');
  }},
  { key: 'actor_id', label: '操作人', width: '100px', render: (r) => r.actor_id ? String(r.actor_id).slice(0, 8) : '—' },
];

async function fetchPage(p: number) {
  page.value = p;
  loading.value = true;
  error.value = null;
  try {
    const params: Record<string, unknown> = { page: p, limit: limit.value };
    if (actionFilter.value) params.action = actionFilter.value;
    if (statusFilter.value) params.status = statusFilter.value;
    if (sourceFilter.value) params.source_name = sourceFilter.value;

    const { data } = await api.get('/api/v1/ingestion/tasks', { params });
    const body = data.data ?? data;
    items.value = body.items ?? [];
    total.value = body.total ?? 0;
  } catch (e: unknown) {
    error.value = (e as Error).message ?? 'Failed to fetch';
  } finally {
    loading.value = false;
  }
}

onMounted(() => fetchPage(1));
</script>

<style scoped>
.ingestion-page { max-width: 1200px; margin: 0 auto; padding: var(--space-8) 24px; }
.page-header { margin-bottom: 16px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--color-text-primary); margin: 0; }

.filter-bar { display: flex; gap: var(--space-2); margin-bottom: 16px; }
.filter-select { padding: var(--space-2) 12px; border: 1px solid var(--color-border); border-radius: var(--radius-lg); font-size: 13px; background: var(--color-navbar-bg, var(--color-surface)); color: var(--color-text-primary); }

.pagination { display: flex; align-items: center; justify-content: center; gap: var(--space-4); margin-top: 24px; font-size: 13px; color: var(--color-text-secondary); }
.pagination button { padding: var(--space-1-5) 16px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-navbar-bg, var(--color-surface)); cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
</style>

<style>
.badge { font-size: 12px; padding: var(--space-0-5) 8px; border-radius: var(--radius-sm); }
.badge-status-success { background: var(--color-success-icon-bg); color: var(--color-success-text); }
.badge-status-skipped { background: var(--color-hover); color: var(--color-text-muted); }
.badge-status-rejected { background: var(--color-error-icon-bg); color: var(--color-error-text); }
.badge-status-withdrawn { background: var(--color-border); color: var(--color-text-muted); }
</style>
