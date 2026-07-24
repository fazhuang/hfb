<template>
  <div
    v-if="open"
    class="dpd-backdrop"
    @click.self="onCancel"
    @keydown="onKeyDown"
  >
    <div
      class="dpd-dialog"
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="dpd-title"
      aria-describedby="dpd-message"
    >
      <div class="dpd-header">
        <h2 id="dpd-title" class="dpd-title">删除课题</h2>
      </div>

      <p id="dpd-message" class="dpd-message">
        确定要删除课题「<strong>{{ projectTitle }}</strong>」吗？此操作不可撤销。
      </p>

      <div
        v-if="errorMessage"
        class="dpd-error"
        role="alert"
        aria-live="assertive"
      >
        {{ errorMessage }}
      </div>

      <div class="dpd-actions">
        <button
          ref="cancelBtnRef"
          type="button"
          class="dpd-btn dpd-btn--cancel"
          :disabled="submitting"
          @click="onCancel"
        >
          取消
        </button>
        <button
          type="button"
          class="dpd-btn dpd-btn--danger"
          :disabled="submitting"
          @click="onConfirm"
        >
          {{ submitting ? '删除中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import api from '@/api/client';

const props = defineProps<{
  open: boolean;
  projectId: string;
  projectTitle: string;
  triggerEl?: HTMLElement | null;
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
  deleted: [];
}>();

const submitting = ref(false);
const errorMessage = ref('');
const cancelBtnRef = ref<HTMLButtonElement | null>(null);

// Focus restoration: use caller-supplied stable trigger element when available.
// The menuitem that opens this dialog is unmounted before the watch fires,
// so the parent page must pass the "更多操作" button via triggerEl.

watch(
  () => props.open,
  (val) => {
    if (val) {
      errorMessage.value = '';
      nextTick(() => {
        cancelBtnRef.value?.focus();
      });
    } else {
      // Restore focus to the stable trigger button (passed by parent) when dialog closes
      nextTick(() => {
        props.triggerEl?.focus();
      });
    }
  },
);

async function onConfirm() {
  submitting.value = true;
  errorMessage.value = '';
  try {
    await api.delete(`/api/v1/workspace/sessions/${props.projectId}`);
    emit('deleted');
    emit('update:open', false);
  } catch (e: unknown) {
    const msg =
      (e as any)?.response?.data?.message ||
      (e as any)?.message ||
      '删除失败';
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
  const dialog = (e.currentTarget as HTMLElement).querySelector('.dpd-dialog');
  if (!dialog) return;
  const focusable = dialog.querySelectorAll<HTMLElement>(
    'button:not(:disabled), [tabindex]:not([tabindex="-1"])',
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
.dpd-backdrop {
  position: fixed;
  inset: 0;
  z-index: var(--z-dropdown)00;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay-light);
  padding: var(--space-5);
}

.dpd-dialog {
  background: var(--color-surface);
  border-radius: var(--radius-2xl);
  padding: var(--space-8);
  width: 100%;
  max-width: 420px;
  box-shadow: var(--shadow-lg);
  animation: hfb-fade-in var(--transition-base) ease;
}

.dpd-header {
  margin-bottom: var(--space-4);
}

.dpd-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0;
}

.dpd-message {
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-6);
  line-height: var(--leading-normal);
}

.dpd-error {
  font-size: var(--text-sm);
  color: var(--color-error-text);
  padding: var(--space-2) var(--space-3);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  line-height: 1.4;
  margin-bottom: var(--space-4);
}

.dpd-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
}

.dpd-btn {
  padding: var(--btn-padding-lg);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-lg);
  font-weight: var(--font-semibold);
  cursor: pointer;
  border: none;
  transition: all var(--transition-base);
}

.dpd-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dpd-btn--danger {
  background: var(--color-error-text);
  color: var(--color-surface);
}

.dpd-btn--danger:hover:not(:disabled) {
  background: var(--color-error-light-text);
}

.dpd-btn--danger:focus-visible:not(:disabled) {
  background: var(--color-error-light-text);
}

.dpd-btn--cancel {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.dpd-btn--cancel:hover:not(:disabled) {
  background: var(--color-hover);
}

.dpd-btn--cancel:focus-visible:not(:disabled) {
  background: var(--color-hover);
}
</style>
