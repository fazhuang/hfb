<template>
  <section class="dss-step" aria-labelledby="dss-heading">
    <h2 id="dss-heading" class="dss-heading">第二步：文献选择</h2>

    <div class="dss-system-notice" role="note">
      <span class="dss-notice-icon" aria-hidden="true">ℹ️</span>
      <p>
        系统将根据您的研究问题自动检索相关文献。当前版本不支持手动选择特定文献，所有可检索到的相关文献都将纳入分析范围。
      </p>
    </div>

    <div class="dss-summary">
      <h3 class="dss-summary-title">研究问题</h3>
      <p class="dss-summary-text">{{ question }}</p>
    </div>

    <div class="dss-actions">
      <button
        type="button"
        class="dss-back-btn"
        :disabled="disabled"
        @click="$emit('back')"
      >
        返回修改问题
      </button>
      <button
        type="button"
        class="dss-submit-btn"
        :disabled="disabled"
        @click="$emit('submit')"
      >
        开始分析
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
defineProps<{
  question: string;
  disabled?: boolean;
}>();

defineEmits<{
  back: [];
  submit: [];
}>();
</script>

<style scoped>
.dss-step {
  padding: 0;
}

.dss-heading {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-4);
}

.dss-system-notice {
  display: flex;
  gap: var(--space-2-5);
  padding: var(--space-3-5) 16px;
  border: 1px solid var(--color-accent);
  border-left: 4px solid var(--color-accent);
  border-radius: var(--radius-md);
  background: var(--color-accent-light);
  margin-bottom: 24px;
}

.dss-notice-icon {
  font-size: 16px;
  flex-shrink: 0;
  margin-top: 1px;
}

.dss-system-notice p {
  margin: 0;
  font-size: 13px;
  color: var(--color-accent);
  line-height: 1.6;
}

.dss-summary {
  padding: var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  background: var(--color-page-bg);
  margin-bottom: 24px;
}

.dss-summary-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  margin: 0 0 var(--space-2);
}

.dss-summary-text {
  font-size: 15px;
  color: var(--color-text-primary);
  margin: 0;
  line-height: 1.6;
}

.dss-actions {
  display: flex;
  gap: var(--space-3);
  align-items: center;
}

.dss-back-btn {
  padding: var(--space-2-5) 20px;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: var(--color-navbar-bg, var(--color-surface));
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
}

.dss-back-btn:hover:not(:disabled) {
  background: var(--color-hover);
}

.dss-back-btn:focus-visible:not(:disabled) {
  background: var(--color-hover);
}

.dss-back-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dss-submit-btn {
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

.dss-submit-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, var(--color-info));
}

.dss-submit-btn:focus-visible:not(:disabled) {
  background: var(--color-accent-hover, var(--color-info));
}

.dss-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
