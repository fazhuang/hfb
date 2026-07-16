<template>
  <!-- Backdrop -->
  <div
    v-if="open"
    class="cpd-backdrop"
    @click.self="onCancel"
    @keydown.escape="onCancel"
  >
    <!-- Dialog -->
    <div
      class="cpd-dialog"
      role="dialog"
      aria-modal="true"
      :aria-label="t('researchEntry.newTitle')"
    >
      <div class="cpd-header">
        <h2 class="cpd-title">{{ t('researchEntry.newTitle') }}</h2>
        <p class="cpd-subtitle">{{ t('researchEntry.newSubtitle') }}</p>
      </div>

      <form class="cpd-form" @submit.prevent="onSubmit">
        <!-- Name (required) -->
        <div class="cpd-field">
          <label for="cpd-name" class="cpd-label">
            {{ t('researchEntry.topicName') }}
            <span class="cpd-required" aria-label="required">*</span>
          </label>
          <input
            id="cpd-name"
            ref="nameInputRef"
            v-model.trim="name"
            type="text"
            class="cpd-input"
            :placeholder="t('researchEntry.topicNamePlaceholder')"
            required
            autofocus
            :disabled="submitting"
          />
        </div>

        <!-- Description (optional) -->
        <div class="cpd-field">
          <label for="cpd-desc" class="cpd-label">
            {{ t('researchEntry.topicDesc') }}
          </label>
          <textarea
            id="cpd-desc"
            v-model.trim="description"
            class="cpd-input"
            :placeholder="t('researchEntry.topicDescPlaceholder')"
            rows="3"
            :disabled="submitting"
          ></textarea>
        </div>

        <!-- Server error -->
        <div
          v-if="errorMessage"
          class="cpd-error"
          role="alert"
          aria-live="assertive"
        >
          {{ errorMessage }}
        </div>

        <!-- Actions -->
        <div class="cpd-actions">
          <button
            type="button"
            class="cpd-btn cpd-btn--cancel"
            :disabled="submitting"
            @click="onCancel"
          >
            {{ t('common.cancel') }}
          </button>
          <button
            type="submit"
            class="cpd-btn cpd-btn--primary"
            :disabled="!canSubmit || submitting"
          >
            {{ submitting ? t('common.loading') + '...' : t('researchEntry.create') }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/api/client';

const { t } = useI18n();

const props = defineProps<{
  open: boolean;
}>();

const emit = defineEmits<{
  'update:open': [value: boolean];
  created: [];
}>();

const name = ref('');
const description = ref('');
const submitting = ref(false);
const errorMessage = ref('');
const nameInputRef = ref<HTMLInputElement | null>(null);

const canSubmit = computed(() => name.value.trim().length > 0 && !submitting.value);

// Watch open to auto-focus and reset form
watch(() => props.open, (val) => {
  if (val) {
    name.value = '';
    description.value = '';
    errorMessage.value = '';
    nextTick(() => {
      nameInputRef.value?.focus();
    });
  }
});

async function onSubmit() {
  if (!canSubmit.value) return;
  submitting.value = true;
  errorMessage.value = '';
  try {
    await api.post('/api/v1/workspace/sessions', {
      title: name.value.trim(),
    });
    emit('created');
    emit('update:open', false);
  } catch (e: unknown) {
    const msg = (e as any)?.response?.data?.message
      || (e as any)?.message
      || t('common.error');
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
.cpd-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  padding: 20px;
}

.cpd-dialog {
  background: var(--color-navbar-bg, #fff);
  border-radius: 12px;
  padding: 32px;
  width: 100%;
  max-width: 460px;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.15);
  animation: cpdFadeIn 0.15s ease;
}

@keyframes cpdFadeIn {
  from { opacity: 0; transform: scale(0.97); }
  to { opacity: 1; transform: scale(1); }
}

.cpd-header {
  margin-bottom: 24px;
}

.cpd-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 6px;
}

.cpd-subtitle {
  font-size: 14px;
  color: var(--color-text-muted, #718096);
  margin: 0;
}

.cpd-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.cpd-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cpd-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary, #4a5568);
}

.cpd-required {
  color: var(--color-error-text, #c53030);
  margin-left: 2px;
}

.cpd-input {
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

.cpd-input:focus {
  outline: none;
  border-color: var(--color-accent, #4299e1);
  box-shadow: 0 0 0 3px rgba(66, 153, 225, 0.15);
}

.cpd-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

textarea.cpd-input {
  resize: vertical;
}

.cpd-error {
  font-size: 13px;
  color: var(--color-error-text, #c53030);
  padding: 8px 12px;
  background: rgba(197, 48, 48, 0.08);
  border-radius: 6px;
  line-height: 1.4;
}

.cpd-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding-top: 6px;
}

.cpd-btn {
  padding: 10px 22px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  transition: all 0.15s;
}

.cpd-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cpd-btn--primary {
  background: var(--color-accent, #4299e1);
  color: #fff;
}

.cpd-btn--primary:hover:not(:disabled) {
  background: var(--color-accent-hover, #3182ce);
}

.cpd-btn--cancel {
  background: transparent;
  color: var(--color-text-secondary, #4a5568);
  border: 1px solid var(--color-border, #e2e8f0);
}

.cpd-btn--cancel:hover:not(:disabled) {
  background: var(--color-hover, #edf2f7);
}
</style>
