<template>
  <div class="cv-list-page">
    <div class="page-header">
      <h1>古籍版本库</h1>
    </div>

    <div class="filter-bar">
      <div class="search-box">
        <input v-model="query" type="text" placeholder="搜索著作名称、版本、馆藏..." @keyup.enter="fetchPage(1)" />
        <button class="search-btn" @click="fetchPage(1)">{{ t('common.search') }}</button>
      </div>
      <select v-model="reviewFilter" class="filter-select" @change="fetchPage(1)">
        <option value="">— 审核状态 —</option>
        <option v-for="rs in REVIEW_STATUSES" :key="rs" :value="rs">{{ REVIEW_LABELS[rs] || rs }}</option>
      </select>
      <select v-model="domainFilter" class="filter-select" @change="fetchPage(1)">
        <option value="">— 公共领域状态 —</option>
        <option v-for="ds in DOMAIN_STATUSES" :key="ds" :value="ds">{{ DOMAIN_LABELS[ds] || ds }}</option>
      </select>
    </div>

    <DataTable
      :columns="columns"
      :rows="(items as unknown as Record<string, unknown>[])"
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

interface ClassicalVersionBrief {
  id: string;
  work_title: string;
  version_name: string;
  dynasty: string | null;
  edition_type: string | null;
  repository: string | null;
  public_domain_status: string;
  review_status: string;
  created_at: string | null;
}

const REVIEW_STATUSES = ['pending_review', 'under_review', 'approved', 'rejected'];
const REVIEW_LABELS: Record<string, string> = {
  pending_review: '待审核', under_review: '审核中', approved: '已通过', rejected: '已驳回',
};
const DOMAIN_STATUSES = ['confirmed_public_domain', 'copyright_claimed', 'unknown', 'not_applicable'];
const DOMAIN_LABELS: Record<string, string> = {
  confirmed_public_domain: '确认为公版', copyright_claimed: '版权主张', unknown: '未知', not_applicable: '不适用',
};

const items = ref<ClassicalVersionBrief[]>([]);
const total = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const page = ref(1);
const limit = ref(20);
const query = ref('');
const reviewFilter = ref('');
const domainFilter = ref('');

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)));

const columns: TableColumn[] = [
  { key: 'work_title', label: '著作名称', width: '200px' },
  { key: 'version_name', label: '版本名称', width: '180px' },
  { key: 'dynasty', label: '朝代', width: '80px' },
  { key: 'edition_type', label: '版本类型', width: '90px' },
  { key: 'repository', label: '馆藏机构', width: '160px' },
  { key: 'public_domain_status', label: '公版状态', width: '110px', render: (r) => `<span class="badge">${DOMAIN_LABELS[r.public_domain_status as string] || r.public_domain_status}</span>` },
  { key: 'review_status', label: '审核', width: '90px', render: (r) => `<span class="badge badge-review-${r.review_status}">${REVIEW_LABELS[r.review_status as string] || r.review_status}</span>` },
  { key: 'created_at', label: '创建时间', width: '140px', render: (r) => r.created_at ? new Date(r.created_at as string).toLocaleDateString('zh-CN') : '—' },
];

async function fetchPage(p: number) {
  page.value = p;
  loading.value = true;
  error.value = null;
  try {
    const params: Record<string, unknown> = { page: p, limit: limit.value };
    if (query.value.trim()) params.q = query.value.trim();
    if (reviewFilter.value) params.review_status = reviewFilter.value;
    if (domainFilter.value) params.public_domain_status = domainFilter.value;

    const { data } = await api.get('/api/classical-versions', { params });
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
.cv-list-page { max-width: 1200px; margin: 0 auto; padding: 32px 24px; }
.page-header { margin-bottom: 16px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--color-text-primary, #1a365d); margin: 0; }

.filter-bar { display: flex; gap: 8px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
.search-box { display: flex; gap: 8px; }
.search-box input { padding: 8px 12px; border: 1px solid var(--color-border, #e2e8f0); border-radius: 8px; font-size: 14px; min-width: 200px; background: var(--color-page-bg, #f7fafc); color: var(--color-text-primary, #1a365d); }
.search-btn { padding: 8px 16px; background: var(--color-accent, #2b6cb0); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 13px; }
.filter-select { padding: 8px 12px; border: 1px solid var(--color-border, #e2e8f0); border-radius: 8px; font-size: 13px; background: var(--color-navbar-bg, #fff); color: var(--color-text-primary, #1a365d); }

.pagination { display: flex; align-items: center; justify-content: center; gap: 16px; margin-top: 24px; font-size: 13px; color: var(--color-text-secondary, #4a5568); }
.pagination button { padding: 6px 16px; border: 1px solid var(--color-border, #e2e8f0); border-radius: 6px; background: var(--color-navbar-bg, #fff); cursor: pointer; font-size: 13px; }
.pagination button:disabled { opacity: 0.4; cursor: not-allowed; }
</style>

<style>
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; background: var(--color-tag-bg, #edf2f7); color: var(--color-text-secondary, #4a5568); }
.badge-review-pending_review { background: #fefcbf; color: #975a16; }
.badge-review-under_review { background: #bee3f8; color: #2a4365; }
.badge-review-approved { background: #c6f6d5; color: #276749; }
.badge-review-rejected { background: #fed7d7; color: #c53030; }
</style>
