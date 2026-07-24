<template>
  <div class="review-page">
    <div class="page-header">
      <h1>全文审核队列</h1>
    </div>

    <div class="filter-bar">
      <select v-model="reviewFilter" class="filter-select" @change="fetchPage(1)">
        <option value="">— 审核状态 —</option>
        <option v-for="rs in REVIEW_STATUSES" :key="rs" :value="rs">{{ REVIEW_LABELS[rs] || rs }}</option>
      </select>
      <select v-model="copyrightFilter" class="filter-select" @change="fetchPage(1)">
        <option value="">— 版权状态 —</option>
        <option v-for="cs in COPYRIGHT_STATUSES" :key="cs" :value="cs">{{ COPYRIGHT_LABELS[cs] || cs }}</option>
      </select>
    </div>

    <DataTable
      :columns="columns"
      :rows="(items as unknown as Record<string, unknown>[])"
      :loading="loading"
      :error="error"
      :clickable="true"
      :row-key="(r: Record<string, unknown>) => r.id as string"
      @row-click="(r: Record<string, unknown>) => router.push(`/literature/${r.id}`)"
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
import { useRouter } from 'vue-router';
import api from '@/api/client';
import DataTable, { type TableColumn } from '@/components/common/DataTable.vue';

const { t } = useI18n();
const router = useRouter();

interface DocumentBrief {
  id: string;
  title: string;
  dynasty: string | null;
  category: string | null;
  copyright_status: string;
  review_status: string;
  rag_enabled: boolean;
  source_name: string | null;
  withdrawn_at: string | null;
  created_at: string | null;
}

const REVIEW_STATUSES = ['pending_review', 'under_review', 'approved', 'rejected'];
const REVIEW_LABELS: Record<string, string> = {
  pending_review: '待审核', under_review: '审核中', approved: '已通过', rejected: '已驳回',
};
const COPYRIGHT_STATUSES = ['public_domain', 'open_access', 'licensed', 'user_uploaded_with_permission', 'unknown', 'metadata_only', 'forbidden_fulltext', 'commercial_restricted', 'pirated'];
const COPYRIGHT_LABELS: Record<string, string> = {
  public_domain: '公共领域', open_access: '开放获取', licensed: '已授权',
  user_uploaded_with_permission: '用户上传(已授权)', unknown: '未知',
  metadata_only: '仅元数据', forbidden_fulltext: '禁止全文', commercial_restricted: '商业限制', pirated: '盗版',
};

const items = ref<DocumentBrief[]>([]);
const total = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const page = ref(1);
const limit = ref(20);
const reviewFilter = ref('pending_review');
const copyrightFilter = ref('');

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)));

const columns: TableColumn[] = [
  { key: 'title', label: '标题', width: '280px' },
  { key: 'source_name', label: '来源', width: '90px' },
  { key: 'copyright_status', label: '版权', width: '100px', render: (r) => `<span class="badge">${COPYRIGHT_LABELS[r.copyright_status as string] || r.copyright_status}</span>` },
  { key: 'review_status', label: '审核', width: '90px', render: (r) => `<span class="badge badge-review-${r.review_status}">${REVIEW_LABELS[r.review_status as string] || r.review_status}</span>` },
  { key: 'rag_enabled', label: '智能检索', width: '60px', render: (r) => r.rag_enabled ? '✅' : '—' },
  { key: 'withdrawn_at', label: '状态', width: '80px', render: (r) => r.withdrawn_at ? '<span class="badge badge-withdrawn">已撤回</span>' : '' },
  { key: 'created_at', label: '提交时间', width: '140px', render: (r) => r.created_at ? new Date(r.created_at as string).toLocaleDateString('zh-CN') : '—' },
];

async function fetchPage(p: number) {
  page.value = p;
  loading.value = true;
  error.value = null;
  try {
    const params: Record<string, unknown> = { page: p, limit: limit.value };
    if (reviewFilter.value) params.review_status = reviewFilter.value;
    if (copyrightFilter.value) params.copyright_status = copyrightFilter.value;

    const { data } = await api.get('/api/v1/documents', { params });
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
.review-page { max-width: 1200px; margin: 0 auto; padding: var(--space-8) 24px; }
.page-header { margin-bottom: 16px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--color-text-primary); margin: 0; }

.filter-bar { display: flex; gap: var(--space-2); margin-bottom: 16px; }
.filter-select { padding: var(--space-2) 12px; border: 1px solid var(--color-border); border-radius: var(--radius-lg); font-size: 13px; background: var(--color-navbar-bg, var(--color-surface)); color: var(--color-text-primary); }

.pagination { display: flex; align-items: center; justify-content: center; gap: var(--space-4); margin-top: 24px; font-size: 13px; color: var(--color-text-secondary); }
.pagination button { padding: var(--space-1-5) 16px; border: 1px solid var(--color-border); border-radius: var(--radius-md); background: var(--color-navbar-bg, var(--color-surface)); cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
</style>

<style>
.badge { font-size: 12px; padding: var(--space-0-5) 8px; border-radius: var(--radius-sm); background: var(--color-hover); color: var(--color-text-secondary); }
.badge-review-pending_review { background: var(--color-warning-bg); color: var(--color-warning-text); }
.badge-review-under_review { background: var(--color-info-text); color: var(--color-accent-light); }
.badge-review-approved { background: var(--color-success-icon-bg); color: var(--color-success-text); }
.badge-review-rejected { background: var(--color-error-icon-bg); color: var(--color-error-text); }
.badge-withdrawn { background: var(--color-border); color: var(--color-text-muted); }
</style>
