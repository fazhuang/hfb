<template>
  <nav class="research-primary-nav" role="navigation" aria-label="Primary navigation">
    <!-- Research Modules -->
    <ul class="rpn-section">
      <li v-for="item in researchNavItems" :key="item.path">
        <router-link
          :to="item.path"
          class="rpn-link"
          :class="{ 'rpn-link--active': item.active }"
          :aria-label="item.label"
          :title="item.label"
        >
          <HfbIcon :icon="item.icon" :size="16" class="rpn-link-icon" />
          <span class="rpn-link-label" :class="{ 'sr-only': collapsed }">{{ item.label }}</span>
        </router-link>
      </li>
    </ul>

    <!-- Administration separator + link -->
    <template v-if="adminNavItems.length > 0">
      <div class="rpn-separator"></div>
      <ul class="rpn-section">
        <li v-for="item in adminNavItems" :key="item.path">
          <a v-if="item.external" :href="item.path" class="rpn-link rpn-link--admin">
            <HfbIcon :icon="item.icon" :size="16" class="rpn-link-icon" />
            <span class="rpn-link-label" :class="{ 'sr-only': collapsed }">{{ item.label }}</span>
          </a>
          <router-link
            v-else
            :to="item.path"
            class="rpn-link rpn-link--admin"
            :class="{ 'rpn-link--active': item.active }"
          >
            <HfbIcon :icon="item.icon" :size="16" class="rpn-link-icon" />
            <span class="rpn-link-label" :class="{ 'sr-only': collapsed }">{{ item.label }}</span>
          </router-link>
        </li>
      </ul>
    </template>
  </nav>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { useAuthStore } from '@/stores/auth';
import HfbIcon from '@/components/common/HfbIcon.vue';
import type { LucideIconName } from '@/components/common/HfbIcon.vue';

defineProps<{
  collapsed?: boolean;
}>();

const route = useRoute();
const { t } = useI18n();
const auth = useAuthStore();

interface NavItem {
  path: string;
  icon: LucideIconName;
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
    icon: 'flask-conical',
    label: t('nav.startResearch'),
    active: section.value === 'research',
  },
  {
    path: '/library',
    icon: 'library',
    label: t('nav.library'),
    active: section.value === 'library',
  },
  {
    path: '/knowledge',
    icon: 'link',
    label: t('nav.knowledge'),
    active: section.value === 'knowledge',
  },
  {
    path: '/reports',
    icon: 'bar-chart-3',
    label: t('nav.reports'),
    active: section.value === 'reports',
  },
  {
    path: '/candidate-review',
    icon: 'check-check',
    label: t('nav.candidateReview'),
    active: route.path === '/candidate-review',
  },
]);

const adminNavItems = computed<NavItem[]>(() => {
  const items: NavItem[] = [];
  if (auth.canReviewDocuments || auth.canManageSourcePolicies) {
    items.push({
      path: '/admin/literature-review',
      icon: 'settings',
      label: t('nav.administration'),
      active: section.value === 'admin',
    });
  }
  return items;
});
</script>

<style scoped>
.research-primary-nav {
  padding: var(--space-3) var(--space-2);
  flex: 1;
}

.rpn-section {
  list-style: none;
  margin: 0;
  padding: 0;
}

.rpn-separator {
  height: 1px;
  background: var(--color-border);
  margin: var(--space-2) var(--space-3);
}

.rpn-link {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-3);
  border-radius: var(--radius-lg);
  text-decoration: none;
  font-size: var(--text-base);
  color: var(--color-text-secondary);
  transition: background var(--transition-base);
  margin-bottom: 2px;
}

.rpn-link:hover {
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.rpn-link:focus-visible {
  background: var(--color-hover);
  color: var(--color-text-primary);
}

.rpn-link--active {
  background: var(--color-accent-light);
  color: var(--color-accent);
  font-weight: var(--font-semibold);
}

.rpn-link--admin {
  font-size: var(--text-sm);
  color: var(--color-text-muted);
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
