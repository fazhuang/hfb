<template>
  <!-- Backdrop -->
  <div v-if="open" class="cpd-backdrop" @click.self="onCancel" @keydown.escape="onCancel">
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
        <div v-if="errorMessage" class="cpd-error" role="alert" aria-live="assertive">
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
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/api/client';

const { t } = useI18n();

const props = defineProps<{
  open: boolean;
  triggerEl?: HTMLElement | null;
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

// Focus restoration: use caller-supplied stable trigger element when available.
// On touch viewports, clicking a button does not transfer focus to it, so
// the parent page must pass the button reference explicitly via triggerEl.

// Watch open to auto-focus and reset form
watch(
  () => props.open,
  (val) => {
    if (val) {
      name.value = '';
      description.value = '';
      errorMessage.value = '';
      // Double nextTick guarantees Vue has finished inserting the dialog
      // into the DOM and any reactive sidebar collapse has settled before
      // we claim focus. Without this, auto-focus races against layout shifts
      // at narrow viewports (≤768px) where the sidebar auto-collapses.
      // Triple nextTick adds an extra microtask cycle for WebKit to
      // fully resolve layout-after-collapse, which can otherwise steal
      // focus from the dialog during the first Tab cycle.
      // Use requestAnimationFrame as the final anchor — it fires after
      // all layout/paint work is complete, guaranteeing the dialog is
      // in its final position before we claim focus.
      nextTick(() => {
        nextTick(() => {
          requestAnimationFrame(() => {
            nameInputRef.value?.focus();
          });
        });
      });
    } else {
      // Restore focus to the stable trigger button (passed by parent) when dialog closes
      nextTick(() => {
        props.triggerEl?.focus();
      });
    }
  },
);

// Bind the focus-trap keydown handler on document so it catches Tab even when
// focus leaks to body (e.g. after sidebar-collapse layout shift at ≤768px).
// Template @keydown on backdrop only catches bubbling from children, not from body.
function onDocumentKeyDown(e: KeyboardEvent) {
  if (!props.open) return;
  onKeyDown(e);
}

onMounted(() => {
  document.addEventListener('keydown', onDocumentKeyDown);
});

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onDocumentKeyDown);
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
    const msg = (e as any)?.response?.data?.message || (e as any)?.message || t('common.error');
    errorMessage.value = msg;
  } finally {
    submitting.value = false;
  }
}

/**
 * Keep focus within the dialog when Tab or Shift+Tab is pressed.
 * Handler is bound on .cpd-dialog itself (not backdrop).
 */
function onKeyDown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    onCancel();
    return;
  }
  if (e.key !== 'Tab') return;
  // Handler is on document; always query the dialog from the DOM.
  const dialog = document.querySelector('.cpd-dialog') as HTMLElement | null;
  if (!dialog) return;
  const focusable = dialog.querySelectorAll<HTMLElement>(
    'input:not(:disabled), textarea:not(:disabled), button:not(:disabled), [tabindex]:not([tabindex="-1"])',
  );
  if (focusable.length === 0) return;
  const first = focusable[0]!;
  const last = focusable[focusable.length - 1]!;
  const idx = Array.prototype.indexOf.call(focusable, document.activeElement);

  // Always prevent the browser's default Tab — we manage focus manually.
  // The browser's natural tab order may skip elements outside the visible
  // viewport (e.g. cancel btn at narrow viewports ≤768px), leaking focus
  // to body and then to sidebar chrome.
  e.preventDefault();

  if (e.shiftKey) {
    if (idx <= 0) {
      last.focus();
    } else {
      focusable[idx - 1]!.focus();
    }
  } else {
    if (idx === -1 || document.activeElement === last) {
      first.focus();
    } else {
      focusable[idx + 1]!.focus();
    }
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
  z-index: var(--z-dropdown) 00;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-overlay-light);
  padding: var(--space-5);
}

.cpd-dialog {
  background: var(--color-surface);
  border-radius: var(--radius-2xl);
  padding: var(--space-8);
  width: 100%;
  max-width: 460px;
  box-shadow: var(--shadow-lg);
  animation: hfb-fade-in var(--transition-base) ease;
}

.cpd-header {
  margin-bottom: var(--space-6);
}

.cpd-title {
  font-size: var(--text-xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1-5);
}

.cpd-subtitle {
  font-size: var(--text-base);
  color: var(--color-text-muted);
  margin: 0;
}

.cpd-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4-5);
}

.cpd-field {
  display: flex;
  flex-direction: column;
  gap: var(--space-1-5);
}

.cpd-label {
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  color: var(--color-text-secondary);
}

.cpd-required {
  color: var(--color-error-text);
  margin-left: 2px;
}

.cpd-input {
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

.cpd-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring);
}

.cpd-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

textarea.cpd-input {
  resize: vertical;
}

.cpd-error {
  font-size: var(--text-sm);
  color: var(--color-error-text);
  padding: var(--space-2) var(--space-3);
  background: var(--color-error-bg);
  border-radius: var(--radius-md);
  line-height: 1.4;
}

.cpd-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-3);
  padding-top: 6px;
}

.cpd-btn {
  padding: var(--btn-padding-lg);
  border-radius: var(--btn-radius);
  font-size: var(--btn-font-lg);
  font-weight: var(--font-semibold);
  cursor: pointer;
  border: none;
  transition: all var(--transition-base);
}

.cpd-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.cpd-btn--primary {
  background: var(--color-accent);
  color: var(--color-surface);
}

.cpd-btn--primary:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.cpd-btn--primary:focus-visible:not(:disabled) {
  background: var(--color-accent-hover);
}

.cpd-btn--cancel {
  background: transparent;
  color: var(--color-text-secondary);
  border: 1px solid var(--color-border);
}

.cpd-btn--cancel:hover:not(:disabled) {
  background: var(--color-hover);
}

.cpd-btn--cancel:focus-visible:not(:disabled) {
  background: var(--color-hover);
}
</style>
