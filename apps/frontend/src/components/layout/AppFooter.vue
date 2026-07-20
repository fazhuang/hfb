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
  padding: var(--space-4) var(--space-6);
  border-top: 1px solid var(--color-border);
  background: var(--color-footer-bg);
  text-align: center;
  margin-top: auto;
}

.footer-inner {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  flex-wrap: wrap;
}

.footer-text {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
}

.footer-divider {
  color: var(--color-text-muted);
  font-size: var(--text-xs);
}
</style>
