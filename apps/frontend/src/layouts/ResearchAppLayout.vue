<template>
  <div class="research-app-layout">
    <!-- Sidebar -->
    <aside class="ral-sidebar" :class="{ 'ral-sidebar--collapsed': sidebarCollapsed }" aria-label="主导航侧栏">
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

    <!-- Main content area -->
    <div class="ral-main-wrapper" :class="{ 'ral-main-wrapper--shifted': !sidebarCollapsed }">
      <!-- Page header slot — filled by router-view pages via ResearchPageHeader -->
      <div class="ral-content" data-main-content tabindex="-1">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { useAuthStore } from '@/stores/auth';
import ResearchPrimaryNav from '@/components/layout/ResearchPrimaryNav.vue';

const auth = useAuthStore();
const sidebarCollapsed = ref(false);

// Auto-collapse sidebar on narrow viewports where it overlays content.
// At ≤768px the sidebar is position:fixed and intercepts pointer events
// on elements underneath. Collapsing it keeps the page usable.
let narrowQuery: MediaQueryList | null = null;

function onNarrowChange(e: MediaQueryListEvent | MediaQueryList) {
  sidebarCollapsed.value = e.matches;
}

onMounted(() => {
  narrowQuery = window.matchMedia('(max-width: 768px)');
  narrowQuery.addEventListener('change', onNarrowChange);
  // Set initial state
  onNarrowChange(narrowQuery);
});

onBeforeUnmount(() => {
  if (narrowQuery) {
    narrowQuery.removeEventListener('change', onNarrowChange);
  }
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
  background: var(--color-navbar-bg, #ffffff);
  border-right: 1px solid var(--color-border, #e2e8f0);
  display: flex;
  flex-direction: column;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow-y: auto;
  transition: width 0.2s;
}

.ral-sidebar--collapsed {
  width: 64px;
}

.ral-brand {
  padding: 16px;
  border-bottom: 1px solid var(--color-border, #e2e8f0);
}

.ral-brand-link {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: var(--color-text-primary, #1a365d);
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
  padding: 12px;
  border-top: 1px solid var(--color-border, #e2e8f0);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ral-project-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
}

.ral-project-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--color-accent, #4299e1);
  flex-shrink: 0;
}

.ral-user-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
}

.ral-user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--color-accent, #4299e1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.ral-user-name {
  font-size: 13px;
  color: var(--color-text-secondary, #4a5568);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.ral-collapse-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 6px;
  font-size: 12px;
  color: var(--color-text-muted, #a0aec0);
  border-radius: 4px;
}

.ral-collapse-btn:hover {
  background: var(--color-hover, #edf2f7);
}

.ral-collapse-btn:focus-visible {
  background: var(--color-hover, #edf2f7);
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

/* ---- Responsive ---- */
@media (max-width: 768px) {
  .ral-sidebar {
    position: fixed;
    z-index: 200;
    transform: translateX(0);
  }

  .ral-sidebar--collapsed {
    transform: translateX(-64px);
    width: 64px;
  }

  .ral-main-wrapper {
    margin-left: 0;
  }

  /* When the sidebar is NOT collapsed (shifted state), it overlays content.
     The sidebar is position: fixed at mobile widths, so no margin is needed —
     adding margin-left: 240px leaves only 135px for content at 375px width. */
  .ral-main-wrapper--shifted {
    margin-left: 0;
  }
}
</style>
