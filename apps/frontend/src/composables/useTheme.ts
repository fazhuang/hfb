import { ref, watchEffect } from 'vue';

export type Theme = 'light' | 'dark' | 'auto';

const THEME_STORAGE_KEY = 'hfb-theme';
const DARK_CLASS = 'dark';

const theme = ref<Theme>(loadTheme());

function loadTheme(): Theme {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'auto') {
      return stored;
    }
  } catch {
    // localStorage unavailable
  }
  return 'auto';
}

function resolveTheme(value: Theme): 'light' | 'dark' {
  if (value === 'auto') {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }
  return value;
}

export function useTheme() {
  watchEffect(() => {
    const resolved = resolveTheme(theme.value);
    document.documentElement.classList.toggle(DARK_CLASS, resolved === 'dark');
  });

  function setTheme(value: Theme): void {
    theme.value = value;
    try {
      localStorage.setItem(THEME_STORAGE_KEY, value);
    } catch {
      // ignore
    }
  }

  return {
    theme,
    setTheme,
  };
}

/**
 * Watch system preference changes when theme is 'auto'
 */
if (typeof window !== 'undefined') {
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (theme.value === 'auto') {
      // Force reactivity by re-setting
      document.documentElement.classList.toggle(
        DARK_CLASS,
        window.matchMedia('(prefers-color-scheme: dark)').matches,
      );
    }
  });
}
