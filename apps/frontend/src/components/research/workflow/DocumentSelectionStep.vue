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
  color: var(--color-text-primary, #1a365d);
  margin: 0 0 16px;
}

.dss-system-notice {
  display: flex;
  gap: 10px;
  padding: 14px 16px;
  border: 1px solid #4299e1;
  border-left: 4px solid #4299e1;
  border-radius: 6px;
  background: #ebf8ff;
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
  color: #2b6cb0;
  line-height: 1.6;
}

.dss-summary {
  padding: 16px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  background: var(--color-page-bg, #fafafa);
  margin-bottom: 24px;
}

.dss-summary-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-muted, #a0aec0);
  text-transform: uppercase;
  margin: 0 0 8px;
}

.dss-summary-text {
  font-size: 15px;
  color: var(--color-text-primary, #1a365d);
  margin: 0;
  line-height: 1.6;
}

.dss-actions {
  display: flex;
  gap: 12px;
  align-items: center;
}

.dss-back-btn {
  padding: 10px 20px;
  border: 1px solid var(--color-border, #e2e8f0);
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  background: var(--color-navbar-bg, #fff);
  color: var(--color-text-secondary, #4a5568);
  transition: all 0.15s;
}

.dss-back-btn:hover:not(:disabled) {
  background: var(--color-hover, #edf2f7);
}

.dss-back-btn:focus-visible:not(:disabled) {
  background: var(--color-hover, #edf2f7);
}

.dss-back-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.dss-submit-btn {
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

.dss-submit-btn:hover:not(:disabled) {
  background: var(--color-accent-hover, #3182ce);
}

.dss-submit-btn:focus-visible:not(:disabled) {
  background: var(--color-accent-hover, #3182ce);
}

.dss-submit-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
