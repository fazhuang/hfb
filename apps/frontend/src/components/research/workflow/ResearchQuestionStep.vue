<template>
  <section class="rqs-step" aria-labelledby="rqs-heading">
    <h2 id="rqs-heading" class="rqs-heading">第一步：研究问题</h2>

    <p class="rqs-description">请输入您的研究问题。系统将自动检索相关文献并生成研究报告。</p>

    <form class="rqs-form" @submit.prevent="$emit('next')">
      <div class="rqs-field">
        <label for="rqs-input" class="rqs-label">研究问题 <span aria-hidden="true">*</span></label>
        <input
          id="rqs-input"
          :value="question"
          type="text"
          class="rqs-input"
          :class="{ 'rqs-input--error': error }"
          placeholder="例如：针灸甲乙经中关于经络的论述"
          :disabled="disabled"
          :aria-invalid="!!error"
          :aria-describedby="error ? 'rqs-error' : undefined"
          autocomplete="off"
          @input="$emit('update:question', ($event.target as HTMLInputElement).value)"
        />
        <p v-if="error" id="rqs-error" class="rqs-error" role="alert">{{ error }}</p>
      </div>

      <div class="rqs-actions">
        <button type="submit" class="rqs-submit-btn" :disabled="disabled || !question.trim()">
          下一步：文献选择
        </button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  question: string;
  disabled?: boolean;
  error?: string;
}>();

defineEmits<{
  'update:question': [value: string];
  next: [];
}>();
</script>

<style scoped>
.rqs-step {
  padding: 0;
}

.rqs-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.rqs-description {
  font-size: 14px;
  color: var(--color-text-muted);
  margin: 0 0 var(--space-6);
  line-height: 1.5;
}

.rqs-form {
  max-width: 640px;
}

.rqs-field {
  margin-bottom: 20px;
}

.rqs-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.rqs-label span {
  color: var(--color-error-text);
}

.rqs-input {
  width: 100%;
  padding: var(--space-2-5) 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 15px;
  color: var(--color-text-primary);
  background: var(--color-navbar-bg, var(--color-surface));
  box-sizing: border-box;
  transition: border-color var(--transition-base);
}

.rqs-input:focus {
  outline: none;
  border-color: var(--color-accent);
  box-shadow: var(--shadow-focus-sm);
}

.rqs-input--error {
  border-color: var(--color-error-text);
}

.rqs-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.rqs-error {
  margin: var(--space-1-5) 0 0;
  font-size: 13px;
  color: var(--color-error-text);
}

.rqs-submit-btn {
  padding: var(--space-2-5) 24px;
  border: none;
  border-radius: var(--radius-lg);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: var(--color-accent);
  color: var(--color-surface);
  transition: background var(--transition-base);
}

.rqs-submit-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, var(--color-info));
}

.rqs-submit-btn:focus-visible:not(:disabled) {
  background: var(--color-accent-hover, var(--color-info));
}

.rqs-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .rqs-submit-btn {
    width: 100%;
  }
}
</style>
