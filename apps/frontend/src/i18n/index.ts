import { createI18n } from 'vue-i18n';
import zhCN from './locales/zh-CN';
import en from './locales/en';

export type SupportedLocale = 'zh-CN' | 'en';

export const SUPPORTED_LOCALES: Array<SupportedLocale> = ['zh-CN', 'en'];
export const DEFAULT_LOCALE: SupportedLocale = 'zh-CN';

export function detectBrowserLocale(): SupportedLocale {
  const nav = typeof navigator !== 'undefined' ? navigator.language : 'zh-CN';
  if (nav.startsWith('zh')) return 'zh-CN';
  if (SUPPORTED_LOCALES.includes(nav as SupportedLocale)) return nav as SupportedLocale;
  return DEFAULT_LOCALE;
}

function loadLocale(): SupportedLocale {
  try {
    const stored = localStorage.getItem('hfb-locale');
    if (stored && SUPPORTED_LOCALES.includes(stored as SupportedLocale)) {
      return stored as SupportedLocale;
    }
  } catch {
    // localStorage may be unavailable
  }
  return detectBrowserLocale();
}

const i18n = createI18n({
  legacy: false,
  locale: loadLocale(),
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    en,
  },
});

export function setLocale(locale: SupportedLocale): void {
  i18n.global.locale.value = locale;
  try {
    localStorage.setItem('hfb-locale', locale);
  } catch {
    // ignore
  }
}

export default i18n;
