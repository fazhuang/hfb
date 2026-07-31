<template>
  <div v-if="open" class="epd-backdrop" @click.self="onCancel" @keydown="onKeyDown">
    <div class="epd-dialog" role="dialog" aria-modal="true" aria-label="编辑课题">
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

        <div v-if="errorMessage" class="epd-error" role="alert" aria-live="assertive">
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
  triggerEl?: HTMLElement | null;
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
    } else {
      // Restore focus to the stable trigger button (passed by parent) when dialog closes
      nextTick(() => {
        props.triggerEl?.focus();
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
    const msg = (e as any)?.response?.data?.message || (e as any)?.message || '保存失败';
    errorMessage.value = msg;
  } finally {
    submitting.value = false;
  }
}

function onCancel() {
  if (submitting.value) return;
  emit('update:open', false);
}

/**
 * Keep focus within the dialog when Tab or Shift+Tab is pressed.
 */
function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    onCancel();
    return;
  }
  if (e.key !== 'Tab') return;
  const dialog = (e.currentTarget as HTMLElement).querySelector('.epd-dialog');
  if (!dialog) return;
  const focusable = dialog.querySelectorAll<HTMLElement>(
    'input:not(:disabled), textarea:not(:disabled), button:not(:disabled), [tabindex]:not([tabindex="-1"])',
  );
  if (focusable.length === 0) return;
  const first = focusable[0]!;
  const last = focusable[focusable.length - 1]!;
  if (e.shiftKey) {
    if (document.activeElement === first) {
      e.preventDefault();
      last.focus();
    }
  } else {
    if (document.activeElement === last) {
      e.preventDefault();
      first.focus();
    }
  }
}
</script>

<style scoped>
.epd-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-dropdown) 00;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay-light);
  padding: var(--space-5);
}

.epd-dialog {
  background: var(--color-surface);
  border-radius: var(--radius-2xl);
  padding: var(--space-8);
  width: 100%;
  max-width: 480px;
  box-shadow: var(--shadow-lg);
  animation: hfb-fade-in var(--transition-base) ease;
}

.epd-header {
  margin-bottom: var(--space-6);
}

.epd-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
}

.epd-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4-5);
}

.epd-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1-5);
}

.epd-label {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}

.epd-input {
  padding: var(--space-2-5) 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-family: inherit;
  color: var(--color-text-primary);
  background: var(--color-page-bg);
  transition: border-color var(--transition-base);
  box-sizing: border-box;
}

.epd-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.epd-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.epd-textarea {
  resize: vertical;
}

.epd-error {
  font-size: var(--text-sm);
  color: var(--color-error-text);
  padding: var(--space-2) var(--space-3);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  line-height: 1.4;
}

.epd-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding-top: 6px;
}

.epd-btn {
  padding: var(--btn-padding-lg);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-lg);
  font-weight: var(--font-semibold);
  cursor: pointer;
  border: none;
  transition: all var(--transition-base);
}

.epd-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.epd-btn--primary {
  background: var(--color-accent);
  color: var(--color-surface);
}

.epd-btn--primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.epd-btn--primary:focus-visible:not(:disabled) {
  background: var(--color-accent-hover);
}

.epd-btn--cancel {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.epd-btn--cancel:hover:not(:disabled) {
  background: var(--color-hover);
}

.epd-btn--cancel:focus-visible:not(:disabled) {
  background: var(--color-hover);
}
</style>
