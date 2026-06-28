<template>
  <nav class="app-navbar" role="navigation" aria-label="Main navigation">
    <div class="navbar-brand">
      <router-link to="/" class="brand-link">
        <span class="brand-icon">📜</span>
        <span class="brand-text">{{ t('system.title') }}</span>
      </router-link>
    </div>

    <button
      class="mobile-menu-toggle"
      :aria-expanded="menuOpen"
      aria-label="Toggle navigation menu"
      @click="menuOpen = !menuOpen"
    >
      <span class="hamburger" :class="{ open: menuOpen }"></span>
    </button>

    <ul class="navbar-links" :class="{ open: menuOpen }">
      <li v-for="item in navItems" :key="item.path">
        <router-link
          :to="item.path"
          class="nav-link"
          active-class="nav-link--active"
          @click="menuOpen = false"
        >
          <span class="nav-icon">{{ item.icon }}</span>
          {{ t(item.labelKey) }}
        </router-link>
      </li>
    </ul>

    <div class="navbar-actions">
      <!-- Auth -->
      <template v-if="auth.isAuthenticated">
        <span class="user-greeting">{{ auth.userName }}</span>
        <button class="auth-btn" @click="logout">{{ t('auth.logout') }}</button>
      </template>
      <template v-else>
        <router-link :to="{ name: 'login' }" class="auth-link">{{ t('auth.login') }}</router-link>
      </template>

      <!-- Locale Switcher -->
      <div class="locale-switcher">
        <button
          v-for="loc in locales"
          :key="loc"
          class="locale-btn"
          :class="{ active: locale === loc }"
          @click="switchLocale(loc)"
        >
          {{ loc === 'zh-CN' ? '中' : 'EN' }}
        </button>
      </div>

      <!-- Theme Toggle -->
      <button class="theme-toggle" :aria-label="t('theme.dark')" @click="cycleTheme">
        <span v-if="resolvedTheme === 'light'">☀️</span>
        <span v-else>🌙</span>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useTheme } from '@/composables/useTheme';
import { setLocale, SUPPORTED_LOCALES, type SupportedLocale } from '@/i18n';
import type { Theme } from '@/composables/useTheme';
import { useAuthStore } from '@/stores/auth';

const { t, locale } = useI18n();
const { theme, setTheme } = useTheme();
const auth = useAuthStore();
const router = useRouter();

const menuOpen = ref(false);

const navItems = [
  { path: '/', icon: '🏠', labelKey: 'nav.home' },
  { path: '/books', icon: '📚', labelKey: 'nav.books' },
  { path: '/persons', icon: '👤', labelKey: 'nav.persons' },
  { path: '/research', icon: '校', labelKey: 'nav.research' },
  { path: '/graph', icon: '🔗', labelKey: 'nav.graph' },
  { path: '/workspace', icon: '🧪', labelKey: 'nav.workspace' },
  { path: '/search', icon: '🔍', labelKey: 'nav.search' },
  { path: '/about', icon: 'ℹ️', labelKey: 'nav.about' },
] as const;

const locales = SUPPORTED_LOCALES;

const resolvedTheme = computed(() => {
  if (theme.value === 'auto') {
    if (typeof window !== 'undefined' && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  }
  return theme.value;
});

function switchLocale(loc: SupportedLocale) {
  setLocale(loc);
}

function logout() {
  auth.logout();
  router.push({ name: 'home' });
}

const themeCycle: Array<Theme> = ['light', 'dark', 'auto'];
let themeIndex = themeCycle.indexOf(theme.value);

function cycleTheme() {
  themeIndex = (themeIndex + 1) % themeCycle.length;
  setTheme(themeCycle[themeIndex]!);
}
</script>

<style scoped>
/* (existing styles unchanged) */
.app-navbar {
  display: flex;
  align-items: center;
  padding: 0 24px;
  height: 56px;
  background: var(--color-navbar-bg, #ffffff);
  border-bottom: 1px solid var(--color-border, #e2e8f0);
  position: sticky;
  top: 0;
  z-index: 100;
  gap: 24px;
}

.navbar-brand {
  flex-shrink: 0;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--color-text-primary, #1a365d);
}

.brand-icon {
  font-size: 22px;
}

.brand-text {
  font-size: 16px;
  font-weight: 700;
  white-space: nowrap;
}

.navbar-links {
  display: flex;
  list-style: none;
  gap: 4px;
  margin: 0;
  padding: 0;
  flex: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border-radius: 6px;
  text-decoration: none;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
  transition: all 0.15s;
}

.nav-link:hover {
  background: var(--color-hover, #edf2f7);
  color: var(--color-text-primary, #1a365d);
}

.nav-link--active {
  background: var(--color-active, #ebf8ff);
  color: var(--color-accent, #2b6cb0);
  font-weight: 600;
}

.nav-icon {
  font-size: 16px;
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.user-greeting {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
}

.auth-link,
.auth-btn {
  font-size: 13px;
  text-decoration: none;
  color: var(--color-accent, #2b6cb0);
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--color-accent, #2b6cb0);
  background: transparent;
  cursor: pointer;
  transition: all 0.15s;
}

.auth-link:hover,
.auth-btn:hover {
  background: var(--color-accent, #2b6cb0);
  color: white;
}

.locale-switcher {
  display: flex;
  border-radius: 6px;
  overflow: hidden;
  border: 1px solid var(--color-border, #e2e8f0);
}

.locale-btn {
  padding: 4px 10px;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  color: var(--color-text-secondary, #4a5568);
  transition: all 0.15s;
}

.locale-btn.active {
  background: var(--color-accent, #2b6cb0);
  color: #fff;
}

.locale-btn:not(.active):hover {
  background: var(--color-hover, #edf2f7);
}

.theme-toggle {
  padding: 6px 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 18px;
  border-radius: 6px;
  transition: background 0.15s;
}

.theme-toggle:hover {
  background: var(--color-hover, #edf2f7);
}

.mobile-menu-toggle {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
}

.hamburger {
  display: block;
  width: 20px;
  height: 2px;
  background: var(--color-text-primary, #1a365d);
  position: relative;
  transition: background 0.2s;
}

.hamburger::before,
.hamburger::after {
  content: '';
  display: block;
  width: 20px;
  height: 2px;
  background: var(--color-text-primary, #1a365d);
  position: absolute;
  transition: transform 0.2s;
}

.hamburger::before {
  top: -6px;
}

.hamburger::after {
  top: 6px;
}

.hamburger.open {
  background: transparent;
}

.hamburger.open::before {
  transform: rotate(45deg);
  top: 0;
}

.hamburger.open::after {
  transform: rotate(-45deg);
  top: 0;
}

@media (max-width: 768px) {
  .app-navbar {
    padding: 0 16px;
    height: 52px;
  }

  .mobile-menu-toggle {
    display: block;
    margin-left: auto;
  }

  .navbar-links {
    display: none;
    position: absolute;
    top: 52px;
    left: 0;
    right: 0;
    flex-direction: column;
    background: var(--color-navbar-bg, #ffffff);
    border-bottom: 1px solid var(--color-border, #e2e8f0);
    padding: 8px;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  }

  .navbar-links.open {
    display: flex;
  }
}
</style>
