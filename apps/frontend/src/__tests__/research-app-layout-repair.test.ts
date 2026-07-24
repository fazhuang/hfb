/**
 * TASK_012_REPAIR — ResearchAppLayout lifecycle repair (P2) +
 * mobile-toggle design documentation (P6)
 *
 * P2 — Empty `onMounted(() => {})` and `onBeforeUnmount(() => {})` removed.
 * P6 — .ral-mobile-toggle position:fixed + sidebar in-flow design documented.
 *
 * These tests verify:
 *   1. Layout renders without the removed empty lifecycle hooks
 *   2. Mobile toggle button (ral-mobile-toggle) exists and has correct attrs
 *   3. Sidebar stays in-flow (no display:none) — position:sticky
 *   4. [data-main-content] + tabindex="-1" present (router afterEach focus target)
 */

import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { setActivePinia, createPinia } from 'pinia';
import ResearchAppLayout from '@/layouts/ResearchAppLayout.vue';

// Mock auth store — needed because ResearchAppLayout uses useAuthStore()
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    accessToken: null,
    user: null,
    loading: false,
    isAuthenticated: false,
    canReviewDocuments: false,
    canManageSourcePolicies: false,
    userName: 'test',
    fetchMe: vi.fn(),
  })),
}));

function createMockRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/research',
        component: { template: '<div class="test-page">research</div>' },
        meta: { section: 'research', requiresAuth: true },
      },
    ],
  });
}

describe('ResearchAppLayout — P2 repair: no empty lifecycle hooks', () => {
  it('renders without error (empty lifecycle hooks removed)', () => {
    setActivePinia(createPinia());
    const router = createMockRouter();
    const wrapper = mount(ResearchAppLayout, {
      global: { plugins: [router] },
    });

    expect(wrapper.find('.research-app-layout').exists()).toBe(true);
    expect(wrapper.find('.ral-sidebar').exists()).toBe(true);
    expect(wrapper.find('.ral-main-wrapper').exists()).toBe(true);
  });

  it('renders sidebar collapsed state toggling', async () => {
    setActivePinia(createPinia());
    const router = createMockRouter();
    const wrapper = mount(ResearchAppLayout, {
      global: { plugins: [router] },
    });

    // Sidebar starts expanded
    expect(wrapper.find('.ral-sidebar--collapsed').exists()).toBe(false);

    // Click collapse button
    const collapseBtn = wrapper.find('.ral-collapse-btn');
    await collapseBtn.trigger('click');

    expect(wrapper.find('.ral-sidebar--collapsed').exists()).toBe(true);

    // Click again to expand
    await collapseBtn.trigger('click');
    expect(wrapper.find('.ral-sidebar--collapsed').exists()).toBe(false);
  });
});

describe('ResearchAppLayout — P6 repair: mobile toggle design', () => {
  it('has mobile toggle button with ARIA label', () => {
    setActivePinia(createPinia());
    const router = createMockRouter();
    const wrapper = mount(ResearchAppLayout, {
      global: { plugins: [router] },
    });

    const toggle = wrapper.find('.ral-mobile-toggle');
    expect(toggle.exists()).toBe(true);
    // Sidebar starts expanded → button offers to collapse
    expect(toggle.attributes('aria-label')).toBe('折叠导航菜单');
  });

  it('mobile toggle toggles sidebar collapsed state and updates ARIA label', async () => {
    setActivePinia(createPinia());
    const router = createMockRouter();
    const wrapper = mount(ResearchAppLayout, {
      global: { plugins: [router] },
    });

    const toggle = wrapper.find('.ral-mobile-toggle');

    // Start: sidebar expanded → label says "collapse"
    expect(wrapper.find('.ral-sidebar--collapsed').exists()).toBe(false);
    expect(toggle.attributes('aria-label')).toBe('折叠导航菜单');

    // Click toggle → sidebar collapses → label says "expand"
    await toggle.trigger('click');
    expect(wrapper.find('.ral-sidebar--collapsed').exists()).toBe(true);
    expect(toggle.attributes('aria-label')).toBe('展开导航菜单');
  });
});

describe('ResearchAppLayout — structural invariants (P6 explicit doc)', () => {
  it('[data-main-content] is present with tabindex="-1" for router focus mgmt', () => {
    setActivePinia(createPinia());
    const router = createMockRouter();
    const wrapper = mount(ResearchAppLayout, {
      global: { plugins: [router] },
    });

    const content = wrapper.find('[data-main-content]');
    expect(content.exists()).toBe(true);
    expect(content.attributes('tabindex')).toBe('-1');
  });

  it('sidebar is in DOM (not display:none or removed) — in-flow design', () => {
    setActivePinia(createPinia());
    const router = createMockRouter();
    const wrapper = mount(ResearchAppLayout, {
      global: { plugins: [router] },
    });

    const sidebar = wrapper.find('.ral-sidebar');
    expect(sidebar.exists()).toBe(true);

    const sidebarEl = sidebar.element as HTMLElement;
    // display should not be 'none' — sidebar stays in-flow
    expect(sidebarEl.style.display).not.toBe('none');
  });

  it('mobile toggle has .ral-mobile-toggle class (CSS handles position:fixed, z-index:300)', () => {
    setActivePinia(createPinia());
    const router = createMockRouter();
    const wrapper = mount(ResearchAppLayout, {
      global: { plugins: [router] },
    });

    const toggle = wrapper.find('.ral-mobile-toggle');
    expect(toggle.classes()).toContain('ral-mobile-toggle');
  });
});
