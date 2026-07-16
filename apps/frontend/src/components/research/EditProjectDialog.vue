<template>
  <div
    v-if="open"
    class="epd-backdrop"
    @click.self="onCancel"
    @keydown.escape="onCancel"
  >
    <div
      class="epd-dialog"
      role="dialog"
      aria-modal="true"
      aria-label="编辑课题"
    >
      <div class="epd-header">
        <h2 class="epd-title">编辑课题</h2>
      </div>

      <form class="epd-form" @submit.prevent="onSubmit">
        <div class="epd-field">
          <label for="epd-title" class="epd-label">课题名称</label>
          <input
            id="epd-title"
            ref="titleInputRef"
            v-model.trim="formTitle"
            type="text"
            class="epd-input"
            required
            :disabled="submitting"
          />
        </div>

        <div class="epd-field">
          <label for="epd-desc" class="epd-label">课题说明</label>
          <textarea
            id="epd-desc"
            v-model="formNotes"
            class="epd-input epd-textarea"
            rows="4"
            placeholder="可选。Markdown 格式的研究说明..."
            :disabled="submitting"
          ></textarea>
        </div>

        <div
          v-if="errorMessage"
          class="epd-error"
          role="alert"
          aria-live="assertive"
        >
          {{ errorMessage }}
        </div>

        <div class="epd-actions">
          <button
            type="button"
            class="epd-btn epd-btn--cancel"
            :disabled="submitting"
            @click="onCancel"
          >
            取消
          </button>
          <button
            type="submit"
            class="epd-btn epd-btn--primary"
            :disabled="!canSubmit || submitting"
          >
            {{ submitting ? '保存中...' : '保存' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import api from '@/api/client';

const props = defineProps<{
  open: boolean;
  projectId: string;
  currentTitle: string;
  currentNotes: string;
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
  saved: [];
}>();

const formTitle = ref('');
const formNotes = ref('');
const submitting = ref(false);
const errorMessage = ref('');
const titleInputRef = ref<HTMLInputElement | null>(null);

const canSubmit = computed(() => formTitle.value.trim().length > 0 && !submitting.value);

watch(
  () => props.open,
  (val) => {
    if (val) {
      formTitle.value = props.currentTitle;
      formNotes.value = props.currentNotes || '';
      errorMessage.value = '';
      nextTick(() => {
        titleInputRef.value?.focus();
      });
    }
  },
);

async function onSubmit() {
  if (!canSubmit.value) return;
  submitting.value = true;
  errorMessage.value = '';
  try {
    await api.patch(`/api/v1/workspace/sessions/${props.projectId}`, {
      title: formTitle.value.trim(),
      context_notes: formNotes.value.trim() || null,
    });
    emit('saved');
    emit('update:open', false);
  } catch (e: unknown) {
    const msg =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '保存失败';
    errorMessage.value = msg;
  } finally {
    submitting.value = false;
  }
}

function onCancel() {
  if (submitting.value) return;
  emit('update:open', false);
}
</script>

<style scoped>
.epd-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  padding: 20px;
}

.epd-dialog {
  background: var(--color-navbar-bg, #fff);
  border-radius: 12px;
  padding: 32px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  animation: epdFadeIn 0.15s ease;
}

@keyframes epdFadeIn {
  from {
    opacity: 0;
    transform: scale(0.97);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.epd-header {
  margin-bottom: 24px;
}

.epd-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
}

.epd-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.epd-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.epd-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
}

.epd-input {
  padding: 10px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: var(--color-text-primary, #1a365d);
  background: var(--color-page-bg, #fafafa);
  transition: border-color 0.15s;
  box-sizing: border-box;
}

.epd-input:focus {
  outline: none;
  border-color: var(--color-accent, #4299e1);
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.15);
}

.epd-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.epd-textarea {
  resize: vertical;
}

.epd-error {
  font-size: 13px;
  color: var(--color-error-text, #c53030);
  padding: 8px 12px;
  background: rgba(197, 48, 48, 0.08);
  border-radius: 6px;
  line-height: 1.4;
}

.epd-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 6px;
}

.epd-btn {
  padding: 10px 22px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.epd-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.epd-btn--primary {
  background: var(--color-accent, #4299e1);
  color: #fff;
}

.epd-btn--primary:hover:not(:disabled) {
  background: var(--color-accent-hover, #3182ce);
}

.epd-btn--cancel {
  background: transparent;
  color: var(--color-text-secondary, #4a5568);
  border: 1px solid var(--color-border, #e2e8f0);
}

.epd-btn--cancel:hover:not(:disabled) {
  background: var(--color-hover, #edf2f7);
}
</style>
