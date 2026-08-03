<template>
  <div class="research-app-layout">
    <!-- Sidebar -->
    <aside
      class="ral-sidebar"
      :class="{ 'ral-sidebar--collapsed': sidebarCollapsed }"
      aria-label="主导航侧栏"
    >
      <div class="ral-brand">
        <router-link to="/" class="ral-brand-link">
          <span class="ral-brand-icon">📜</span>
          <span v-if="!sidebarCollapsed" class="ral-brand-text">皇甫谧数字人文平台</span>
        </router-link>
      </div>

      <ResearchPrimaryNav :collapsed="sidebarCollapsed" />

      <div class="ral-sidebar-footer">
        <div class="ral-project-badge" v-if="!sidebarCollapsed">
          <span class="ral-project-dot"></span>
          <span class="ral-project-name">当前项目</span>
        </div>
        <div class="ral-user-area">
          <span class="ral-user-avatar">{{ userInitial }}</span>
          <span v-if="!sidebarCollapsed" class="ral-user-name">{{ userName }}</span>
        </div>
        <button
          class="ral-collapse-btn"
          :title="sidebarCollapsed ? '展开侧栏' : '折叠侧栏'"
          @click="sidebarCollapsed = !sidebarCollapsed"
        >
          {{ sidebarCollapsed ? '▶' : '◀' }}
        </button>
      </div>
    </aside>

    <!-- Mobile sidebar backdrop — closes sidebar on tap outside -->
    <div
      v-if="!sidebarCollapsed"
      class="ral-sidebar-backdrop"
      @click="sidebarCollapsed = true"
      aria-hidden="true"
    ></div>

    <!-- Mobile sidebar toggle — always reachable at narrow viewports -->
    <button
      class="ral-mobile-toggle"
      @click="sidebarCollapsed = !sidebarCollapsed"
      :aria-label="sidebarCollapsed ? '展开导航菜单' : '折叠导航菜单'"
      :title="sidebarCollapsed ? '展开导航菜单' : '折叠导航菜单'"
    >
      {{ sidebarCollapsed ? '☰' : '✕' }}
    </button>

    <!-- Main content area -->
    <div class="ral-main-wrapper">
      <!-- Page header slot — filled by router-view pages via ResearchPageHeader -->
      <div class="ral-content" data-main-content tabindex="-1">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import ResearchPrimaryNav from '@/components/layout/ResearchPrimaryNav.vue';

const auth = useAuthStore();
const sidebarCollapsed = ref(false);

// Sidebar becomes overlay at < 768px, stays in-flow at ≥ 768px.
const MOBILE_BREAKPOINT = 768;
let mql: MediaQueryList | null = null;

function syncMobile() {
  if (mql) {
    sidebarCollapsed.value = mql.matches;
  }
}

