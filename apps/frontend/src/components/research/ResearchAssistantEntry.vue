<template>
  <!-- Inline mode: embedded form (no sidebar/sheet chrome) -->
  <template v-if="mode === 'inline'">
    <form class="rae-inline-form" @submit.prevent="onSubmit">
      <label for="rae-question-input-inline" class="sr-only">研究问题</label>
      <div class="rae-inline-row">
        <input
          id="rae-question-input-inline"
          ref="inlineInputRef"
          v-model.trim="question"
          type="text"
          class="rae-inline-input"
          placeholder="输入您的研究问题..."
          :disabled="submitting"
          autocomplete="off"
        />
        <button type="submit" class="rae-inline-btn" :disabled="!question || submitting">
          开始研究
        </button>
      </div>
    </form>
  </template>

  <!-- Sidebar mode: desktop collapsible sidebar -->
  <template v-else-if="mode === 'sidebar'">
    <button
      class="rae-sidebar-toggle"
      :aria-expanded="sidebarOpen"
      :aria-controls="sidebarId"
      @click="sidebarOpen = !sidebarOpen"
    >
      <span class="rae-toggle-label">AI 助手</span>
      <span class="rae-toggle-icon" aria-hidden="true">{{ sidebarOpen ? '◀' : '▶' }}</span>
    </button>

    <aside
      v-if="sidebarOpen"
      :id="sidebarId"
      class="rae-sidebar"
      aria-labelledby="rae-heading"
    >
      <h2 id="rae-heading" class="rae-heading">AI 研究助手</h2>
      <p class="rae-description">输入研究问题，进入研究工作流进行系统研究。</p>

      <form class="rae-form" @submit.prevent="onSubmit">
        <label for="rae-question-input" class="sr-only">研究问题</label>
        <input
          id="rae-question-input"
          v-model.trim="question"
          type="text"
          class="rae-input"
          placeholder="输入您的研究问题..."
          :disabled="submitting"
          autocomplete="off"
        />
        <button type="submit" class="rae-submit-btn" :disabled="!question || submitting">
          开始研究
        </button>
      </form>

      <p class="rae-hint">问题将通过安全机制传入研究流程，不会直接调用 AI。</p>
    </aside>
  </template>

  <!-- Sheet mode: mobile slide-up panel -->
  <template v-else-if="mode === 'sheet'">
    <button
      class="rae-sheet-toggle"
      :aria-expanded="sheetOpen"
      aria-controls="rae-sheet"
      @click="openSheet"
    >
      <span>AI 助手</span>
    </button>

    <Teleport to="body">
      <div v-if="sheetOpen" class="rae-sheet-backdrop" @click="closeSheet" />
      <div
        v-if="sheetOpen"
        id="rae-sheet"
        ref="sheetRef"
        class="rae-sheet"
        role="dialog"
        aria-modal="true"
        aria-label="AI 研究助手"
        @keydown="onSheetKeydown"
      >
        <div class="rae-sheet-header">
          <h2 class="rae-heading">AI 研究助手</h2>
          <button class="rae-sheet-close" aria-label="关闭" @click="closeSheet">&times;</button>
        </div>
        <p class="rae-description">输入研究问题，进入研究工作流进行系统研究。</p>

        <form class="rae-form" @submit.prevent="onSheetSubmit">
          <label for="rae-sheet-input" class="sr-only">研究问题</label>
          <input
            id="rae-sheet-input"
            ref="sheetInputRef"
            v-model.trim="question"
            type="text"
            class="rae-input"
            placeholder="输入您的研究问题..."
            :disabled="submitting"
            autocomplete="off"
          />
          <button type="submit" class="rae-submit-btn" :disabled="!question || submitting">
            开始研究
          </button>
        </form>
      </div>
    </Teleport>
  </template>
</template>

<script setup lang="ts">
import { ref, onBeforeUnmount, nextTick, watch } from 'vue';
import { useRouter } from 'vue-router';

type RAEIMode = 'inline' | 'sidebar' | 'sheet';

const props = withDefaults(defineProps<{
  projectId: string;
  mode?: RAEIMode;
}>(), {
  mode: 'sidebar',
});

const router = useRouter();
const question = ref('');
const submitting = ref(false);

const sidebarOpen = ref(false);

const sheetOpen = ref(false);
const sheetRef = ref<HTMLElement | null>(null);
const sheetInputRef = ref<HTMLInputElement | null>(null);
const inlineInputRef = ref<HTMLInputElement | null>(null);

const STORAGE_KEY = `hfb.research.${props.projectId}.pending-question`;
const sidebarId = `rae-sidebar-${props.projectId}`;

let previousSheetFocus: HTMLElement | null = null;

const TABBABLE = 'input:not([disabled]), button:not([disabled]), [tabindex]:not([tabindex="-1"])';

function onSubmit() {
  const q = question.value;
  if (!q) return;
  submitting.value = true;
  try { sessionStorage.setItem(STORAGE_KEY, q); } catch { /* unavailable */ }
  router.push(`/research/${props.projectId}/workflow`);
}

function onSheetSubmit() {
  const q = question.value;
  if (!q) return;
  submitting.value = true;
  try { sessionStorage.setItem(STORAGE_KEY, q); } catch { /* unavailable */ }
  closeSheetForNavigation();
  router.push(`/research/${props.projectId}/workflow`);
}

