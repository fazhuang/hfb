<template>
  <div class="lit-detail-page">
    <div v-if="loading" class="page-state">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="page-state page-state--error">{{ error }}</div>
    <div v-else-if="doc" class="detail-content">
      <!-- Header -->
      <div class="detail-header">
        <router-link to="/literature" class="back-link">← {{ t('common.back') }}</router-link>

        <!-- P2-②: Active research topic context banner -->
        <div v-if="researchStore.hasActiveResearch" class="topic-context-banner">
          🔬 {{ t('researchEntry.currentResearch') }}: <strong>{{ researchStore.currentTopic?.name }}</strong>
        </div>

        <h1>{{ doc.title }}</h1>
        <div class="meta-row">
          <span v-if="doc.dynasty" class="meta-tag">{{ doc.dynasty }}</span>
          <span v-if="doc.category" class="meta-tag">{{ doc.category }}</span>
          <span v-if="doc.source_name" class="meta-tag">{{ doc.source_name }}</span>
        </div>
        <!-- P0-③: Ask AI about this document -->
        <div class="doc-actions">
          <button
            class="ask-ai-btn"
            @click="askAIAboutDoc"
            :title="t('literature.askAI')"
          >
            🤖 {{ t('literature.askAI') }}
          </button>
        </div>
      </div>

      <!-- Compliance panel -->
      <section class="panel compliance-panel">
        <h3>合规信息</h3>
        <div class="compliance-grid">
          <div class="field">
            <span class="field-label">版权状态</span>
            <span class="badge badge-copyright">{{ COPYRIGHT_LABELS[doc.copyright_status] || doc.copyright_status }}</span>
          </div>
          <div class="field">
            <span class="field-label">许可类型</span>
            <span>{{ doc.license_type || '—' }}</span>
          </div>
          <div class="field">
            <span class="field-label">授权依据</span>
            <span class="truncate">{{ doc.authorization_basis || '—' }}</span>
          </div>
          <div class="field">
            <span class="field-label">审核状态</span>
            <span class="badge" :class="`badge-review-${doc.review_status}`">{{ REVIEW_LABELS[doc.review_status] || doc.review_status }}</span>
          </div>
          <div class="field">
            <span class="field-label">智能检索</span>
            <span>{{ doc.rag_enabled ? '✅ 已启用' : '⛔ 未启用' }}</span>
          </div>
          <div v-if="doc.reviewed_by" class="field">
            <span class="field-label">审核人</span>
            <span>{{ doc.reviewed_by }}</span>
          </div>
          <div v-if="doc.reviewed_at" class="field">
            <span class="field-label">审核时间</span>
            <span>{{ new Date(doc.reviewed_at).toLocaleString('zh-CN') }}</span>
          </div>
        </div>
        <div v-if="doc.withdrawn_at" class="withdrawn-alert">
          ⚠️ 该文献已于 {{ new Date(doc.withdrawn_at).toLocaleString('zh-CN') }} 撤回 — {{ doc.withdraw_reason || '未提供原因' }}
        </div>
      </section>

      <!-- Content -->
      <section v-if="doc.content_text" class="panel">
        <h3>{{ t('literature.fulltext') }}</h3>
        <div class="content-text">{{ doc.content_text }}</div>
      </section>

      <!-- Metadata -->
      <section class="panel">
        <h3>{{ t('literature.metadata') }}</h3>
        <div class="meta-grid">
          <div class="field"><span class="field-label">拼音</span><span>{{ doc.title_pinyin || '—' }}</span></div>
          <div class="field"><span class="field-label">英文</span><span>{{ doc.title_english || '—' }}</span></div>
          <div class="field"><span class="field-label">年份</span><span>{{ doc.year || '—' }}</span></div>
          <div class="field"><span class="field-label">语言</span><span>{{ doc.language }}</span></div>
          <div class="field"><span class="field-label">页数</span><span>{{ doc.page_count || '—' }}</span></div>
          <div class="field">
            <span class="field-label">来源链接</span>
            <a v-if="doc.source_url" :href="doc.source_url" target="_blank" rel="noopener noreferrer" class="external-link">查看来源</a>
            <span v-else>—</span>
          </div>
          <div class="field"><span class="field-label">Checksum</span><span class="mono">{{ doc.content_checksum || '—' }}</span></div>
        </div>
      </section>

      <!-- Abstract -->
      <section v-if="doc.abstract" class="panel">
        <h3>{{ t('book.abstract') }}</h3>
        <p class="abstract-text">{{ doc.abstract }}</p>
      </section>

      <!-- Admin actions -->
      <section v-if="auth.canReviewDocuments" class="panel admin-panel">
        <h3>{{ t('literature.adminActions') }}</h3>

        <!-- Review -->
        <div v-if="!doc.withdrawn_at" class="action-group">
          <h4>{{ t('literature.review') }}</h4>
          <div class="action-row">
            <select v-model="reviewStatus" class="action-select">
              <option v-for="rs in REVIEW_STATUSES" :key="rs" :value="rs">{{ REVIEW_LABELS[rs] || rs }}</option>
            </select>
            <button class="btn btn-primary" :disabled="reviewLoading" @click="submitReview">{{ reviewLoading ? '...' : t('literature.submitReview') }}</button>
          </div>
          <p v-if="reviewMsg" class="action-msg" :class="{ 'msg-ok': reviewOk }">{{ reviewMsg }}</p>
        </div>

        <!-- 智能检索开关 -->
        <div class="action-group">
          <h4>智能检索</h4>
          <div class="action-row">
            <button v-if="!doc.rag_enabled" class="btn btn-secondary" :disabled="ragLoading" @click="toggleRag(true)">启用智能检索</button>
            <button v-else class="btn btn-secondary" :disabled="ragLoading" @click="toggleRag(false)">停用智能检索</button>
          </div>
          <p v-if="ragMsg" class="action-msg" :class="{ 'msg-ok': ragOk }">{{ ragMsg }}</p>
        </div>

        <!-- Withdraw -->
        <div v-if="!doc.withdrawn_at" class="action-group action-group--danger">
          <h4>{{ t('literature.withdraw') }}</h4>
          <div class="action-row">
            <input v-model="withdrawReason" type="text" class="action-input" :placeholder="t('literature.withdrawReasonPlaceholder')" />
            <button class="btn btn-danger" :disabled="withdrawLoading" @click="submitWithdraw">{{ withdrawLoading ? '...' : t('literature.confirmWithdraw') }}</button>
          </div>
          <p v-if="withdrawMsg" class="action-msg" :class="{ 'msg-ok': withdrawOk }">{{ withdrawMsg }}</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import { useResearchStore } from '@/stores/research';
