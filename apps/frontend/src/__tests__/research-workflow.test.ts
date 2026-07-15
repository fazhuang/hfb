import { flushPromises, mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { describe, expect, it, vi, beforeEach } from 'vitest';

import i18n from '@/i18n';
import ResearchWorkflowView from '@/views/ResearchWorkflowView.vue';

// ---------------------------------------------------------------------------
// Vitest hoisting: vi.mock factories are hoisted, so the mock implementation
// must be defined via vi.hoisted() to be available at factory time.
// ---------------------------------------------------------------------------

const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: {
    defaults: { baseURL: '' },
    get: mockGet,
    post: vi.fn(),
    put: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// Response helpers
// ---------------------------------------------------------------------------

function sessionResponse(items: Array<{ id: string; title: string }>) {
  return { data: { data: items } };
}

function nullComparisonResponse() {
  return { data: { data: null } };
}

function validComparisonResponse() {
  return {
    data: {
      data: {
        workflow_type: 'evidence_backed_version_comparison',
        corpus_status: 'validation',
        source: {
          passage_id: 'p1',
          text: '甲乙',
          citation: '卷第一',
          evidence_complete: false,
          version: {
            id: 'v1', name: '明刻本', repository: null, shelf_mark: null,
          },
        },
        target: {
          passage_id: 'p2',
          text: '丙丁',
          citation: '卷第一',
          evidence_complete: false,
          version: {
            id: 'v2', name: '宋刻本', repository: null, shelf_mark: null,
          },
        },
        comparison: {
          differences: 1,
          similarity_ratio: 0.85,
          operations: [
            { op: 'replace', source_text: '甲', target_text: '丙' },
          ],
        },
      },
    },
  };
}

// ---------------------------------------------------------------------------

describe('ResearchWorkflowView — restoreLatestWorkflow', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  it('skips sessions whose version-comparison returns data:null', async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') {
        return sessionResponse([
          { id: 's1', title: 'A' },
          { id: 's2', title: 'B' },
          { id: 's3', title: 'C' },
        ]);
      }
      if (url === '/api/v1/research/sessions/s1/version-comparison') {
        return nullComparisonResponse();
      }
      if (url === '/api/v1/research/sessions/s2/version-comparison') {
        return nullComparisonResponse();
      }
      if (url === '/api/v1/research/sessions/s3/version-comparison') {
        return validComparisonResponse();
      }
      return { data: { data: [] } };
    });

    const wrapper = mount(ResearchWorkflowView, {
      global: {
        plugins: [createPinia(), i18n],
      },
    });

    await flushPromises();
    await wrapper.vm.$nextTick();

    // Verify all 3 sessions were probed
    const calls = mockGet.mock.calls.map((c: string[]) => c[0]) as string[];
    const comparisonCalls = calls.filter((u: string) =>
      u.includes('/version-comparison'),
    );
    expect(comparisonCalls).toHaveLength(3);

    // Page rendered with the valid comparison
    const text = wrapper.text();
    expect(text).toContain('明刻本');
    expect(text).toContain('宋刻本');
  });

  it('renders workflow UI even when session list is empty', async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') {
        return sessionResponse([]);
      }
      return { data: { data: [] } };
    });

    const wrapper = mount(ResearchWorkflowView, {
      global: {
        plugins: [createPinia(), i18n],
      },
    });

    await flushPromises();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('验证语料');
    expect(text).toContain('检索条文');

    const calls = mockGet.mock.calls.map((c: string[]) => c[0]) as string[];
    const comparisonCalls = calls.filter((u: string) =>
      u.includes('/version-comparison'),
    );
    expect(comparisonCalls).toHaveLength(0);
  });

  it('survives network errors while probing comparison sessions', async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') {
        return sessionResponse([{ id: 's4', title: 'Broken' }]);
      }
      throw new Error('Network Error');
    });

    // Should not throw
    const wrapper = mount(ResearchWorkflowView, {
      global: {
        plugins: [createPinia(), i18n],
      },
    });

    await flushPromises();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('验证语料');
    expect(text).toContain('检索条文');
  });
});
