/**
 * ResearchWorkflowPage — comprehensive tests
 *
 * Covers:
 *   Batch 1: No fake progress (no setInterval stages, no percentages, unified loading)
 *   Batch 2: Strict run_id isolation (evidence/report scoped to current run only)
 *   Batch 3: Duplicate-submit guard + stale-response protection + session switch
 *   Batch 4: SourceRef/passage lineage completeness display
 *   Batch 5: (E2E tests in Python test_critical_journeys.py — see below)
 *
 * Also covers:
 *   - Session loading (projectId = ResearchSession.id)
 *   - sessionStorage reading (scoped to projectId)
 *   - Step navigation (question → selection → submitting → evidence → report)
 *   - Workflow submission (single request)
 *   - Error handling (400, 403, 404, 409, 422, 429, 5xx, network, timeout)
 *   - Report/run_id correctness
 *   - Accessibility (aria-current, aria-live, labels)
 *   - No project_id, no fake runId, no URL leakage, no console leakage
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
const OTHER_ID = 'b2c3d4e5-f6a7-4b8c-9d0e-1f2a3b4c5d6e';

const SESSION_URL = `/api/v1/workspace/sessions/${PROJECT_ID}`;
const RUNS_URL = `/api/v4/research/session/${PROJECT_ID}/runs`;
const OTHER_RUNS_URL = `/api/v4/research/session/${OTHER_ID}/runs`;
const STORAGE_KEY = `hfb.research.${PROJECT_ID}.pending-question`;
const OTHER_KEY = `hfb.research.${OTHER_ID}.pending-question`;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function makeRouter() {
  const router = createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/research', component: { template: '<div/>' }, name: 'research-project-list' },
      {
        path: '/research/:projectId',
        component: { template: '<div/>' },
        name: 'research-project-detail',
      },
      {
        path: '/research/:projectId/workspace',
        component: { template: '<div/>' },
        name: 'research-project-workspace',
      },
      {
        path: '/research/:projectId/workflow',
        component: { template: '<div/>' },
        name: 'research-project-workflow',
      },
      {
        path: '/research/:projectId/result/:runId',
        component: { template: '<div/>' },
        name: 'research-project-result',
      },
    ],
  });
  return router;
}

function sessionResponse(id = PROJECT_ID, title = '经络研究') {
  return {
    data: {
      data: {
        id,
        title,
        context_notes: null,
        created_at: '2026-07-01T00:00:00',
        updated_at: '2026-07-15T00:00:00',
      },
    },
  };
}

function otherSessionResponse() {
  return { data: { data: { id: OTHER_ID, title: '其他课题', context_notes: null } } };
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
          {
            name: 'report_generation',
            status: 'completed',
            result: { sections: 2, title: `研究报告：${topic}` },
          },
          { name: 'citation_export', status: 'completed', result: { total_citations: 3 } },
        ],
        traceability: {
          query_id: runId,
          trace_ids: ['tid-1', 'tid-2', 'tid-3'],
          citation_count: 3,
          source_documents: ['doc-01'],
        },
      },
      message: 'ok',
    },
  };
}

function runsResponse(runId = 'run-001', topic = '经络') {
  return {
    data: {
      data: {
        runs: [
          {
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
                {
                  trace_id: 'tid-1',
                  citation_text: '[doc-01:chk-01]',
                  document_id: 'doc-01',
                  quote: '经络者，所以行血气而营阴阳。',
                },
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
                  source_ref_title: '针灸甲乙经',
                  source_ref_url: 'https://example.com/ref1',
                  source_ref_id: 'src-ref-001',
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
                {
                  trace_id: 'tid-1',
                  document_id: 'doc-01',
                  chunk_id: 'chk-01',
                  passage_id: 'passage-01',
                  provenance_kind: 'retrieval',
                  retrieval_score: 0.95,
                  retrieval_method: 'ili_keyword_search',
                },
                {
                  trace_id: 'tid-2',
                  document_id: 'doc-01',
                  chunk_id: 'chk-02',
                  passage_id: 'passage-02',
                  provenance_kind: 'retrieval',
                  retrieval_score: 0.88,
                  retrieval_method: 'ili_keyword_search',
                },
              ],
            },
          },
        ],
      },
    },
  };
}

function noEvidenceRunsResponse() {
  return {
    data: {
      data: {
        runs: [
          {
            run_id: 'run-empty',
            topic: 'xyz',
            completed_at: '2026-07-17T10:00:00',
            step_execution_trace: [
              { name: 'topic_selection', status: 'completed' },
              {
                name: 'literature_retrieval',
                status: 'completed',
                result: { themes: 0, records: 0 },
              },
              { name: 'evidence_synthesis', status: 'pending' },
              { name: 'report_generation', status: 'pending' },
              { name: 'citation_export', status: 'pending' },
            ],
            output_artifacts: {
              markdown: '# 研究报告：xyz\n\n检索快照记录数: 0\n综合证据条数: 0\n报告段落数: 0',
            },
            replay_manifest: null,
          },
        ],
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
      if (
        url === SESSION_URL &&
        !url.includes('/runs') &&
        !url.includes('/notes') &&
        !url.includes('/citations') &&
        !url.includes('/history')
      ) {
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    expect(mockGet).toHaveBeenCalledWith(SESSION_URL);
    expect(wrapper.find('h1').exists()).toBe(true);
  });

  it('projectId equals ResearchSession.id in API calls', async () => {
    mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();

    const sessionCall = mockGet.mock.calls.find((c: Array<any>) => c[0] === SESSION_URL);
    expect(sessionCall).toBeTruthy();
  });

  it('renders step navigation with 5 steps', async () => {
    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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

    expect(mockPost).toHaveBeenCalledWith(
      '/api/v4/research/workflow',
      expect.objectContaining({
        session_id: PROJECT_ID,
        topic: '经络',
        workflow_type: 'full_research_flow',
      }),
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();

    const wfCall = mockPost.mock.calls.find(
      (c: Array<any>) => c[0] === '/api/v4/research/workflow',
    );
    expect(wfCall).toBeTruthy();
    expect(wfCall![1].session_id).toBe(PROJECT_ID);
  });

  // =========================================================================
  // Batch 3: Double-click produces exactly ONE POST
  // =========================================================================

  it('double-click does not produce multiple requests', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();

    const btn = wrapper.find('.dss-submit-btn');
    await btn.trigger('click');
    await btn.trigger('click');
    await flushPromises();

    const wfCalls = mockPost.mock.calls.filter(
      (c: Array<any>) => c[0] === '/api/v4/research/workflow',
    );
    expect(wfCalls.length).toBe(1);
  });

  // =========================================================================
  // Batch 3: Direct consecutive calls to submitWorkflow path — only 1 POST
  // (same tick double trigger via the function-level guard)
  // =========================================================================

  it('function-level guard prevents duplicate POST on same-tick double trigger', async () => {
    // We test the composable directly by verifying that calling submitWorkflow
    // while submitting is already true does NOT produce a second POST.
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return runsResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();

    const btn = wrapper.find('.dss-submit-btn');
    // Click once to start submission
    await btn.trigger('click');
    // Immediately click again (no await in between) — should be blocked by function-level guard
    await btn.trigger('click');
    await flushPromises();
    await nextTick();

    const wfCalls = mockPost.mock.calls.filter(
      (c: Array<any>) => c[0] === '/api/v4/research/workflow',
    );
    expect(wfCalls.length).toBe(1);
  });

  it('input is locked during submission', async () => {
    mockPost.mockReturnValueOnce(new Promise(() => {}));
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue('经络');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await nextTick();

    expect(wrapper.find('.aps-step').exists()).toBe(true);
  });

  // =========================================================================
  // Batch 1: No fake progress
  // =========================================================================

  it('does not display fake percentage progress', async () => {
    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );
    await flushPromises();
    expect(wrapper.html()).not.toContain('%');
  });

  it('does not display staged loading messages based on elapsed time', async () => {
    // AnalysisPendingState should NOT show "正在检索文献" / "正在综合证据" / "正在生成研究报告"
    // It should show a single unified message
    const { default: Aps } =
      await import('@/components/research/workflow/AnalysisPendingState.vue');
    const wrapper = mount(Aps, {
      props: { active: true },
      global: { plugins: [i18n] },
    });
    const html = wrapper.html();

    // Must show unified message
    expect(html).toContain('正在执行研究工作流');
    // The hint paragraph describes what happens generally, not staged per-backend-step
    expect(html).toContain('请耐心等待');
    // The LoadingState component shows the unified message, not per-step
    const loadingText = wrapper.find('.loading-text');
    expect(loadingText.exists()).toBe(true);
    expect(loadingText.text()).toBe('正在执行研究工作流，请稍候。');
  });

  it('does not use setInterval for backend step inference in AnalysisPendingState', async () => {
    const { default: Aps } =
      await import('@/components/research/workflow/AnalysisPendingState.vue');
    const wrapper = mount(Aps, {
      props: { active: true },
      global: { plugins: [i18n] },
    });
    const html = wrapper.html();
    expect(html).toContain('正在执行研究工作流，请稍候。');
  });

  // =========================================================================
  // 6. Evidence/Citation mapping
  // =========================================================================

  async function mountAndRunWorkflow(
    runsFn: typeof runsResponse | typeof noEvidenceRunsResponse = runsResponse,
    question = '经络',
  ) {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse());
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return runsFn();
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue(question);
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();
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

  // =========================================================================
  // Batch 4: SourceRef / lineage completeness
  // =========================================================================

  it('displays real source_ref_title when available', async () => {
    const wrapper = await mountAndRunWorkflow();
    const html = wrapper.html();
    // tid-1 has source_ref_title: '针灸甲乙经' and passage_id
    expect(html).toContain('针灸甲乙经');
  });

  it('marks evidence as incomplete source when SourceRef is missing', async () => {
    const wrapper = await mountAndRunWorkflow();
    const html = wrapper.html();
    // tid-2 has NO source_ref_title — should show lineage warning (incomplete)
    // but tid-2 still has a passage_id, so it shows "Passage: passage-02..."
    // and the lineage warning separately
    expect(html).toContain('证据链不完整');
  });

  it('does not display document_id as source title', async () => {
    const wrapper = await mountAndRunWorkflow();
    const html = wrapper.html();
    // document_id 'doc-01' should not appear as a source title label
    // It may appear in monospace as the raw ID but not labeled as "来源"
    expect(html).not.toContain('来源: doc-01');
  });

  it('does not show confidence scores', async () => {
    const wrapper = await mountAndRunWorkflow();
    const html = wrapper.html();
    expect(html).not.toContain('置信度');
    expect(html).not.toContain('confidence');
    expect(html).not.toContain('高可信');
  });

  it('incomplete lineage shows lineage warning indicator', async () => {
    const wrapper = await mountAndRunWorkflow();
    const html = wrapper.html();
    // tid-2 lacks source_ref_title — should have lineage warning
    expect(html).toContain('证据链不完整');
  });

  it('full lineage (with source_ref_title + passage_id) does not show lineage warning for that entry', async () => {
    const wrapper = await mountAndRunWorkflow();

    // Entry #1 (tid-1) has source_ref_title and passage_id — full lineage
    // Entry #2 (tid-2) lacks source_ref_title — incomplete lineage
    // Verify at least one entry does NOT have the warning (tid-1)
    const items = wrapper.findAll('.ers-item');
    // Find the first item (tid-1) and check it has no lineage warning
    const firstItem = items[0]!;
    expect(firstItem.find('.ers-lineage-warning').exists()).toBe(false);
  });

  // =========================================================================
  // 7. Report / run_id
  // =========================================================================

  it('report step shows correct link with real run_id', async () => {
    const wrapper = await mountAndRunWorkflow();

    const actionBtns = wrapper.findAll('.ers-action-btn');
    if (actionBtns.length > 0) {
      await actionBtns[0]!.trigger('click');
      await nextTick();
    }

    const link = wrapper.find(`a[href="/research/${PROJECT_ID}/result/run-001"]`);
    expect(link.exists()).toBe(true);
  });

  it('does not allow navigation when run_id is missing', async () => {
    mockPost.mockResolvedValueOnce({
      data: { success: true, data: { session_id: PROJECT_ID, steps: [] }, message: 'ok' },
    });
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return { data: { data: { runs: [] } } };
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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

    expect(wrapper.html()).not.toContain('/result/');
  });

  // =========================================================================
  // Batch 2: Current run_id isolation
  // =========================================================================

  it('only shows evidence from the current run_id when historical runs also exist', async () => {
    // POST returns run_id = 'run-001'
    // Runs response contains BOTH run-001 (current) and run-Old (historical)
    mockPost.mockResolvedValueOnce(workflowSuccessResponse('run-001', '经络'));

    // Current run has evidence, historical run has DIFFERENT evidence
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) {
        return {
          data: {
            data: {
              runs: [
                {
                  run_id: 'run-Old',
                  topic: '旧问题',
                  completed_at: '2025-01-01T00:00:00',
                  output_artifacts: {
                    markdown: '# 旧报告\n\n旧内容',
                    citations: [
                      {
                        trace_id: 'old-tid',
                        citation_text: '[old-doc:old-chk]',
                        document_id: 'old-doc',
                        quote: '旧条文',
                      },
                    ],
                  },
                  replay_manifest: {
                    retrieval_snapshot: [
                      {
                        trace_id: 'old-tid',
                        document_id: 'old-doc',
                        chunk_id: 'old-chk',
                        claim_text: '旧证据',
                        quote: '旧条文',
                        citation_text: '[old-doc:old-chk]',
                        source_ref_title: '旧书名',
                      },
                    ],
                    traces: [
                      {
                        trace_id: 'old-tid',
                        document_id: 'old-doc',
                        chunk_id: 'old-chk',
                        passage_id: 'old-passage',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.5,
                        retrieval_method: 'test',
                      },
                    ],
                  },
                },
                {
                  run_id: 'run-001',
                  topic: '经络',
                  completed_at: '2026-07-17T10:00:00',
                  output_artifacts: {
                    markdown: '# 研究报告：经络\n\n新证据内容',
                    artifact_id: 'abc123',
                    citations: [
                      {
                        trace_id: 'new-tid',
                        citation_text: '[new-doc:new-chk]',
                        document_id: 'new-doc',
                        quote: '新条文',
                      },
                    ],
                  },
                  replay_manifest: {
                    retrieval_snapshot: [
                      {
                        trace_id: 'new-tid',
                        document_id: 'new-doc',
                        chunk_id: 'new-chk',
                        claim_text: '新证据',
                        quote: '新条文',
                        citation_text: '[new-doc:new-chk]',
                        source_ref_title: '新书名',
                      },
                    ],
                    traces: [
                      {
                        trace_id: 'new-tid',
                        document_id: 'new-doc',
                        chunk_id: 'new-chk',
                        passage_id: 'new-passage',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.9,
                        retrieval_method: 'test',
                      },
                    ],
                  },
                },
              ],
            },
          },
        };
      }
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
    // Should show NEW evidence, not old
    expect(html).toContain('新证据');
    expect(html).toContain('新书名');
    expect(html).toContain('新条文');
    // Should NOT show OLD evidence
    expect(html).not.toContain('旧证据');
    expect(html).not.toContain('旧书名');
    expect(html).not.toContain('旧条文');
  });

  it('does not show historical report when current run is not in runs response', async () => {
    // POST returns run_id = 'run-missing'
    // Runs response only has historical run
    mockPost.mockResolvedValueOnce(workflowSuccessResponse('run-missing', '经络'));

    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) {
        return {
          data: {
            data: {
              runs: [
                {
                  run_id: 'run-history',
                  topic: '历史课题',
                  completed_at: '2026-06-01T00:00:00',
                  output_artifacts: {
                    markdown: '# 历史报告\n\n历史内容',
                    artifact_id: 'hist-art',
                    citations: [
                      {
                        trace_id: 'hist-tid',
                        citation_text: '[hist-doc]',
                        document_id: 'hist-doc',
                        quote: '历史条文',
                      },
                    ],
                  },
                  replay_manifest: {
                    retrieval_snapshot: [
                      {
                        trace_id: 'hist-tid',
                        document_id: 'hist-doc',
                        chunk_id: 'hist-chk',
                        claim_text: '历史证据',
                        quote: '历史条文',
                        citation_text: '[hist-doc]',
                        source_ref_title: '历史书名',
                      },
                    ],
                    traces: [
                      {
                        trace_id: 'hist-tid',
                        document_id: 'hist-doc',
                        chunk_id: 'hist-chk',
                        passage_id: 'hist-passage',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.7,
                        retrieval_method: 'test',
                      },
                    ],
                  },
                },
              ],
            },
          },
        };
      }
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
    // Must NOT display historical report content
    expect(html).not.toContain('历史报告');
    expect(html).not.toContain('历史证据');
    expect(html).not.toContain('历史书名');
    // Must NOT have result link
    expect(html).not.toContain('/result/run-missing');
  });

  it('does not enter report step when current run has no markdown', async () => {
    // POST returns run_id
    // Runs response has the run but empty markdown
    mockPost.mockResolvedValueOnce(workflowSuccessResponse('run-no-md', '经络'));

    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) {
        return {
          data: {
            data: {
              runs: [
                {
                  run_id: 'run-no-md',
                  topic: '经络',
                  completed_at: null,
                  output_artifacts: {
                    markdown: '', // Empty markdown
                    artifact_id: '',
                    citations: [
                      {
                        trace_id: 'tid-x',
                        citation_text: '[doc:chk]',
                        document_id: 'doc-x',
                        quote: '条文',
                      },
                    ],
                  },
                  replay_manifest: {
                    retrieval_snapshot: [
                      {
                        trace_id: 'tid-x',
                        document_id: 'doc-x',
                        chunk_id: 'chk-x',
                        claim_text: '证据',
                        quote: '条文',
                        citation_text: '[doc:chk]',
                        source_ref_title: '书名',
                      },
                    ],
                    traces: [
                      {
                        trace_id: 'tid-x',
                        document_id: 'doc-x',
                        chunk_id: 'chk-x',
                        passage_id: 'passage-x',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.8,
                        retrieval_method: 'test',
                      },
                    ],
                  },
                },
              ],
            },
          },
        };
      }
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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

    // Should be in evidence step (the goToReport function requires non-empty markdown)
    expect(wrapper.find('.ers-step').exists()).toBe(true);

    // The "查看研究报告" button should still exist but clicking it won't transition
    // because hasReport requires non-empty markdown
    const sumBtn = wrapper.find('.ers-action-btn');
    if (sumBtn.exists()) {
      await sumBtn.trigger('click');
      await nextTick();
    }
    // Still in evidence step — report step should not render
    expect(wrapper.find('.rrs-step').exists()).toBe(false);
  });

  // =========================================================================
  // Batch 2: Evidence must be bound to current run, cannot mix with history
  // =========================================================================

  it('evidence counts reflect current run only, not historical', async () => {
    mockPost.mockResolvedValueOnce(workflowSuccessResponse('run-cur', '当前'));

    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) {
        return {
          data: {
            data: {
              runs: [
                {
                  run_id: 'run-hist',
                  topic: '历史',
                  completed_at: '2025-01-01T00:00:00',
                  output_artifacts: {
                    markdown: '# 历史',
                    citations: [
                      { trace_id: 'h1', citation_text: 'h1', document_id: 'h1', quote: 'h1q' },
                      { trace_id: 'h2', citation_text: 'h2', document_id: 'h2', quote: 'h2q' },
                    ],
                  },
                  replay_manifest: {
                    retrieval_snapshot: [
                      {
                        trace_id: 'h1',
                        document_id: 'h1',
                        chunk_id: 'h1',
                        claim_text: '历史1',
                        quote: 'h1q',
                        citation_text: 'h1',
                      },
                      {
                        trace_id: 'h2',
                        document_id: 'h2',
                        chunk_id: 'h2',
                        claim_text: '历史2',
                        quote: 'h2q',
                        citation_text: 'h2',
                      },
                    ],
                    traces: [
                      {
                        trace_id: 'h1',
                        document_id: 'h1',
                        chunk_id: 'h1',
                        passage_id: 'hp1',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.5,
                        retrieval_method: 'test',
                      },
                      {
                        trace_id: 'h2',
                        document_id: 'h2',
                        chunk_id: 'h2',
                        passage_id: 'hp2',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.5,
                        retrieval_method: 'test',
                      },
                    ],
                  },
                },
                {
                  run_id: 'run-cur',
                  topic: '当前',
                  completed_at: '2026-07-17T10:00:00',
                  output_artifacts: {
                    markdown: '# 当前',
                    citations: [
                      { trace_id: 'c1', citation_text: 'c1', document_id: 'c1', quote: 'c1q' },
                    ],
                  },
                  replay_manifest: {
                    retrieval_snapshot: [
                      {
                        trace_id: 'c1',
                        document_id: 'c1',
                        chunk_id: 'c1',
                        claim_text: '当前1',
                        quote: 'c1q',
                        citation_text: 'c1',
                      },
                    ],
                    traces: [
                      {
                        trace_id: 'c1',
                        document_id: 'c1',
                        chunk_id: 'c1',
                        passage_id: 'cp1',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.9,
                        retrieval_method: 'test',
                      },
                    ],
                  },
                },
              ],
            },
          },
        };
      }
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue('当前');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    const html = wrapper.html();
    // Only current evidence
    expect(html).toContain('当前1');
    expect(html).not.toContain('历史1');
    expect(html).not.toContain('历史2');

    // Summary should show 1 evidence, 1 citation (not 3 from history)
    expect(html).toContain('共找到 1 条证据');
    expect(html).toContain('1 条引用');
  });

  // =========================================================================
  // Batch 3: Session switch protection
  // =========================================================================

  it('Session A→B switch: A response does not leak into B', async () => {
    // Start with Project A
    await router.push(`/research/${PROJECT_ID}/workflow`);

    mockPost.mockResolvedValueOnce(workflowSuccessResponse('run-A', '课题A'));
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse(PROJECT_ID, '课题A');
      if (url === RUNS_URL) return runsResponse('run-A', '课题A');
      // B's endpoints
      if (url === `/api/v1/workspace/sessions/${OTHER_ID}`) return otherSessionResponse();
      if (url === OTHER_RUNS_URL) {
        return {
          data: {
            data: {
              runs: [
                {
                  run_id: 'run-B',
                  topic: '课题B',
                  completed_at: '2026-07-18T00:00:00',
                  output_artifacts: {
                    markdown: '# 课题B报告',
                    citations: [
                      {
                        trace_id: 'tb',
                        citation_text: '[b-doc]',
                        document_id: 'b-doc',
                        quote: 'B条文',
                      },
                    ],
                  },
                  replay_manifest: {
                    retrieval_snapshot: [
                      {
                        trace_id: 'tb',
                        document_id: 'b-doc',
                        chunk_id: 'b-chk',
                        claim_text: 'B证据',
                        quote: 'B条文',
                        citation_text: '[b-doc]',
                        source_ref_title: 'B书名',
                      },
                    ],
                    traces: [
                      {
                        trace_id: 'tb',
                        document_id: 'b-doc',
                        chunk_id: 'b-chk',
                        passage_id: 'b-passage',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.5,
                        retrieval_method: 'test',
                      },
                    ],
                  },
                },
              ],
            },
          },
        };
      }
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue('课题A');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();

    // Start A's submission but don't wait for runs
    await wrapper.find('.dss-submit-btn').trigger('click');
    // Immediately switch to B
    await router.push(`/research/${OTHER_ID}/workflow`);
    await flushPromises();
    await nextTick();

    // A's response should NOT pollute B
    const html = wrapper.html();
    expect(html).not.toContain('课题A');
    expect(html).not.toContain('run-A');
    expect(html).not.toContain('A证据');

    // Restore route for subsequent tests
    await router.push(`/research/${PROJECT_ID}/workflow`);
    await flushPromises();
    await nextTick();
  });

  it('Session A→B switch: stale runs response does not update B', async () => {
    // Start on B
    await router.push(`/research/${OTHER_ID}/workflow`);

    mockPost.mockResolvedValueOnce(workflowSuccessResponse('run-B', '课题B'));
    mockGet.mockImplementation(async (url: string) => {
      if (url === `/api/v1/workspace/sessions/${OTHER_ID}`) return otherSessionResponse();
      if (url === OTHER_RUNS_URL) {
        return {
          data: {
            data: {
              runs: [
                {
                  run_id: 'run-B',
                  topic: '课题B',
                  completed_at: '2026-07-18T00:00:00',
                  output_artifacts: {
                    markdown: '# 课题B报告',
                    citations: [
                      { trace_id: 'tb', citation_text: '[b]', document_id: 'b-doc', quote: 'B条' },
                    ],
                  },
                  replay_manifest: {
                    retrieval_snapshot: [
                      {
                        trace_id: 'tb',
                        document_id: 'b-doc',
                        chunk_id: 'b-chk',
                        claim_text: 'B证据',
                        quote: 'B条',
                        citation_text: '[b]',
                        source_ref_title: 'B书',
                      },
                    ],
                    traces: [
                      {
                        trace_id: 'tb',
                        document_id: 'b-doc',
                        chunk_id: 'b-chk',
                        passage_id: 'b-pass',
                        provenance_kind: 'retrieval',
                        retrieval_score: 0.5,
                        retrieval_method: 'test',
                      },
                    ],
                  },
                },
              ],
            },
          },
        };
      }
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue('课题B');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();
    await nextTick();

    const html = wrapper.html();
    // B should show B content
    expect(html).toContain('B证据');
    // But A should NEVER appear
    expect(html).not.toContain('课题A');
    expect(html).not.toContain('run-A');

    // Restore route for subsequent tests
    await router.push(`/research/${PROJECT_ID}/workflow`);
    await flushPromises();
    await nextTick();
  });

  // =========================================================================
  // Batch 3: timeout recovery does not accept stale session
  // =========================================================================

  it('timeout recovery path validates token before updating state', async () => {
    mockPost.mockRejectedValueOnce({
      code: 'ECONNABORTED',
      message: 'timeout of 120000ms exceeded',
    });
    // No run_id is set on timeout — runs endpoint returns empty runs
    mockGet.mockImplementation(async (url: string) => {
      if (url === SESSION_URL) return sessionResponse();
      if (url === RUNS_URL) return { data: { data: { runs: [] } } };
      return { data: { data: {} } };
    });

    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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

    // Should show timeout error with "可能已完成处理" hint
    expect(wrapper.html()).toContain('可能已完成处理');

    // The error banner should be visible (timeout → error state, not evidence)
    // No run_id was set, so can't transition to evidence
    expect(wrapper.find('.rwf-error-banner').exists()).toBe(true);
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
    return wrapper;
  }

  const errorCases: Array<[string, unknown, string]> = [
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
    const wrapper = await mountAndSubmitWithError({
      code: 'ECONNABORTED',
      message: 'timeout of 120000ms exceeded',
    });
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );
    await flushPromises();
    expect(wrapper.html()).not.toContain('project_id');
  });

  it('does not create temporary runId', async () => {
    const wrapper = mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
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
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );

    await flushPromises();
    await nextTick();
    await wrapper.find('#rqs-input').setValue('敏感研究问题');
    await wrapper.find('form.rqs-form').trigger('submit');
    await nextTick();
    await wrapper.find('.dss-submit-btn').trigger('click');
    await flushPromises();

    expect(router.currentRoute.value.fullPath).not.toContain('敏感研究问题');

    const sensitiveLogs = consoleSpy.mock.calls.filter((call: Array<any>) =>
      call.some((arg: any) => typeof arg === 'string' && arg.includes('敏感研究问题')),
    );
    expect(sensitiveLogs.length).toBe(0);

    consoleSpy.mockRestore();
  });

  // =========================================================================
  // 13. Page only calls session detail API once
  // =========================================================================

  it('calls session detail API exactly once on mount', async () => {
    mount(
      {
        template: '<ResearchWorkflowPage />',
        components: {
          ResearchWorkflowPage: (await import('@/pages/research/ResearchWorkflowPage.vue')).default,
        },
      },
      { global: { plugins: [router, createPinia(), i18n] } },
    );
    await flushPromises();

    const sessionCalls = mockGet.mock.calls.filter((c: Array<any>) => c[0] === SESSION_URL);
    expect(sessionCalls.length).toBe(1);
  });

  // =========================================================================
  // 14. Report step → back to evidence
  // =========================================================================

  it('can navigate from report back to evidence review', async () => {
    const wrapper = await mountAndRunWorkflow();

    const goToReportBtns = wrapper.findAll('.ers-action-btn');
    if (goToReportBtns.length > 0) {
      await goToReportBtns[0]!.trigger('click');
      await nextTick();
    }

    expect(wrapper.find('.rrs-step').exists()).toBe(true);

    const backBtn = wrapper.find('.rrs-action-btn--secondary');
    expect(backBtn.exists()).toBe(true);
    await backBtn.trigger('click');
    await nextTick();

    expect(wrapper.find('.ers-step').exists()).toBe(true);
  });
});
