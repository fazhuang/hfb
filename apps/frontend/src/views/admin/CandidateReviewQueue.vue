<template>
  <div class="crq">
    <div class="crq-header">
      <h1 class="crq-title">候选审核队列</h1>
      <p class="crq-subtitle">
        人工确认 AI/规则抽取的候选证据；通过后原子发布为 Evidence + Citation，驳回则标记拒绝。
      </p>
    </div>

    <!-- 过滤 -->
    <div class="crq-filters">
      <select v-model="statusFilter" class="crq-select" @change="fetchPage(1)">
        <option value="pending">待审核</option>
        <option value="approved">已通过</option>
        <option value="rejected">已驳回</option>
        <option value="drift_invalid">已失效(漂移)</option>
      </select>
      <label class="crq-mine">
        <input v-model="mineOnly" type="checkbox" @change="fetchPage(1)" />
        只看我的候选
      </label>
    </div>

    <!-- 加载态 -->
    <div v-if="loading" class="crq-loading" aria-busy="true">正在加载候选队列…</div>

    <!-- 错误态 -->
    <div v-else-if="error" class="crq-error" role="alert">{{ error }}</div>

    <!-- 空态 -->
    <div v-else-if="items.length === 0" class="crq-empty">当前没有符合条件的候选。</div>

    <!-- 候选卡片 -->
    <div v-else class="crq-list">
      <article v-for="c in items" :key="c.id" class="crq-card">
        <header class="crq-card__header">
          <span class="crq-card__id" :title="c.id">#{{ c.id.slice(0, 8) }}</span>
          <span class="crq-badge" :class="`crq-badge--${c.status}`">
            {{ STATUS_LABELS[c.status] || c.status }}
          </span>
          <span class="crq-card__meta">
            {{ c.ai_model }} · 置信 {{ (c.confidence * 100).toFixed(0) }}%
          </span>
        </header>

        <!-- 原文摘录 -->
        <blockquote class="crq-exact">{{ c.exact_text }}</blockquote>

        <!-- 提取载荷 -->
        <dl class="crq-payload">
          <div class="crq-payload__row">
            <dt>证据描述</dt>
            <dd>{{ payloadOf(c).description || '—' }}</dd>
          </div>
          <div class="crq-payload__row">
            <dt>证据等级</dt>
            <dd>{{ levelLabel(payloadOf(c).evidence_level) }}</dd>
          </div>
          <div v-if="payloadOf(c).note" class="crq-payload__row">
            <dt>备注</dt>
            <dd>{{ payloadOf(c).note }}</dd>
          </div>
        </dl>

        <footer class="crq-card__footer">
          <span class="crq-card__time">
            提交于 {{ formatTime(c.created_at) }}
          </span>

          <!-- 待审核操作 -->
          <div v-if="c.status === 'pending'" class="crq-actions">
            <button
              type="button"
              class="crq-btn crq-btn--ghost"
              :disabled="busyId === c.id"
              @click="toggleReject(c)"
            >
              驳回
            </button>
            <button
              type="button"
              class="crq-btn crq-btn--primary"
              :disabled="busyId === c.id"
              @click="approve(c)"
            >
              {{ busyId === c.id ? '处理中…' : '通过并发布' }}
            </button>
          </div>
        </footer>

        <!-- 驳回理由输入 -->
        <div v-if="rejectingId === c.id" class="crq-reject">
          <label :for="`crq-reason-${c.id}`" class="crq-reject__label">驳回理由</label>
          <textarea
            :id="`crq-reason-${c.id}`"
            v-model.trim="rejectReason"
            class="crq-reject__input"
            rows="2"
            maxlength="2000"
            placeholder="说明驳回原因（必填）"
          ></textarea>
          <div class="crq-reject__actions">
            <button
              type="button"
              class="crq-btn crq-btn--ghost"
              :disabled="busyId === c.id"
              @click="rejectingId = null"
            >
              取消
            </button>
            <button
              type="button"
              class="crq-btn crq-btn--danger"
              :disabled="!rejectReason || busyId === c.id"
              @click="reject(c)"
            >
              确认驳回
            </button>
          </div>
        </div>
      </article>
    </div>

    <!-- 分页 -->
    <div v-if="total > limit" class="crq-pagination">
      <button :disabled="page <= 1" @click="fetchPage(page - 1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="fetchPage(page + 1)">下一页</button>
    </div>

    <!-- 操作反馈 -->
    <div v-if="feedback" class="crq-feedback" :class="`crq-feedback--${feedbackKind}`" role="status">
      {{ feedback }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import api, { getErrorMessage } from '@/api/client';

interface CandidatePayload {
  description?: string;
  evidence_level?: number;
  quote_text?: string | null;
  note?: string | null;
}

interface CandidateItem {
  id: string;
  session_id: string;
  chunk_id: string;
  version_id: string;
  exact_text: string;
  start_char: number;
  end_char: number;
  extracted_payload: CandidatePayload;
  input_snapshot: Record<string, unknown>;
  extractor_name: string;
  ai_model: string;
  ai_version: string;
  confidence: number;
  status: string;
  reviewed_by_user_id: string | null;
  reviewed_at: string | null;
  rejection_reason: string | null;
  published_evidence_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

const STATUS_LABELS: Record<string, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回',
  modified: '已修改',
  drift_invalid: '已失效(漂移)',
};

const EVIDENCE_LEVEL_LABELS: Record<number, string> = {
  1: '一级·出土实物',
  2: '二级·最早善本',
  3: '三级·史书注疏',
  4: '四级·现代论著',
};

const items = ref<Array<CandidateItem>>([]);
const total = ref(0);
const loading = ref(false);
const error = ref<string | null>(null);
const page = ref(1);
const limit = ref(20);
const statusFilter = ref('pending');
const mineOnly = ref(false);
const busyId = ref<string | null>(null);
const rejectingId = ref<string | null>(null);
const rejectReason = ref('');
const feedback = ref('');
const feedbackKind = ref<'success' | 'error'>('success');

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)));