import api from '@/api/client';

const { t } = useI18n();
const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const researchStore = useResearchStore();

interface DocumentDetail {
  id: string;
  title: string;
  title_pinyin: string | null;
  title_english: string | null;
  dynasty: string | null;
  year: number | null;
  category: string | null;
  abstract: string | null;
  content_text: string | null;
  source_url: string | null;
  page_count: number | null;
  language: string;
  copyright_status: string;
  license_type: string | null;
  authorization_basis: string | null;
  review_status: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  rag_enabled: boolean;
  content_checksum: string | null;
  source_name: string | null;
  withdrawn_at: string | null;
  withdraw_reason: string | null;
  created_at: string | null;
  updated_at: string | null;
}

const COPYRIGHT_LABELS: Record<string, string> = {
  public_domain: '公共领域', open_access: '开放获取', licensed: '已授权',
  user_uploaded_with_permission: '用户上传(已授权)', unknown: '未知',
  metadata_only: '仅元数据', forbidden_fulltext: '禁止全文', commercial_restricted: '商业限制', pirated: '盗版',
};
const REVIEW_STATUSES = ['pending_review', 'under_review', 'approved', 'rejected'];
const REVIEW_LABELS: Record<string, string> = {
  pending_review: '待审核', under_review: '审核中', approved: '已通过', rejected: '已驳回',
};

