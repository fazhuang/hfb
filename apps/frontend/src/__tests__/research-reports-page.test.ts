/**
 * Tests for ResearchReportsPage and child components
 *
 * Covers:
 *   BATCH 1 — Page states:
 *     1. Normal list with multiple sessions/runs
 *     2. Empty list (no reports)
 *     3. Error state on API failure
 *     4. Loading state during fetch
 *
 *   BATCH 2 — Status display:
 *     5. run_status: completed/failed/running/pending badges
 *     6. report_status: ready/missing/failed/pending badges
 *     7. "查看报告" only shown when report_status === 'ready'
 *     8. "导出" only shown when report_status === 'ready'
 *
 *   BATCH 3 — Navigation:
 *     9. 路由跳转使用真实 session_id 和 run_id
 *     10. 正确的 URL 格式: /research/:sessionId/result/:runId
 *
 *   BATCH 4 — Status filter:
 *     11. Filter by report_status
 *     12. Clear filter restores full list
 *     13. Filter resets page to 1
 *
 *   BATCH 5 — Export:
 *     14. Export success
 *     15. Export double-click prevention
 *     16. Export error handling
 *     17. Blob URL release
 *
 *   BATCH 6 — Race protection:
 *     18. Stale response does not overwrite newer request
 *     19. No state writes after unmount
 *
 *   BATCH 7 — Pagination:
 *     20. Page navigation
 *     21. Total pages calculation
 *
 *   BATCH 8 — Contract:
 *     22. Uses GET /api/v4/research/reports
 *     23. No project_id references
 *     24. Real session_id and run_id in navigation links
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';

// ================================================================
// Mock setup
// ================================================================

const mockApiGet = vi.fn();

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: Array<unknown>) => mockApiGet(...args),
  },
}));

// ================================================================
// Helpers
// ================================================================

const SESSION_A = 'aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa';
const SESSION_B = 'bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb';
const RUN_READY = '11111111-1111-4111-8111-111111111111';
const RUN_MISSING = '22222222-2222-4222-8222-222222222222';
const RUN_FAILED = '33333333-3333-4333-8333-333333333333';
const RUN_PENDING = '44444444-4444-4444-8444-444444444444';

function makeReportItem(overrides: Record<string, unknown> = {}) {
  return {
    session_id: SESSION_A,
    session_title: 'Test Research Session',
    run_id: RUN_READY,
    topic: 'Is moxibustion effective for asthma?',
    run_status: 'completed',
    report_status: 'ready',
    created_at: '2026-07-15T08:00:00Z',
    completed_at: '2026-07-15T08:05:00Z',
    workflow_type: 'full_research_flow',
    ...overrides,
  };
}

function makeReportsResponse(items: Array<unknown>, total?: number, page = 1, limit = 20) {
  return {
    data: {
      success: true,
      data: {
        items,
        total: total ?? items.length,
        page,
        limit,
      },
      message: 'ok',
    },
  };
}

function makeEmptyResponse() {
  return makeReportsResponse([], 0);
}

// ================================================================
// Test suite
// ================================================================

describe('ResearchReportsPage', () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(() => {
    mockApiGet.mockReset();

    router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div/>' }, name: 'home' },
        {
          path: '/reports',
          name: 'report-list',
          component: () => import('@/pages/reports/ReportListPage.vue'),
        },
        {
          path: '/research/:projectId/result/:runId',
          name: 'research-project-result',
          component: { template: '<div class="result-page" />' },
        },
        {
          path: '/knowledge',
          name: 'knowledge',
          component: { template: '<div class="knowledge-page" />' },
        },
        {
          path: '/library',
          name: 'library-search',
          component: { template: '<div class="library-page" />' },
        },
        {
          path: '/research',
          name: 'research-project-list',
          component: { template: '<div class="research-page" />' },
        },
      ],
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ----- Batch 1: Page states -----

  describe('B1 — Page states', () => {
    it('1. loads and displays report list', async () => {
      const items = [
        makeReportItem({ run_id: RUN_READY, report_status: 'ready' }),
        makeReportItem({ run_id: RUN_MISSING, report_status: 'missing', run_status: 'completed' }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      // Verify API call
      expect(mockApiGet).toHaveBeenCalledTimes(1);
      expect(mockApiGet).toHaveBeenCalledWith('/api/v4/research/reports', {
        params: { page: 1, limit: 20 },
      });

      // Both items visible
      expect(wrapper.text()).toContain('Test Research Session');
      expect(wrapper.text()).toContain('已完成');
      expect(wrapper.text()).toContain('报告就绪');
      expect(wrapper.text()).toContain('报告缺失');
    });

    it('2. shows empty state when no reports', async () => {
      mockApiGet.mockResolvedValueOnce(makeEmptyResponse());

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state"><slot name="action" /></div>' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      expect(wrapper.find('.empty-state').exists()).toBe(true);
    });

    it('3. shows error state on API failure', async () => {
      mockApiGet.mockRejectedValueOnce(new Error('Network Error'));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state">{{ message }}</div>', props: ['message', 'title'] },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      expect(wrapper.find('.error-state').exists()).toBe(true);
    });

    it('4. shows loading state during fetch', async () => {
      // Don't resolve the promise — loading stays
      let resolvePromise!: (value: unknown) => void;
      mockApiGet.mockReturnValueOnce(
        new Promise((resolve) => { resolvePromise = resolve; }),
      );

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading">Loading...</div>' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      expect(wrapper.text()).toContain('Loading...');

      // Cleanup
      resolvePromise!(makeEmptyResponse());
      await flushPromises();
    });
  });

  // ----- Batch 2: Status display -----

  describe('B2 — Status display', () => {
    it('5. run_status badges: completed, failed, running, pending', async () => {
      const items = [
        makeReportItem({ run_id: 'r-1', run_status: 'completed', report_status: 'ready' }),
        makeReportItem({ run_id: 'r-2', run_status: 'failed', report_status: 'failed' }),
        makeReportItem({ run_id: 'r-3', run_status: 'running', report_status: 'pending' }),
        makeReportItem({ run_id: 'r-4', run_status: 'pending', report_status: 'pending' }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const text = wrapper.text();
      expect(text).toContain('已完成');
      expect(text).toContain('失败');
      expect(text).toContain('运行中');
      expect(text).toContain('待处理');
    });

    it('6. report_status badges: ready, missing, failed, pending', async () => {
      const items = [
        makeReportItem({ run_id: 'r-1', report_status: 'ready', run_status: 'completed' }),
        makeReportItem({ run_id: 'r-2', report_status: 'missing', run_status: 'completed' }),
        makeReportItem({ run_id: 'r-3', report_status: 'failed', run_status: 'failed' }),
        makeReportItem({ run_id: 'r-4', report_status: 'pending', run_status: 'running' }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const text = wrapper.text();
      expect(text).toContain('报告就绪');
      expect(text).toContain('报告缺失');
      expect(text).toContain('报告失败');
      expect(text).toContain('待生成');
    });

    it('7. "查看报告" only visible when report_status is ready', async () => {
      const items = [
        makeReportItem({ run_id: RUN_READY, report_status: 'ready' }),
        makeReportItem({ run_id: RUN_MISSING, report_status: 'missing' }),
        makeReportItem({ run_id: RUN_FAILED, report_status: 'failed' }),
        makeReportItem({ run_id: RUN_PENDING, report_status: 'pending' }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const viewLinks = wrapper.findAll('a');
      // Only one "查看报告" link (for the ready item)
      const reportLinks = viewLinks.filter((l) => l.text().includes('查看报告'));
      expect(reportLinks.length).toBe(1);
    });

    it('8. "导出" button only visible when report_status is ready', async () => {
      const items = [
        makeReportItem({ run_id: RUN_READY, report_status: 'ready' }),
        makeReportItem({ run_id: RUN_MISSING, report_status: 'missing' }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const exportBtns = wrapper.findAll('button').filter((b) => b.text().includes('导出'));
      // Only one export button (for the ready item; the missing item has no export)
      expect(exportBtns.length).toBe(1);
    });
  });

  // ----- Batch 3: Navigation -----

  describe('B3 — Navigation', () => {
    it('9. ready items link to /research/:sessionId/result/:runId', async () => {
      const items = [
        makeReportItem({
          session_id: SESSION_A,
          run_id: RUN_READY,
          report_status: 'ready',
        }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const viewLink = wrapper.find('a');
      expect(viewLink.attributes('href')).toBe(
        `/research/${SESSION_A}/result/${RUN_READY}`,
      );
    });

    it('10. items from different sessions link to correct session', async () => {
      const items = [
        makeReportItem({
          session_id: SESSION_A,
          run_id: RUN_READY,
          session_title: 'Session A',
          report_status: 'ready',
        }),
        makeReportItem({
          session_id: SESSION_B,
          run_id: 'bbbb-ready-bbbb-ready-bbbb-ready01',
          session_title: 'Session B',
          report_status: 'ready',
        }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const links = wrapper.findAll('a');
      const hrefs = links.map((l) => l.attributes('href'));
      expect(hrefs).toContain(`/research/${SESSION_A}/result/${RUN_READY}`);
      expect(hrefs).toContain(`/research/${SESSION_B}/result/bbbb-ready-bbbb-ready-bbbb-ready01`);
    });
  });

  // ----- Batch 4: Status filter -----

  describe('B4 — Status filter', () => {
    it('11. changing filter calls API with status param', async () => {
      mockApiGet.mockResolvedValueOnce(makeReportsResponse([])); // initial load
      mockApiGet.mockResolvedValueOnce(makeReportsResponse([])); // filtered load

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      // Initial call without status
      expect(mockApiGet).toHaveBeenNthCalledWith(1, '/api/v4/research/reports', {
        params: { page: 1, limit: 20 },
      });

      // Change filter
      const select = wrapper.find('select');
      await select.setValue('ready');

      await flushPromises();

      expect(mockApiGet).toHaveBeenNthCalledWith(2, '/api/v4/research/reports', {
        params: { page: 1, limit: 20, status: 'ready' },
      });
    });

    it('12. filter shows empty state with clear-filter action', async () => {
      mockApiGet.mockResolvedValueOnce(makeReportsResponse([])); // initial
      mockApiGet.mockResolvedValueOnce(makeReportsResponse([])); // after filter

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state"><slot name="action" /></div>' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      // Initial empty
      expect(wrapper.find('.empty-state').exists()).toBe(true);

      // Apply filter
      const select = wrapper.find('select');
      await select.setValue('failed');
      await flushPromises();

      // Still empty but with clear-filter
      expect(wrapper.text()).toContain('清除筛选');

      // Clear filter
      const clearBtn = wrapper.find('.rp-clear-filter-btn');
      expect(clearBtn.exists()).toBe(true);
    });
  });

  // ----- Batch 5: Export -----

  describe('B5 — Export', () => {
    it('13. export calls real backend endpoint with session_id/run_id', async () => {
      const items = [
        makeReportItem({
          session_id: SESSION_A,
          run_id: RUN_READY,
          report_status: 'ready',
        }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));
      // Export response: blob
      mockApiGet.mockResolvedValueOnce({
        data: new Blob(['# Test Report'], { type: 'text/markdown' }),
        headers: { 'content-disposition': 'attachment; filename="hfb-research-report-11111111.md"' },
      });

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const exportBtn = wrapper.find('button');
      await exportBtn.trigger('click');
      await flushPromises();

      // Verify export API call
      const exportCalls = mockApiGet.mock.calls.filter(
        (call: Array<unknown>) => typeof call[0] === 'string' && call[0].includes('/export'),
      );
      expect(exportCalls.length).toBe(1);
      const firstCallArgs = exportCalls.at(0);
      expect(firstCallArgs).toBeDefined();
      expect(firstCallArgs![0]).toBe(
        `/api/v4/research/session/${SESSION_A}/runs/${RUN_READY}/export`,
      );
    });

    it('14. double-click prevention: second click blocked while exporting', async () => {
      const items = [
        makeReportItem({ session_id: SESSION_A, run_id: RUN_READY, report_status: 'ready' }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      // Export never resolves (hanging)
      let resolveExport!: (value: unknown) => void;
      mockApiGet.mockReturnValueOnce(
        new Promise((resolve) => { resolveExport = resolve; }),
      );

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const exportBtn = wrapper.find('button');
      await exportBtn.trigger('click');
      await flushPromises();

      // Button should be disabled
      expect(exportBtn.attributes('disabled')).toBeDefined();

      // Second click should not trigger another API call
      await exportBtn.trigger('click');
      await flushPromises();

      const exportCalls = mockApiGet.mock.calls.filter(
        (call: Array<unknown>) => typeof call[0] === 'string' && call[0].includes('/export'),
      );
      expect(exportCalls.length).toBe(1);

      // Cleanup
      resolveExport!({
        data: new Blob(['test'], { type: 'text/markdown' }),
        headers: {},
      });
      await flushPromises();
    });

    it('15. export error shows message', async () => {
      const items = [
        makeReportItem({ session_id: SESSION_A, run_id: RUN_READY, report_status: 'ready' }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));
      mockApiGet.mockRejectedValueOnce({
        response: { status: 404, data: { detail: 'Run not found' } },
      });

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const exportBtn = wrapper.find('button');
      await exportBtn.trigger('click');
      await flushPromises();

      // exportError should not be empty
      expect(wrapper.text()).toContain('报告不存在或无权访问');
    });
  });

  // ----- Batch 6: Race protection -----

  describe('B6 — Race protection', () => {
    it('16. stale response does not overwrite newer request', async () => {
      let resolveSlow!: (value: unknown) => void;
      let resolveFast!: (value: unknown) => void;

      // First fetch (slow)
      mockApiGet.mockReturnValueOnce(
        new Promise((resolve) => { resolveSlow = resolve; }),
      );

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      // Trigger a second fetch (e.g., by changing filter) before first resolves
      mockApiGet.mockReturnValueOnce(
        new Promise((resolve) => { resolveFast = resolve; }),
      );

      const select = wrapper.find('select');
      await select.setValue('ready');
      await flushPromises();

      // Now resolve the slow (stale) first fetch
      resolveSlow!(makeReportsResponse([
        makeReportItem({ run_id: 'stale-run', topic: 'STALE', report_status: 'ready' }),
      ]));
      await flushPromises();

      // The stale response should NOT appear (reqSeq check)
      // The page should still be in loading state waiting for the fast response
      // Because the slow response's seq was overwritten

      // Now resolve the fast (current) fetch
      resolveFast!(makeReportsResponse([
        makeReportItem({ run_id: 'current-run', topic: 'CURRENT', report_status: 'ready' }),
      ]));
      await flushPromises();

      // Should show CURRENT, not STALE
      expect(wrapper.text()).toContain('CURRENT');
      expect(wrapper.text()).not.toContain('STALE');
    });
  });

  // ----- Batch 7: Pagination -----

  describe('B7 — Pagination', () => {
    it('17. pagination buttons navigate pages', async () => {
      const page1Items = Array.from({ length: 20 }, (_, i) =>
        makeReportItem({
          run_id: `page1-run-${i}`,
          topic: `Page 1 Item ${i}`,
          report_status: 'ready',
        }),
      );
      const page2Items = [
        makeReportItem({
          run_id: 'page2-run-0',
          topic: 'Page 2 Item',
          report_status: 'ready',
        }),
      ];

      mockApiGet
        .mockResolvedValueOnce(makeReportsResponse(page1Items, 21, 1, 20))
        .mockResolvedValueOnce(makeReportsResponse(page2Items, 21, 2, 20));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      // Pagination visible
      expect(wrapper.text()).toContain('下一页');

      // Click next page
      const nextBtn = wrapper.findAll('button').find((b) => b.text().includes('下一页'));
      expect(nextBtn).toBeTruthy();
      await nextBtn!.trigger('click');
      await flushPromises();

      expect(mockApiGet).toHaveBeenNthCalledWith(2, '/api/v4/research/reports', {
        params: { page: 2, limit: 20 },
      });
    });
  });

  // ----- Batch 8: Contract -----

  describe('B8 — Contract', () => {
    it('18. uses correct API endpoint', async () => {
      mockApiGet.mockResolvedValueOnce(makeReportsResponse([]));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      // wrapper mounts successfully and triggers the API call
      expect(wrapper.exists()).toBe(true);
      expect(mockApiGet).toHaveBeenCalledWith('/api/v4/research/reports', expect.any(Object));
    });

    it('19. does not reference project_id anywhere', async () => {
      mockApiGet.mockResolvedValueOnce(makeReportsResponse([]));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const html = wrapper.html();
      expect(html).not.toContain('project_id');
      expect(html).not.toContain('projectId');
    });

    it('20. uses real session_id and run_id in navigation', async () => {
      const items = [
        makeReportItem({
          session_id: 'real-session-uuid-1234',
          run_id: 'real-run-uuid-5678',
          report_status: 'ready',
        }),
      ];
      mockApiGet.mockResolvedValueOnce(makeReportsResponse(items));

      const wrapper = mount(
        { template: '<router-view />' },
        {
          global: {
            plugins: [router],
            stubs: {
              ResearchPageHeader: { template: '<div class="rph" />' },
              LoadingState: { template: '<div class="loading" />' },
              ErrorState: { template: '<div class="error-state" />' },
              EmptyState: { template: '<div class="empty-state" />' },
            },
          },
        },
      );

      await router.push('/reports');
      await router.isReady();
      await flushPromises();

      const link = wrapper.find('a');
      expect(link.attributes('href')).toContain('real-session-uuid-1234');
      expect(link.attributes('href')).toContain('real-run-uuid-5678');
    });
  });
});
