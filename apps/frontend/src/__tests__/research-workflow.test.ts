import { mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { describe, expect, it, vi } from 'vitest';

import i18n from '@/i18n';
import ResearchWorkflowView from '@/views/ResearchWorkflowView.vue';

vi.mock('@/api/client', () => ({
  default: {
    defaults: { baseURL: '' },
    get: vi.fn().mockResolvedValue({ data: { data: [] } }),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

describe('ResearchWorkflowView', () => {
  it('warns about validation data and blocks comparison without two passages', () => {
    const wrapper = mount(ResearchWorkflowView, {
      global: {
        plugins: [createPinia(), i18n],
      },
    });

    expect(wrapper.text()).toContain('验证语料');
    expect(wrapper.get('[data-testid="search-passages"]').attributes('disabled')).toBeDefined();
    const compareButton = wrapper.get('[data-testid="compare-passages"]');
    expect(compareButton.attributes('disabled')).toBeDefined();
  });
});