const doc = ref<DocumentDetail | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const reviewStatus = ref('pending_review');
const reviewLoading = ref(false);
const reviewMsg = ref('');
const reviewOk = ref(false);

const ragLoading = ref(false);
const ragMsg = ref('');
const ragOk = ref(false);

const withdrawReason = ref('');
const withdrawLoading = ref(false);
const withdrawMsg = ref('');
const withdrawOk = ref(false);

async function fetchDoc() {
  const id = route.params.id as string;
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get(`/api/v1/documents/${id}`);
    const d = (data.data ?? data) as DocumentDetail;
    doc.value = d;
    reviewStatus.value = d.review_status;
  } catch (e: unknown) {
    error.value = (e as Error).message ?? 'Failed to fetch';
  } finally {
    loading.value = false;
  }
}

async function submitReview() {
  if (!doc.value) return;
  reviewLoading.value = true;
  reviewMsg.value = '';
  try {
    await api.patch(`/api/v1/documents/${doc.value.id}/review`, { review_status: reviewStatus.value });
    doc.value.review_status = reviewStatus.value;
    reviewOk.value = true;
    reviewMsg.value = '审核状态已更新';
  } catch (e: unknown) {
    reviewOk.value = false;
    reviewMsg.value = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '审核失败';
  } finally {
    reviewLoading.value = false;
  }
}

async function toggleRag(enabled: boolean) {
  if (!doc.value) return;
  ragLoading.value = true;
  ragMsg.value = '';
  try {
    await api.patch(`/api/v1/documents/${doc.value.id}`, { rag_enabled: enabled });
    doc.value.rag_enabled = enabled;
    ragOk.value = true;
    ragMsg.value = enabled ? '智能检索已启用' : '智能检索已停用';
  } catch (e: unknown) {
    ragOk.value = false;
    ragMsg.value = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '操作失败';
  } finally {
    ragLoading.value = false;
  }
}

async function submitWithdraw() {
  if (!doc.value) return;
  withdrawLoading.value = true;
  withdrawMsg.value = '';
  try {
    await api.post(`/api/v1/documents/${doc.value.id}/withdraw`, { reason: withdrawReason.value });
    doc.value.withdrawn_at = new Date().toISOString();
    doc.value.withdraw_reason = withdrawReason.value;
    withdrawOk.value = true;
    withdrawMsg.value = '文献已撤回';
  } catch (e: unknown) {
    withdrawOk.value = false;
    withdrawMsg.value = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? '撤回失败';
  } finally {
    withdrawLoading.value = false;
  }
}

onMounted(fetchDoc);

// P0-③: Navigate to research workspace assistant tab with document context
async function askAIAboutDoc() {
  if (!doc.value) return;
  const title = doc.value.title;
  // Navigate to workspace with doc context as query param
  router.push({
    name: 'research-workspace',
    query: { tab: 'assistant', ask: `请分析《${title}》` },
  });
}

</script>

