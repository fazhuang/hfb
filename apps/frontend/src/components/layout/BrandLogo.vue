<template>
  <span class="brand-logo">
    <span
      class="brand-logo__icon"
      :style="{ width: `${size}px`, height: `${size}px` }"
      aria-hidden="true"
    >
      <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
        <rect x="3" y="3" width="42" height="42" rx="11" fill="none" stroke="currentColor" stroke-width="2.5" />
        <line x1="15" y1="19" x2="33" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        <line x1="15" y1="26" x2="33" y2="26" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
        <line x1="24" y1="11" x2="24" y2="37" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
        <circle cx="24" cy="11" r="3" fill="currentColor" />
      </svg>
    </span>
    <span v-if="!collapsed" class="brand-logo__text">
      <span v-if="locale === 'zh-CN'" class="brand-logo__title">
        <span class="brand-logo__main">皇甫谧</span><span class="brand-logo__sub">数字人文平台</span>
      </span>
      <span v-else class="brand-logo__title">{{ t('system.title') }}</span>
      <span v-if="showSubtitle" class="brand-logo__subtitle">{{ t('system.subtitle') }}</span>
    </span>
  </span>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n';

const { t, locale } = useI18n();

withDefaults(
  defineProps<{
    /** Icon size in px */
    size?: number;
    /** Hide the text block (used by collapsed sidebar) */
    collapsed?: boolean;
    /** Show the uppercase latin subtitle below the title */
    showSubtitle?: boolean;
  }>(),
  {
    size: 34,
    collapsed: false,
    showSubtitle: false,
  },
);
</script>

<style scoped>
.brand-logo {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-primary);
}

.brand-logo__icon {
  flex-shrink: 0;
  color: var(--color-accent);
}

.brand-logo__icon svg {
  width: 100%;
  height: 100%;
  display: block;
}

.brand-logo__text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-logo__title {
  font-family: var(--font-serif);
  font-weight: var(--font-bold);
  font-size: 17px;
  white-space: nowrap;
  letter-spacing: 0.06em;
  color: var(--color-text-primary);
}

.brand-logo__main {
  font-size: 1.15em;
  margin-right: 0.35em;
}

.brand-logo__sub {
  font-size: 0.72em;
  font-weight: var(--font-medium);
  letter-spacing: 0.04em;
  color: var(--color-text-secondary);
}

.brand-logo__subtitle {
  font-family: 'HfbLatin', 'Cormorant Garamond', 'Georgia', serif;
  font-weight: var(--font-semibold);
  font-size: 10px;
  color: var(--color-text-muted);
  white-space: nowrap;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}
</style>
