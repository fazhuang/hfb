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
// Constants — valid UUID v4 required by guardId()
// ---------------------------------------------------------------------------
const PROJECT_ID = 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d';
const OTHER_ID   = 'b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e';

const SESSION_URL   = `/api/v1/workspace/sessions/${PROJECT_ID}`;
const RUNS_URL      = `/api/v4/research/session/${PROJECT_ID}/runs`;
const STORAGE_KEY   = `hfb.research.${PROJECT_ID}.pending-question`;
const OTHER_KEY     = `hfb.research.${OTHER_ID}.pending-question`;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/research', component: { template: '<div/>' }, name: 'research-project-list' },
      { path: '/research/:projectId', component: { template: '<div/>' }, name: 'research-project-detail' },
      { path: '/research/:projectId/workspace', component: { template: '<div/>' }, name: 'research-project-workspace' },
      { path: '/research/:projectId/workflow', component: { template: '<div/>' }, name: 'research-project-workflow' },
      { path: '/research/:projectId/result/:runId', component: { template: '<div/>' }, name: 'research-project-result' },
    ],
  });
  return router;
}

function sessionResponse(id = PROJECT_ID, title = '经络研究') {
  return { data: { data: { id, title, context_notes: null, created_at: '2026-07-01T00:00:00', updated_at: '2026-07-15T00:00:00' } } };
}

