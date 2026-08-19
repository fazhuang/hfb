<template>
  <div class="sap">
    <header class="sap-header">
      <h1 class="sap-title">来源准入清单</h1>
      <p class="sap-subtitle">
        对应 HFB-DAT-0306 §3：Research Lead 逐行填写来源，Steering Committee 逐条审核。
        全部 13 行审核通过后，由部署层手动开放古籍上传（不自动放行）。
      </p>
    </header>

    <!-- 进度汇总 -->
    <div v-if="summary" class="sap-summary" role="status">
      <span class="sap-summary__item">共 {{ summary.total_rows }} 行</span>
      <span class="sap-summary__item">已填 {{ summary.filled }}</span>
      <span class="sap-summary__item">待审核 {{ summary.submitted }}</span>
      <span class="sap-summary__item sap-summary__item--ok">已通过 {{ summary.approved }}</span>
      <span class="sap-summary__item sap-summary__item--bad">已驳回 {{ summary.rejected }}</span>
      <span v-if="summary.complete" class="sap-summary__complete">✓ 清单已完成（待部署放行）</span>
    </div>

    <!-- 加载 / 错误 -->
    <div v-if="loading" class="sap-loading">正在加载清单…</div>
    <div v-else-if="error" class="sap-error" role="alert">{{ error }}</div>

    <!-- 三个分组 -->
    <section v-for="group in groups" v-else :key="group.key" class="sap-group">
      <h2 class="sap-group__title">{{ group.label }}</h2>

      <article v-for="row in rowsOf(group.key)" :key="row.entry_key" class="sap-row">
        <header class="sap-row__header">
          <span class="sap-row__key">{{ row.entry_key }}</span>
          <span class="sap-badge" :class="`sap-badge--${row.status}`">
            {{ STATUS_LABELS[row.status] || row.status }}
          </span>
        </header>

        <!-- 已填内容展示 -->
        <template v-if="row.status !== 'empty'">
          <dl class="sap-fields">
            <div class="sap-field"><dt>来源 URI / 馆藏标识</dt><dd>{{ row.source_uri }}</dd></div>
            <div class="sap-field"><dt>版权/授权依据</dt><dd>{{ row.authorization_basis }}</dd></div>
            <div class="sap-field"><dt>版本标识</dt><dd>{{ row.version_label }}</dd></div>
            <div class="sap-field"><dt>导入范围</dt><dd>{{ row.import_scope }}</dd></div>
            <div class="sap-field"><dt>绑定计划</dt><dd>{{ row.binding_plan }}</dd></div>
            <div class="sap-field"><dt>风险说明</dt><dd>{{ row.risk_note }}</dd></div>
          </dl>
          <p v-if="row.review_note" class="sap-review-note">审核意见：{{ row.review_note }}</p>
        </template>
        <p v-else class="sap-empty">尚未填写。</p>

        <!-- 操作区 -->
        <footer class="sap-row__actions">
          <!-- 填写 / 重新填写（Research Lead） -->
          <button
            v-if="row.status === 'empty' || row.status === 'rejected'"
            type="button"
            class="sap-btn sap-btn--secondary"
            :disabled="busyKey === row.entry_key"
            @click="toggleEdit(row.entry_key)"
          >
            {{ row.status === 'rejected' ? '重新填写' : '填写' }}
          </button>

          <!-- 审核（Steering Committee，仅 submitted 行） -->
          <template v-if="canReview && row.status === 'submitted'">
            <button
              type="button"
              class="sap-btn sap-btn--ghost"
              :disabled="busyKey === row.entry_key"
              @click="openReject(row.entry_key)"
            >
              驳回
            </button>
            <button
              type="button"
              class="sap-btn sap-btn--primary"
              :disabled="busyKey === row.entry_key"
              @click="review(row.entry_key, 'approve')"
            >
              通过
            </button>
          </template>
        </footer>

        <!-- 内联填写表单 -->
        <form v-if="editingKey === row.entry_key" class="sap-edit" @submit.prevent="submit(row.entry_key)">
          <div class="sap-edit__grid">
            <label class="sap-edit__field">
              <span>来源 URI / 馆藏标识 *</span>
              <input v-model="editForm.source_uri" required maxlength="2000" />
            </label>
            <label class="sap-edit__field">
              <span>版权/授权依据 *</span>
              <input v-model="editForm.authorization_basis" required maxlength="500" />
            </label>
            <label class="sap-edit__field">
              <span>版本标识 *</span>
              <input v-model="editForm.version_label" required maxlength="500" />
            </label>
            <label class="sap-edit__field">
              <span>导入范围 *</span>
              <input v-model="editForm.import_scope" required maxlength="500" />
            </label>
            <label class="sap-edit__field sap-edit__field--wide">
              <span>SourceRef → Evidence → Citation 绑定计划 *</span>
              <textarea v-model="editForm.binding_plan" required rows="2"></textarea>
            </label>
            <label class="sap-edit__field sap-edit__field--wide">
              <span>风险说明 *</span>
              <textarea v-model="editForm.risk_note" required rows="2"></textarea>
            </label>
          </div>
          <div class="sap-edit__actions">
            <button type="button" class="sap-btn sap-btn--ghost" @click="editingKey = null">取消</button>
            <button type="submit" class="sap-btn sap-btn--primary" :disabled="busyKey === row.entry_key">
              保存并提交
            </button>
          </div>
        </form>

        <!-- 内联驳回表单 -->
        <form v-if="rejectingKey === row.entry_key" class="sap-edit" @submit.prevent="review(row.entry_key, 'reject')">
          <label class="sap-edit__field">
            <span>驳回理由（可选）</span>
            <textarea v-model="reviewNote" rows="2" maxlength="2000"></textarea>
          </label>
          <div class="sap-edit__actions">
            <button type="button" class="sap-btn sap-btn--ghost" @click="rejectingKey = null">取消</button>
            <button type="submit" class="sap-btn sap-btn--danger" :disabled="busyKey === row.entry_key">
              确认驳回
            </button>
          </div>
        </form>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import api, { getErrorMessage } from '@/api/client';
