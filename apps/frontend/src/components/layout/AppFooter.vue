<template>
  <footer class="app-footer">
    <div class="footer-inner">
      <span class="footer-text">{{ t('footer.copyright') }}</span>
      <span class="footer-divider">·</span>
      <span class="footer-text">{{ t('footer.license') }}</span>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
const { t } = useI18n();
</script>

<style scoped>
.app-footer {
  padding: 16px 24px;
  border-top: 1px solid var(--color-border, #e2e8f0);
  background: var(--color-footer-bg, #f8fafc);
  text-align: center;
  margin-top: auto;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.footer-text {
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.footer-divider {
  color: var(--color-text-muted, #a0aec0);
  font-size: 12px;
}
</style>
