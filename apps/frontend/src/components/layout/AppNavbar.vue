<template>
  <nav class="app-navbar" role="navigation" aria-label="Main navigation">
    <!-- Brand logo -->
    <div class="navbar-brand">
      <router-link to="/" class="brand-link">
        <span class="brand-icon" aria-hidden="true">
          <svg viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
            <rect x="3" y="3" width="42" height="42" rx="11" fill="none" stroke="currentColor" stroke-width="2.5" />
            <line x1="15" y1="19" x2="33" y2="19" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            <line x1="15" y1="26" x2="33" y2="26" stroke="currentColor" stroke-width="2" stroke-linecap="round" />
            <line x1="24" y1="11" x2="24" y2="37" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" />
            <circle cx="24" cy="11" r="3" fill="currentColor" />
          </svg>
        </span>
        <span class="brand-text-wrap">
          <span v-if="locale === 'zh-CN'" class="brand-text">
            <span class="brand-text--main">皇甫谧</span><span class="brand-text--sub">数字人文平台</span>
          </span>
          <span v-else class="brand-text">{{ t('system.title') }}</span>
          <span class="brand-subtitle">{{ t('system.subtitle') }}</span>
        </span>
      </router-link>
    </div>

    <!-- Mobile Menu Toggle Button -->
    <button
      class="mobile-menu-toggle"
      :aria-expanded="menuOpen"
      aria-label="Toggle navigation menu"
      @click="menuOpen = !menuOpen"
    >
      <span class="hamburger" :class="{ open: menuOpen }"></span>
    </button>

    <!-- Navigation Bar Main Links Area -->
    <div class="navbar-links" :class="{ open: menuOpen }">
      <!-- Standard Primary Links -->
      <ul class="nav-menu-list">
        <li>
          <router-link
            to="/"
            class="nav-link"
            active-class="nav-link--active"
            @click="closeAllMenus"
          >
            <span class="nav-icon" aria-hidden="true">🏠</span>
            <span>{{ t('nav.home') }}</span>
          </router-link>
        </li>

        <!-- Research Workspace Module (Authenticated Users) -->
        <template v-if="auth.isAuthenticated">
          <li v-for="item in researchNavItems" :key="item.path">
            <router-link
              :to="item.path"
              class="nav-link"
              :class="{ 'nav-link--pulse': item.pulse }"
              active-class="nav-link--active"
              :title="item.pulse ? t('onboarding.pulseStartResearch') : undefined"
              @click="closeAllMenus"
            >
              <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
              <span>{{ t(item.labelKey) }}</span>
            </router-link>
          </li>
        </template>

        <!-- Public Classical Resources Dropdown (When authed) or Direct Links (When guest) -->
        <li v-if="auth.isAuthenticated" class="nav-dropdown-wrapper" ref="resourcesDropdownRef">
          <button
            class="nav-link dropdown-toggle-btn"
            :class="{ active: isPublicResourceActive }"
            :aria-expanded="resourcesOpen"
            aria-haspopup="true"
            @click="toggleResourcesMenu"
            @keydown.escape="resourcesOpen = false"
          >
            <span class="nav-icon" aria-hidden="true">📚</span>
            <span>典籍资源</span>
            <span class="dropdown-caret" :class="{ open: resourcesOpen }">▾</span>
          </button>
          <ul v-show="resourcesOpen" class="dropdown-menu">
            <li v-for="item in publicNavItems" :key="item.path">
              <router-link
                :to="item.path"
                class="dropdown-item"
                active-class="dropdown-item--active"
                @click="closeAllMenus"
              >
                <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
                <span>{{ t(item.labelKey) }}</span>
              </router-link>
            </li>
          </ul>
        </li>

        <!-- Unauthenticated Public Links (Flat layout for simple browsing) -->
        <template v-else>
          <li v-for="item in publicNavItems" :key="item.path">
            <router-link
              :to="item.path"
              class="nav-link"
              active-class="nav-link--active"
              @click="closeAllMenus"
            >
              <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
              <span>{{ t(item.labelKey) }}</span>
            </router-link>
          </li>
        </template>
      </ul>

      <!-- System Admin Dropdown (Only shown if user has admin/reviewer permissions) -->
      <div v-if="adminNavItems.length > 0" class="nav-dropdown-wrapper" ref="adminDropdownRef">
        <button
          class="nav-link admin-dropdown-btn"
          :class="{ active: isAdminActive }"
          :aria-expanded="adminOpen"
          aria-haspopup="true"
          @click="toggleAdminMenu"
          @keydown.escape="adminOpen = false"
        >
          <span class="nav-icon" aria-hidden="true">⚙️</span>
          <span>系统管理</span>
          <span class="dropdown-caret" :class="{ open: adminOpen }">▾</span>
        </button>
        <ul v-show="adminOpen" class="dropdown-menu">
          <li v-for="item in adminNavItems" :key="item.path">
            <router-link
              :to="item.path"
              class="dropdown-item"
              active-class="dropdown-item--active"
              @click="closeAllMenus"
            >
              <span class="nav-icon" aria-hidden="true">{{ item.icon }}</span>
              <span>{{ t(item.labelKey) }}</span>
            </router-link>
          </li>
        </ul>
      </div>
    </div>

    <!-- Right Actions Area (Auth / User Profile / Locale / Theme) -->
    <div class="navbar-actions">
      <!-- Authenticated User Menu Dropdown -->
      <div v-if="auth.isAuthenticated" class="user-dropdown-wrapper" ref="userDropdownRef">
        <button
          class="user-menu-btn"
          :aria-expanded="userMenuOpen"
          aria-haspopup="true"
          @click="toggleUserMenu"
          @keydown.escape="userMenuOpen = false"
        >
          <span class="user-avatar">{{ userInitial }}</span>
          <span class="user-name-text">{{ auth.userName }}</span>
          <span class="dropdown-caret" :class="{ open: userMenuOpen }">▾</span>
        </button>

        <ul v-show="userMenuOpen" class="dropdown-menu user-dropdown-menu">
          <li class="user-info-header">
            <div class="user-info-name">{{ auth.userName }}</div>
            <div class="user-info-role">{{ auth.isSuperAdmin ? '超级管理员' : (auth.canReviewDocuments ? '审核管理员' : '研究员') }}</div>
          </li>
          <li class="dropdown-divider"></li>
          <li>
            <router-link to="/research" class="dropdown-item" @click="closeAllMenus">
              <span class="nav-icon" aria-hidden="true">🔬</span>
              <span>进入研究中心</span>
            </router-link>
          </li>
          <li class="dropdown-divider"></li>
          <li>
            <button class="dropdown-item logout-action-btn" @click="handleLogout">
              <span class="nav-icon" aria-hidden="true">🚪</span>
              <span>{{ t('auth.logout') }}</span>
            </button>
          </li>
        </ul>
      </div>

      <!-- Guest Login Button -->
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
      <button
        class="theme-toggle"
        :aria-label="t('theme.dark')"
        :title="t('onboarding.themeTooltip')"
        @click="cycleTheme"
      >
        <span v-if="resolvedTheme === 'light'" aria-hidden="true">☀️</span>
        <span v-else aria-hidden="true">🌙</span>
      </button>
    </div>
  </nav>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import { useI18n } from 'vue-i18n';
