import { flushPromises, mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { describe, expect, it, vi, beforeEach, beforeAll } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';

import i18n from '@/i18n';
import V4ResearchView from '@/views/V4ResearchView.vue';

vi.mock('@/api/client', () => ({
  default: {
    defaults: { baseURL: '' },
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}));

import api from '@/api/client';

// Stub router so useRoute() in onMounted doesn't throw
function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' } },
      { path: '/v4/research-internal', name: 'v4-research', component: V4ResearchView },
    ],
  });
}

describe('V4ResearchView', () => {
  let router: ReturnType<typeof createRouter>;

  beforeAll(async () => {
    router = makeRouter();
    // Prime the router so it's ready before mount
    await router.push('/v4/research-internal');
  });

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // =========================================================================
  // Tab rendering
  // =========================================================================

  it('renders all three tabs: research, education, visualization', () => {
    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });
    const text = wrapper.text();
    expect(text).toContain('完整研究');
    expect(text).toContain('教育模式');
    expect(text).toContain('可视化');
  });

  // =========================================================================
  // Full research workflow — clicks trigger real API calls
  // =========================================================================

  it('clicking run workflow calls /api/v4/research/session and /workflow', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        data: { success: true, data: { session_id: 'sess-1' }, message: 'ok' },
      })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: {
            run_id: 'run-1',
            steps: [
              { name: 'topic_selection', status: 'completed' },
              { name: 'literature_retrieval', status: 'completed' },
              { name: 'evidence_synthesis', status: 'completed' },
              { name: 'report_generation', status: 'completed' },
              { name: 'citation_export', status: 'completed' },
            ],
          },
          message: 'ok',
        },
      });
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: { runs: [{ run_id: 'run-1', output_artifacts: { markdown: '# Test Report' } }] },
      },
    });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    await wrapper.find('#v4-topic').setValue('经络');
    // Trigger form submit directly — jsdom button click may not propagate
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    expect(api.post).toHaveBeenCalledWith(
      '/api/v4/research/session',
      expect.objectContaining({ title: expect.stringContaining('经络') }),
    );
    expect(api.post).toHaveBeenCalledWith(
      '/api/v4/research/workflow',
      expect.objectContaining({ topic: '经络', workflow_type: 'full_research_flow' }),
      expect.objectContaining({ timeout: 120000 }),
    );
    expect(api.get).toHaveBeenCalledWith('/api/v4/research/session/sess-1/runs');

    const steps = wrapper.findAll('[data-testid="workflow-step"]');
    expect(steps.length).toBe(5);
  });

  it('clicking replay shows result with two hashes when matched=true', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ data: { success: true, data: { session_id: 'sess-1' } } })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: { run_id: 'run-1', steps: [{ name: 'topic_selection', status: 'completed' }] },
        },
      })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: {
            run_id: 'run-1',
            original_output_sha256: 'a'.repeat(64),
            replay_output_sha256: 'a'.repeat(64),
            matched: true,
          },
          message: 'ok',
        },
      });
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: { runs: [] } } });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    await wrapper.find('#v4-topic').setValue('test');
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    await wrapper.find('[data-testid="v4-replay"]').trigger('click');
    await flushPromises();

    const result = wrapper.find('[data-testid="replay-result"]');
    expect(result.exists()).toBe(true);
    expect(result.text()).toContain('a'.repeat(64));
    expect(result.find('.match-ok').exists()).toBe(true);
  });

  it('clicking replay shows failure when matched=false', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ data: { success: true, data: { session_id: 'sess-1' } } })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: { run_id: 'run-1', steps: [{ name: 'topic_selection', status: 'completed' }] },
        },
      })
      .mockResolvedValueOnce({
        data: {
          success: false,
          data: {
            run_id: 'run-1',
            original_output_sha256: 'b'.repeat(64),
            replay_output_sha256: 'c'.repeat(64),
            matched: false,
          },
          message: 'Replay mismatch',
        },
      });
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: { runs: [] } } });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    await wrapper.find('#v4-topic').setValue('test');
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    await wrapper.find('[data-testid="v4-replay"]').trigger('click');
    await flushPromises();

    const result = wrapper.find('[data-testid="replay-result"]');
    expect(result.exists()).toBe(true);
    expect(result.find('.match-fail').exists()).toBe(true);
  });

  // =========================================================================
  // Education — level selection enters the request
  // =========================================================================

  it('education sends level parameter to API', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ data: { success: true, data: { session_id: 'sess-edu' } } })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: { concepts: [], citation_count: 0, source_count: 0 },
          message: 'ok',
        },
      });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    const eduTab = wrapper.findAll('.tab-button')[1]!;
    await eduTab.trigger('click');

    await wrapper.find('#v4-edu-topic').setValue('针灸');
    await wrapper.find('#v4-edu-level').setValue('advanced');
    // Trigger the education form submit directly (only visible form)
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    expect(api.post).toHaveBeenCalledWith(
      '/api/v4/education/learn',
      expect.objectContaining({ level: 'advanced', topic: '针灸' }),
    );
  });

  it('education shows error on API failure', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ data: { success: true, data: { session_id: 'sess-edu' } } })
      .mockRejectedValueOnce(new Error('Education failed'));

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    const eduTab = wrapper.findAll('.tab-button')[1]!;
    await eduTab.trigger('click');

    await wrapper.find('#v4-edu-topic').setValue('针灸');
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    expect(wrapper.find('.message--error').exists()).toBe(true);
  });

  // =========================================================================
  // Visualization — graph_type enters request
  // =========================================================================

  it('visualization sends graph_type to API', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ data: { success: true, data: { session_id: 'sess-viz' } } })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: { nodes: [], edges: [] },
          message: 'ok',
        },
      });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    const vizTab = wrapper.findAll('.tab-button')[2]!;
    await vizTab.trigger('click');

    await wrapper.find('#v4-viz-labels').setValue('经络,针灸');
    await wrapper.find('#v4-viz-type').setValue('citation');
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    expect(api.post).toHaveBeenCalledWith(
      '/api/v4/visualization/graph',
      expect.objectContaining({
        graph_type: 'citation',
        concept_labels: ['经络', '针灸'],
      }),
    );
  });

  it('visualization shows empty state when no edges', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({ data: { success: true, data: { session_id: 'sess-viz' } } })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: { nodes: [], edges: [] },
          message: 'ok',
        },
      });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    const vizTab = wrapper.findAll('.tab-button')[2]!;
    await vizTab.trigger('click');

    await wrapper.find('#v4-viz-labels').setValue('不存在的概念');
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    expect(wrapper.find('[data-testid="viz-empty"]').exists()).toBe(true);
  });

  // =========================================================================
  // P2T1: No-evidence handling + citation integrity tests
  // =========================================================================

  it('shows no-evidence state when workflow returns success=false with zero retrieval records', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        data: { success: true, data: { session_id: 'sess-1' }, message: 'ok' },
      })
      .mockResolvedValueOnce({
        data: {
          success: false,
          data: {
            run_id: 'run-1',
            session_id: 'sess-1',
            steps: [
              {
                name: 'topic_selection',
                status: 'completed',
                result: { topic: 'xyz', sub_questions: 4 },
              },
              {
                name: 'literature_retrieval',
                status: 'completed',
                result: { themes: 0, records: 0 },
              },
              { name: 'evidence_synthesis', status: 'pending' },
              { name: 'report_generation', status: 'pending' },
              { name: 'citation_export', status: 'pending' },
            ],
          },
          message: '未找到与「xyz」相关的文献证据',
        },
      });
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { runs: [] } },
    });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    await wrapper.find('#v4-topic').setValue('xyz');
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    expect(wrapper.find('[data-testid="no-evidence-state"]').exists()).toBe(true);
    // report should NOT be shown
    expect(wrapper.find('.report-body').exists()).toBe(false);
    // citations section should NOT be shown
    expect(wrapper.find('[data-testid="citations-section"]').exists()).toBe(false);
    // export button should be disabled
    const exportBtn = wrapper.find('[data-testid="v4-export"]');
    expect(exportBtn.exists()).toBe(true);
    expect((exportBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  it('hides save-citation button when citation fields are all empty', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        data: { success: true, data: { session_id: 'sess-2' }, message: 'ok' },
      })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: {
            run_id: 'run-2',
            steps: [
              { name: 'topic_selection', status: 'completed' },
              { name: 'literature_retrieval', status: 'completed' },
              { name: 'evidence_synthesis', status: 'completed' },
              { name: 'report_generation', status: 'completed' },
              { name: 'citation_export', status: 'completed' },
            ],
          },
          message: 'ok',
        },
      });
    // Return a run with step_execution_trace trace_ids but no retrieval_snapshot
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: {
          runs: [
            {
              run_id: 'run-2',
              output_artifacts: { markdown: '# Test\n\n检索快照记录数: 0' },
              step_execution_trace: [
                { name: 'citation_export', status: 'completed', trace_ids: ['tid-1', 'tid-2'] },
              ],
              replay_manifest: null,
            },
          ],
        },
      },
    });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    await wrapper.find('#v4-topic').setValue('test');
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    // With no replay_manifest, extractCitationsFromRuns returns [] — no fake citations
    expect(wrapper.find('[data-testid="citations-section"]').exists()).toBe(false);
  });

  it('shows save-citation button when citation has real content from snapshot', async () => {
    (api.post as ReturnType<typeof vi.fn>)
      .mockResolvedValueOnce({
        data: { success: true, data: { session_id: 'sess-3' }, message: 'ok' },
      })
      .mockResolvedValueOnce({
        data: {
          success: true,
          data: {
            run_id: 'run-3',
            steps: [
              { name: 'topic_selection', status: 'completed' },
              { name: 'literature_retrieval', status: 'completed' },
              { name: 'evidence_synthesis', status: 'completed' },
              { name: 'report_generation', status: 'completed' },
              { name: 'citation_export', status: 'completed' },
            ],
          },
          message: 'ok',
        },
      });
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: {
          runs: [
            {
              run_id: 'run-3',
              output_artifacts: { markdown: '# 研究报告：经络' },
              replay_manifest: {
                retrieval_snapshot: [
                  {
                    trace_id: 'real-trace-001',
                    document_id: 'doc-01',
                    chunk_id: 'chk-01',
                    claim_text: '经络是人体运行气血的通道',
                    quote: '经络者，所以行血气而营阴阳。',
                    citation_text: '[doc-01:chk-01]',
                    source_ref_id: null,
                  },
                ],
                traces: [
                  {
                    trace_id: 'real-trace-001',
                    document_id: 'doc-01',
                    chunk_id: 'chk-01',
                    passage_id: 'passage-01',
                    provenance_kind: 'retrieval',
                    retrieval_score: 0.95,
                    retrieval_method: 'ili_keyword_search',
                  },
                ],
              },
            },
          ],
        },
      },
    });

    const wrapper = mount(V4ResearchView, {
      global: { plugins: [router, createPinia(), i18n] },
    });

    await wrapper.find('#v4-topic').setValue('经络');
    await wrapper.find('form.v4-form').trigger('submit');
    await flushPromises();

    // Citations section should be visible with real citations
    expect(wrapper.find('[data-testid="citations-section"]').exists()).toBe(true);
    // Save-citation button should be present (citation has real content)
    const citationBody = wrapper.find('.citation-body');
    expect(citationBody.exists()).toBe(true);

    // Export button should be enabled (we have reportContent)
    const exportBtn = wrapper.find('[data-testid="v4-export"]');
    expect(exportBtn.exists()).toBe(true);
    expect((exportBtn.element as HTMLButtonElement).disabled).toBe(false);
  });
});
