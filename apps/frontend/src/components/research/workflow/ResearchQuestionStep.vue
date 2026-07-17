<template>
  <section class="rqs-step" aria-labelledby="rqs-heading">
    <h2 id="rqs-heading" class="rqs-heading">第一步：研究问题</h2>

    <p class="rqs-description">
      请输入您的研究问题。系统将自动检索相关文献并生成研究报告。
    </p>

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
        <button
          type="submit"
          class="rqs-submit-btn"
          :disabled="disabled || !question.trim()"
        >
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
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 8px;
}

.rqs-description {
  font-size: 14px;
  color: var(--color-text-muted, #718096);
  margin: 0 0 24px;
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
  color: var(--color-text-secondary, #4a5568);
}

.rqs-label span {
  color: #c53030;
}

.rqs-input {
  width: 100%;
  padding: 10px 14px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 15px;
  color: var(--color-text-primary, #1a365d);
  background: var(--color-navbar-bg, #fff);
  box-sizing: border-box;
  transition: border-color 0.15s;
}

.rqs-input:focus {
  outline: none;
  border-color: var(--color-accent, #4299e1);
  box-shadow: 0 0 0 2px rgba(66, 153, 225, 0.15);
}

.rqs-input--error {
  border-color: #c53030;
}

.rqs-input:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.rqs-error {
  margin: 6px 0 0;
  font-size: 13px;
  color: #c53030;
}

.rqs-submit-btn {
  padding: 10px 24px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: var(--color-accent, #4299e1);
  color: #fff;
  transition: background 0.15s;
}

.rqs-submit-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, #3182ce);
}

.rqs-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
