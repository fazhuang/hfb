import { mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { describe, expect, it } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';

import i18n from '@/i18n';
import ResearchWorkflowView from '@/views/ResearchWorkflowView.vue';

// R3: ResearchWorkflowView is now a compatibility adapter (< 100 lines).
// All business logic removed. Tests verify adapter renders navigation hint.

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/research', component: { template: '<div/>' }, name: 'research-project-list' },
    ],
  });
}

describe('ResearchWorkflowView — R3 adapter', () => {
  it('renders migration hint with link to research project list', () => {
    const router = makeRouter();
    const wrapper = mount(ResearchWorkflowView, {
      global: {
        plugins: [router, createPinia(), i18n],
      },
    });

    const text = wrapper.text();
    expect(text).toContain('版本研究已迁移');
    expect(text).toContain('前往研究课题列表');
  });
});