<style scoped>
.lit-detail-page { max-width: 900px; margin: 0 auto; padding: 32px 24px; }
.page-state { text-align: center; padding: 80px 20px; color: var(--color-text-muted, #a0aec0); font-size: 14px; }
.page-state--error { color: var(--color-error-text, #c53030); }

.detail-header { margin-bottom: 24px; }
.back-link { font-size: 13px; color: var(--color-accent, #2b6cb0); text-decoration: none; display: inline-block; margin-bottom: 8px; }

/* P2-②: Topic context banner */
.topic-context-banner {
  padding: 8px 14px;
  margin-bottom: 12px;
  background: var(--color-active, #ebf8ff);
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 8px;
  font-size: 13px;
  color: var(--color-accent, #2b6cb0);
}
.detail-header h1 { font-size: 28px; font-weight: 700; color: var(--color-text-primary, #1a365d); margin: 0 0 8px; }
.meta-row { display: flex; gap: 8px; flex-wrap: wrap; }
.meta-tag { font-size: 13px; padding: 3px 10px; background: var(--color-accent, #2b6cb0); color: white; border-radius: 4px; }
.doc-actions { margin-top: 12px; }
.ask-ai-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border: 1px solid var(--color-accent, #2b6cb0);
  border-radius: 8px;
  background: var(--color-navbar-bg, #fff);
  color: var(--color-accent, #2b6cb0);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.ask-ai-btn:hover {
  background: var(--color-accent, #2b6cb0);
  color: white;
}

.panel { margin-bottom: 24px; padding: 20px; border: 1px solid var(--color-border, #e2e8f0); border-radius: 10px; background: var(--color-navbar-bg, #fff); }
.panel h3 { font-size: 15px; font-weight: 600; color: var(--color-text-primary, #1a365d); margin: 0 0 12px; padding-bottom: 8px; border-bottom: 2px solid var(--color-accent, #2b6cb0); }

.compliance-grid, .meta-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 8px; }
.field { display: flex; align-items: baseline; gap: 8px; font-size: 14px; color: var(--color-text-secondary, #4a5568); }
.field-label { font-weight: 600; min-width: 64px; color: var(--color-text-muted, #a0aec0); font-size: 13px; white-space: nowrap; }
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 300px; }
.mono { font-family: var(--font-mono); font-size: 12px; }

.content-text { font-size: 14px; line-height: 1.9; color: var(--color-text-primary, #1a365d); white-space: pre-wrap; max-height: 600px; overflow-y: auto; }
.abstract-text { font-size: 14px; line-height: 1.8; color: var(--color-text-secondary, #4a5568); }
.external-link { color: var(--color-accent, #2b6cb0); text-decoration: underline; }

.withdrawn-alert { margin-top: 12px; padding: 10px 14px; background: #fed7d7; border-radius: 6px; font-size: 13px; color: #c53030; }

/* Admin panel */
.admin-panel { border-color: var(--color-accent, #2b6cb0); }
.action-group { margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid var(--color-border, #e2e8f0); }
.action-group:last-child { border-bottom: none; margin-bottom: 0; padding-bottom: 0; }
.action-group h4 { font-size: 14px; font-weight: 600; color: var(--color-text-primary, #1a365d); margin: 0 0 8px; }
.action-group--danger h4 { color: #c53030; }
.action-row { display: flex; gap: 8px; align-items: center; }
.action-select, .action-input { padding: 6px 10px; border: 1px solid var(--color-border, #e2e8f0); border-radius: 6px; font-size: 13px; background: var(--color-navbar-bg, #fff); color: var(--color-text-primary, #1a365d); }
.action-input { flex: 1; }
.btn { padding: 6px 16px; border: none; border-radius: 6px; font-size: 13px; cursor: pointer; }
.btn-primary { background: var(--color-accent, #2b6cb0); color: white; }
.btn-secondary { background: var(--color-tag-bg, #edf2f7); color: var(--color-text-primary, #1a365d); }
.btn-danger { background: #c53030; color: white; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.action-msg { font-size: 13px; margin: 6px 0 0; }
.msg-ok { color: #276749; }
</style>

<style>
/* Badge styles (unscoped for inline render) */
.badge { font-size: 12px; padding: 2px 8px; border-radius: 4px; }
.badge-copyright { background: var(--color-tag-bg, #edf2f7); color: var(--color-text-secondary, #4a5568); }
.badge-review-pending_review { background: #fefcbf; color: #975a16; }
.badge-review-under_review { background: #bee3f8; color: #2a4365; }
.badge-review-approved { background: #c6f6d5; color: #276749; }
.badge-review-rejected { background: #fed7d7; color: #c53030; }
</style>