import { useAuthStore } from '@/stores/auth';

interface AdmissionRow {
  id: string | null;
  entry_key: string;
  source_type: string;
  source_uri: string | null;
  authorization_basis: string | null;
  version_label: string | null;
  import_scope: string | null;
  binding_plan: string | null;
  risk_note: string | null;
  status: string;
  review_note: string | null;
}

interface AdmissionSummary {
  total_rows: number;
  filled: number;
  submitted: number;
  approved: number;
  rejected: number;
  complete: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  empty: '未填写',
  submitted: '待审核',
  approved: '已通过',
  rejected: '已驳回',
};

const GROUPS = [
  { key: 'CV-', label: '古籍版本（CV-01 ~ CV-05）' },
  { key: 'DOC-', label: '研究文献（DOC-01 ~ DOC-05）' },
  { key: 'HOLD-', label: '馆藏资料（HOLD-01 ~ HOLD-03）' },
];

const auth = useAuthStore();
const rows = ref<Array<AdmissionRow>>([]);
const summary = ref<AdmissionSummary | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const busyKey = ref<string | null>(null);
const editingKey = ref<string | null>(null);
const rejectingKey = ref<string | null>(null);
const reviewNote = ref('');
const editForm = ref({
  source_uri: '',
  authorization_basis: '',
  version_label: '',
  import_scope: '',
  binding_plan: '',
  risk_note: '',
});

const canReview = computed(() => auth.canReviewDocuments);

const groups = GROUPS;

function rowsOf(prefix: string): Array<AdmissionRow> {
  return rows.value.filter((r) => r.entry_key.startsWith(prefix));
}

function rowByKey(key: string): AdmissionRow | undefined {
  return rows.value.find((r) => r.entry_key === key);
}

function toggleEdit(key: string): void {
  editingKey.value = editingKey.value === key ? null : key;
  rejectingKey.value = null;
  reviewNote.value = '';
  const row = rowByKey(key);
  editForm.value = {
    source_uri: row?.source_uri ?? '',
    authorization_basis: row?.authorization_basis ?? '',
    version_label: row?.version_label ?? '',
    import_scope: row?.import_scope ?? '',
    binding_plan: row?.binding_plan ?? '',
    risk_note: row?.risk_note ?? '',
  };
}

function openReject(key: string): void {
  rejectingKey.value = rejectingKey.value === key ? null : key;
  editingKey.value = null;
  reviewNote.value = '';
}

