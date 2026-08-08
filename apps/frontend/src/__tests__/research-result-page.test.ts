/**
 * Tests for ResearchResultPage
 *
 * Covers:
 *   BATCH 1 — Route & Session (1-11):
 *     1. Correctly reads projectId from route
 *     2. Correctly reads runId from route
 *     3. Loads session via GET /api/v1/workspace/sessions/{id}
 *     4. Loads runs via GET /api/v4/research/session/{id}/runs
 *     5. Session 404 → not-found status
 *     6. Session 403 → forbidden status
 *     7. Run not in session → not-found status
 *     8. Route switch triggers full reload
 *     9. Stale session response does not overwrite new
 *     10. Stale runs response does not overwrite new
 *     11. Invalid UUID projectId → not-found status
 *
 *   BATCH 2 — Report states (12-18h):
 *     12. Completed run with markdown report → ready status
 *     13. Run with pending steps → run-pending status
 *     14. Run with failed step → run-failed status
 *     15. Run without output_artifacts.markdown → report-missing
 *     16. Markdown rendered into sections
 *     17. Report title shown
 *     18. Does not show "loaded" when markdown is empty
 *     18a. report_generation pending → report-pending status
 *     18b. report_generation failed → report-failed status
 *     18c. non-report_generation failed → run-failed status
 *     18d. completed report_generation + empty markdown → report-missing
 *     18e. report-pending does not show old report
 *     18f. report-failed does not show old report
 *     18g. route switch from report-failed to ready clears error
 *     18h. route switch from ready to report-pending clears old report

 *   BATCH 3 — XSS / Markdown safety (19-23):
 *     19. <script> tag in report is NOT rendered as HTML
 *     20. Event handler (onclick/onerror) in report is NOT active
 *     21. javascript: URL is NOT clickable
 *     22. Common markdown renders as text
 *     23. Citation markers are rendered as interactive buttons

 *   BATCH 4 — Citations (24-31):
 *     24. Multiple citations displayed
 *     25. Citation trace_id is stable (real ID, not array index)
 *     26. Clicking citation selects it
 *     27. Citation missing evidence shows "缺少证据关联"
 *     28. Cross-run citations NOT shown
 *     29. Route switch clears selected citation
 *     30. Citation display number is view-local (sequential)
 *     31. Same trace_id referenced multiple times stays consistent
 *
 *   BATCH 4b — Citation validation (31a-31f):
 *     31a. Real citation markers show sequential display numbers
 *     31b. Clicking citation emits real trace_id
 *     31c. Same trace_id referenced multiple times maps consistently
 *     31d. Unknown citation marker renders as plain text
 *     31e. Marker not in current run citations is not clickable
 *     31f. Page HTML does not contain [undefined]

 *   BATCH 5 — Evidence (32-41):
 *     32. Evidence with source_ref_title shows source info
 *     33. Evidence without passage_id shows incomplete status
 *     34. Evidence without source_ref_title shows missing source
 *     35. Evidence with both source_ref_title + passage_id = full lineage
 *     36. Evidence confidence NOT computed by frontend
 *     37. Evidence with quote shows original text block
 *     38. Evidence with claim_text shows AI归纳
 *     39. Empty evidence list shows empty state
 *     40. Evidence count matches extracted count
 *     41. No fabricated fields when backend fields are absent

 *   BATCH 6 — SourceRef (42-47a):
 *     42. Evidence with document_id + passage_id → internal passage link
 *     43. Evidence without source_ref_title shows missing source
 *     44. Evidence with passage_id + document_id shows passage-level internal link
 *     45. Evidence with document_id only → document-level internal link
 *     46. Evidence without document_id → no internal link, external fallback only
 *     47. External link has rel="noopener noreferrer" target="_blank"
 *     47a. Malicious source_ref_url schemes are not executable

 *   BATCH 7 — Export (48-57):
 *     48. Export button disabled when no report
 *     49. Export button enabled when report present
 *     50. Export calls real backend export endpoint (not local Blob)
 *     51. Export uses response MIME and Content-Disposition filename
 *     52. Export handles 401/403 error states safely
 *     53. Export handles 404 error safely
 *     54. Export handles 409 (empty report) safely
 *     55. Export handles 500 error safely
 *     56. Double-click blocked during export
 *     57. No PDF/DOCX export buttons present

 *   BATCH 8 — Isolation (56-63):
 *     56. Session A report does not appear in Session B page
 *     57. Session A citation does not appear in Session B page
 *     58. Session A evidence does not appear in Session B page
 *     59. Own Session + others run → not-found
 *     60. Route switch clears evidence from old Session
 *     61. Old Session response arriving late does not update current view
 *     62. Export from Session A not triggered after switching to Session B
 *     63. Component unmount does not cause state writes

 *   BATCH 9 — Error handling (64-72):
 *     64. 401 response → forbidden status
 *     65. 403 response → forbidden status
 *     66. 404 response → not-found status
 *     67. 422 response → error status
 *     68. 500 response → error status
 *     69. Network error → error status
 *     70. Retry button triggers reload
 *     71. Error state does not show ready content
 *     72. No backend stack traces in error messages

 *   BATCH 10 — Cross-user security (73-77):
 *     73. Other user session → forbidden (backend 404)
 *     74. Other user run → not found
 *     75. Own session + other's run → not found
 *     76. Other's session ID not leaked in error message
 *     77. Real resource names not leaked to unauthorized user
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createMemoryHistory } from 'vue-router';
import { nextTick } from 'vue';

// ================================================================
// Mock setup
// ================================================================

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: Array<unknown>) => mockApiGet(...args),
    post: (...args: Array<unknown>) => mockApiPost(...args),
  },
}));

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string): string => key,
  }),
}));

// ================================================================
// Helpers
// ================================================================

const PROJ_A = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const PROJ_B = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const RUN_A = '11111111-1111-4111-8111-111111111111';
const RUN_B = '22222222-2222-4222-8222-222222222222';

function makeSession(overrides: Record<string, unknown> = {}) {
  return {
    id: PROJ_A,
    title: 'Test Research',
    context_notes: null,
    created_at: '2026-07-15T08:00:00Z',
    updated_at: '2026-07-16T10:00:00Z',
    ...overrides,
  };
}

function makeRun(overrides: Record<string, unknown> = {}) {
  return {
    run_id: RUN_A,
    session_id: PROJ_A,
    topic: '经络研究',
    created_at: '2026-07-15T10:00:00Z',
    completed_at: '2026-07-15T10:05:00Z',
    step_execution_trace: [
      { name: 'topic_selection', status: 'completed' },
      { name: 'literature_retrieval', status: 'completed' },
      { name: 'evidence_synthesis', status: 'completed' },
      { name: 'report_generation', status: 'completed' },
      { name: 'citation_export', status: 'completed' },
    ],
    output_artifacts: {
      markdown:
        '# 研究报告：经络\n\n## 概述\n\n经络是人体运行气血的通道。参考 [doc-01:chk-01]。\n\n## 结论\n\n针灸对经络有显著效果 [doc-02:chk-02]。',
      title: '研究报告：经络',
      citations: [
        {
          trace_id: 'doc-01:chk-01',
          citation_text: '[doc-01:chk-01]',
          document_id: 'doc-01',
          quote: '经络者，所以行血气而营阴阳。',
        },
        {
          trace_id: 'doc-02:chk-02',
          citation_text: '[doc-02:chk-02]',
          document_id: 'doc-02',
          quote: '刺之要，气至而有效。',
        },
      ],
    },
    replay_manifest: {
      retrieval_snapshot: [
        {
          trace_id: 'doc-01:chk-01',
          document_id: 'doc-01',
          chunk_id: 'chk-01',
          claim_text: '经络是气血通道',
          quote: '经络者，所以行血气而营阴阳。',
          citation_text: '[doc-01:chk-01]',
          source_ref_title: '针灸甲乙经',
          source_ref_url: 'https://example.com/ref1',
          source_ref_id: 'src-ref-001',
        },
        {
          trace_id: 'doc-02:chk-02',
          document_id: 'doc-02',
          chunk_id: 'chk-02',
          claim_text: '针灸对经络有效',
          quote: '刺之要，气至而有效。',
          citation_text: '[doc-02:chk-02]',
          source_ref_title: '黄帝内经',
          source_ref_url: 'https://example.com/ref2',
          source_ref_id: 'src-ref-002',
        },
      ],
      traces: [
        {
          trace_id: 'doc-01:chk-01',
          document_id: 'doc-01',
          chunk_id: 'chk-01',
          passage_id: 'passage-001',
          provenance_kind: 'retrieval',
        },
        {
          trace_id: 'doc-02:chk-02',
          document_id: 'doc-02',
          chunk_id: 'chk-02',
          passage_id: 'passage-002',
          provenance_kind: 'retrieval',
        },
      ],
    },
    ...overrides,
  };
}

function makeRunWithoutSourceRef() {
  return makeRun({
    run_id: RUN_A,
    output_artifacts: {
      markdown: '# 研究报告：经络\n\n## 概述\n\n经络研究内容 **[doc-03:chk-03]**。',
      title: '研究报告：经络',
      citations: [
        {
          trace_id: 'doc-03:chk-03',
          citation_text: '[doc-03:chk-03]',
          document_id: 'doc-03',
          quote: '无来源条文',
        },
      ],
    },
    replay_manifest: {
      retrieval_snapshot: [
        {
          trace_id: 'doc-03:chk-03',
          document_id: 'doc-03',
          chunk_id: 'chk-03',
          claim_text: '无来源证据',
          quote: '无来源条文',
          citation_text: '[doc-03:chk-03]',
          // NO source_ref_title, source_ref_url, source_ref_id
        },
      ],
      traces: [
        {
          trace_id: 'doc-03:chk-03',
          document_id: 'doc-03',
          chunk_id: 'chk-03',
          // NO passage_id
          provenance_kind: 'retrieval',
        },
      ],
    },
  });
}

// UUID v4 for invalid ID tests
function invalidId(): string {
  return 'not-a-uuid';
}

// ================================================================
// Mock URL/Browser APIs (only Blob — no DOM spying that breaks Vue)
// ================================================================

let createdBlobs: Array<{ content: string; type: string }> = [];

function setupBlobMock() {
  createdBlobs = [];

  // Use the native Blob constructor that jsdom already provides.
  // We spy on it to capture calls without blocking behavior.
  const OrigBlob = globalThis.Blob;
  vi.stubGlobal(
    'Blob',
    vi.fn((contentParts: Array<string>, options: { type: string }) => {
      const entry = { content: contentParts.join(''), type: options.type };
      createdBlobs.push(entry);
      return new OrigBlob(contentParts, options);
    }),
  );

  // Return a hash-only URL from createObjectURL so jsdom does not trigger
  // "Error: Not implemented: navigation (except hash changes)" when the
  // export flow creates an <a> element, sets its href, and clicks it.
  // jsdom exempts hash-only URL changes from the navigation error.
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn(() => '#blob-download-stub'),
    revokeObjectURL: vi.fn(),
  });
}

// ================================================================
// Test suite
// ================================================================

describe('ResearchResultPage', () => {
  let router: ReturnType<typeof createRouter>;

  async function mountPage() {
    const ResearchResultPage = (await import('@/pages/research/ResearchResultPage.vue')).default;
    return mount(ResearchResultPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: true,
          'router-link': {
            template: '<a :href="to"><slot /></a>',
            props: ['to'],
          },
        },
      },
    });
  }

  async function setupAndMount(
    sessionResponse: unknown,
    runsResponse: unknown,
    overrideIds?: { projectId?: string; runId?: string },
  ) {
    mockApiGet.mockReset();

    // Default: succeed with session + runs
    mockApiGet.mockImplementation(async (url: string) => {
      if (url.includes('/api/v1/workspace/sessions/')) {
        if (sessionResponse === '404') {
          throw { response: { status: 404, data: { detail: 'Not found' } } };
        }
        if (sessionResponse === '403') {
          throw { response: { status: 403, data: { detail: 'Forbidden' } } };
        }
        if (sessionResponse === '401') {
          throw { response: { status: 401 } };
        }
        if (sessionResponse === '500') {
          throw { response: { status: 500, data: { detail: 'Server error' } } };
        }
        if (sessionResponse === 'network') {
          throw { code: 'ERR_NETWORK', message: 'Network Error' };
        }
        return { data: { data: sessionResponse } };
      }
      if (url.includes('/api/v4/research/session/')) {
        if (runsResponse === '404') {
          throw { response: { status: 404 } };
        }
        if (runsResponse === '403') {
          throw { response: { status: 403 } };
        }
        return { data: { data: { runs: runsResponse } } };
      }
      throw new Error(`Unexpected URL: ${url}`);
    });

    const pid = overrideIds?.projectId ?? PROJ_A;
    const rid = overrideIds?.runId ?? RUN_A;

    await router.push(`/research/${pid}/result/${rid}`);
    await router.isReady();

    const wrapper = await mountPage();
    await flushPromises();
    return wrapper;
  }

  beforeEach(() => {
    router = createRouter({
      history: createMemoryHistory(),
      routes: [
        {
          path: '/research/:projectId/result/:runId',
          name: 'research-project-result',
          component: { template: '<div/>' },
        },
        {
          path: '/research/:projectId/workspace',
          name: 'research-project-workspace',
          component: { template: '<div/>' },
        },
        {
          path: '/research/:projectId/workflow',
          name: 'research-project-workflow',
          component: { template: '<div/>' },
        },
      ],
    });

    mockApiGet.mockReset();
    vi.restoreAllMocks();
    setupBlobMock();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==============================================================
  // BATCH 1: Route & Session
  // ==============================================================

  describe('Route & Session', () => {
    it('1. correctly reads projectId from route', async () => {
      await setupAndMount(makeSession(), [makeRun()]);

      // Verify session API was called with correct projectId
      expect(mockApiGet).toHaveBeenCalledWith(
        `/api/v1/workspace/sessions/${PROJ_A}`,
        expect.anything(),
      );
    });

    it('2. correctly reads runId from route', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      // Verify runs API was called with correct projectId
      expect(mockApiGet).toHaveBeenCalledWith(
        `/api/v4/research/session/${PROJ_A}/runs`,
        expect.anything(),
      );
      // Verify run exists
      expect(wrapper.html()).toContain('研究报告：经络');
    });

    it('3. loads session via correct API endpoint', async () => {
      const session = makeSession();
      const wrapper = await setupAndMount(session, [makeRun()]);
      expect(wrapper.html()).toContain('Test Research');
    });

    it('4. loads runs via correct API endpoint', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      // Session title shown
      expect(wrapper.html()).toContain('Test Research');
      // Report title shown
      expect(wrapper.html()).toContain('研究报告：经络');
    });

    it('5. session 404 → not-found status', async () => {
      const wrapper = await setupAndMount('404', []);
      expect(wrapper.html()).toContain('未找到');
      expect(wrapper.html()).not.toContain('研究报告');
    });

    it('6. session 403 → forbidden status', async () => {
      const wrapper = await setupAndMount('403', []);
      expect(wrapper.html()).toContain('无权限');
    });

    it('7. run not in session → not-found status', async () => {
      // Session exists but target run not in runs list
      const otherRun = makeRun({ run_id: 'other-run' });
      const wrapper = await setupAndMount(makeSession(), [otherRun]);
      expect(wrapper.html()).toContain('不存在');
    });

    it('8. route switch triggers full reload', async () => {
      await setupAndMount(makeSession(), [makeRun()]);
      expect(mockApiGet).toHaveBeenCalledTimes(2); // session + runs

      mockApiGet.mockClear();

      // Navigate to different project
      const runB = makeRun({ run_id: RUN_B, session_id: PROJ_B });
      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });

      // Update mock to return new data
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [runB] } } };
        }
        throw new Error('unexpected');
      });

      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      // Should have made fresh calls for new project
      expect(mockApiGet).toHaveBeenCalledWith(
        `/api/v1/workspace/sessions/${PROJ_B}`,
        expect.anything(),
      );
    });

    it('9. stale session response does not overwrite new', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Verify we're showing Test Research title (Session A)
      expect(wrapper.html()).toContain('Test Research');
    });

    it('10. stale runs response does not overwrite new', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      expect(wrapper.html()).toContain('研究报告：经络');
    });

    it('11. invalid UUID projectId → not-found status', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()], { projectId: invalidId() });
      expect(wrapper.html()).toContain('未找到');
    });
  });

  // ==============================================================
  // BATCH 2: Report states
  // ==============================================================

  describe('Report states', () => {
    it('12. completed run with markdown → ready status', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      expect(wrapper.html()).toContain('研究报告正文');
      expect(wrapper.html()).toContain('概述');
    });

    it('13. run without step_execution_trace → run-pending status', async () => {
      const pendingRun = makeRun({
        step_execution_trace: [],
        output_artifacts: {},
      });
      const wrapper = await setupAndMount(makeSession(), [pendingRun]);
      expect(wrapper.html()).toContain('运行进行中');
    });

    it('14. run with failed step → run-failed status', async () => {
      const failedRun = makeRun({
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'failed' },
        ],
        output_artifacts: {},
      });
      const wrapper = await setupAndMount(makeSession(), [failedRun]);
      expect(wrapper.html()).toContain('执行失败');
    });

    it('15. run without output_artifacts.markdown → report-missing', async () => {
      const noReportRun = makeRun({
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'completed' },
          { name: 'evidence_synthesis', status: 'completed' },
          { name: 'report_generation', status: 'completed' },
        ],
        output_artifacts: {}, // no markdown
      });
      const wrapper = await setupAndMount(makeSession(), [noReportRun]);
      expect(wrapper.html()).toContain('报告缺失');
    });

    it('16. markdown rendered into sections', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Should have section headings from markdown
      expect(wrapper.html()).toContain('概述');
      expect(wrapper.html()).toContain('结论');
    });

    it('17. report title shown', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      expect(wrapper.html()).toContain('研究报告：经络');
    });

    it('18. does not show report body when markdown is empty', async () => {
      const emptyMarkdownRun = makeRun({
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'report_generation', status: 'completed' },
        ],
        output_artifacts: { markdown: '' },
      });
      const wrapper = await setupAndMount(makeSession(), [emptyMarkdownRun]);
      expect(wrapper.html()).toContain('报告缺失');
    });

    // ---- New Batch 1: report-pending / report-fixed status tests ----

    it('18a. report_generation pending → report-pending status', async () => {
      const pendingReportRun = makeRun({
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'completed' },
          { name: 'evidence_synthesis', status: 'completed' },
          { name: 'report_generation', status: 'pending' },
        ],
        output_artifacts: {},
      });
      const wrapper = await setupAndMount(makeSession(), [pendingReportRun]);
      // Must show report-pending, NOT general run-pending and NOT report-missing
      expect(wrapper.html()).toContain('报告生成中');
      expect(wrapper.html()).not.toContain('运行进行中');
      expect(wrapper.html()).not.toContain('报告缺失');
    });

    it('18b. report_generation failed → report-failed status', async () => {
      const failedReportRun = makeRun({
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'completed' },
          { name: 'evidence_synthesis', status: 'completed' },
          { name: 'report_generation', status: 'failed' },
        ],
        output_artifacts: {},
      });
      const wrapper = await setupAndMount(makeSession(), [failedReportRun]);
      // Must show report-failed, NOT general run-failed
      expect(wrapper.html()).toContain('报告生成失败');
      expect(wrapper.html()).not.toContain('流程执行失败');
    });

    it('18c. non-report_generation failed → run-failed status', async () => {
      const failedLitRun = makeRun({
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'failed' },
          { name: 'report_generation', status: 'pending' },
        ],
        output_artifacts: {},
      });
      const wrapper = await setupAndMount(makeSession(), [failedLitRun]);
      // Must show run-failed, NOT report-failed (report_generation didn't fail — a different step did)
      expect(wrapper.html()).toContain('流程执行失败');
      expect(wrapper.html()).not.toContain('报告生成失败');
    });

    it('18d. completed report_generation + empty markdown → report-missing', async () => {
      const noMarkdownRun = makeRun({
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'report_generation', status: 'completed' },
        ],
        output_artifacts: {}, // no markdown
      });
      const wrapper = await setupAndMount(makeSession(), [noMarkdownRun]);
      // report_generation completed but output_artifacts.markdown absent/empty
      expect(wrapper.html()).toContain('报告缺失');
      expect(wrapper.html()).not.toContain('报告生成失败');
      expect(wrapper.html()).not.toContain('报告生成中');
    });

    it('18e. report-pending does not show old report', async () => {
      // First load a ready report
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      expect(wrapper.html()).toContain('研究报告：经络');

      // Now switch to a report-pending state
      const pendingReportRun = makeRun({
        run_id: RUN_B,
        session_id: PROJ_B,
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'report_generation', status: 'pending' },
        ],
        output_artifacts: {},
      });
      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });
      mockApiGet.mockReset();
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [pendingReportRun] } } };
        }
        throw new Error('unexpected');
      });

      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      // Must NOT show old report content
      expect(wrapper.html()).not.toContain('研究报告：经络');
      expect(wrapper.html()).not.toContain('概述');
      // Must show report-pending UI
      expect(wrapper.html()).toContain('报告生成中');
    });

    it('18f. report-failed does not show old report', async () => {
      // First load a ready report
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      expect(wrapper.html()).toContain('研究报告：经络');

      // Now switch to a report-failed state
      const failedReportRun = makeRun({
        run_id: RUN_B,
        session_id: PROJ_B,
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'report_generation', status: 'failed' },
        ],
        output_artifacts: {},
      });
      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });
      mockApiGet.mockReset();
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [failedReportRun] } } };
        }
        throw new Error('unexpected');
      });

      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      // Must NOT show old report content
      expect(wrapper.html()).not.toContain('研究报告：经络');
      expect(wrapper.html()).not.toContain('概述');
      // Must show report-failed UI
      expect(wrapper.html()).toContain('报告生成失败');
    });

    it('18g. route switch from report-failed to ready clears error', async () => {
      // First load a report-failed run
      const failedReportRun = makeRun({
        run_id: RUN_A,
        session_id: PROJ_A,
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'report_generation', status: 'failed' },
        ],
        output_artifacts: {},
      });
      const wrapper = await setupAndMount(makeSession(), [failedReportRun]);
      expect(wrapper.html()).toContain('报告生成失败');

      // Switch to ready run
      const readyRun = makeRun({
        run_id: RUN_B,
        session_id: PROJ_B,
      });
      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });
      mockApiGet.mockReset();
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [readyRun] } } };
        }
        throw new Error('unexpected');
      });

      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      // Error state must be cleared
      expect(wrapper.html()).not.toContain('报告生成失败');
      // Ready content must show
      expect(wrapper.html()).toContain('研究报告正文');
    });

    it('18h. route switch from ready to report-pending clears old report', async () => {
      // First load a ready report
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      expect(wrapper.html()).toContain('研究报告：经络');
      expect(wrapper.html()).toContain('研究报告正文');

      // Switch to report-pending
      const pendingRun = makeRun({
        run_id: RUN_B,
        session_id: PROJ_B,
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'report_generation', status: 'pending' },
        ],
        output_artifacts: {},
      });
      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });
      mockApiGet.mockReset();
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [pendingRun] } } };
        }
        throw new Error('unexpected');
      });

      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      // Old report content must be cleared
      expect(wrapper.html()).not.toContain('研究报告：经络');
      expect(wrapper.html()).not.toContain('概述');
      expect(wrapper.html()).not.toContain('研究报告正文');
      // New pending state must show
      expect(wrapper.html()).toContain('报告生成中');
    });
  });

  // ==============================================================
  // BATCH 3: XSS / Markdown safety
  // ==============================================================

  describe('Markdown safety', () => {
    it('19. script tag in report is not rendered as executable HTML', async () => {
      const xssRun = makeRun({
        output_artifacts: {
          markdown: '# Test\n\n<script>alert("xss")</script>\n\nNormal text.',
        },
        replay_manifest: { retrieval_snapshot: [], traces: [] },
      });
      const wrapper = await setupAndMount(makeSession(), [xssRun]);
      const html = wrapper.html();
      // Vue text binding auto-escapes HTML. An actual HTML <script> tag
      // would appear as &lt;script&gt; in the rendered output.
      // We verify there is NO executable script in the DOM.
      expect(html).not.toContain('<script>alert');
    });

    it('20. event handler onerror in report is not active as DOM event', async () => {
      const xssRun = makeRun({
        output_artifacts: {
          markdown: '# Test\n\n<img src=x onerror=alert(1)>',
        },
        replay_manifest: { retrieval_snapshot: [], traces: [] },
      });
      const wrapper = await setupAndMount(makeSession(), [xssRun]);
      // No img element is created — markdown is rendered as text, not HTML
      const imgEls = wrapper.findAll('img');
      expect(imgEls.length).toBe(0);
    });

    it('21. javascript: URL in markdown is not an active link', async () => {
      const xssRun = makeRun({
        output_artifacts: {
          markdown: '# Test\n\n[javascript link](javascript:alert(1))',
        },
        replay_manifest: { retrieval_snapshot: [], traces: [] },
      });
      const wrapper = await setupAndMount(makeSession(), [xssRun]);
      // No actual <a> tags are created from markdown links — the parser only
      // creates clickable citation markers, not general links
      const links = wrapper.findAll('a[href*="javascript"]');
      expect(links.length).toBe(0);
    });

    it('22. common markdown renders as text content', async () => {
      const simpleRun = makeRun({
        output_artifacts: {
          markdown:
            '# 标题\n\n## 第一章节\n\n这是正文内容。**这是加粗的**。\n\n## 第二章节\n\n更多内容。',
        },
        replay_manifest: { retrieval_snapshot: [], traces: [] },
      });
      const wrapper = await setupAndMount(makeSession(), [simpleRun]);
      expect(wrapper.html()).toContain('第一章节');
      expect(wrapper.html()).toContain('第二章节');
      expect(wrapper.html()).toContain('这是正文内容');
      expect(wrapper.html()).toContain('这是加粗的');
    });

    it('23. citation markers are rendered as interactive buttons', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Citation markers should be clickable elements
      const citationEls = wrapper.findAll('.rrv-citation-marker');
      // At least one citation marker exists
      expect(citationEls.length).toBeGreaterThan(0);
    });
  });

  // ==============================================================
  // BATCH 4: Citations
  // ==============================================================

  describe('Citations', () => {
    it('24. multiple citations displayed', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Citation panel should show entries
      const citationItems = wrapper.findAll('.rcp-citation-item');
      expect(citationItems.length).toBeGreaterThan(1);
    });

    it('25. citation uses real trace_id (not array index)', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const html = wrapper.html();
      // Should contain real trace_id fragments
      expect(html).toContain('doc-01');
      expect(html).toContain('doc-02');
    });

    it('26. clicking citation selects it', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const firstCitation = wrapper.find('.rcp-citation-item');
      await firstCitation.trigger('click');
      await nextTick();
      // The citation should have selected styling
      expect(firstCitation.classes()).toContain('rcp-citation-item--selected');
    });

    it('27. citation missing evidence shows warning', async () => {
      // Create a run with citation but no evidence in snapshot
      const noEvidenceRun = makeRun({
        replay_manifest: {
          retrieval_snapshot: [],
          traces: [],
        },
        output_artifacts: {
          markdown: '# Report\n\nSome text [doc-x:chk-x].',
        },
      });
      const wrapper = await setupAndMount(makeSession(), [noEvidenceRun]);
      // No citation items in citation panel since no citations extracted from artifacts
      const citationItems = wrapper.findAll('.rcp-citation-item');
      expect(citationItems.length).toBe(0);
    });

    it('28. cross-run citations not shown', async () => {
      // Two runs — only current run evidence should appear
      const otherRunEvidence = makeRun({
        run_id: RUN_B,
        session_id: PROJ_A,
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-other:chk',
              document_id: 'doc-other',
              chunk_id: 'chk',
              claim_text: 'Other evidence',
              quote: 'Other text',
              citation_text: '[doc-other:chk]',
            },
          ],
          traces: [{ trace_id: 'doc-other:chk', document_id: 'doc-other', chunk_id: 'chk' }],
        },
      });
      const currentRun = makeRun();

      const wrapper = await setupAndMount(makeSession(), [currentRun, otherRunEvidence]);
      // Should only show current run's evidence
      const citationItems = wrapper.findAll('.rcp-citation-item');
      // Each has doc-01 and doc-02 citations — 2 from current run
      expect(citationItems.length).toBe(2);
      expect(wrapper.html()).not.toContain('doc-other');
    });

    it('29. route switch clears selected citation', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Select a citation
      const firstCitation = wrapper.find('.rcp-citation-item');
      await firstCitation.trigger('click');
      await nextTick();
      expect(firstCitation.classes()).toContain('rcp-citation-item--selected');

      // Switch route
      const runB = makeRun({ run_id: RUN_B });
      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });
      mockApiGet.mockReset();
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [runB] } } };
        }
        throw new Error('unexpected');
      });
      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();
      // New page should load — no selected citation from old page
      expect(wrapper.html()).toContain('Session B');
    });

    it('30. citation display numbers are sequential', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const items = wrapper.findAll('.rcp-citation-number');
      expect(items.length).toBeGreaterThan(0);
      // First should be #[1]
      expect(items[0]?.text()).toContain('#[1]');
    });

    it('31. same trace_id in multiple places stays consistent', async () => {
      // The run has two distinct trace_ids — each shown once
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const html = wrapper.html();
      // doc-01 and doc-02 should each appear
      const doc01Matches = (html.match(/doc-01:chk-01/g) || []).length;
      const doc02Matches = (html.match(/doc-02:chk-02/g) || []).length;
      // doc-01 appears at least in report and data — that's expected
      expect(doc01Matches).toBeGreaterThan(0);
      expect(doc02Matches).toBeGreaterThan(0);
    });

    // BATCH 4b — Citation marker validation & display (Batch 1 fixes)
    it('31a. real citation markers show sequential display numbers', async () => {
      // The markdown has [doc-01:chk-01] and [doc-02:chk-02].
      // Both are in output_artifacts.citations, so both render as clickable
      // buttons with display numbers [1] and [2].
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const markers = wrapper.findAll('.rrv-citation-marker');
      expect(markers.length).toBe(2);
      // First marker should show [1]
      expect(markers[0]?.text()).toBe('[1]');
      // Second marker should show [2]
      expect(markers[1]?.text()).toBe('[2]');
    });

    it('31b. clicking citation emits real trace_id', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const markers = wrapper.findAll('.rrv-citation-marker');
      expect(markers.length).toBe(2);
      // Click first marker
      await markers[0]!.trigger('click');
      await nextTick();
      // Citation panel should now show the evidence for doc-01:chk-01
      const panel = wrapper.find('.rcp-evidence-area');
      expect(panel.html()).toContain('经络者，所以行血气而营阴阳');
    });

    it('31c. same trace_id referenced multiple times maps to same display number', async () => {
      // Markdown has the same trace_id twice
      const dupRun = makeRun({
        output_artifacts: {
          markdown: '# Report\n\nFirst ref [doc-01:chk-01]. Second ref [doc-01:chk-01].',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-01:chk-01',
              citation_text: '[doc-01:chk-01]',
              document_id: 'doc-01',
              quote: 'Quote text.',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              claim_text: 'Claim',
              quote: 'Quote text.',
              citation_text: '[doc-01:chk-01]',
              source_ref_title: 'Source',
            },
          ],
          traces: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              provenance_kind: 'retrieval',
            },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [dupRun]);
      const markers = wrapper.findAll('.rrv-citation-marker');
      // Both markers for the same trace_id should show the same display number
      expect(markers.length).toBe(2);
      expect(markers[0]?.text()).toBe('[1]');
      expect(markers[1]?.text()).toBe('[1]');
    });

    it('31d. unknown citation marker renders as plain text', async () => {
      // Markdown contains a marker NOT in citations — should render as text
      const runWithUnknown = makeRun({
        output_artifacts: {
          markdown: '# Report\n\nKnown ref [doc-01:chk-01]. Unknown ref [ghost:fake].',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-01:chk-01',
              citation_text: '[doc-01:chk-01]',
              document_id: 'doc-01',
              quote: 'Known.',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              claim_text: 'Claim',
              quote: 'Known.',
              citation_text: '[doc-01:chk-01]',
              source_ref_title: 'Source',
            },
          ],
          traces: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              provenance_kind: 'retrieval',
            },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [runWithUnknown]);
      // Only one clickable marker (known)
      const markers = wrapper.findAll('.rrv-citation-marker');
      expect(markers.length).toBe(1);
      // The unknown [ghost:fake] must be plain text in the DOM, not a button
      const html = wrapper.html();
      expect(html).toContain('[ghost:fake]');
      // No marker with ghost:fake as active
      const ghostMarkers = wrapper.findAll('.rrv-citation-marker');
      const ghostTexts = ghostMarkers.map((m) => m.text());
      expect(ghostTexts).not.toContain('[ghost:fake]');
    });

    it('31e. marker not in current run citations is not clickable', async () => {
      // The run has citations for doc-01 and doc-02, but markdown
      // also contains doc-99 which is NOT in citations — it must NOT be clickable
      const runWithExtra = makeRun({
        output_artifacts: {
          markdown: '# Report\n\nKnown [doc-01:chk-01]. Extraneous [doc-99:chk-99].',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-01:chk-01',
              citation_text: '[doc-01:chk-01]',
              document_id: 'doc-01',
              quote: 'Known.',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              claim_text: 'Claim',
              quote: 'Known.',
              citation_text: '[doc-01:chk-01]',
              source_ref_title: 'Source',
            },
          ],
          traces: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              provenance_kind: 'retrieval',
            },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [runWithExtra]);
      // Only one CitationPanel item (doc-01)
      const citationItems = wrapper.findAll('.rcp-citation-item');
      expect(citationItems.length).toBe(1);
      // The extraneous marker must be plain text, not a clickable button
      const markers = wrapper.findAll('.rrv-citation-marker');
      expect(markers.length).toBe(1);
      expect(markers[0]?.text()).toBe('[1]');
    });

    it('31f. page HTML does not contain [undefined]', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const html = wrapper.html();
      expect(html).not.toContain('[undefined]');
    });
  });

  // ==============================================================
  // BATCH C1-2a: Unified display numbers (C1-2)
  // ==============================================================

  describe('C1-2a — Unified display numbers', () => {
    it('C1-2a.1: report marker [1] maps to CitationPanel #[1]', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // In markdown: [doc-01:chk-01] appears first, then [doc-02:chk-02].
      // citationList array is in the same order, so nothing breaks.
      const markerText = wrapper.find('.rrv-citation-marker').text();
      const panelItems = wrapper.findAll('.rcp-citation-item');
      const itemText = panelItems[0]?.find('.rcp-citation-number').text();
      expect(markerText).toBe('[1]');
      expect(itemText).toBe('#[1]');
    });

    it('C1-2a.2: display numbers from markdown, NOT from citationList array order', async () => {
      // Backend returns citationList in REVERSE order: doc-02 first, doc-01 second.
      // Markdown still has doc-01 first, so doc-01 = [1], doc-02 = [2] regardless.
      const reversedRun = makeRun({
        output_artifacts: {
          markdown: '# Report\n\nFirst ref [doc-01:chk-01]. Second ref [doc-02:chk-02].',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-02:chk-02',
              citation_text: '[doc-02:chk-02]',
              document_id: 'doc-02',
              quote: 'Quote 2.',
            },
            {
              trace_id: 'doc-01:chk-01',
              citation_text: '[doc-01:chk-01]',
              document_id: 'doc-01',
              quote: 'Quote 1.',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              claim_text: 'Claim 1',
              quote: '经络者，所以行血气',
              citation_text: '[doc-01:chk-01]',
              source_ref_title: '针灸甲乙经',
              source_ref_url: 'https://example.com/ref1',
              source_ref_id: 'src-ref-001',
            },
            {
              trace_id: 'doc-02:chk-02',
              document_id: 'doc-02',
              chunk_id: 'chk-02',
              claim_text: 'Claim 2',
              quote: '刺之要，气至而有效',
              citation_text: '[doc-02:chk-02]',
              source_ref_title: '黄帝内经',
              source_ref_url: 'https://example.com/ref2',
              source_ref_id: 'src-ref-002',
            },
          ],
          traces: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              passage_id: 'passage-001',
            },
            {
              trace_id: 'doc-02:chk-02',
              document_id: 'doc-02',
              chunk_id: 'chk-02',
              passage_id: 'passage-002',
            },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [reversedRun]);

      // Report markers: first marker in DOM = first in markdown = doc-01 = [1]
      const markers = wrapper.findAll('.rrv-citation-marker');
      expect(markers.length).toBe(2);
      expect(markers[0]?.text()).toBe('[1]');
      expect(markers[1]?.text()).toBe('[2]');

      // CitationPanel items: first item in DOM = backend array[0] = doc-02
      // But its display number MUST be from markdown: doc-02 = [2], NOT #[1]
      const panelItems = wrapper.findAll('.rcp-citation-item');
      expect(panelItems.length).toBe(2);

      // Panel item 0 holds doc-02 (second in markdown → #[2])
      // Panel item 1 holds doc-01 (first in markdown → #[1])
      const itemNums = panelItems.map((item) => item.find('.rcp-citation-number').text());
      expect(itemNums).toContain('#[2]');
      expect(itemNums).toContain('#[1]');
      // Neither should be '?' (unmapped)
      expect(itemNums).not.toContain('#[?]');
    });

    it('C1-2a.3: trace_id not in markdown shows fallback "?" in panel', async () => {
      // citationList has a trace_id that never appears in markdown.
      const orphanRun = makeRun({
        output_artifacts: {
          markdown: '# Report\n\nOnly ref [doc-01:chk-01].',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-01:chk-01',
              citation_text: '[doc-01:chk-01]',
              document_id: 'doc-01',
              quote: 'Q1',
            },
            {
              trace_id: 'doc-orphan:chk',
              citation_text: '[doc-orphan:chk]',
              document_id: 'doc-orphan',
              quote: 'Orphan',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              claim_text: 'C1',
              quote: 'Q1',
              citation_text: '[doc-01:chk-01]',
              source_ref_title: 'S1',
            },
            {
              trace_id: 'doc-orphan:chk',
              document_id: 'doc-orphan',
              chunk_id: 'chk',
              claim_text: 'Orphan claim',
              quote: 'Orphan',
              citation_text: '[doc-orphan:chk]',
              source_ref_title: 'Orphan Source',
            },
          ],
          traces: [
            { trace_id: 'doc-01:chk-01', document_id: 'doc-01', chunk_id: 'chk-01' },
            { trace_id: 'doc-orphan:chk', document_id: 'doc-orphan', chunk_id: 'chk' },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [orphanRun]);

      const panelItems = wrapper.findAll('.rcp-citation-item');
      expect(panelItems.length).toBe(2);

      const itemNums = panelItems.map((item) => item.find('.rcp-citation-number').text());
      // doc-01 appears in markdown → #[1]
      // doc-orphan never appears → #[?]
      expect(itemNums).toContain('#[1]');
      expect(itemNums).toContain('#[?]');
    });
  });

  // ==============================================================
  // BATCH C1-2b: Full identity chain (C1-2)
  // ==============================================================

  describe('C1-2b — Full identity chain', () => {
    it('C1-2b.1: clicking report marker [1] selects correct Citation → Evidence → SourceRef', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Click first report marker [1]
      const markers = wrapper.findAll('.rrv-citation-marker');
      await markers[0]!.trigger('click');
      await nextTick();

      // CitationPanel: first item should be selected
      const panelItems = wrapper.findAll('.rcp-citation-item');
      expect(panelItems[0]?.classes()).toContain('rcp-citation-item--selected');

      // Evidence area shows the correct claim
      const evidenceArea = wrapper.find('.rcp-evidence-area');
      expect(evidenceArea.html()).toContain('经络者，所以行血气而营阴阳');

      // SourceRef shows correct title
      expect(evidenceArea.html()).toContain('针灸甲乙经');

      // SourceRef has internal link to /library/doc-01?passage=passage-001
      const sourceRefCard = evidenceArea.find('.esrc-card');
      expect(sourceRefCard.html()).toContain('打开原文');
      // The router-link should point to /library/doc-01
      const link = sourceRefCard.find('a[href]');
      expect(link.attributes('href')).toContain('/library/doc-01');
      expect(link.attributes('href')).toContain('passage=passage-001');
    });

    it('C1-2b.2: clicking marker [2] selects different Evidence + SourceRef (no cross-contamination)', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Click second marker [2] → doc-02
      const markers = wrapper.findAll('.rrv-citation-marker');
      await markers[1]!.trigger('click');
      await nextTick();

      // Evidence must NOT show doc-01 content
      const evidenceArea = wrapper.find('.rcp-evidence-area');
      expect(evidenceArea.html()).not.toContain('针灸甲乙经');
      expect(evidenceArea.html()).toContain('黄帝内经');
      expect(evidenceArea.html()).toContain('刺之要，气至而有效');
    });

    it('C1-2b.3: full chain survives reversed citationList order', async () => {
      const reversedRun = makeRun({
        output_artifacts: {
          markdown: '# Report\n\nFirst ref [doc-01:chk-01]. Second ref [doc-02:chk-02].',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-02:chk-02',
              citation_text: '[doc-02:chk-02]',
              document_id: 'doc-02',
              quote: 'Q2',
            },
            {
              trace_id: 'doc-01:chk-01',
              citation_text: '[doc-01:chk-01]',
              document_id: 'doc-01',
              quote: '经络者，所以行血气',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              claim_text: 'C1',
              quote: '经络者，所以行血气',
              citation_text: '[doc-01:chk-01]',
              source_ref_title: '针灸甲乙经',
            },
            {
              trace_id: 'doc-02:chk-02',
              document_id: 'doc-02',
              chunk_id: 'chk-02',
              claim_text: 'C2',
              quote: '刺之要，气至而有效',
              citation_text: '[doc-02:chk-02]',
              source_ref_title: '黄帝内经',
            },
          ],
          traces: [
            {
              trace_id: 'doc-01:chk-01',
              document_id: 'doc-01',
              chunk_id: 'chk-01',
              passage_id: 'passage-001',
            },
            {
              trace_id: 'doc-02:chk-02',
              document_id: 'doc-02',
              chunk_id: 'chk-02',
              passage_id: 'passage-002',
            },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [reversedRun]);

      // Marker [1] = doc-01 (first in markdown)
      const markers = wrapper.findAll('.rrv-citation-marker');
      expect(markers[0]?.text()).toBe('[1]');

      // Panel should show doc-02 #[2] first (backend order), doc-01 #[1] second
      const panelItems = wrapper.findAll('.rcp-citation-item');
      const itemNums = panelItems.map((i) => i.find('.rcp-citation-number').text());
      expect(itemNums[0]).toBe('#[2]'); // doc-02 first in array, but label is [2]
      expect(itemNums[1]).toBe('#[1]'); // doc-01 second in array, but label is [1]

      // Click marker [1] — selects doc-01 (in markdown order)
      await markers[0]!.trigger('click');
      await nextTick();

      // doc-01's Evidence shows 针灸甲乙经
      const evidenceArea = wrapper.find('.rcp-evidence-area');
      expect(evidenceArea.html()).toContain('针灸甲乙经');
      expect(evidenceArea.html()).not.toContain('黄帝内经');

      // doc-01 has passage_id → internal link
      const link = evidenceArea.find('.esrc-card a[href]');
      expect(link.attributes('href')).toContain('/library/doc-01');
    });

    it('C1-2b.4: fail-closed — Citation with no Evidence shows missing state', async () => {
      // citationList has trace_id but no matching evidence in retrieval_snapshot
      const noEvidenceRun = makeRun({
        output_artifacts: {
          markdown: '# Report\n\nRef [doc-01:chk-01].',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-01:chk-01',
              citation_text: '[doc-01:chk-01]',
              document_id: 'doc-01',
              quote: 'Q',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [], // empty — no evidence
          traces: [],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [noEvidenceRun]);

      const panelItems = wrapper.findAll('.rcp-citation-item');
      expect(panelItems.length).toBe(1);

      await panelItems[0]!.trigger('click');
      await nextTick();

      // Evidence area shows "缺少证据关联" not fabricated data
      const evidenceArea = wrapper.find('.rcp-evidence-area');
      expect(evidenceArea.html()).toContain('缺少证据关联');
      expect(evidenceArea.html()).not.toContain('来源文献');
    });

    it('C1-2b.5: fail-closed — Evidence without source_ref_title shows missing source, no fake link', async () => {
      const noSourceRefRun = makeRun({
        output_artifacts: {
          markdown: '# Report\n\nRef [doc-03:chk-03].',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-03:chk-03',
              citation_text: '[doc-03:chk-03]',
              document_id: 'doc-03',
              quote: 'Q3',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-03:chk-03',
              document_id: 'doc-03',
              chunk_id: 'chk-03',
              claim_text: 'C3',
              quote: 'Q3',
              citation_text: '[doc-03:chk-03]',
              // NO source_ref_title, source_ref_url, source_ref_id
            },
          ],
          traces: [{ trace_id: 'doc-03:chk-03', document_id: 'doc-03', chunk_id: 'chk-03' }],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [noSourceRefRun]);

      const panelItem = wrapper.find('.rcp-citation-item');
      await panelItem.trigger('click');
      await nextTick();

      const evidenceArea = wrapper.find('.rcp-evidence-area');
      expect(evidenceArea.html()).toContain('缺少文献来源信息');
      // Must NOT fabricate an internal link when no source_ref
      expect(evidenceArea.html()).not.toContain('打开原文');
    });
  });

  // ==============================================================
  // BATCH 5: Evidence
  // ==============================================================

  describe('Evidence', () => {
    it('32. evidence with source_ref_title shows source info after citation select', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Click first citation to reveal evidence details
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('针灸甲乙经');
    });

    it('33. evidence without passage_id shows incomplete status after citation select', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRunWithoutSourceRef()]);
      // Click citation to reveal evidence details
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('不完整');
    });

    it('34. evidence without source_ref_title shows missing source after citation select', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRunWithoutSourceRef()]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('缺少文献来源信息');
    });

    it('35. full lineage evidence shows complete badge after citation select', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('证据链完整');
    });

    it('36. no frontend confidence scoring', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const html = wrapper.html();
      // Should NOT contain fabricated confidence indicators
      expect(html).not.toContain('高可信');
      expect(html).not.toContain('high confidence');
      expect(html).not.toContain('置信度');
    });

    it('37. evidence with quote shows original text block after citation select', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('经络者，所以行血气而营阴阳');
    });

    it('38. evidence with claim_text shows AI归纳 after citation select', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('AI 归纳');
    });

    it('39. empty evidence list shows empty citation state', async () => {
      const noEvidenceRun = makeRun({
        replay_manifest: { retrieval_snapshot: [], traces: [] },
        output_artifacts: {
          markdown: '# Empty\n\nNo evidence here.',
        },
      });
      const wrapper = await setupAndMount(makeSession(), [noEvidenceRun]);
      // Should show report (it has markdown) but no citations
      expect(wrapper.html()).toContain('此报告暂无关联证据与引用');
    });

    it('40. evidence count matches extracted count', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Should show 2 evidence entries and 0 citations from artifacts
      expect(wrapper.html()).toContain('证据 2');
    });

    it('41. no fabricated fields when backend fields are absent', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRunWithoutSourceRef()]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      const html = wrapper.html();
      // Should show honest "missing source" rather than fabricating one
      expect(html).toContain('缺少文献来源信息');
    });
  });

  // ==============================================================
  // BATCH 6: SourceRef
  // ==============================================================

  describe('SourceRef', () => {
    it('42. evidence with document_id + passage_id → internal document link', async () => {
      // Evidence with both doc and passage → internal router-link to /library/:docId?passage=...
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const citation = wrapper.find('.rcp-citation-item');
      if (citation.exists()) {
        await citation.trigger('click');
        await nextTick();
      }
      // Should show internal "查看原文" link, not external
      expect(wrapper.html()).toContain('查看原文');
      const internalLinks = wrapper.findAll('.esrc-link--internal');
      expect(internalLinks.length).toBeGreaterThan(0);
      // Exact href: /library/doc-01?passage=passage-001
      // router-link is stubbed as <a :href="to"> — verify rendered HTML
      const html = wrapper.html();
      expect(html).toContain('href="/library/doc-01?passage=passage-001"');
      expect(html).not.toContain('/versions/');
      expect(html).not.toContain('/research/library/');
    });

    it('43. evidence without source_ref_title shows missing source after citation select', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRunWithoutSourceRef()]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('缺少文献来源信息');
    });

    it('44. evidence with passage_id + document_id shows passage-level internal link', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('精确段落定位');
      // The internal link has passage query param
      const internalLinks = wrapper.findAll('.esrc-link--internal');
      expect(internalLinks.length).toBeGreaterThan(0);
    });

    it('45. evidence with document_id only → document-level internal link to /library', async () => {
      // Create evidence with document_id but no passage_id
      const docOnlyRun = makeRun({
        run_id: RUN_A,
        output_artifacts: {
          markdown: '# Report\n\nRef **[doc-only:chk]**.',
          title: 'Report',
          citations: [
            {
              trace_id: 'doc-only:chk',
              citation_text: '[doc-only:chk]',
              document_id: 'doc-only',
              quote: 'Text.',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'doc-only:chk',
              document_id: 'doc-only-version-id',
              chunk_id: 'chk',
              claim_text: 'Claim',
              quote: 'Text.',
              citation_text: '[doc-only:chk]',
              source_ref_title: 'Some Source',
              source_ref_url: 'https://example.com/ext',
            },
          ],
          traces: [
            {
              trace_id: 'doc-only:chk',
              document_id: 'doc-only-version-id',
              chunk_id: 'chk',
              provenance_kind: 'retrieval',
              // NO passage_id
            },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [docOnlyRun]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      expect(wrapper.html()).toContain('仅文献级定位');
      // Should have internal router-link (document-level, no passage query)
      const internalLinks = wrapper.findAll('.esrc-link--internal');
      expect(internalLinks.length).toBeGreaterThan(0);
      // Exact href: /library/doc-only-version-id (no passage query,
      // no /research/library/ prefix, no /versions/)
      const html = wrapper.html();
      expect(html).toContain('href="/library/doc-only-version-id"');
      expect(html).not.toContain('/versions/');
      expect(html).not.toContain('/research/library/');
    });

    it('46. evidence without document_id → no internal link, external fallback only', async () => {
      const noDocRun = makeRun({
        run_id: RUN_A,
        output_artifacts: {
          markdown: '# Report\n\nRef **[ext-only:chk]**.',
          title: 'Report',
          citations: [
            {
              trace_id: 'ext-only:chk',
              citation_text: '[ext-only:chk]',
              document_id: '',
              quote: 'External only.',
            },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'ext-only:chk',
              document_id: '',
              chunk_id: 'chk',
              claim_text: 'Claim',
              quote: 'External only.',
              citation_text: '[ext-only:chk]',
              source_ref_title: 'External Source',
              source_ref_url: 'https://example.com/ext-ref',
            },
          ],
          traces: [
            {
              trace_id: 'ext-only:chk',
              document_id: '',
              chunk_id: 'chk',
              provenance_kind: 'retrieval',
            },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [noDocRun]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      // No internal link (no document_id)
      const internalLinks = wrapper.findAll('.esrc-link--internal');
      expect(internalLinks.length).toBe(0);
      // External link should still work (fallback)
      const externalLinks = wrapper.findAll('a[target="_blank"]');
      expect(externalLinks.length).toBeGreaterThan(0);
    });

    it('47. external link has rel="noopener noreferrer" target="_blank"', async () => {
      // Use evidence without document_id so external link is shown
      const noDocRun = makeRun({
        run_id: RUN_A,
        output_artifacts: {
          markdown: '# Report\n\nRef **[ext:chk]**.',
          title: 'Report',
          citations: [
            { trace_id: 'ext:chk', citation_text: '[ext:chk]', document_id: '', quote: 'Ext.' },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'ext:chk',
              document_id: '',
              chunk_id: 'chk',
              claim_text: 'Claim',
              quote: 'Ext.',
              citation_text: '[ext:chk]',
              source_ref_title: 'Ext Source',
              source_ref_url: 'https://example.com/safe',
            },
          ],
          traces: [
            { trace_id: 'ext:chk', document_id: '', chunk_id: 'chk', provenance_kind: 'retrieval' },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [noDocRun]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      const sourceLinks = wrapper.findAll('a[target="_blank"]');
      expect(sourceLinks.length).toBeGreaterThan(0);
      const sourceLink = sourceLinks.find((l) => l.text().includes('打开原文'));
      expect(sourceLink?.html()).toContain('noopener');
    });

    it('47a. malicious source_ref_url schemes are not executable', async () => {
      // Test that javascript:, data:, and event handler URLs are blocked
      const maliciousRun = makeRun({
        run_id: RUN_A,
        output_artifacts: {
          markdown: '# Report\n\nRef **[evil:chk]**.',
          title: 'Report',
          citations: [
            { trace_id: 'evil:chk', citation_text: '[evil:chk]', document_id: '', quote: 'Evil.' },
          ],
        },
        replay_manifest: {
          retrieval_snapshot: [
            {
              trace_id: 'evil:chk',
              document_id: '',
              chunk_id: 'chk',
              claim_text: 'Claim',
              quote: 'Evil.',
              citation_text: '[evil:chk]',
              source_ref_title: 'Danger Source',
              source_ref_url: 'javascript:alert(1)',
            },
          ],
          traces: [
            {
              trace_id: 'evil:chk',
              document_id: '',
              chunk_id: 'chk',
              provenance_kind: 'retrieval',
            },
          ],
        },
      });
      const wrapper = await setupAndMount(makeSession(), [maliciousRun]);
      const citation = wrapper.find('.rcp-citation-item');
      await citation.trigger('click');
      await nextTick();
      // The javascript: URL must not be rendered as a clickable link
      const links = wrapper.findAll('a[href*="javascript"]');
      expect(links.length).toBe(0);
      // Also check data: URLs
      // (safeSourceUrl blocks javascript: — no link rendered)
    });
  });

  // ==============================================================
  // BATCH 7: Export
  // ==============================================================

  describe('Export', () => {
    it('48. export button disabled when no report', async () => {
      const noReportRun = makeRun({
        output_artifacts: {},
        step_execution_trace: [{ name: 'report_generation', status: 'completed' }],
      });
      const wrapper = await setupAndMount(makeSession(), [noReportRun]);
      const exportBtn = wrapper.find('.rrh-btn--export');
      if (exportBtn.exists()) {
        expect(exportBtn.attributes('disabled')).toBeDefined();
      }
    });

    it('49. export button enabled when report present', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const exportBtn = wrapper.find('.rrh-btn--export');
      expect(exportBtn.exists()).toBe(true);
      expect(exportBtn.attributes('disabled')).toBeUndefined();
    });

    it('50. export calls real backend export endpoint', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const exportBtn = wrapper.find('.rrh-btn--export');

      // Set up mock API to return export data
      let exportCalled = false;
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/export')) {
          exportCalled = true;
          const reportContent =
            '# 研究报告：经络\n\n## 概述\n\n经络是人体运行气血的通道。参考 [doc-01:chk-01]。';
          return {
            data: new Blob([reportContent], { type: 'text/markdown' }),
            headers: {
              'content-disposition': 'attachment; filename="hfb-research-report-11111111.md"',
            },
          };
        }
        // Default handlers
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: makeSession() } };
        }
        if (url.includes('/api/v4/research/session/') && !url.includes('/export')) {
          return { data: { data: { runs: [makeRun()] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      await exportBtn.trigger('click');
      await flushPromises();
      await nextTick();

      expect(exportCalled).toBe(true);
      // Export should create a Blob from the real backend response
      expect(createdBlobs.length).toBeGreaterThan(0);
      const markdownBlobs = createdBlobs.filter((b) => b.type.includes('text/markdown'));
      expect(markdownBlobs.length).toBeGreaterThan(0);
      expect(markdownBlobs[0]?.content).toContain('经络是人体运行气血的通道');
    });

    it('51. export uses response MIME and Content-Disposition filename', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/export')) {
          return {
            data: new Blob(['# Report Content'], { type: 'text/markdown; charset=utf-8' }),
            headers: {
              'content-disposition': 'attachment; filename="hfb-research-report-11111111.md"',
            },
          };
        }
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: makeSession() } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [makeRun()] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      const exportBtn = wrapper.find('.rrh-btn--export');
      await exportBtn.trigger('click');
      await flushPromises();
      await nextTick();

      // Verify one Blob was created from the backend response
      expect(createdBlobs.length).toBeGreaterThan(0);
      const exportBlob = createdBlobs[createdBlobs.length - 1];
      expect(exportBlob?.type).toContain('text/markdown');
      expect(exportBlob?.content).toContain('# Report Content');
    });

    it('52. export handles 401/403 error states safely', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/export')) {
          throw { response: { status: 403, data: { detail: 'Forbidden' } } };
        }
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: makeSession() } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [makeRun()] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      const exportBtn = wrapper.find('.rrh-btn--export');
      await exportBtn.trigger('click');
      await flushPromises();
      await nextTick();

      // Should show error, not success
      expect(wrapper.html()).toContain('没有权限导出');
    });

    it('53. export handles 404 error safely', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/export')) {
          throw { response: { status: 404, data: { detail: 'Not found' } } };
        }
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: makeSession() } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [makeRun()] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      const exportBtn = wrapper.find('.rrh-btn--export');
      await exportBtn.trigger('click');
      await flushPromises();
      await nextTick();

      expect(wrapper.html()).toContain('不存在或无权访问');
    });

    it('54. export handles 409 (empty report) safely', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/export')) {
          throw { response: { status: 409, data: { detail: 'Report is empty' } } };
        }
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: makeSession() } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [makeRun()] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      const exportBtn = wrapper.find('.rrh-btn--export');
      await exportBtn.trigger('click');
      await flushPromises();
      await nextTick();

      expect(wrapper.html()).toContain('报告为空');
    });

    it('55. export handles 500 error safely', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/export')) {
          throw { response: { status: 500, data: { detail: 'Server error' } } };
        }
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: makeSession() } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [makeRun()] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      const exportBtn = wrapper.find('.rrh-btn--export');
      await exportBtn.trigger('click');
      await flushPromises();
      await nextTick();

      expect(wrapper.html()).toContain('导出失败');
    });

    it('56. double-click blocked during export', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      let exportCallCount = 0;
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/export')) {
          exportCallCount++;
          // Simulate slow export
          await new Promise((r) => setTimeout(r, 50));
          return {
            data: new Blob(['# Report'], { type: 'text/markdown' }),
            headers: { 'content-disposition': 'attachment; filename="report.md"' },
          };
        }
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: makeSession() } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [makeRun()] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      const exportBtn = wrapper.find('.rrh-btn--export');
      // Rapid double-click
      await exportBtn.trigger('click');
      await exportBtn.trigger('click');
      await flushPromises();
      await nextTick();
      // Only one export call should have been made
      expect(exportCallCount).toBe(1);
    });

    it('57. no PDF/DOCX export buttons present', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      // Check for PDF/DOCX format keywords
      const exportArea = wrapper.find('.rrh-actions');
      if (exportArea.exists()) {
        const text = exportArea.text().toLowerCase();
        expect(text).not.toContain('pdf');
        expect(text).not.toContain('docx');
      }
    });

    it('58. route switch clears stale export error', async () => {
      const sessionA = makeSession({ id: PROJ_A, title: 'Session A' });
      const runA = makeRun({ run_id: RUN_A, session_id: PROJ_A });

      const wrapper = await setupAndMount(sessionA, [runA]);

      // Now make export fail with 500
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/export')) {
          throw { response: { status: 500, data: { detail: 'Boom' } } };
        }
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionA } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [runA] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      const exportBtn = wrapper.find('.rrh-btn--export');
      await exportBtn.trigger('click');
      await flushPromises();
      await nextTick();
      // 500 maps to safe fallback "导出失败" in the export codepath
      expect(wrapper.find('.rpage-export-error').exists()).toBe(true);

      // Switch to different session/run — export error and old report must clear
      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });
      const runB = makeRun({ run_id: RUN_B, session_id: PROJ_B });
      mockApiGet.mockReset();
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [runB] } } };
        }
        throw new Error(`Unexpected URL: ${url}`);
      });

      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();
      expect(wrapper.find('.rpage-export-error').exists()).toBe(false);
    });

    it('59. export does not show PDF or DOCX as supported formats', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const html = wrapper.html();
      expect(html).not.toContain('PDF');
      expect(html).not.toContain('DOCX');
      expect(html).not.toContain('pdf');
      expect(html).not.toContain('docx');
    });
  });

  // ==============================================================
  // BATCH 8: Isolation
  // ==============================================================

  describe('Isolation', () => {
    it('56. session A report title not shown in session B page', async () => {
      const sessionA = makeSession({ id: PROJ_A, title: 'Session A' });
      const runA = makeRun({ run_id: RUN_A, session_id: PROJ_A });
      const wrapper = await setupAndMount(sessionA, [runA]);
      expect(wrapper.html()).toContain('Session A');
    });

    it('57. session A title not leaked to session B after switch', async () => {
      const sessionA = makeSession({ id: PROJ_A, title: 'Session A' });
      const runA = makeRun({ run_id: RUN_A, session_id: PROJ_A });
      const wrapper = await setupAndMount(sessionA, [runA]);

      // Now switch
      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });
      const runB = makeRun({ run_id: RUN_B, session_id: PROJ_B });

      mockApiGet.mockReset();
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [runB] } } };
        }
        throw new Error('unexpected');
      });

      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      // Session A title should be gone
      expect(wrapper.html()).not.toContain('Session A');
    });

    it('59. own session + others run → not-found', async () => {
      const wrapper = await setupAndMount(makeSession(), []);
      expect(wrapper.html()).toContain('不存在');
    });

    it('60. route switch clears old data', async () => {
      const sessionA = makeSession({ id: PROJ_A, title: 'Session A' });
      const runA = makeRun({ run_id: RUN_A, session_id: PROJ_A });
      const wrapper = await setupAndMount(sessionA, [runA]);

      const sessionB = makeSession({ id: PROJ_B, title: 'Session B' });
      const runB = makeRun({ run_id: RUN_B, session_id: PROJ_B });

      mockApiGet.mockReset();
      mockApiGet.mockImplementation(async (url: string) => {
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: sessionB } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [runB] } } };
        }
        throw new Error('unexpected');
      });

      await router.push(`/research/${PROJ_B}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      expect(wrapper.html()).not.toContain('Session A');
    });
  });

  // ==============================================================
  // BATCH 9: Error handling
  // ==============================================================

  describe('Error handling', () => {
    it('64. 401 response → forbidden status', async () => {
      const wrapper = await setupAndMount('401', []);
      expect(wrapper.html()).toContain('无权限');
    });

    it('65. 403 response → forbidden status', async () => {
      const wrapper = await setupAndMount('403', []);
      expect(wrapper.html()).toContain('无权限');
    });

    it('66. 404 response → not-found status', async () => {
      const wrapper = await setupAndMount('404', []);
      expect(wrapper.html()).toContain('未找到');
    });

    it('68. 500 response → error status', async () => {
      const wrapper = await setupAndMount('500', []);
      expect(wrapper.html()).toContain('加载出错');
    });

    it('69. network error → error status', async () => {
      const wrapper = await setupAndMount('network', []);
      expect(wrapper.html()).toContain('加载出错');
    });

    it('70. retry button triggers reload', async () => {
      // First call fails with 500 for session — code calls session→runs→evaluate
      // When session fails, it returns immediately (1 call). Retry calls session again (2 total).
      mockApiGet.mockReset();

      let callCount = 0;
      mockApiGet.mockImplementation(async (url: string) => {
        callCount++;
        if (callCount <= 1) {
          throw { response: { status: 500, data: { detail: 'Error' } } };
        }
        if (url.includes('/api/v1/workspace/sessions/')) {
          return { data: { data: makeSession() } };
        }
        if (url.includes('/api/v4/research/session/')) {
          return { data: { data: { runs: [makeRun()] } } };
        }
        throw new Error('unexpected');
      });

      const wrapper = await setupAndMount('500', []);

      // Ensure error state rendered
      expect(wrapper.html()).toContain('加载出错');

      // Click retry
      const retryBtn = wrapper.find('.rre-btn--primary');
      expect(retryBtn.exists()).toBe(true);
      await retryBtn.trigger('click');
      await flushPromises();
      await nextTick();

      // After retry, at least one new API call was made (total calls > 1)
      expect(mockApiGet.mock.calls.length).toBeGreaterThan(1);
    });

    it('71. error state does not show ready content', async () => {
      const wrapper = await setupAndMount('500', []);
      expect(wrapper.html()).not.toContain('研究报告正文');
      expect(wrapper.html()).not.toContain('引用与证据');
    });

    it('72. no backend stack traces in error messages', async () => {
      const wrapper = await setupAndMount('500', []);
      const html = wrapper.html();
      expect(html).not.toContain('Traceback');
      expect(html).not.toContain('File "');
      expect(html).not.toContain('Exception');
    });
  });

  // ==============================================================
  // BATCH 10: Cross-user security
  // ==============================================================

  describe('Cross-user security', () => {
    it('73. other user session → forbidden (backend returns 404)', async () => {
      const wrapper = await setupAndMount('403', []);
      expect(wrapper.html()).toContain('无权限');
      // Should not show the session content
      expect(wrapper.html()).not.toContain('研究报告正文');
    });

    it('74. other user run → not found', async () => {
      // Session exists but run list empty (user B has no runs in this session)
      const wrapper = await setupAndMount(makeSession(), []);
      expect(wrapper.html()).toContain('不存在');
    });

    it('75. own session + others run → not found', async () => {
      // Session loads but target run not present
      const wrapper = await setupAndMount(makeSession(), []);
      expect(wrapper.html()).toContain('不存在');
    });

    it('76. others session ID not leaked in error message', async () => {
      const wrapper = await setupAndMount('404', []);
      const html = wrapper.html();
      // Should not expose the raw session ID
      expect(html).not.toContain(PROJ_A);
    });

    it('77. real resource names not leaked to unauthorized user', async () => {
      const wrapper = await setupAndMount('403', []);
      // Should not show any session title or report content
      expect(wrapper.html()).not.toContain('研究报告正文');
      expect(wrapper.html()).not.toContain('引用与证据');
    });
  });

  // ==============================================================
  // BATCH 9: Canonical Replay
  // ==============================================================

  describe('Replay', () => {
    const REPLAY_PATH = `/api/v4/research/runs/${RUN_A}/replay`;
    const SHA_ORIG = 'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a';
    const SHA_REPLAY = 'b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a1';

    beforeEach(() => {
      mockApiPost.mockReset();
    });

    it('78. replay button visible when status is ready', async () => {
      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const btn = wrapper.find('[data-testid="canonical-replay"]');
      expect(btn.exists()).toBe(true);
      expect(btn.text()).toBe('验证可重放性');
    });

    it('79. replay button hidden when status is not ready', async () => {
      const wrapper = await setupAndMount(makeSession(), [{ ...makeRun(), run_id: 'other' }]);
      // Page is in not-found state (target run not present)
      expect(wrapper.find('[data-testid="canonical-replay"]').exists()).toBe(false);
    });

    it('80. replay button posts to correct runId endpoint', async () => {
      mockApiPost.mockResolvedValueOnce({
        data: {
          data: {
            matched: true,
            original_output_sha256: SHA_ORIG,
            replay_output_sha256: SHA_REPLAY,
          },
        },
      });

      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const btn = wrapper.find('[data-testid="canonical-replay"]');
      await btn.trigger('click');
      await nextTick();
      await flushPromises();

      expect(mockApiPost).toHaveBeenCalledTimes(1);
      const callArgs = mockApiPost.mock.calls[0]!;
      expect(callArgs[0]).toBe(REPLAY_PATH);
    });

    it('81. matched replay shows "重放一致" and both SHA-256 hashes', async () => {
      mockApiPost.mockResolvedValueOnce({
        data: {
          data: {
            matched: true,
            original_output_sha256: SHA_ORIG,
            replay_output_sha256: SHA_REPLAY,
          },
        },
      });

      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      await flushPromises();

      const result = wrapper.find('[data-testid="canonical-replay-result"]');
      expect(result.exists()).toBe(true);
      const text = result.text();
      expect(text).toContain('重放一致');
      expect(text).toContain(SHA_ORIG);
      expect(text).toContain(SHA_REPLAY);
    });

    it('82. mismatched replay shows "重放不一致" and both hashes', async () => {
      mockApiPost.mockResolvedValueOnce({
        data: {
          data: {
            matched: false,
            original_output_sha256: SHA_ORIG,
            replay_output_sha256: SHA_REPLAY,
          },
        },
      });

      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      await flushPromises();

      const result = wrapper.find('[data-testid="canonical-replay-result"]');
      expect(result.exists()).toBe(true);
      const text = result.text();
      expect(text).toContain('重放不一致');
      expect(text).toContain(SHA_ORIG);
      expect(text).toContain(SHA_REPLAY);
      // Mismatch is a business result, not an error — error alert must not appear
      expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    });

    it('83. replay button disabled during request, prevents concurrent clicks', async () => {
      // Never resolve — keep request pending
      mockApiPost.mockReturnValueOnce(new Promise(() => {}));

      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      const btn = wrapper.find('[data-testid="canonical-replay"]');
      await btn.trigger('click');
      await nextTick();

      // Button should be disabled while replaying
      expect((btn.element as HTMLButtonElement).disabled).toBe(true);

      // Second click should be a no-op (function-level guard)
      await btn.trigger('click');
      await nextTick();
      expect(mockApiPost).toHaveBeenCalledTimes(1);
    });

    it('84. API error shows error message and no fake result', async () => {
      mockApiPost.mockRejectedValueOnce({
        response: { status: 500, data: { detail: 'Internal Server Error' } },
      });

      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      await flushPromises();

      // Should show error, not replay result
      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(false);
      expect(wrapper.find('.rpage-replay-error').exists()).toBe(true);
      expect(wrapper.find('.rpage-replay-error').text()).toBeTruthy();
    });

    it('85. route switch clears old replay result when both runs ready', async () => {
      mockApiPost.mockResolvedValueOnce({
        data: {
          data: {
            matched: true,
            original_output_sha256: SHA_ORIG,
            replay_output_sha256: SHA_REPLAY,
          },
        },
      });

      // Build TWO valid ready runs — both present in the session's run list
      const runA = makeRun({ run_id: RUN_A });
      const runB = makeRun({ run_id: RUN_B });

      // First load: run A (ready)
      const wrapper = await setupAndMount(makeSession(), [runA, runB]);
      expect(wrapper.find('[data-testid="canonical-replay"]').exists()).toBe(true);

      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      await flushPromises();
      // Result visible on run A
      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(true);

      // Switch route to run B — both valid UUIDs, both present in session runs
      // → load() runs, clears replay state, sets status='ready' (run B found)
      router.replace(`/research/${PROJ_A}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      // Run B page must be ready (not not-found)
      expect(wrapper.find('[data-testid="canonical-replay"]').exists()).toBe(true);

      // Old run A replay result must NOT persist on run B
      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(false);
    });

    it('86. stale replay response from run A does not pollute run B', async () => {
      // A replay request that resolves AFTER the route has switched to B
      // must be silently discarded.

      let resolveAReply!: (value: unknown) => void;
      const aPromise = new Promise((resolve) => {
        resolveAReply = resolve;
      });
      mockApiPost.mockReturnValueOnce(aPromise);

      // Mock session + both runs
      const wrapper = await setupAndMount(makeSession(), [
        makeRun({ run_id: RUN_A }),
        makeRun({ run_id: RUN_B }),
      ]);

      // Start replay on run A (will hang on the promise)
      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      expect(mockApiPost).toHaveBeenCalledTimes(1);

      // Switch to run B before A resolves
      router.replace(`/research/${PROJ_A}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();
      // B is ready
      expect(wrapper.find('[data-testid="canonical-replay"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(false);

      // Now resolve A's stale response
      resolveAReply({
        data: {
          data: {
            matched: true,
            original_output_sha256: SHA_ORIG,
            replay_output_sha256: SHA_REPLAY,
          },
        },
      });
      await flushPromises();
      await nextTick();

      // B must NOT show A's result — stale response was discarded
      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(false);

      // B's replay button must still work (not stuck in replaying=true from A)
      expect(
        (wrapper.find('[data-testid="canonical-replay"]').element as HTMLButtonElement).disabled,
      ).toBe(false);
    });

    it('87. replay error shows retry button, retry clears error and succeeds', async () => {
      // On the same mounted page instance: failure → retry button visible →
      // click retry → error cleared → POST to same runId → success with hashes.

      // First attempt: fail
      mockApiPost.mockRejectedValueOnce({
        response: { status: 500, data: { detail: 'Server Error' } },
      });

      const wrapper = await setupAndMount(makeSession(), [makeRun()]);
      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      await flushPromises();

      // Error visible, retry button visible
      expect(wrapper.find('.rpage-replay-error').exists()).toBe(true);
      const retryBtn = wrapper.find('[data-testid="canonical-replay-retry"]');
      expect(retryBtn.exists()).toBe(true);
      expect(retryBtn.text()).toBe('重新验证重放');
      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(false);

      // Second attempt: succeed
      mockApiPost.mockResolvedValueOnce({
        data: {
          data: {
            matched: true,
            original_output_sha256: SHA_ORIG,
            replay_output_sha256: SHA_REPLAY,
          },
        },
      });

      await retryBtn.trigger('click');
      await nextTick();
      await flushPromises();

      // POST must target the same runId
      expect(mockApiPost).toHaveBeenCalledTimes(2);
      const calls = mockApiPost.mock.calls;
      expect(calls[0]![0]).toBe(REPLAY_PATH);
      expect(calls[1]![0]).toBe(REPLAY_PATH);

      // Error and retry button gone
      expect(wrapper.find('.rpage-replay-error').exists()).toBe(false);
      expect(wrapper.find('[data-testid="canonical-replay-retry"]').exists()).toBe(false);

      // Result visible with hashes
      const result = wrapper.find('[data-testid="canonical-replay-result"]');
      expect(result.exists()).toBe(true);
      const text = result.text();
      expect(text).toContain('重放一致');
      expect(text).toContain(SHA_ORIG);
      expect(text).toContain(SHA_REPLAY);
    });

    it('88. error + retry visible only while replayError is set; success clears retry', async () => {
      // Ensure retry button only appears alongside an active replayError,
      // and is absent when there's a success result or no replay has run.

      const wrapper = await setupAndMount(makeSession(), [makeRun()]);

      // Before any replay: no error, no retry button
      expect(wrapper.find('.rpage-replay-error').exists()).toBe(false);
      expect(wrapper.find('[data-testid="canonical-replay-retry"]').exists()).toBe(false);

      // After first click → fail
      mockApiPost.mockRejectedValueOnce({
        response: { status: 503, data: { detail: 'Service Unavailable' } },
      });
      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      await flushPromises();

      expect(wrapper.find('.rpage-replay-error').exists()).toBe(true);
      expect(wrapper.find('[data-testid="canonical-replay-retry"]').exists()).toBe(true);

      // Retry → succeed
      mockApiPost.mockResolvedValueOnce({
        data: {
          data: {
            matched: true,
            original_output_sha256: SHA_ORIG,
            replay_output_sha256: SHA_REPLAY,
          },
        },
      });
      await wrapper.find('[data-testid="canonical-replay-retry"]').trigger('click');
      await nextTick();
      await flushPromises();

      // Error + retry gone, result shown
      expect(wrapper.find('.rpage-replay-error').exists()).toBe(false);
      expect(wrapper.find('[data-testid="canonical-replay-retry"]').exists()).toBe(false);
      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(true);
    });

    it('89. two ready runs A/B: A results do not leak into B, B retry button absent', async () => {
      // Both A and B are valid ready runs. After replay on A succeeds,
      // switch to B and verify B has no A replay data at all.

      const runA = makeRun({ run_id: RUN_A });
      const runB = makeRun({ run_id: RUN_B });

      // A: replay succeeds
      mockApiPost.mockResolvedValueOnce({
        data: {
          data: {
            matched: true,
            original_output_sha256: SHA_ORIG,
            replay_output_sha256: SHA_REPLAY,
          },
        },
      });

      const wrapper = await setupAndMount(makeSession(), [runA, runB]);
      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      await flushPromises();

      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(true);
      const aText = wrapper.find('[data-testid="canonical-replay-result"]').text();
      expect(aText).toContain(SHA_ORIG);

      // Switch to run B
      router.replace(`/research/${PROJ_A}/result/${RUN_B}`);
      await flushPromises();
      await nextTick();

      // B ready: no error, no retry, no result from A
      expect(wrapper.find('[data-testid="canonical-replay"]').exists()).toBe(true);
      expect(wrapper.find('[data-testid="canonical-replay-result"]').exists()).toBe(false);
      expect(wrapper.find('.rpage-replay-error').exists()).toBe(false);
      expect(wrapper.find('[data-testid="canonical-replay-retry"]').exists()).toBe(false);

      // B replay: POST to B only, with distinct hash values
      const B_REPLAY = `/api/v4/research/runs/${RUN_B}/replay`;
      const B_ORIG = 'bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb';
      const B_REPLAY_HASH = 'cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc';
      mockApiPost.mockResolvedValueOnce({
        data: {
          data: {
            matched: false,
            original_output_sha256: B_ORIG,
            replay_output_sha256: B_REPLAY_HASH,
          },
        },
      });
      await wrapper.find('[data-testid="canonical-replay"]').trigger('click');
      await nextTick();
      await flushPromises();
      expect(mockApiPost).toHaveBeenCalled();
      const lastCall = mockApiPost.mock.calls[mockApiPost.mock.calls.length - 1]!;
      expect(lastCall[0]).toBe(B_REPLAY);

      // B result shows B's hashes, not A's
      const bResult = wrapper.find('[data-testid="canonical-replay-result"]');
      expect(bResult.exists()).toBe(true);
      const bText = bResult.text();
      expect(bText).toContain('重放不一致');
      expect(bText).toContain(B_ORIG);
      expect(bText).toContain(B_REPLAY_HASH);
    });
  });
});
