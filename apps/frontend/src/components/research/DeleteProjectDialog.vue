<template>
  <div
    v-if="open"
    class="dpd-backdrop"
    @click.self="onCancel"
    @keydown.escape="onCancel"
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
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
  deleted: [];
}>();

const submitting = ref(false);
const errorMessage = ref('');
const cancelBtnRef = ref<HTMLButtonElement | null>(null);

watch(
  () => props.open,
  (val) => {
    if (val) {
      errorMessage.value = '';
      nextTick(() => {
        cancelBtnRef.value?.focus();
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
</script>

<style scoped>
.dpd-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  padding: 20px;
}

.dpd-dialog {
  background: var(--color-navbar-bg, #fff);
  border-radius: 12px;
  padding: 32px;
  width: 100%;
  max-width: 420px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  animation: dpdFadeIn 0.15s ease;
}

@keyframes dpdFadeIn {
  from {
    opacity: 0;
    transform: scale(0.97);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

.dpd-header {
  margin-bottom: 16px;
}

.dpd-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
}

.dpd-message {
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
  margin: 0 0 24px;
  line-height: 1.5;
}

.dpd-error {
  font-size: 13px;
  color: var(--color-error-text, #c53030);
  padding: 8px 12px;
  background: rgba(197, 48, 48, 0.08);
  border-radius: 6px;
  line-height: 1.4;
  margin-bottom: 16px;
}

.dpd-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.dpd-btn {
  padding: 10px 22px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.dpd-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dpd-btn--danger {
  background: #c53030;
  color: #fff;
}

.dpd-btn--danger:hover:not(:disabled) {
  background: #9b2c2c;
}

.dpd-btn--cancel {
  background: transparent;
  color: var(--color-text-secondary, #4a5568);
  border: 1px solid var(--color-border, #e2e8f0);
}

.dpd-btn--cancel:hover:not(:disabled) {
  background: var(--color-hover, #edf2f7);
}
</style>
