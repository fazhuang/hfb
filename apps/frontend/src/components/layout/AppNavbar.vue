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
          :class="{ 'nav-link--pulse': item.pulse }"
          active-class="nav-link--active"
          :title="item.pulse ? t('onboarding.pulseStartResearch') : undefined"
          @click="menuOpen = false; showResearchPulse = false"
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
      <div class="locale-switcher" :title="t('onboarding.localeTooltip')">
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
      <button class="theme-toggle" :aria-label="t('theme.dark')" :title="t('onboarding.themeTooltip')" @click="cycleTheme">
        <span v-if="resolvedTheme === 'light'">☀️</span>
        <span v-else>🌙</span>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter } from 'vue-router';
import { useTheme } from '@/composables/useTheme';
import { setLocale, SUPPORTED_LOCALES, type SupportedLocale } from '@/i18n';
import type { Theme } from '@/composables/useTheme';
import { useAuthStore } from '@/stores/auth';
import { useResearchStore } from '@/stores/research';

const { t, locale } = useI18n();
const { theme, setTheme } = useTheme();
const auth = useAuthStore();
const researchStore = useResearchStore();
const router = useRouter();

const menuOpen = ref(false);

// P2: Pulse animation on "Start Research" nav link — runs 5 cycles then stops
const showResearchPulse = ref(auth.isAuthenticated && !researchStore.hasActiveResearch);

onMounted(() => {
  if (showResearchPulse.value) {
    setTimeout(() => { showResearchPulse.value = false; }, 5000); // 5 cycles ≈ 5s
  }
});

interface NavItem {
  path: string;
  icon: string;
  labelKey: string;
  pulse?: boolean;
}

const navItems = computed<NavItem[]>(() => {
  const base: NavItem[] = [
    { path: '/', icon: '🏠', labelKey: 'nav.home' },
  ];

  // Research entry: shown as primary action right after Home
  if (auth.isAuthenticated) {
    if (researchStore.hasActiveResearch) {
      base.push({ path: '/research/home', icon: '🔬', labelKey: 'nav.currentResearch' });
    } else {
      base.push({ path: '/research/new', icon: '🔬', labelKey: 'nav.startResearch', pulse: showResearchPulse.value });
    }
  }

  base.push(
    { path: '/books', icon: '📚', labelKey: 'nav.books' },
    { path: '/literature', icon: '📄', labelKey: 'nav.literature' },
    { path: '/classical-versions', icon: '🏛️', labelKey: 'nav.classicalVersions' },
    { path: '/persons', icon: '👤', labelKey: 'nav.persons' },
    { path: '/research/workspace?tab=research', icon: '校', labelKey: 'nav.research' },
    { path: '/research/workspace?tab=v4-research', icon: '🧬', labelKey: 'nav.v4Research' },
    { path: '/graph', icon: '🔗', labelKey: 'nav.graph' },
    { path: '/research/workspace', icon: '🧪', labelKey: 'nav.workspace' },
    { path: '/search', icon: '🔍', labelKey: 'nav.search' },
    { path: '/about', icon: 'ℹ️', labelKey: 'nav.about' },
  );
  if (auth.canReviewDocuments) {
    base.push(
      { path: '/admin/literature-review', icon: '✅', labelKey: 'nav.adminReview' },
      { path: '/admin/ingestion-tasks', icon: '📋', labelKey: 'nav.adminIngestion' },
    );
  }
  if (auth.canManageSourcePolicies) {
    base.push(
      { path: '/admin/source-policy', icon: '🔐', labelKey: 'nav.adminSourcePolicy' },
    );
  }
  return base;
});

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
  researchStore.clearTopic();
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
.app-navbar {
  display: flex;
  align-items: center;
  padding: 0 var(--space-6);
  height: 56px;
  background: var(--color-navbar-bg);
  border-bottom: 1px solid var(--color-border);
  position: sticky;
  top: 0;
  z-index: var(--z-dropdown)0;
  gap: var(--space-6);
}

.navbar-brand {
  flex-shrink: 0;
}

.brand-link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
  color: var(--color-text-primary);
}

.brand-icon {
  font-size: var(--text-2xl);
}

.brand-text {
  font-size: var(--text-lg);
  font-weight: var(--font-bold);
  white-space: nowrap;
}

.navbar-links {
  display: flex;
  list-style: none;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
  flex: 1;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-1-5) 14px;
  border-radius: var(--radius-md);
  text-decoration: none;
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
}

.nav-link:hover {
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.nav-link:focus-visible {
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.nav-link--active {
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: var(--font-semibold);
}

.nav-link--pulse {
  animation: navPulse var(--transition-slow) ease-in-out 5;
  position: relative;
}

.nav-link--pulse::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: var(--radius-lg);
  border: 2px solid var(--color-accent);
  animation: navPulseRing var(--transition-slow) ease-in-out 5;
  opacity: 0;
}

@keyframes navPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

@keyframes navPulseRing {
  0% { opacity: 0; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.08); }
  100% { opacity: 0; transform: scale(1.15); }
}

.nav-icon {
  font-size: var(--text-lg);
}

.navbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
}

.user-greeting {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
}

.auth-link,
.auth-btn {
  font-size: var(--text-sm);
  text-decoration: none;
  color: var(--color-accent);
  padding: var(--space-1) 10px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-accent);
  background: transparent;
  cursor: pointer;
  transition: all var(--transition-base);
}

.auth-link:hover,
.auth-btn:hover {
  background: var(--color-accent);
  color: white;
}

.auth-link:focus-visible,
.auth-btn:focus-visible {
  background: var(--color-accent);
  color: white;
}

.locale-switcher {
  display: flex;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.locale-btn {
  padding: var(--space-1) 10px;
  border: none;
  background: transparent;
  font-size: var(--text-xs);
  font-weight: var(--font-semibold);
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all var(--transition-base);
}

.locale-btn.active {
  background: var(--color-accent);
  color: var(--color-surface);
}

.locale-btn:not(.active):hover {
  background: var(--color-hover);
}

.locale-btn:not(.active):focus-visible {
  background: var(--color-hover);
}

.theme-toggle {
  padding: var(--space-1-5) 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 18px;
  border-radius: var(--radius-md);
  transition: background var(--transition-base);
}

.theme-toggle:hover {
  background: var(--color-hover);
}

.theme-toggle:focus-visible {
  background: var(--color-hover);
}

.mobile-menu-toggle {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-2);
}

.hamburger {
  display: block;
  width: 20px;
  height: 2px;
  background: var(--color-text-primary);
  position: relative;
  transition: background var(--transition-slow);
}

.hamburger::before,
.hamburger::after {
  content: '';
  display: block;
  width: 20px;
  height: 2px;
  background: var(--color-text-primary);
  position: absolute;
  transition: transform var(--transition-slow);
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
    padding: 0 var(--space-4);
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
    background: var(--color-navbar-bg);
    border-bottom: 1px solid var(--color-border);
    padding: var(--space-2);
    box-shadow: var(--shadow-md);
  }

  .navbar-links.open {
    display: flex;
  }
}
</style>
