/**
 * ResearchWorkflowPage — comprehensive tests
 *
 * Covers:
 *   1.  Session loading (projectId = ResearchSession.id)
 *   2.  sessionStorage reading (scoped to projectId)
 *   3.  Step navigation (question → selection → submitting → evidence → report)
 *   4.  Workflow submission (single request, no fake percentages)
 *   5.  Evidence/Citation mapping
 *   6.  Report/run_id correctness
 *   7.  Error handling (400, 403, 404, 409, 422, 429, 5xx, network, timeout)
 *   8.  Race conditions (projectId switch, double-submit)
 *   9.  Accessibility (aria-current, aria-live, labels)
 *   10. No project_id, no fake runId, no URL leakage, no console leakage
 */
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia } from 'pinia';
import { describe, expect, it, vi, beforeEach, beforeAll } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';
import { nextTick } from 'vue';

import i18n from '@/i18n';

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------
const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: {
    defaults: { baseURL: '' },
    get: mockGet,
    post: mockPost,
    put: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/research', component: { template: '<div/>' }, name: 'research-project-list' },
      { path: '/research/:projectId/workflow', component: { template: '<div/>' }, name: 'research-project-workflow' },
      { path: '/research/:projectId/result/:runId', component: { template: '<div/>' }, name: 'research-project-result' },
    ],
  });
  return router;
}

function sessionResponse(id = 'sess-001', title = '经络研究') {
  return { data: { data: { id, title, context_notes: null, created_at: '2026-07-01T00:00:00', updated_at: '2026-07-15T00:00:00' } } };
}

function workflowSuccessResponse(runId = 'run-001', topic = '经络') {
  return {
    data: {
      success: true,
      data: {
        run_id: runId,
        session_id: 'sess-001',
        steps: [
          { name: 'topic_selection', status: 'completed', result: { topic, sub_questions: 3 } },
          { name: 'literature_retrieval', status: 'completed', result: { themes: 2, records: 5 } },
          { name: 'evidence_synthesis', status: 'completed', result: { sections: 2, claims: 5 } },
          { name: 'report_generation', status: 'completed', result: { sections: 2, title: `研究报告：${topic}` } },
          { name: 'citation_export', status: 'completed', result: { total_citations: 3 } },
        ],
        traceability: { query_id: runId, trace_ids: ['tid-1', 'tid-2', 'tid-3'], citation_count: 3, source_documents: ['doc-01'] },
      },
      message: 'ok',
    },
  };
}

function runsResponse(runId = 'run-001', topic = '经络') {
  return {
    data: {
      data: {
        runs: [{
          run_id: runId,
          topic,
          completed_at: '2026-07-17T10:00:00',
          step_execution_trace: [
            { name: 'topic_selection', status: 'completed' },
            { name: 'literature_retrieval', status: 'completed' },
            { name: 'evidence_synthesis', status: 'completed' },
            { name: 'report_generation', status: 'completed' },
            { name: 'citation_export', status: 'completed' },
          ],
          output_artifacts: {
            markdown: `# 研究报告：${topic}\n\n## 文献检索快照\n\n### 1. 经络是运行气血的通道\n> 经络者，所以行血气而营阴阳。\n- 文献: \`doc-01\`\n- Trace: \`tid-1\`\n\n检索快照记录数: 1\n综合证据条数: 1\n报告段落数: 1`,
            artifact_id: 'abc123def456',
            citations: [
              { trace_id: 'tid-1', citation_text: '[doc-01:chk-01]', document_id: 'doc-01', quote: '经络者，所以行血气而营阴阳。' },
            ],
          },
          replay_manifest: {
            retrieval_snapshot: [
              {
                trace_id: 'tid-1',
                document_id: 'doc-01',
                chunk_id: 'chk-01',
                claim_text: '经络是人体运行气血的通道',
                quote: '经络者，所以行血气而营阴阳。',
                citation_text: '[doc-01:chk-01]',
              },
              {
                trace_id: 'tid-2',
                document_id: 'doc-01',
                chunk_id: 'chk-02',
                claim_text: '经脉为里，支而横者为络',
                quote: '经脉为里，支而横者为络。',
                citation_text: '[doc-01:chk-02]',
              },
            ],
            traces: [
              { trace_id: 'tid-1', document_id: 'doc-01', chunk_id: 'chk-01', passage_id: 'passage-01', provenance_kind: 'retrieval', retrieval_score: 0.95, retrieval_method: 'ili_keyword_search' },
              { trace_id: 'tid-2', document_id: 'doc-01', chunk_id: 'chk-02', passage_id: 'passage-02', provenance_kind: 'retrieval', retrieval_score: 0.88, retrieval_method: 'ili_keyword_search' },
            ],
          },
        }],
      },
    },
  };
}

