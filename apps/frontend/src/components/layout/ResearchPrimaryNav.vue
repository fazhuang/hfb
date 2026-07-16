<template>
  <nav class="research-primary-nav" role="navigation" aria-label="Primary navigation">
    <!-- Research Modules -->
    <ul class="rpn-section">
      <li v-for="item in researchNavItems" :key="item.path">
        <router-link
          :to="item.path"
          class="rpn-link"
          :class="{ 'rpn-link--active': item.active }"
        >
          <span class="rpn-link-icon">{{ item.icon }}</span>
          <span v-if="!collapsed" class="rpn-link-label">{{ item.label }}</span>
        </router-link>
      </li>
    </ul>

    <!-- Administration separator + link -->
    <div class="rpn-separator"></div>
    <ul class="rpn-section">
      <li v-for="item in adminNavItems" :key="item.path">
        <a
          v-if="item.external"
          :href="item.path"
          class="rpn-link rpn-link--admin"
        >
          <span class="rpn-link-icon">{{ item.icon }}</span>
          <span v-if="!collapsed" class="rpn-link-label">{{ item.label }}</span>
        </a>
        <router-link
          v-else
          :to="item.path"
          class="rpn-link rpn-link--admin"
          :class="{ 'rpn-link--active': item.active }"
        >
          <span class="rpn-link-icon">{{ item.icon }}</span>
          <span v-if="!collapsed" class="rpn-link-label">{{ item.label }}</span>
        </router-link>
      </li>
    </ul>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';

defineProps<{
  collapsed?: boolean;
}>();

const route = useRoute();

interface NavItem {
  path: string;
  icon: string;
  label: string;
  active: boolean;
  external?: boolean;
}

/** Walk all matched route records to find the active section. */
function currentSection(): string {
  for (const r of route.matched) {
    if (r.meta.section) return r.meta.section as string;
  }
  return '';
}

const section = computed(() => currentSection());

const researchNavItems = computed<NavItem[]>(() => [
  {
    path: '/research',
    icon: '🔬',
    label: 'Research',
    active: section.value === 'research',
  },
  {
    path: '/library',
    icon: '📚',
    label: 'Library',
    active: section.value === 'library',
  },
  {
    path: '/knowledge',
    icon: '🔗',
    label: 'Knowledge',
    active: section.value === 'knowledge',
  },
  {
    path: '/reports',
    icon: '📊',
    label: 'Reports',
    active: section.value === 'reports',
  },
]);

const adminNavItems = computed<NavItem[]>(() => [
  {
    path: '/admin/literature-review',
    icon: '⚙️',
    label: 'Administration',
    active: section.value === 'admin',
  },
]);
</script>

<style scoped>
.research-primary-nav {
  padding: 12px 8px;
  flex: 1;
}

.rpn-section {
  list-style: none;
  margin: 0;
  padding: 0;
}

.rpn-separator {
  height: 1px;
  background: var(--color-border, #e2e8f0);
  margin: 8px 12px;
}

.rpn-link {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  text-decoration: none;
  font-size: 14px;
  color: var(--color-text-secondary, #4a5568);
  transition: background 0.15s;
  margin-bottom: 2px;
}

.rpn-link:hover {
  background: var(--color-hover, #edf2f7);
  color: var(--color-text-primary, #1a365d);
}

.rpn-link--active {
  background: var(--color-active, #ebf8ff);
  color: var(--color-accent, #2b6cb0);
  font-weight: 600;
}

.rpn-link--admin {
  font-size: 13px;
  color: var(--color-text-muted, #a0aec0);
}

.rpn-link-icon {
  font-size: 18px;
  width: 24px;
  text-align: center;
  flex-shrink: 0;
}

.rpn-link-label {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