import { useRouter, useRoute } from 'vue-router';
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
const route = useRoute();

const menuOpen = ref(false);
const adminOpen = ref(false);
const resourcesOpen = ref(false);
const userMenuOpen = ref(false);

const adminDropdownRef = ref<HTMLElement | null>(null);
const resourcesDropdownRef = ref<HTMLElement | null>(null);
const userDropdownRef = ref<HTMLElement | null>(null);

// P2: Pulse animation on "Start Research" nav link — runs 5 cycles then stops
const showResearchPulse = ref(auth.isAuthenticated && !researchStore.hasActiveResearch);

onMounted(() => {
  if (showResearchPulse.value) {
    setTimeout(() => {
      showResearchPulse.value = false;
    }, 5000);
  }
  document.addEventListener('click', handleClickOutside);
});

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside);
});

function handleClickOutside(event: MouseEvent) {
  const target = event.target as Node;
  if (adminDropdownRef.value && !adminDropdownRef.value.contains(target)) {
    adminOpen.value = false;
  }
  if (resourcesDropdownRef.value && !resourcesDropdownRef.value.contains(target)) {
    resourcesOpen.value = false;
  }
  if (userDropdownRef.value && !userDropdownRef.value.contains(target)) {
    userMenuOpen.value = false;
  }
}

function toggleAdminMenu() {
  adminOpen.value = !adminOpen.value;
  if (adminOpen.value) {
    resourcesOpen.value = false;
    userMenuOpen.value = false;
  }
}

function toggleResourcesMenu() {
  resourcesOpen.value = !resourcesOpen.value;
  if (resourcesOpen.value) {
    adminOpen.value = false;
    userMenuOpen.value = false;
  }
}

function toggleUserMenu() {
  userMenuOpen.value = !userMenuOpen.value;
  if (userMenuOpen.value) {
    adminOpen.value = false;
    resourcesOpen.value = false;
  }
}

