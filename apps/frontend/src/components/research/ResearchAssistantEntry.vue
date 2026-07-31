<template>
  <aside class="rae-sidebar" aria-labelledby="rae-heading">
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

<script setup lang="ts">
/**
 * ResearchAssistantEntry — AI 研究助手入口
 *
 * Does NOT call any AI API. Collects a research question and navigates
 * to the workflow page. The question is passed via sessionStorage to
 * avoid leaking it in the URL.
 *
 * If sessionStorage is unavailable (SSR or restricted context), falls
 * back to navigation without the question.
 *
 * ref: docs/20-product/2013-research-workspace-migration.md
 */
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const props = defineProps<{
  projectId: string;
}>();

const router = useRouter();
const question = ref('');
const submitting = ref(false);

const STORAGE_KEY = `hfb.research.${props.projectId}.pending-question`;

function onSubmit() {
  const q = question.value;
  if (!q) return;

  submitting.value = true;

  try {
    sessionStorage.setItem(STORAGE_KEY, q);
  } catch {
    // sessionStorage unavailable — navigate without question
  }

  router.push(`/research/${props.projectId}/workflow`);
}
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

.rae-sidebar {
  /* Inherits parent sidebar styling */
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
</style>