async function fetchList(): Promise<void> {
  loading.value = true;
  error.value = null;
  try {
    const { data } = await api.get('/api/v1/source-admissions');
    rows.value = data.items ?? [];
    summary.value = data.summary ?? null;
  } catch (e: unknown) {
    error.value = getErrorMessage(e, '加载准入清单失败');
  } finally {
    loading.value = false;
  }
}

async function submit(key: string): Promise<void> {
  busyKey.value = key;
  try {
    await api.put(`/api/v1/source-admissions/${key}`, editForm.value);
    editingKey.value = null;
    await fetchList();
  } catch (e: unknown) {
    error.value = getErrorMessage(e, '提交失败');
  } finally {
    busyKey.value = null;
  }
}

async function review(key: string, decision: 'approve' | 'reject'): Promise<void> {
  busyKey.value = key;
  try {
    await api.post(`/api/v1/source-admissions/${key}/review`, {
      decision,
      note: decision === 'reject' ? reviewNote.value || null : null,
    });
    rejectingKey.value = null;
    reviewNote.value = '';
    await fetchList();
  } catch (e: unknown) {
    error.value = getErrorMessage(e, '审核失败');
  } finally {
    busyKey.value = null;
  }
}

onMounted(() => fetchList());
</script>

<style scoped>
.sap {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-6);
  display: grid;
  gap: var(--space-4);
}

.sap-header {
  display: grid;
  gap: var(--space-1);
}

.sap-title {
  margin: 0;
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.sap-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.sap-summary {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  padding: var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
}

.sap-summary__item {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.sap-summary__item--ok {
  color: var(--color-success-text);
}

.sap-summary__item--bad {
  color: var(--color-error-text);
}

.sap-summary__complete {
  margin-left: auto;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-success-text);
}

.sap-loading,
.sap-error {
  padding: var(--space-6);
  text-align: center;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.sap-error {
  color: var(--color-error);
}

.sap-group {
  display: grid;
  gap: var(--space-3);
}

.sap-group__title {
  margin: 0;
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  border-bottom: 1px solid var(--color-border);
  padding-bottom: var(--space-2);
}

.sap-row {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.sap-row__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.sap-row__key {
  font-family: monospace;
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
}

.sap-badge {
  font-size: var(--text-xs);
  padding: var(--space-0-5) var(--space-2);
  border-radius: var(--radius-sm);
  background: var(--color-hover);
  color: var(--color-text-secondary);
}

.sap-badge--submitted {
  background: var(--color-warning-bg);
  color: var(--color-warning-text);
}

.sap-badge--approved {
  background: var(--color-success-bg);
  color: var(--color-success-text);
}

.sap-badge--rejected {
  background: var(--color-error-icon-bg);
  color: var(--color-error-text);
}

.sap-empty {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-muted);
}

.sap-fields {
  display: grid;
  gap: var(--space-1-5);
  margin: 0;
}

.sap-field {
  display: grid;
  grid-template-columns: 180px 1fr;
  gap: var(--space-2);
  font-size: var(--text-sm);
}

.sap-field dt {
  color: var(--color-text-muted);
  flex-shrink: 0;
}

.sap-field dd {
  margin: 0;
  color: var(--color-text-primary);
  word-break: break-word;
}

.sap-review-note {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-error-text);
  padding: var(--space-2);
  border: 1px solid var(--color-error);
  border-radius: var(--radius-sm);
}

.sap-row__actions {
  display: flex;
  gap: var(--space-2);
  border-top: 1px solid var(--color-border);
  padding-top: var(--space-2);
}

.sap-btn {
  padding: var(--space-1-5) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  cursor: pointer;
}

.sap-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.sap-btn--primary {
  background: var(--color-accent);
  border-color: var(--color-accent);
  color: var(--color-on-accent);
}

.sap-btn--secondary {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.sap-btn--ghost {
  background: transparent;
}

.sap-btn--danger {
  background: var(--color-error);
  border-color: var(--color-error);
  color: var(--color-on-accent);
}

.sap-edit {
  display: grid;
  gap: var(--space-3);
  padding: var(--space-3);
  border: 1px dashed var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-bg);
}

.sap-edit__grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-3);
}

.sap-edit__field {
  display: grid;
  gap: var(--space-1);
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.sap-edit__field--wide {
  grid-column: 1 / -1;
}

.sap-edit__field input,
.sap-edit__field textarea {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  width: 100%;
}

.sap-edit__field textarea {
  resize: vertical;
}

.sap-edit__actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
