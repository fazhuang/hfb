import { mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { describe, expect, it, vi } from 'vitest';

import i18n from '@/i18n';
import V4ResearchView from '@/views/V4ResearchView.vue';

vi.mock('@/api/client', () => ({
  default: {
    defaults: { baseURL: '' },
    get: vi.fn().mockResolvedValue({ data: { data: { runs: [] } } }),
    post: vi.fn().mockResolvedValue({
      data: {
        success: true,
        data: {
          session_id: 'test-session-id',
          run_id: 'test-run-id',
          steps: [
            { name: 'topic_selection', status: 'completed' },
            { name: 'literature_retrieval', status: 'completed' },
            { name: 'evidence_synthesis', status: 'completed' },
            { name: 'report_generation', status: 'completed' },
            { name: 'citation_export', status: 'completed' },
          ],
          traceability: { query_id: 'q', trace_ids: [], citation_count: 0, source_documents: [] },
        },
        message: 'ok',
      },
    }),
    put: vi.fn(),
  },
}));

describe('V4ResearchView', () => {
  it('renders all three tabs: research, education, visualization', () => {
    const wrapper = mount(V4ResearchView, {
      global: {
        plugins: [createPinia(), i18n],
      },
    });

    const text = wrapper.text();
    expect(text).toContain('完整研究');
    expect(text).toContain('教育模式');
    expect(text).toContain('可视化');
  });

  it('has a research workflow submit button', () => {
    const wrapper = mount(V4ResearchView, {
      global: {
        plugins: [createPinia(), i18n],
      },
    });

    const btn = wrapper.find('[data-testid="v4-run-workflow"]');
    expect(btn.exists()).toBe(true);
  });

  it('has an education mode submit button', async () => {
    const wrapper = mount(V4ResearchView, {
      global: {
        plugins: [createPinia(), i18n],
      },
    });

    // Switch to education tab
    const eduTab = wrapper.findAll('.tab-button')[1]!;
    await eduTab.trigger('click');

    const btn = wrapper.find('[data-testid="v4-run-education"]');
    expect(btn.exists()).toBe(true);
  });

  it('has a visualization submit button', async () => {
    const wrapper = mount(V4ResearchView, {
      global: {
        plugins: [createPinia(), i18n],
      },
    });

    // Switch to visualization tab
    const vizTab = wrapper.findAll('.tab-button')[2]!;
    await vizTab.trigger('click');

    const btn = wrapper.find('[data-testid="v4-run-viz"]');
    expect(btn.exists()).toBe(true);
  });
});
