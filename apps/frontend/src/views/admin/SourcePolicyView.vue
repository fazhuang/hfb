<template>
  <div class="sp-page">
    <div class="page-header">
      <h1>来源白名单管理</h1>
    </div>

    <div v-if="msg" class="action-msg" :class="{ 'msg-ok': msgOk }">{{ msg }}</div>

    <!-- Add new -->
    <div class="add-form">
      <input v-model="newName" type="text" class="add-input" placeholder="来源标识 (如 openalex)" @keyup.enter="addSource" />
      <label class="add-check">
        <input v-model="newEnabled" type="checkbox" /> 启用
      </label>
      <button class="btn btn-primary" :disabled="addLoading" @click="addSource">{{ addLoading ? '...' : '添加' }}</button>
    </div>

    <DataTable
      :columns="columns"
      :rows="items as unknown as Record<string, unknown>[]"
      :loading="loading"
      :error="error"
    />

    <p v-if="!loading && !error && items.length === 0" class="empty-state">暂无来源策略。请添加来源。</p>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import api from '@/api/client';
import DataTable, { type TableColumn } from '@/components/common/DataTable.vue';

interface SourcePolicy {
  id: string;
  source_name: string;
  enabled: boolean;
  created_at: string;
  updated_at: string;
}

const items = ref<SourcePolicy[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const msg = ref('');
const msgOk = ref(false);

const newName = ref('');
const newEnabled = ref(true);
const addLoading = ref(false);

const columns: TableColumn[] = [
  { key: 'source_name', label: '来源标识', width: '200px' },
  { key: 'enabled', label: '启用', width: '80px', render: (r) => r.enabled ? '✅ 已启用' : '⛔ 已禁用' },
  { key: 'created_at', label: '创建时间', width: '150px', render: (r) => new Date(r.created_at as string).toLocaleDateString('zh-CN') },
  { key: 'updated_at', label: '更新时间', width: '150px', render: (r) => new Date(r.updated_at as string).toLocaleDateString('zh-CN') },
  {
    key: 'actions', label: '操作', width: '120px',
    render: (r) => {
      const enabled = r.enabled as boolean;
      const id = r.id as string;
      // ponytail: inline action buttons via render — no slot complexity needed
      return `<button class="sp-toggle-btn" data-id="${id}" data-action="toggle">${enabled ? '禁用' : '启用'}</button>
              <button class="sp-delete-btn" data-id="${id}" data-action="delete">删除</button>`;
    },
  },
];

async function fetchPolicies() {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get('/api/v1/admin/source-policies');
    const body = data.data ?? data;
    items.value = body.items ?? [];
  } catch (e: unknown) {
    error.value = (e as Error).message ?? 'Failed to fetch';
  } finally {
    loading.value = false;
  }
}

async function addSource() {
  if (!newName.value.trim()) return;
  addLoading.value = true;
  msg.value = '';
  try {
    await api.post('/api/v1/admin/source-policies', { source_name: newName.value.trim(), enabled: newEnabled.value });
    newName.value = '';
    newEnabled.value = true;
    msgOk.value = true;
    msg.value = '来源已添加';
    await fetchPolicies();
  } catch (e: unknown) {
    msgOk.value = false;
    msg.value = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '添加失败';
  } finally {
    addLoading.value = false;
  }
}

async function toggleSource(id: string) {
  const sp = items.value.find((i) => i.id === id);
  if (!sp) return;
  try {
    await api.patch(`/api/v1/admin/source-policies/${id}`, { enabled: !sp.enabled });
    sp.enabled = !sp.enabled;
  } catch {
    // ignore
  }
}

async function deleteSource(id: string) {
  try {
    await api.delete(`/api/v1/admin/source-policies/${id}`);
    items.value = items.value.filter((i) => i.id !== id);
  } catch {
    // ignore
  }
}

// Event delegation for inline buttons
function handleTableClick(e: Event) {
  const target = e.target as HTMLElement;
  const id = target.getAttribute('data-id');
  const action = target.getAttribute('data-action');
  if (!id || !action) return;
  if (action === 'toggle') void toggleSource(id);
  if (action === 'delete') void deleteSource(id);
}

onMounted(async () => {
  await fetchPolicies();
  // ponytail: event delegation on the table wrapper
  document.querySelector('.data-table-wrapper')?.addEventListener('click', handleTableClick);
});
</script>

<style scoped>
.sp-page { max-width: 900px; margin: 0 auto; padding: 32px 24px; }
.page-header { margin-bottom: 16px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--color-text-primary, #1a365d); margin: 0; }

.add-form { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; }
.add-input { padding: 8px 12px; border: 1px solid var(--color-border, #e2e8f0); border-radius: 8px; font-size: 14px; min-width: 200px; background: var(--color-page-bg, #f7fafc); color: var(--color-text-primary, #1a365d); }
.add-check { font-size: 13px; color: var(--color-text-secondary, #4a5568); display: flex; align-items: center; gap: 4px; }
.btn { padding: 6px 16px; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
.btn-primary { background: var(--color-accent, #2b6cb0); color: white; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

.action-msg { font-size: 13px; margin-bottom: 12px; padding: 8px 12px; border-radius: 6px; }
.msg-ok { background: #c6f6d5; color: #276749; }
.action-msg:not(.msg-ok) { background: #fed7d7; color: #c53030; }

.empty-state { text-align: center; padding: 40px 16px; color: var(--color-text-muted, #a0aec0); font-size: 14px; }
</style>

<style>
/* Inline button styles (unscoped for render HTML) */
.sp-toggle-btn { font-size: 12px; padding: 2px 8px; margin-right: 4px; border: 1px solid var(--color-border, #e2e8f0); border-radius: 4px; background: var(--color-navbar-bg, #fff); color: var(--color-text-primary, #1a365d); cursor: pointer; }
.sp-delete-btn { font-size: 12px; padding: 2px 8px; border: 1px solid #c53030; border-radius: 4px; background: #fff; color: #c53030; cursor: pointer; }
</style>