function closeAllMenus() {
  menuOpen.value = false;
  adminOpen.value = false;
  resourcesOpen.value = false;
  userMenuOpen.value = false;
  showResearchPulse.value = false;
}

interface NavItem {
  path: string;
  icon: string;
  labelKey: string;
  pulse?: boolean;
}

/** Research Module Nav Items (Icon 📖 used for Research Library to avoid 📚 collision) */
const researchNavItems = computed<NavItem[]>(() => [
  {
    path: '/research',
    icon: '🔬',
    labelKey: 'nav.startResearch',
    pulse: showResearchPulse.value,
  },
  { path: '/library', icon: '📖', labelKey: 'nav.library' },
  { path: '/knowledge', icon: '🔗', labelKey: 'nav.knowledge' },
  { path: '/reports', icon: '📊', labelKey: 'nav.reports' },
]);

/** Public Classical Catalogue Resources */
const publicNavItems = computed<NavItem[]>(() => [
  { path: '/books', icon: '📚', labelKey: 'nav.books' },
  { path: '/literature', icon: '📄', labelKey: 'nav.literature' },
  { path: '/classical-versions', icon: '🏛️', labelKey: 'nav.classicalVersions' },
  { path: '/persons', icon: '👤', labelKey: 'nav.persons' },
  { path: '/about', icon: 'ℹ️', labelKey: 'nav.about' },
]);

/** Admin Task Nav Items */
const adminNavItems = computed<NavItem[]>(() => {
  const items: NavItem[] = [];
  if (auth.canReviewDocuments) {
    items.push(
      { path: '/admin/literature-review', icon: '✅', labelKey: 'nav.adminReview' },
      { path: '/admin/ingestion-tasks', icon: '📋', labelKey: 'nav.adminIngestion' },
    );
  }
  if (auth.canManageSourcePolicies) {
    items.push({ path: '/admin/source-policy', icon: '🔐', labelKey: 'nav.adminSourcePolicy' });
  }
  return items;
});

const isPublicResourceActive = computed(() =>
  publicNavItems.value.some((item) => route.path === item.path || route.path.startsWith(item.path + '/')),
);

const isAdminActive = computed(() =>
  adminNavItems.value.some((item) => route.path === item.path || route.path.startsWith(item.path + '/')),
);

const userInitial = computed(() => (auth.userName ? auth.userName.charAt(0).toUpperCase() : '?'));

const locales = SUPPORTED_LOCALES;

const resolvedTheme = computed(() => {
  if (theme.value === 'auto') {
    if (
      typeof window !== 'undefined' &&
      window.matchMedia('(prefers-color-scheme: dark)').matches
    ) {
      return 'dark';
    }
    return 'light';
  }
  return theme.value;
});

function switchLocale(loc: SupportedLocale) {
  setLocale(loc);
}

function handleLogout() {
  closeAllMenus();
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
  z-index: var(--z-dropdown, 1000);
  gap: var(--space-4);
}

.navbar-brand {
  flex-shrink: 0;
  margin-right: var(--space-2);
}

.brand-link {
  display: flex;
  align-items: center;
  gap: var(--space-2-5);
  text-decoration: none;
  color: var(--color-text-primary);
  transition: transform var(--transition-base);
}

.brand-link:hover {
  transform: translateY(-1px);
}

.brand-icon {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  color: var(--color-accent);
}

.brand-icon svg {
  width: 100%;
  height: 100%;
  display: block;
}

.brand-text-wrap {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.brand-text {
  font-size: 17px;
  font-weight: var(--font-bold);
  white-space: nowrap;
  color: var(--color-text-primary);
  font-family: 'HfbSerif', 'Noto Serif SC', 'Kaiti SC', 'Songti SC', serif;
  letter-spacing: 0.06em;
}

.brand-text--main {
  font-size: 1.15em;
  margin-right: 0.35em;
}

.brand-text--sub {
  font-size: 0.72em;
  font-weight: var(--font-medium);
  letter-spacing: 0.04em;
  color: var(--color-text-secondary);
}

.brand-subtitle {
  font-size: 10px;
  font-weight: var(--font-semibold);
  color: var(--color-text-muted);
  white-space: nowrap;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  font-family: 'HfbLatin', 'Cormorant Garamond', 'Georgia', serif;
}

.navbar-links {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
}

.nav-menu-list {
  display: flex;
  align-items: center;
  list-style: none;
  gap: var(--space-1);
  margin: 0;
  padding: 0;
}

.nav-link {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-1-5) 12px;
  border-radius: var(--radius-md);
  text-decoration: none;
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-secondary);
  background: transparent;
  border: none;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--transition-base);
}

