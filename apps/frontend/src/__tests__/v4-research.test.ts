import { mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { describe, expect, it, beforeEach, beforeAll } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';

import i18n from '@/i18n';
import V4ResearchView from '@/views/V4ResearchView.vue';

// R3: V4ResearchView is now a compatibility adapter (< 100 lines).
// All business logic removed. Tests verify adapter renders navigation hint.

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' } },
      { path: '/research', component: { template: '<div/>' }, name: 'research-project-list' },
      { path: '/v4/research-internal', name: 'v4-research', component: V4ResearchView },
    ],
  });
}

describe('V4ResearchView — R3 adapter', () => {
  let router: ReturnType<typeof createRouter>;

  beforeAll(async () => {
    router = makeRouter();
    await router.push('/v4/research-internal');
  });

  beforeEach(() => {
    // no mocks needed — adapter has no API calls
  });

  it('renders migration hint', () => {
    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });
    const text = wrapper.text();
    expect(text).toContain('V4 研究');
    expect(text).toContain('已迁移');
  });

  it('renders link to research project list', () => {
    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });
    const link = wrapper.find('a');
    expect(link.exists()).toBe(true);
  });
});
