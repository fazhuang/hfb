<template>
  <nav class="wsn-nav" aria-label="研究工作流步骤">
    <ol class="wsn-steps" role="list">
      <li
        v-for="(step, idx) in steps"
        :key="idx"
        class="wsn-step"
        :class="{
          'wsn-step--current': idx === currentIndex,
          'wsn-step--completed': idx < currentIndex,
          'wsn-step--disabled': idx > currentIndex && !isStepClickable(idx),
        }"
      >
        <button
          v-if="isStepClickable(idx)"
          type="button"
          class="wsn-step-btn"
          :aria-current="idx === currentIndex ? 'step' : undefined"
          @click="$emit('go-to', idx)"
        >
          <span class="wsn-step-number" aria-hidden="true">
            <template v-if="idx < currentIndex">✓</template>
            <template v-else>{{ idx + 1 }}</template>
          </span>
          <span class="wsn-step-label">{{ step.label }}</span>
          <span v-if="idx < currentIndex" class="wsn-step-sr-status">已完成</span>
        </button>
        <span
          v-else
          class="wsn-step-text"
          :aria-current="idx === currentIndex ? 'step' : undefined"
        >
          <span class="wsn-step-number" aria-hidden="true">
            <template v-if="idx < currentIndex">✓</template>
            <template v-else>{{ idx + 1 }}</template>
          </span>
          <span class="wsn-step-label">{{ step.label }}</span>
          <span v-if="idx < currentIndex" class="wsn-step-sr-status">已完成</span>
        </span>
      </li>
    </ol>
  </nav>
</template>

<script setup lang="ts">
export interface WorkflowNavStep {
  label: string;
}

defineProps<{
  steps: WorkflowNavStep[];
  currentIndex: number;
  /** Steps 0 and 1 are user input steps and are always clickable */
  submitting?: boolean;
}>();

defineEmits<{
  'go-to': [index: number];
}>();

function isStepClickable(idx: number): boolean {
  // Step 0 (question) and 1 (selection) are always clickable
  // Steps 2+ are only clickable if they've been reached (completed)
  return idx <= 1;
}
</script>

<style scoped>
.wsn-nav {
  margin-bottom: 24px;
}

.wsn-steps {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  border-bottom: 2px solid var(--color-border, #e2e8f0);
}

.wsn-step {
  flex: 1;
  min-width: 0;
}

.wsn-step-btn,
.wsn-step-text {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 10px;
  width: 100%;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  font: inherit;
  font-size: 13px;
  cursor: default;
  transition: all 0.15s;
}

.wsn-step-btn {
  cursor: pointer;
  color: var(--color-text-secondary, #4a5568);
  background: transparent;
}

.wsn-step-btn:hover {
  color: var(--color-accent, #2b6cb0);
  background: var(--color-hover, #edf2f7);
}

.wsn-step-btn:focus-visible {
  color: var(--color-accent, #2b6cb0);
  background: var(--color-hover, #edf2f7);
}

.wsn-step-text {
  color: var(--color-text-muted, #a0aec0);
}

.wsn-step--current .wsn-step-btn,
.wsn-step--current .wsn-step-text {
  color: var(--color-accent, #2b6cb0);
  border-bottom-color: var(--color-accent, #2b6cb0);
  font-weight: 700;
}

.wsn-step--completed .wsn-step-btn,
.wsn-step--completed .wsn-step-text {
  color: var(--color-success-text);
  border-bottom-color: var(--color-success-text);
}

/* Visually hidden status text for screen readers */
.wsn-step-sr-status {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}

.wsn-step--disabled .wsn-step-text {
  color: var(--color-text-muted, #a0aec0);
}

.wsn-step-number {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  background: var(--color-page-bg, #fafafa);
  color: var(--color-text-muted, #a0aec0);
  border: 1px solid var(--color-border, #e2e8f0);
}

.wsn-step--current .wsn-step-number {
  background: var(--color-accent, #4299e1);
  color: #fff;
  border-color: var(--color-accent, #4299e1);
}

.wsn-step--completed .wsn-step-number {
  background: var(--color-success);
  color: #fff;
  border-color: var(--color-success);
}

.wsn-step-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 640px) {
  .wsn-step-btn,
  .wsn-step-text {
    flex-direction: column;
    gap: 4px;
    text-align: center;
    padding: 10px 6px;
  }

  .wsn-step-label {
    font-size: 11px;
  }
}
</style>