function payloadOf(c: CandidateItem): CandidatePayload {
  return c.extracted_payload ?? {};
}

function levelLabel(level: number | undefined): string {
  if (level === undefined) return '—';
  return EVIDENCE_LEVEL_LABELS[level] ?? `等级 ${level}`;
}

function formatTime(iso: string | null): string {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('zh-CN');
}

function toggleReject(c: CandidateItem): void {
  rejectingId.value = rejectingId.value === c.id ? null : c.id;
  rejectReason.value = '';
}

async function fetchPage(p: number): Promise<void> {
  page.value = p;
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get('/api/v1/extractions', {
      params: {
        page: p,
        limit: limit.value,
        status: statusFilter.value,
        mine: mineOnly.value || undefined,
      },
    });
    const body = data ?? {};
    items.value = body.items ?? [];
    total.value = body.total ?? 0;
  } catch (e: unknown) {
    error.value = getErrorMessage(e, '加载候选队列失败');
  } finally {
    loading.value = false;
  }
}

async function approve(c: CandidateItem): Promise<void> {
  busyId.value = c.id;
  feedback.value = '';
  try {
    await api.post(`/api/v1/extractions/${c.id}/approval`, {
      session_id: c.session_id,
    });
    feedback.value = '已通过并发布为 Evidence + Citation';
    feedbackKind.value = 'success';
    rejectingId.value = null;
    await fetchPage(page.value);
  } catch (e: unknown) {
    feedback.value = getErrorMessage(e, '审批失败');
    feedbackKind.value = 'error';
  } finally {
    busyId.value = null;
  }
}

async function reject(c: CandidateItem): Promise<void> {
  if (!rejectReason.value) return;
  busyId.value = c.id;
  feedback.value = '';
  try {
    await api.post(`/api/v1/extractions/${c.id}/rejection`, {
      session_id: c.session_id,
      reason: rejectReason.value,
    });
    feedback.value = '已驳回该候选';
    feedbackKind.value = 'success';
    rejectingId.value = null;
    rejectReason.value = '';
    await fetchPage(page.value);
  } catch (e: unknown) {
    feedback.value = getErrorMessage(e, '驳回失败');
    feedbackKind.value = 'error';
  } finally {
    busyId.value = null;
  }
}

onMounted(() => fetchPage(1));
</script>

<style scoped>
.crq {
  max-width: 900px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  display: grid;
  gap: var(--space-4);
}

.crq-header {
  display: grid;
  gap: var(--space-1);
}

.crq-title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.crq-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.crq-filters {
  display: flex;
  gap: var(--space-2);
}

.crq-select {
  padding: var(--space-1-5) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
}

.crq-mine {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1-5);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  cursor: pointer;
}

.crq-mine input {
  accent-color: var(--color-accent);
}

.crq-loading,
.crq-error,
.crq-empty {
  padding: var(--space-6);
  text-align: center;
  color: var(--color-text-secondary);
  font-size: var(--text-sm);
}

.crq-error {
  color: var(--color-error);
}

.crq-list {
  display: grid;
  gap: var(--space-3);
}

.crq-card {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.crq-card__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.crq-card__id {
  font-family: monospace;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.crq-card__meta {
  margin-left: auto;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.crq-badge {
  font-size: var(--text-xs);
  padding: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-hover);
  color: var(--color-text-secondary);
}

.crq-badge--pending {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.crq-badge--approved {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.crq-badge--rejected {
  background: var(--color-error-icon-bg);
  color: var(--color-error-text);
}

.crq-badge--drift_invalid {
  background: var(--color-border);
  color: var(--color-text-muted);
}

.crq-exact {
  margin: 0;
  padding: var(--space-3);
  border-left: 3px solid var(--color-accent);
  background: var(--color-page-bg);
  color: var(--color-text-primary);
  font-family: var(--font-serif, serif);
  font-size: var(--text-base);
  line-height: 1.7;
}

.crq-payload {
  display: grid;
  gap: var(--space-1);
  margin: 0;
}

.crq-payload__row {
  display: grid;
  grid-template-columns: 96px 1fr;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.crq-payload__row dt {
  color: var(--color-text-muted);
}

.crq-payload__row dd {
  margin: 0;
  color: var(--color-text-primary);
}

.crq-card__footer {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-2);
}

.crq-card__time {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.crq-actions {
  margin-left: auto;
  display: flex;
  gap: var(--space-2);
}

.crq-btn {
  padding: var(--space-1-5) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  cursor: pointer;
}

.crq-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.crq-btn--primary {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-on-accent);
}

.crq-btn--ghost {
  background: transparent;
}

.crq-btn--danger {
  background: var(--color-error);
  border-color: var(--color-error);
  color: var(--color-on-accent);
}

.crq-reject {
  display: grid;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
}

.crq-reject__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.crq-reject__input {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  resize: vertical;
}

.crq-reject__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}

.crq-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.crq-pagination button {
  padding: var(--space-1-5) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  cursor: pointer;
}

.crq-pagination button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.crq-feedback {
  position: fixed;
  bottom: var(--space-6);
  right: var(--space-6);
  padding: var(--space-3) var(--space-4);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  box-shadow: var(--shadow-md);
}

.crq-feedback--success {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.crq-feedback--error {
  background: var(--color-error-icon-bg);
  color: var(--color-error-text);
}
</style>
