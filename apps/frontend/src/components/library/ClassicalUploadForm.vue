<template>
  <div class="cuf" role="form" aria-label="上传古籍资料">
    <div class="cuf-header">
      <h3 class="cuf-title">上传古籍资料</h3>
      <p class="cuf-subtitle">
        上传已获授权的古籍 PDF，进入页面级摄入流程；提交后文献进入「待审核」状态，不自动进入检索。
      </p>
    </div>

    <form class="cuf-form" @submit.prevent="onSubmit">
      <!-- PDF 文件（必填） -->
      <div class="cuf-field">
        <label for="cuf-file" class="cuf-label">
          PDF 文件
          <span class="cuf-required" aria-hidden="true">*</span>
        </label>
        <input
          id="cuf-file"
          ref="fileInputRef"
          type="file"
          accept=".pdf,application/pdf"
          class="cuf-input cuf-input--file"
          required
          :disabled="submitting"
          @change="onFileChange"
        />
        <p v-if="selectedFile" class="cuf-hint">
          已选择：{{ selectedFile.name }}（{{ formatSize(selectedFile.size) }}）
        </p>
      </div>

      <!-- 标题（必填） -->
      <div class="cuf-field">
        <label for="cuf-title" class="cuf-label">
          标题
          <span class="cuf-required" aria-hidden="true">*</span>
        </label>
        <input
          id="cuf-title"
          v-model.trim="title"
          type="text"
          class="cuf-input"
          placeholder="如：针灸甲乙经"
          maxlength="500"
          required
          :disabled="submitting"
        />
      </div>

      <!-- 授权依据（必填） -->
      <div class="cuf-field">
        <label for="cuf-basis" class="cuf-label">
          授权依据
          <span class="cuf-required" aria-hidden="true">*</span>
        </label>
        <input
          id="cuf-basis"
          v-model.trim="authorizationBasis"
          type="text"
          class="cuf-input"
          placeholder="如：公有领域 / CC BY 4.0 / 机构授权编号"
          maxlength="200"
          required
          :disabled="submitting"
        />
      </div>

      <!-- 朝代（可选） -->
      <div class="cuf-field">
        <label for="cuf-dynasty" class="cuf-label">朝代</label>
        <input
          id="cuf-dynasty"
          v-model.trim="dynasty"
          type="text"
          class="cuf-input"
          placeholder="如：西晋"
          maxlength="100"
          :disabled="submitting"
        />
      </div>

      <!-- 分类（可选） -->
      <div class="cuf-field">
        <label for="cuf-category" class="cuf-label">分类</label>
        <input
          id="cuf-category"
          v-model.trim="category"
          type="text"
          class="cuf-input"
          placeholder="如：针灸"
          maxlength="200"
          :disabled="submitting"
        />
      </div>

      <!-- 来源链接（可选） -->
      <div class="cuf-field">
        <label for="cuf-source-url" class="cuf-label">来源链接</label>
        <input
          id="cuf-source-url"
          v-model.trim="sourceUrl"
          type="url"
          class="cuf-input"
          placeholder="https://…"
          maxlength="2000"
          :disabled="submitting"
        />
      </div>

      <!-- 提示 / 错误 -->
      <HfbAlert v-if="errorMessage" variant="error" :title="errorMessage" />
      <HfbAlert v-else-if="successMessage" variant="success" :title="successMessage" />

      <!-- 操作 -->
      <div class="cuf-actions">
        <HfbButton type="button" variant="ghost" :disabled="submitting" @click="$emit('cancel')">
          取消
        </HfbButton>
        <HfbButton type="submit" variant="primary" :disabled="!canSubmit" :loading="submitting">
          上传
        </HfbButton>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import api, { getErrorMessage } from '@/api/client';
import HfbAlert from '@/components/common/HfbAlert.vue';
import HfbButton from '@/components/common/HfbButton.vue';

const emit = defineEmits<{
  submitted: [];
  cancel: [];
}>();

const fileInputRef = ref<HTMLInputElement | null>(null);
const selectedFile = ref<File | null>(null);
const title = ref('');
const authorizationBasis = ref('');
const dynasty = ref('');
const category = ref('');
const sourceUrl = ref('');
const submitting = ref(false);
const errorMessage = ref('');
const successMessage = ref('');

const canSubmit = computed(
  () => selectedFile.value !== null && title.value.trim().length > 0 && !submitting.value,
);

function onFileChange(event: Event): void {
  const input = event.target as HTMLInputElement;
  selectedFile.value = input.files?.[0] ?? null;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function resetForm(): void {
  selectedFile.value = null;
  title.value = '';
  authorizationBasis.value = '';
  dynasty.value = '';
  category.value = '';
  sourceUrl.value = '';
  if (fileInputRef.value) fileInputRef.value.value = '';
}

async function onSubmit(): Promise<void> {
  if (!selectedFile.value) return;
  submitting.value = true;
  errorMessage.value = '';
  successMessage.value = '';

  const formData = new FormData();
  formData.append('file', selectedFile.value);
  formData.append('title', title.value.trim());
  formData.append('authorization_basis', authorizationBasis.value.trim());
  if (dynasty.value.trim()) formData.append('dynasty', dynasty.value.trim());
  if (category.value.trim()) formData.append('category', category.value.trim());
  if (sourceUrl.value.trim()) formData.append('source_url', sourceUrl.value.trim());

  try {
    const { data } = await api.post('/api/v1/documents/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000, // 摄入（PDF 解析/逐页切块）可能较慢
    });
    successMessage.value =
      typeof data?.message === 'string' ? data.message : '上传成功，文献已进入待审核状态。';
    // 上传成功后重置并通知父组件刷新列表
    resetForm();
    emit('submitted');
  } catch (e: unknown) {
    errorMessage.value = getErrorMessage(e, '上传失败，请稍后重试');
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.cuf {
  display: grid;
  gap: var(--space-4);
  max-width: 560px;
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-surface);
}

.cuf-header {
  display: grid;
  gap: var(--space-1);
}

.cuf-title {
  margin: 0;
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
}

.cuf-subtitle {
  margin: 0;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.cuf-form {
  display: grid;
  gap: var(--space-3);
}

.cuf-field {
  display: grid;
  gap: var(--space-1);
}

.cuf-label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.cuf-required {
  color: var(--color-error);
}

.cuf-input {
  padding: var(--space-2);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-page-bg, var(--color-surface));
  color: var(--color-text-primary);
  font-size: var(--text-sm);
  width: 100%;
}

.cuf-input:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 1px;
}

.cuf-input--file {
  padding: var(--space-2);
}

.cuf-hint {
  margin: 0;
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.cuf-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