function openSheet() {
  previousSheetFocus = document.activeElement as HTMLElement;
  sheetOpen.value = true;
  document.body.style.overflow = 'hidden';
  nextTick(() => {
    sheetInputRef.value?.focus();
  });
}

function closeSheet() {
  sheetOpen.value = false;
  document.body.style.overflow = '';
  if (previousSheetFocus && typeof previousSheetFocus.focus === 'function') {
    previousSheetFocus.focus();
  }
}

function closeSheetForNavigation() {
  sheetOpen.value = false;
  document.body.style.overflow = '';
}

function onSheetKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') {
    e.preventDefault();
    closeSheet();
    return;
  }
  if (e.key === 'Tab') {
    const sheet = sheetRef.value;
    if (!sheet) return;
    const focusable = sheet.querySelectorAll<HTMLElement>(TABBABLE);
    if (focusable.length === 0) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (first && last) {
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  }
}

// Cleanup sheet scroll lock on unmount
onBeforeUnmount(() => {
  document.body.style.overflow = '';
  sheetOpen.value = false;
});

// Re-focus input when sheet opens (watch for mode/projectId changes)
watch(sheetOpen, (open) => {
  if (open) {
    nextTick(() => sheetInputRef.value?.focus());
  }
});
</script>

<style scoped>
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* ---- Inline ---- */
.rae-inline-form {
  width: 100%;
}

.rae-inline-row {
  display: flex;
  gap: var(--space-2);
}

.rae-inline-input {
  flex: 1;
  padding: var(--space-2-5) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  color: var(--color-text-primary);
  background: var(--color-surface);
  box-sizing: border-box;
  transition: border-color var(--transition-base);
}

.rae-inline-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring-sm);
}

.rae-inline-input::placeholder {
  color: var(--color-text-muted);
}

.rae-inline-btn {
  padding: var(--space-2-5) var(--space-4);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  cursor: pointer;
  background: var(--color-accent);
  color: var(--color-surface);
  white-space: nowrap;
}

.rae-inline-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.rae-inline-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* ---- Sidebar toggle ---- */
.rae-sidebar-toggle {
  position: absolute;
  right: 0;
  top: var(--space-4);
  display: flex;
  align-items: center;
  gap: var(--space-1);
  padding: var(--space-1-5) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  cursor: pointer;
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.rae-toggle-label {
  font-weight: var(--font-medium);
}

.rae-toggle-icon {
  font-size: 11px;
}

/* ---- Sidebar content ---- */
.rae-sidebar {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid var(--color-border);
  padding-left: var(--space-6);
}

.rae-heading {
  font-size: var(--text-lg);
  font-weight: var(--font-semibold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-3);
}

.rae-description {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
  margin: 0 0 var(--space-4);
  line-height: var(--leading-normal);
}

.rae-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.rae-input {
  width: 100%;
  padding: var(--space-2-5) var(--space-3);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  color: var(--color-text-primary);
  background: var(--color-surface);
  box-sizing: border-box;
  transition: border-color var(--transition-base);
}

.rae-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--focus-ring-sm);
}

.rae-input::placeholder {
  color: var(--color-text-muted);
}

.rae-submit-btn {
  padding: var(--space-2-5) var(--space-4);
  border: none;
  border-radius: var(--radius-lg);
  font-size: var(--text-base);
  font-weight: var(--font-semibold);
  cursor: pointer;
  background: var(--color-accent);
  color: var(--color-surface);
  transition: background var(--transition-base);
  display: flex;
  align-items: center;
  justify-content: center;
}

.rae-submit-btn:hover:not(:disabled) {
  background: var(--color-accent-hover);
}

.rae-submit-btn:focus-visible:not(:disabled) {
  background: var(--color-accent-hover);
}

.rae-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.rae-hint {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin: var(--space-3) 0 0;
  line-height: 1.4;
}

/* ---- Sheet toggle ---- */
.rae-sheet-toggle {
  display: none;
  padding: var(--space-2) var(--space-4);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-accent);
  font-size: var(--text-sm);
  font-weight: var(--font-semibold);
  cursor: pointer;
  margin-top: var(--space-4);
}

/* ---- Sheet panel ---- */
.rae-sheet-backdrop {
  position: fixed;
  inset: 0;
  background: var(--color-overlay-light);
  z-index: var(--z-dialog);
}

.rae-sheet {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-height: 60vh;
  background: var(--color-surface);
  border-radius: var(--radius-lg) var(--radius-lg) 0 0;
  z-index: var(--z-drawer);
  padding: var(--space-4) var(--space-5);
  overflow-y: auto;
  animation: rae-sheet-slide-up 300ms var(--ease-in-out);
}

@keyframes rae-sheet-slide-up {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

@media (prefers-reduced-motion: reduce) {
  .rae-sheet {
    animation: none;
  }
}

.rae-sheet-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-2);
}

.rae-sheet-close {
  border: none;
  background: transparent;
  font-size: var(--text-xl);
  cursor: pointer;
  color: var(--color-text-muted);
  padding: 0;
  line-height: 1;
}

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .rae-sidebar-toggle {
    display: none;
  }

  .rae-sheet-toggle {
    display: inline-flex;
  }
}
</style>

<style>
/* Unscoped: Teleported sheet backdrop needs unscoped */
.rae-sheet-backdrop {
  position: fixed;
  inset: 0;
  background: var(--color-overlay-light);
  z-index: var(--z-dialog);
}
</style>