onMounted(() => {
  mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`);
  mql.addEventListener('change', syncMobile);
  syncMobile();

  // Hide DefaultLayout's AppNavbar when this child layout is active.
  // DefaultLayout renders AppNavbar as sibling to AppMain; CSS can't reach
  // a previous sibling, so we set a class on the parent container.
  const wrapper = document.querySelector('.ral-main-wrapper');
  if (wrapper) {
    const root = wrapper.closest('.default-layout');
    if (root) root.classList.add('ral-mobile-active');
  }
});

onUnmounted(() => {
  if (mql) mql.removeEventListener('change', syncMobile);
  const root = document.querySelector('.default-layout.ral-mobile-active');
  if (root) root.classList.remove('ral-mobile-active');
});

const userInitial = auth.userName ? auth.userName.charAt(0) : '?';
const userName = auth.userName || '未登录';
</script>

<style scoped>
.research-app-layout {
  display: flex;
  min-height: 100vh;
}

/* ---- Sidebar ---- */
.ral-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--color-navbar-bg);
  border-right: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  transition: width var(--transition-slow);
}

.ral-sidebar--collapsed {
  width: 64px;
}

.ral-brand {
  padding: var(--space-4);
  border-bottom: 1px solid var(--color-border);
}

.ral-brand-link {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  text-decoration: none;
  color: var(--color-text-primary);
}

.ral-brand-icon {
  font-size: 22px;
  flex-shrink: 0;
}

.ral-brand-text {
  font-size: 15px;
  font-weight: 700;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ---- Sidebar footer ---- */
.ral-sidebar-footer {
  margin-top: auto;
  padding: var(--space-3);
  border-top: 1px solid var(--color-border);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.ral-project-badge {
  display: flex;
  align-items: center;
  gap: var(--space-1-5);
  padding: var(--space-1-5) 8px;
  font-size: 12px;
  color: var(--color-text-muted);
}

.ral-project-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent);
  flex-shrink: 0;
}

.ral-user-area {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-1-5) 8px;
}

.ral-user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-accent);
  color: var(--color-surface);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.ral-user-name {
  font-size: 13px;
  color: var(--color-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ral-collapse-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: var(--space-1-5);
  font-size: 12px;
  color: var(--color-text-muted);
  border-radius: var(--radius-sm);
}

.ral-collapse-btn:hover {
  background: var(--color-hover);
}

.ral-collapse-btn:focus-visible {
  background: var(--color-hover);
}

/* ---- Backdrop (mobile only) ---- */
.ral-sidebar-backdrop {
  display: none;
}

/* ---- Mobile toggle ---- */
.ral-mobile-toggle {
  display: none;
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: var(--z-drawer, 1100);
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 20px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  padding: 0;
  line-height: 1;
}

/* ---- Main wrapper ---- */
.ral-main-wrapper {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.ral-content {
  flex: 1;
}

/* ---- Mobile toggle (base: hidden, shown via media query) ---- */
.ral-mobile-toggle {
  display: none;
  position: fixed;
  top: 12px;
  right: 12px;
  z-index: var(--z-drawer, 1100);
  width: 40px;
  height: 40px;
  align-items: center;
  justify-content: center;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  background: var(--color-surface);
  color: var(--color-text-secondary);
  font-size: 20px;
  cursor: pointer;
  box-shadow: var(--shadow-sm);
  padding: 0;
  line-height: 1;
}

.ral-mobile-toggle:hover {
  background: var(--color-hover);
}

.ral-mobile-toggle:focus-visible {
  outline: 2px solid var(--color-accent);
  outline-offset: 2px;
  background: var(--color-hover);
}

/* ---- Responsive: show toggle at ≤768px ---- */
@media (max-width: 768px) {
  .ral-mobile-toggle {
    display: flex;
  }
}

/* ---- Responsive: mobile overlay sidebar at ≤639px ---- */
@media (max-width: 767px) {
  .ral-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    z-index: var(--z-sidebar, 310);
    transform: translateX(0);
    transition: transform var(--transition-slow), width var(--transition-slow);
  }

  .ral-sidebar--collapsed {
    transform: translateX(-100%);
    width: 240px; /* keep layout width on hidden so transition is smooth */
  }

  .ral-sidebar-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    z-index: calc(var(--z-sidebar, 310) - 1);
    background: rgba(0, 0, 0, 0.35);
  }

  .ral-content {
    min-width: 0;
    overflow-x: hidden;
    word-break: break-word;
  }
}

/* ---- Mobile toggle (media-moved after @640px block, already in cascade) ---- */

</style>

<!-- Global style: hide DefaultLayout's AppNavbar on mobile when ResearchAppLayout is active.
     ResearchAppLayout has its own sidebar + toggle; the global navbar duplicates chrome
     and eats 56px of viewport at 375px, truncating the page header.                 -->
<style>
@media (max-width: 767px) {
  .default-layout.ral-mobile-active > .app-navbar {
    display: none;
  }
}
</style>