.nav-link:hover {
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.nav-link:focus-visible {
  outline: 2px solid var(--color-accent);
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.nav-link--active,
.dropdown-toggle-btn.active,
.admin-dropdown-btn.active {
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
  0%,
  100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.04);
  }
}

@keyframes navPulseRing {
  0% {
    opacity: 0;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.06);
  }
  100% {
    opacity: 0;
    transform: scale(1.12);
  }
}

.nav-icon {
  font-size: 16px;
  flex-shrink: 0;
}

/* Dropdown Menu Container & Styling */
.nav-dropdown-wrapper {
  position: relative;
}

.dropdown-caret {
  font-size: 11px;
  margin-left: 2px;
  transition: transform var(--transition-fast);
}

.dropdown-caret.open {
  transform: rotate(180deg);
}

.dropdown-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  min-width: 170px;
  background: var(--color-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: var(--space-1) 0;
  margin: 0;
  list-style: none;
  z-index: var(--z-dropdown, 1000);
}

.dropdown-item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  color: var(--color-text-secondary);
  text-decoration: none;
  font-size: var(--text-sm);
  width: 100%;
  background: none;
  border: none;
  cursor: pointer;
  text-align: left;
  transition: background var(--transition-fast), color var(--transition-fast);
}

.dropdown-item:hover,
.dropdown-item:focus-visible {
  background: var(--color-hover);
  color: var(--color-text-primary);
  outline: none;
}

.dropdown-item--active {
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: var(--font-semibold);
}

.dropdown-divider {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-1) 0;
}

/* Actions Right Area */
.navbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  margin-left: auto;
}

/* User Account Menu */
.user-dropdown-wrapper {
  position: relative;
}

.user-menu-btn {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1) var(--space-2);
  background: var(--color-hover);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-full, 9999px);
  cursor: pointer;
  color: var(--color-text-primary);
  transition: background var(--transition-fast);
}

.user-menu-btn:hover,
.user-menu-btn:focus-visible {
  background: var(--color-active);
  outline: none;
}

.user-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: var(--color-accent);
  color: var(--color-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--text-xs);
  font-weight: 600;
}

.user-name-text {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  max-width: 100px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-dropdown-menu {
  right: 0;
  left: auto;
  min-width: 190px;
}

.user-info-header {
  padding: var(--space-2) var(--space-3);
}

.user-info-name {
  font-weight: var(--font-bold);
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.user-info-role {
  font-size: var(--text-xs);
  color: var(--color-text-muted);
  margin-top: 2px;
}

.logout-action-btn {
  color: var(--color-error);
}

.logout-action-btn:hover {
  background: var(--color-hover);
}

/* Auth guest link */
.auth-link {
  font-size: var(--text-sm);
  text-decoration: none;
  color: var(--color-accent);
  padding: var(--space-1) 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-accent);
  background: transparent;
  cursor: pointer;
  transition: all var(--transition-base);
}

.auth-link:hover,
.auth-link:focus-visible {
  background: var(--color-accent);
  color: var(--color-surface);
}

/* Locale Switcher */
.locale-switcher {
  display: flex;
  border-radius: var(--radius-md);
  overflow: hidden;
  border: 1px solid var(--color-border);
}

.locale-btn {
  padding: var(--space-1) 8px;
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

.locale-btn:not(.active):hover,
.locale-btn:not(.active):focus-visible {
  background: var(--color-hover);
}

/* Theme Toggle */
.theme-toggle {
  padding: var(--space-1) 8px;
  border: none;
  background: transparent;
  cursor: pointer;
  font-size: 16px;
  border-radius: var(--radius-md);
  color: var(--color-text-primary);
  transition: background var(--transition-base);
}

.theme-toggle:hover,
.theme-toggle:focus-visible {
  background: var(--color-hover);
}

/* Mobile responsive toggle */
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

@media (max-width: 860px) {
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
    align-items: stretch;
    background: var(--color-navbar-bg);
    border-bottom: 1px solid var(--color-border);
    padding: var(--space-3);
    box-shadow: var(--shadow-md);
  }

  .navbar-links.open {
    display: flex;
  }

  .nav-menu-list {
    flex-direction: column;
    align-items: stretch;
    width: 100%;
  }

  .dropdown-menu {
    position: static;
    box-shadow: none;
    border: none;
    padding-left: var(--space-4);
  }

  .user-name-text {
    display: none;
  }
}
</style>

