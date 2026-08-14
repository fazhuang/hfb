<template>
  <div class="placeholder-page">
    <HfbIcon icon="book-open" :size="56" class="placeholder-icon" />
    <h2 class="placeholder-title">{{ t('nav.documents') }}</h2>
    <p class="placeholder-desc">{{ $t('onboarding.comingSoon') }}</p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';
import HfbIcon from '@/components/common/HfbIcon.vue';
const { t } = useI18n();
</script>

<style scoped>
.placeholder-page {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-20) 24px;
  text-align: center;
  flex: 1;
}

.placeholder-icon {
  margin-bottom: 16px;
  opacity: 0.6;
}

.placeholder-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.placeholder-desc {
  font-size: 14px;
  color: var(--color-text-muted);
  max-width: 400px;
  margin: 0;
}
</style>