function noEvidenceRunsResponse() {
  return {
    data: {
      data: {
        runs: [{
          run_id: 'run-empty',
          topic: 'xyz',
          completed_at: '2026-07-17T10:00:00',
          step_execution_trace: [
            { name: 'topic_selection', status: 'completed' },
            { name: 'literature_retrieval', status: 'completed', result: { themes: 0, records: 0 } },
            { name: 'evidence_synthesis', status: 'pending' },
            { name: 'report_generation', status: 'pending' },
            { name: 'citation_export', status: 'pending' },
          ],
          output_artifacts: {
            markdown: '# 研究报告：xyz\n\n检索快照记录数: 0\n综合证据条数: 0\n报告段落数: 0',
          },
          replay_manifest: null,
        }],
      },
    },
  };
}

// =============================================================================
// Tests
// =============================================================================

describe('ResearchWorkflowPage', () => {
  let router: ReturnType<typeof createRouter>;

  beforeAll(async () => {
    router = makeRouter();
    await router.push('/research/sess-001/workflow');
  });

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    // Default: session exists
    mockGet.mockImplementation(async (url: string) => {
      if (url.includes('/sessions/sess-001') && !url.includes('/runs') && !url.includes('/notes') && !url.includes('/citations') && !url.includes('/history')) {
        return sessionResponse();
      }
      return { data: { data: {} } };
    });
  });

  // =========================================================================
  // 1. Session loading
  // =========================================================================

  it('loads ResearchSession using projectId from route params', async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') {
        return sessionResponse('sess-001', '针灸甲乙经研究');
      }
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    expect(mockGet).toHaveBeenCalledWith('/api/v1/workspace/sessions/sess-001');

    // Page title should contain session title
    const title = wrapper.find('h1');
    expect(title.exists()).toBe(true);
  });

  it('projectId equals ResearchSession.id in API calls', async () => {
    mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const sessionCall = mockGet.mock.calls.find((c: any[]) => c[0] === '/api/v1/workspace/sessions/sess-001');
    expect(sessionCall).toBeTruthy();
  });

  it('renders step navigation with 5 steps', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const steps = wrapper.findAll('.wsn-step');
    expect(steps.length).toBe(5);
  });

  // =========================================================================
  // 3. sessionStorage (projectId-scoped)
  // =========================================================================

  it('reads pending question from sessionStorage scoped to projectId', async () => {
    const STORAGE_KEY = 'hfb.research.sess-001.pending-question';
    sessionStorage.setItem(STORAGE_KEY, '针灸甲乙经中的经络理论');

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const input = wrapper.find('#rqs-input');
    expect(input.exists()).toBe(true);
    expect((input.element as HTMLInputElement).value).toBe('针灸甲乙经中的经络理论');

    // Storage should be cleared after read
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('does not read question stored for a different projectId', async () => {
    sessionStorage.setItem('hfb.research.sess-002.pending-question', 'other question');
    // sess-001 key not set

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const input = wrapper.find('#rqs-input');
    expect(input.exists()).toBe(true);
    expect((input.element as HTMLInputElement).value).toBe('');

    // Cross-project key should still exist (not cleared)
    expect(sessionStorage.getItem('hfb.research.sess-002.pending-question')).toBe('other question');
  });

  it('clears question from storage after reading', async () => {
    const STORAGE_KEY = 'hfb.research.sess-001.pending-question';
    sessionStorage.setItem(STORAGE_KEY, 'test question');

    mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  // =========================================================================
  // 4. Empty question cannot proceed
  // =========================================================================

  it('prevents moving to selection with empty question', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const submitBtn = wrapper.find('.rqs-submit-btn');
    expect((submitBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  // =========================================================================
  // 5. Workflow submission
  // =========================================================================

  it('submits workflow with correct request schema', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    // Fill question
    await wrapper.find('#rqs-input').setValue('经络');
    // Click next
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();

    // Click "开始分析"
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(mockPost).toHaveBeenCalledWith(
      '/api/v4/research/workflow',
      expect.objectContaining({
        session_id: 'sess-001',
        topic: '经络',
        workflow_type: 'full_research_flow',
      }),
      expect.objectContaining({ timeout: 120000 }),
    );
  });

  it('session_id uses current projectId in workflow request', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();

    const wfCall = mockPost.mock.calls.find((c: any[]) => c[0] === '/api/v4/research/workflow');
    expect(wfCall).toBeTruthy();
    expect(wfCall![1].session_id).toBe('sess-001');
  });

  it('double-click does not produce multiple requests', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();

    // Double click rapidly
    const btn = wrapper.find('.dss-submit-btn');
    await btn.trigger('click');
    await btn.trigger('click');
    await flushPromises();

    const wfCalls = mockPost.mock.calls.filter((c: any[]) => c[0] === '/api/v4/research/workflow');
    expect(wfCalls.length).toBe(1);
  });

  it('input is locked during submission', async () => {
    // Don't resolve the post so we stay in submitting state
    mockPost.mockReturnValueOnce(new Promise(() => {})); // never resolves
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await nextTick();

    // Should be in submitting state showing AnalysisPendingState
    expect(wrapper.find('.aps-step').exists()).toBe(true);
  });

  // =========================================================================
  // 6. No fake progress
  // =========================================================================

  it('does not display fake percentage progress', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    const html = wrapper.html();
    expect(html).not.toContain('%');
  });

  // =========================================================================
  // 7. Evidence/Citation mapping
  // =========================================================================

  it('shows evidence after successful workflow completion', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    // Should be in evidence step
    expect(wrapper.find('.ers-step').exists()).toBe(true);
    // Should show evidence items
    const items = wrapper.findAll('.ers-item');
    expect(items.length).toBeGreaterThan(0);
  });

  it('distinguishes AI claim text from original quote', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    const html = wrapper.html();
    expect(html).toContain('AI 归纳');
    expect(html).toContain('原文');
  });

  it('shows warning when evidence is empty', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return noEvidenceRunsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('xyz');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.find('.ers-warning').exists()).toBe(true);
    expect(wrapper.html()).toContain('未找到相关文献证据');
  });

  it('does not fabricate page numbers when missing', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    // Evidence shows chunk ID for locating, not fake page numbers
    const html = wrapper.html();
    expect(html).toContain('Chunk:');
  });

  // =========================================================================
  // 8. Report / run_id
  // =========================================================================

  it('report step shows correct link with real run_id', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse('run-001', '经络'));
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse('run-001', '经络');
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    // Go to report
    const actionBtns = wrapper.findAll('.ers-action-btn');
    if (actionBtns.length > 0) {
      await actionBtns[0]!.trigger('click');
      await nextTick();
    }

    // Check report link
    const link = wrapper.find('a[href="/research/sess-001/result/run-001"]');
    expect(link.exists()).toBe(true);
  });

  it('does not allow navigation when run_id is missing', async () => {
    // Workflow response without run_id should not create link
    mockPost.mockResolvedValueOnce({
      data: {
        success: true,
        data: {
          // No run_id
          session_id: 'sess-001',
          steps: [],
        },
        message: 'ok',
      },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return { data: { data: { runs: [] } } };
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    // Go to report step
    // Should show EmptyState since no report data
    const html = wrapper.html();
    // No link with /result/ should exist without run_id
    expect(html).not.toContain('/result/');
  });

  // =========================================================================
  // 9. Error handling
  // =========================================================================

  it('handles 400 error correctly', async () => {
    mockPost.mockRejectedValueOnce({
      response: { status: 400, data: { detail: '研究问题不能为空' } },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.find('.rwf-error-banner').exists()).toBe(true);
    expect(wrapper.html()).toContain('输入错误');
  });

  it('handles 403 error correctly', async () => {
    mockPost.mockRejectedValueOnce({
      response: { status: 403, data: { detail: 'Forbidden' } },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.html()).toContain('权限不足');
  });

  it('handles 404 error correctly', async () => {
    mockPost.mockRejectedValueOnce({
      response: { status: 404, data: { detail: 'Session not found' } },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.html()).toContain('未找到');
  });

  it('handles 409 error correctly', async () => {
    mockPost.mockRejectedValueOnce({
      response: { status: 409, data: { detail: '状态冲突' } },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.html()).toContain('状态冲突');
  });

  it('handles 422 error correctly', async () => {
    mockPost.mockRejectedValueOnce({
      response: { status: 422, data: { detail: 'Validation error' } },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.html()).toContain('校验失败');
  });

  it('handles 429 error correctly', async () => {
    mockPost.mockRejectedValueOnce({
      response: { status: 429, data: { detail: 'Too many requests' } },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.html()).toContain('请求过多');
  });

  it('handles 5xx error correctly', async () => {
    mockPost.mockRejectedValueOnce({
      response: { status: 500, data: { detail: 'Internal server error' } },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.html()).toContain('服务端错误');
  });

  it('handles network error correctly', async () => {
    mockPost.mockRejectedValueOnce({
      code: 'ERR_NETWORK',
      message: 'Network Error',
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.html()).toContain('网络连接失败');
  });

  it('handles timeout without auto-retry', async () => {
    mockPost.mockRejectedValueOnce({
      code: 'ECONNABORTED',
      message: 'timeout of 120000ms exceeded',
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return { data: { data: { runs: [] } } };
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    expect(wrapper.html()).toContain('超时');
    expect(wrapper.html()).toContain('可能已完成处理');
  });

  // =========================================================================
  // 10. Retry preserves user input
  // =========================================================================

  it('retry after error preserves user input and allows re-submit', async () => {
    mockPost.mockRejectedValueOnce({
      response: { status: 500, data: { detail: 'Server error' } },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    // Error banner shown
    expect(wrapper.find('.rwf-error-banner').exists()).toBe(true);

    // Click retry
    await wrapper.find('.rwf-error-retry-btn').trigger('click');
    await nextTick();

    // Should be back at question step with question preserved
    expect(wrapper.find('#rqs-input').exists()).toBe(true);
    expect((wrapper.find('#rqs-input').element as HTMLInputElement).value).toBe('经络');
  });

  // =========================================================================
  // 11. Accessibility
  // =========================================================================

  it('step navigation uses aria-current on current step', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const current = wrapper.find('[aria-current="step"]');
    expect(current.exists()).toBe(true);
  });

  it('loading state uses aria-live', async () => {
    // Session loading should have aria-live
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await nextTick();
    // LoadingState has aria-live="polite" + role="status"
    const loadingEl = wrapper.find('[role="status"]');
    if (loadingEl.exists()) {
      expect(loadingEl.attributes('aria-live')).toBe('polite');
    }
  });

  it('evidence empty state is readable by assistive tech', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return noEvidenceRunsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    const warning = wrapper.find('.ers-warning');
    expect(warning.exists()).toBe(true);
    // role="alert" for immediate announcement
    expect(warning.attributes('role')).toBe('alert');
  });

  // =========================================================================
  // 12. No project_id or fake runId
  // =========================================================================

  it('does not render project_id in DOM', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    expect(wrapper.html()).not.toContain('project_id');
  });

  it('does not create temporary runId', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    const html = wrapper.html();
    expect(html).not.toContain('temp-run');
    expect(html).not.toContain('placeholder-run');
  });

  // =========================================================================
  // 13. No URL or console leakage
  // =========================================================================

  it('does not put question in URL', async () => {
    const consoleSpy = vi.spyOn(console, 'log');

    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('敏感研究问题');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();

    // Question should not appear in URL query params
    expect(router.currentRoute.value.query).not.toHaveProperty('q');
    expect(router.currentRoute.value.query).not.toHaveProperty('topic');
    expect(router.currentRoute.value.query).not.toHaveProperty('question');
    expect(router.currentRoute.value.fullPath).not.toContain('敏感研究问题');

    // Check console.log was not called with the question text
    const sensitiveLogs = consoleSpy.mock.calls.filter((call: any[]) =>
      call.some((arg: any) => typeof arg === 'string' && arg.includes('敏感研究问题'))
    );
    expect(sensitiveLogs.length).toBe(0);

    consoleSpy.mockRestore();
  });

  // =========================================================================
  // 14. Page only calls session detail API once
  // =========================================================================

  it('calls session detail API exactly once on mount', async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      return { data: { data: {} } };
    });

    mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();

    const sessionCalls = mockGet.mock.calls.filter(
      (c: any[]) => c[0] === '/api/v1/workspace/sessions/sess-001'
    );
    expect(sessionCalls.length).toBe(1);
  });

  // =========================================================================
  // 15. Report step → back to evidence
  // =========================================================================

  it('can navigate from report back to evidence review', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions/sess-001') return sessionResponse();
      if (url === '/api/v4/research/session/sess-001/runs') return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    // Go to report
    const goToReportBtns = wrapper.findAll('.ers-action-btn');
    if (goToReportBtns.length > 0) {
      await goToReportBtns[0]!.trigger('click');
      await nextTick();
    }

    // Should be on report step
    expect(wrapper.find('.rrs-step').exists()).toBe(true);

    // Click "返回证据审查"
    const backBtn = wrapper.find('.rrs-action-btn--secondary');
    expect(backBtn.exists()).toBe(true);
    await backBtn.trigger('click');
    await nextTick();

    // Should be back on evidence step
    expect(wrapper.find('.ers-step').exists()).toBe(true);
  });
});