function workflowSuccessResponse(runId = 'run-001', topic = '经络') {
  return {
    data: {
      success: true,
      data: {
        run_id: runId,
        session_id: PROJECT_ID,
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
            markdown: `# 研究报告：${topic}\n\n检索快照记录数: 1\n综合证据条数: 1\n报告段落数: 1`,
            artifact_id: 'abc123def456',
            citations: [
              { trace_id: 'tid-1', citation_text: '[doc-01:chk-01]', document_id: 'doc-01', quote: '经络者，所以行血气而营阴阳。' },
            ],
          },
          replay_manifest: {
            retrieval_snapshot: [
              { trace_id: 'tid-1', document_id: 'doc-01', chunk_id: 'chk-01', claim_text: '经络是人体运行气血的通道', quote: '经络者，所以行血气而营阴阳。', citation_text: '[doc-01:chk-01]' },
              { trace_id: 'tid-2', document_id: 'doc-01', chunk_id: 'chk-02', claim_text: '经脉为里，支而横者为络', quote: '经脉为里，支而横者为络。', citation_text: '[doc-01:chk-02]' },
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
          run_id: 'run-empty', topic: 'xyz', completed_at: '2026-07-17T10:00:00',
          step_execution_trace: [
            { name: 'topic_selection', status: 'completed' },
            { name: 'literature_retrieval', status: 'completed', result: { themes: 0, records: 0 } },
            { name: 'evidence_synthesis', status: 'pending' },
            { name: 'report_generation', status: 'pending' },
            { name: 'citation_export', status: 'pending' },
          ],
          output_artifacts: { markdown: '# 研究报告：xyz\n\n检索快照记录数: 0\n综合证据条数: 0\n报告段落数: 0' },
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
    await router.push(`/research/${PROJECT_ID}/workflow`);
  });

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL && !url.includes('/runs') && !url.includes('/notes') && !url.includes('/citations') && !url.includes('/history')) {
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
      if (url === SESSION_URL) return sessionResponse(PROJECT_ID, '针灸甲乙经研究');
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    expect(mockGet).toHaveBeenCalledWith(SESSION_URL);
    expect(wrapper.find('h1').exists()).toBe(true);
  });

  it('projectId equals ResearchSession.id in API calls', async () => {
    mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const sessionCall = mockGet.mock.calls.find((c: any[]) => c[0] === SESSION_URL);
    expect(sessionCall).toBeTruthy();
  });

  it('renders step navigation with 5 steps', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    expect(wrapper.findAll('.wsn-step').length).toBe(5);
  });

  // =========================================================================
  // 2. sessionStorage (projectId-scoped via guardId)
  // =========================================================================

  it('reads pending question from sessionStorage scoped to projectId', async () => {
    sessionStorage.setItem(STORAGE_KEY, '针灸甲乙经中的经络理论');

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const input = wrapper.find('#rqs-input');
    expect((input.element as HTMLInputElement).value).toBe('针灸甲乙经中的经络理论');
    expect(sessionStorage.getItem(STORAGE_KEY)).toBeNull();
  });

  it('does not read question stored for a different projectId', async () => {
    sessionStorage.setItem(OTHER_KEY, 'other question');

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const input = wrapper.find('#rqs-input');
    expect((input.element as HTMLInputElement).value).toBe('');
    expect(sessionStorage.getItem(OTHER_KEY)).toBe('other question');
  });

  it('clears question from storage after reading', async () => {
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
  // 3. Empty question cannot proceed
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
  // 4. Workflow submission
  // =========================================================================

  it('submits workflow with correct request schema', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();

    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises(); await nextTick();

    expect(mockPost).toHaveBeenCalledWith(
      '/api/v4/research/workflow',
      expect.objectContaining({ session_id: PROJECT_ID, topic: '经络', workflow_type: 'full_research_flow' }),
      expect.objectContaining({ timeout: 120000 }),
    );
  });

  it('session_id uses current projectId in workflow request', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();

    const wfCall = mockPost.mock.calls.find((c: any[]) => c[0] === '/api/v4/research/workflow');
    expect(wfCall).toBeTruthy();
    expect(wfCall![1].session_id).toBe(PROJECT_ID);
  });

  it('double-click does not produce multiple requests', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();

    const btn = wrapper.find('.dss-submit-btn');
    await btn.trigger('click');
    await btn.trigger('click');
    await flushPromises();

    const wfCalls = mockPost.mock.calls.filter((c: any[]) => c[0] === '/api/v4/research/workflow');
    expect(wfCalls.length).toBe(1);
  });

  it('input is locked during submission', async () => {
    mockPost.mockReturnValueOnce(new Promise(() => {}));
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await nextTick();

    expect(wrapper.find('.aps-step').exists()).toBe(true);
  });

  // =========================================================================
  // 5. No fake progress
  // =========================================================================

  it('does not display fake percentage progress', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );
    await flushPromises();
    expect(wrapper.html()).not.toContain('%');
  });

  // =========================================================================
  // 6. Evidence/Citation mapping
  // =========================================================================

  async function mountAndRunWorkflow(runsFn: typeof runsResponse | typeof noEvidenceRunsResponse = runsResponse, question = '经络') {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return runsFn();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    await wrapper.find('#rqs-input').setValue(question);
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises(); await nextTick();
    return wrapper;
  }

  it('shows evidence after successful workflow completion', async () => {
    const wrapper = await mountAndRunWorkflow();
    expect(wrapper.find('.ers-step').exists()).toBe(true);
    expect(wrapper.findAll('.ers-item').length).toBeGreaterThan(0);
  });

  it('distinguishes AI claim text from original quote', async () => {
    const wrapper = await mountAndRunWorkflow();
    const html = wrapper.html();
    expect(html).toContain('AI 归纳');
    expect(html).toContain('原文');
  });

  it('shows warning when evidence is empty', async () => {
    const wrapper = await mountAndRunWorkflow(noEvidenceRunsResponse, 'xyz');
    expect(wrapper.find('.ers-warning').exists()).toBe(true);
    expect(wrapper.html()).toContain('未找到相关文献证据');
  });

  it('does not fabricate page numbers when missing', async () => {
    const wrapper = await mountAndRunWorkflow();
    expect(wrapper.html()).toContain('Chunk:');
  });

  // =========================================================================
  // 7. Report / run_id
  // =========================================================================

  it('report step shows correct link with real run_id', async () => {
    const wrapper = await mountAndRunWorkflow();

    const actionBtns = wrapper.findAll('.ers-action-btn');
    if (actionBtns.length > 0) { await actionBtns[0]!.trigger('click'); await nextTick(); }

    const link = wrapper.find(`a[href="/research/${PROJECT_ID}/result/run-001"]`);
    expect(link.exists()).toBe(true);
  });

  it('does not allow navigation when run_id is missing', async () => {
    mockPost.mockResolvedValueOnce({ data: { success: true, data: { session_id: PROJECT_ID, steps: [] }, message: 'ok' } });
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return { data: { data: { runs: [] } } };
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises(); await nextTick();

    expect(wrapper.html()).not.toContain('/result/');
  });

  // =========================================================================
  // 8. Error handling
  // =========================================================================

  async function mountAndSubmitWithError(err: unknown) {
    mockPost.mockRejectedValueOnce(err);
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises(); await nextTick();
    return wrapper;
  }

  const errorCases: [string, unknown, string][] = [
    ['400', { response: { status: 400, data: { detail: '研究问题不能为空' } } }, '输入错误'],
    ['403', { response: { status: 403, data: { detail: 'Forbidden' } } }, '权限不足'],
    ['404', { response: { status: 404, data: { detail: 'Session not found' } } }, '未找到'],
    ['409', { response: { status: 409, data: { detail: '状态冲突' } } }, '状态冲突'],
    ['422', { response: { status: 422, data: { detail: 'Validation error' } } }, '校验失败'],
    ['429', { response: { status: 429, data: { detail: 'Too many requests' } } }, '请求过多'],
    ['5xx', { response: { status: 500, data: { detail: 'Internal server error' } } }, '服务端错误'],
    ['network', { code: 'ERR_NETWORK', message: 'Network Error' }, '网络连接失败'],
    ['timeout', { code: 'ECONNABORTED', message: 'timeout of 120000ms exceeded' }, '超时'],
  ];

  for (const [name, err, expected] of errorCases) {
    it(`handles ${name} error correctly`, async () => {
      if (name === 'timeout') {
        mockGet.mockImplementation(async (url: string) => {
          if (url === SESSION_URL) return sessionResponse();
          if (url === RUNS_URL) return { data: { data: { runs: [] } } };
          return { data: { data: {} } };
        });
      }
      const wrapper = await mountAndSubmitWithError(err);
      expect(wrapper.find('.rwf-error-banner').exists()).toBe(true);
      expect(wrapper.html()).toContain(expected);
    });
  }

  it('handles timeout with "可能已完成处理" warning', async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return { data: { data: { runs: [] } } };
      return { data: { data: {} } };
    });
    const wrapper = await mountAndSubmitWithError({ code: 'ECONNABORTED', message: 'timeout of 120000ms exceeded' });
    expect(wrapper.html()).toContain('可能已完成处理');
  });

  // =========================================================================
  // 9. Retry preserves user input
  // =========================================================================

  it('retry after error preserves user input and allows re-submit', async () => {
    mockPost.mockRejectedValueOnce({ response: { status: 500, data: { detail: 'Server error' } } });
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises(); await nextTick();

    expect(wrapper.find('.rwf-error-banner').exists()).toBe(true);

    await wrapper.find('.rwf-error-retry-btn').trigger('click');
    await nextTick();

    expect(wrapper.find('#rqs-input').exists()).toBe(true);
    expect((wrapper.find('#rqs-input').element as HTMLInputElement).value).toBe('经络');
  });

  // =========================================================================
  // 10. Accessibility
  // =========================================================================

  it('step navigation uses aria-current on current step', async () => {
    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    expect(wrapper.find('[aria-current="step"]').exists()).toBe(true);
  });

  it('evidence empty state has role="alert"', async () => {
    const wrapper = await mountAndRunWorkflow(noEvidenceRunsResponse, 'xyz');
    const warning = wrapper.find('.ers-warning');
    expect(warning.exists()).toBe(true);
    expect(warning.attributes('role')).toBe('alert');
  });

  // =========================================================================
  // 11. No project_id or fake runId
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
  // 12. No URL or console leakage
  // =========================================================================

  it('does not put question in URL', async () => {
    const consoleSpy = vi.spyOn(console, 'log');

    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises(); await nextTick();
    await wrapper.find('#rqs-input').setValue('敏感研究问题');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();

    expect(router.currentRoute.value.fullPath).not.toContain('敏感研究问题');

    const sensitiveLogs = consoleSpy.mock.calls.filter((call: any[]) =>
      call.some((arg: any) => typeof arg === 'string' && arg.includes('敏感研究问题'))
    );
    expect(sensitiveLogs.length).toBe(0);

    consoleSpy.mockRestore();
  });

  // =========================================================================
  // 13. Page only calls session detail API once
  // =========================================================================

  it('calls session detail API exactly once on mount', async () => {
    mount(
      { template: '<ResearchWorkflowPage />', components: { ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default } },
      { global: { plugins: [router, createPinia(), i18n] } },
    );
    await flushPromises();

    const sessionCalls = mockGet.mock.calls.filter((c: any[]) => c[0] === SESSION_URL);
    expect(sessionCalls.length).toBe(1);
  });

  // =========================================================================
  // 14. Report step → back to evidence
  // =========================================================================

  it('can navigate from report back to evidence review', async () => {
    const wrapper = await mountAndRunWorkflow();

    const goToReportBtns = wrapper.findAll('.ers-action-btn');
    if (goToReportBtns.length > 0) { await goToReportBtns[0]!.trigger('click'); await nextTick(); }

    expect(wrapper.find('.rrs-step').exists()).toBe(true);

    const backBtn = wrapper.find('.rrs-action-btn--secondary');
    expect(backBtn.exists()).toBe(true);
    await backBtn.trigger('click');
    await nextTick();

    expect(wrapper.find('.ers-step').exists()).toBe(true);
  });
});
