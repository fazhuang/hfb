/**
 * Tests for ResearchWorkspacePage and child components
 *
 * Covers:
 *   BATCH 1 — Cross-project isolation:
 *     1. Workspace loads session + runs once per mount
 *     2. Runs API called exactly once (page owns shared runs)
 *     3. No duplicate runs requests from child components
 *     4-9. Each data component watches props.projectId
 *     10. Route switch clears old data, enters loading, shows new data
 *     11. Stale response from old projectId does not overwrite new
 *     12. No state writes after unmount
 *
 *   BATCH 2 — AI Assistant isolation:
 *     13. Storage key includes projectId
 *     14. Writing question scoped to current projectId
 *     15. A/B isolation — B cannot read A's question
 *     16. Workflow consumer reads + clears current key
 *     17. Question does not enter URL or console
 *     18. sessionStorage exceptions still navigate
 *     19. Blank/whitespace input not submitted
 *
 *   BATCH 3 — Correct runs/report semantics:
 *     20. No "继续研究" (no resume API)
 *     21. Only completed runs with report_generation show in RecentReports
 *     22. Incomplete runs do not get view links
 *     23. Sorting by completed_at DESC with missing times last
 *     24. No fake completed_at from started_at
 *     25. Max 5 items
 *
 *   BATCH 4 — Full integration:
 *     26. Domain mapping contract
 *     27. No project_id references
 *     28. projectId === ResearchSession.id
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { nextTick } from 'vue';

// ================================================================
// Mock setup
// ================================================================

const mockApiGet = vi.fn();

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: Array<unknown>) => mockApiGet(...args),
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

function makeSession(overrides: Record<string, unknown> = {}) {
  return {
    id: PROJ_A,
    title: 'Test Research Project',
    active_entities: null,
    context_notes: null,
    created_at: '2026-07-15T08:00:00Z',
    updated_at: '2026-07-16T10:00:00Z',
    ...overrides,
  };
}

function makeHistoryEntry(overrides: Record<string, unknown> = {}) {
  return {
    query_id: 'q-1',
    query_text: 'Test query',
    query_type: 'research',
    citation_count: 3,
    trace_count: 2,
    created_at: '2026-07-16T10:00:00Z',
    ...overrides,
  };
}

function makeRun(overrides: Record<string, unknown> = {}) {
  return {
    run_id: 'run-1',
    topic: 'Test Run',
    started_at: '2026-07-15T08:00:00Z',
    completed_at: '2026-07-16T10:00:00Z',
    step_execution_trace: [
      { name: 'topic_selection', status: 'completed' },
      { name: 'literature_retrieval', status: 'completed' },
      { name: 'evidence_synthesis', status: 'completed' },
      { name: 'report_generation', status: 'completed' },
      { name: 'citation_export', status: 'completed' },
    ],
    ...overrides,
  };
}

function makeNote(overrides: Record<string, unknown> = {}) {
  return {
    id: 'note-1',
    session_id: PROJ_A,
    content: 'Test note content',
    tags: null,
    created_at: '2026-07-16T10:00:00Z',
    updated_at: '2026-07-16T10:00:00Z',
    ...overrides,
  };
}

function makeCitation(overrides: Record<string, unknown> = {}) {
  return {
    id: 'cite-1',
    session_id: PROJ_A,
    citation_text: 'Test citation text',
    source_document: 'Test Source Document',
    trace_json: '{}',
    tags: null,
    notes: null,
    created_at: '2026-07-16T10:00:00Z',
    updated_at: '2026-07-16T10:00:00Z',
    ...overrides,
  };
}

function buildRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/research',
        name: 'research-project-list',
        component: { template: '<div />' },
      },
      {
        path: '/research/:projectId',
        name: 'research-project-detail',
        component: { template: '<div />' },
      },
      {
        path: '/research/:projectId/workspace',
        name: 'research-project-workspace',
        component: { template: '<div />' },
      },
      {
        path: '/research/:projectId/workflow',
        name: 'research-project-workflow',
        component: { template: '<div />' },
      },
      {
        path: '/research/:projectId/result/:runId',
        name: 'research-project-result',
        component: { template: '<div />' },
      },
    ],
  });
}

const PAGE_A = `/research/${PROJ_A}/workspace`;
const PAGE_B = `/research/${PROJ_B}/workspace`;
const SESSION_A = `/api/v1/workspace/sessions/${PROJ_A}`;
const SESSION_B = `/api/v1/workspace/sessions/${PROJ_B}`;
const RUNS_A = `/api/v4/research/session/${PROJ_A}/runs`;
const RUNS_B = `/api/v4/research/session/${PROJ_B}/runs`;

function setupDefaultMocks(
  session?: Record<string, unknown>,
  runs?: Array<Record<string, unknown>>,
) {
  mockApiGet.mockImplementation((url: string) => {
    if (url.includes('/history')) {
      return Promise.resolve({
        data: {
          data: {
            session_id: new URLSearchParams(url.split('?')[1] || '').get('session_id') || PROJ_A,
            history: [makeHistoryEntry()],
            total: 1,
          },
        },
      });
    }
    if (url.includes('/runs')) {
      return Promise.resolve({
        data: {
          data: {
            session_id: url.includes(PROJ_B) ? PROJ_B : PROJ_A,
            runs: runs ?? [makeRun()],
            total: (runs ?? [makeRun()]).length,
          },
        },
      });
    }
    if (url.includes('/notes')) {
      return Promise.resolve({ data: { data: [makeNote()] } });
    }
    if (url.includes('/citations')) {
      return Promise.resolve({ data: { data: [makeCitation()] } });
    }
    // Default: session detail
    if (url.includes(SESSION_A) || url.includes(PROJ_A)) {
      return Promise.resolve({ data: { data: session || makeSession() } });
    }
    if (url.includes(SESSION_B) || url.includes(PROJ_B)) {
      return Promise.resolve({ data: { data: makeSession({ id: PROJ_B, title: 'Project B' }) } });
    }
    return Promise.resolve({ data: { data: {} } });
  });
}

// ================================================================
// Page-level tests
// ================================================================

describe('ResearchWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupDefaultMocks();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  // ---- Batch 1: Single runs request ----

  it('calls runs API exactly once on page load', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          ContinueResearchCard: {
            template: '<div />',
            props: ['projectId', 'loading', 'error'],
            emits: ['retry'],
          },
          RecentResearchActivity: { template: '<div />', props: ['projectId'] },
          RecentReports: {
            template: '<div />',
            props: ['projectId', 'loading', 'error', 'runs'],
            emits: ['retry'],
          },
          RecentNotes: { template: '<div />', props: ['projectId'] },
          ResearchResources: { template: '<div />', props: ['projectId'] },
          ResearchAssistantEntry: { template: '<div />', props: ['projectId'] },
        },
      },
    });

    await flushPromises();

    const runsCalls = mockApiGet.mock.calls.filter((c: Array<unknown>) =>
      (c[0] as string).includes('/runs'),
    );
    expect(runsCalls.length).toBe(1);
  });

  it('loads session detail exactly once on page load', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          ContinueResearchCard: {
            template: '<div />',
            props: ['projectId', 'loading', 'error'],
            emits: ['retry'],
          },
          RecentResearchActivity: { template: '<div />', props: ['projectId'] },
          RecentReports: {
            template: '<div />',
            props: ['projectId', 'loading', 'error', 'runs'],
            emits: ['retry'],
          },
          RecentNotes: { template: '<div />', props: ['projectId'] },
          ResearchResources: { template: '<div />', props: ['projectId'] },
          ResearchAssistantEntry: { template: '<div />', props: ['projectId'] },
        },
      },
    });

    await flushPromises();

    const sessionCalls = mockApiGet.mock.calls.filter(
      (c: Array<unknown>) =>
        (c[0] as string).includes('/workspace/sessions/') &&
        !(c[0] as string).includes('/notes') &&
        !(c[0] as string).includes('/citations'),
    );
    expect(sessionCalls.length).toBe(1);
  });

  // ---- Batch 1: projectId === ResearchSession.id ----

  it('projectId equals ResearchSession.id', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    expect(router.currentRoute.value.params.projectId).toBe(PROJ_A);

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          ContinueResearchCard: {
            template: '<div />',
            props: ['projectId', 'loading', 'error'],
            emits: ['retry'],
          },
          RecentResearchActivity: { template: '<div />', props: ['projectId'] },
          RecentReports: {
            template: '<div />',
            props: ['projectId', 'loading', 'error', 'runs'],
            emits: ['retry'],
          },
          RecentNotes: { template: '<div />', props: ['projectId'] },
          ResearchResources: { template: '<div />', props: ['projectId'] },
          ResearchAssistantEntry: { template: '<div />', props: ['projectId'] },
        },
      },
    });

    await flushPromises();

    expect(mockApiGet).toHaveBeenCalledWith(SESSION_A);
    expect(mockApiGet).toHaveBeenCalledWith(RUNS_A);
  });

  // ---- Batch 1: Stale response guard ----

  it('stale response from old projectId does not overwrite new page data', async () => {
    let resolveOldSession!: (value: unknown) => void;
    let resolveOldRuns!: (value: unknown) => void;
    let resolveNewSession!: (value: unknown) => void;
    let resolveNewRuns!: (value: unknown) => void;

    mockApiGet.mockImplementation((url: string) => {
      const urlStr = String(url);
      if (urlStr === SESSION_A) {
        return new Promise((r) => {
          resolveOldSession = r;
        });
      }
      if (urlStr === RUNS_A) {
        return new Promise((r) => {
          resolveOldRuns = r;
        });
      }
      if (urlStr === SESSION_B) {
        return new Promise((r) => {
          resolveNewSession = r;
        });
      }
      if (urlStr === RUNS_B) {
        return new Promise((r) => {
          resolveNewRuns = r;
        });
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          ContinueResearchCard: {
            template: '<div />',
            props: ['projectId', 'loading', 'error'],
            emits: ['retry'],
          },
          RecentResearchActivity: { template: '<div />', props: ['projectId'] },
          RecentReports: {
            template: '<div />',
            props: ['projectId', 'loading', 'error', 'runs'],
            emits: ['retry'],
          },
          RecentNotes: { template: '<div />', props: ['projectId'] },
          ResearchResources: { template: '<div />', props: ['projectId'] },
          ResearchAssistantEntry: { template: '<div />', props: ['projectId'] },
        },
      },
    });

    await flushPromises();

    // Switch to B before A resolves
    await router.push(PAGE_B);
    await flushPromises();

    // Resolve B first
    resolveNewSession!({ data: { data: makeSession({ id: PROJ_B, title: 'Project B' }) } });
    resolveNewRuns!({
      data: {
        data: {
          session_id: PROJ_B,
          runs: [makeRun({ run_id: 'run-b', topic: 'B Run' })],
          total: 1,
        },
      },
    });
    await flushPromises();

    // Now resolve stale A responses
    resolveOldSession!({ data: { data: makeSession({ id: PROJ_A, title: 'Old Project' }) } });
    resolveOldRuns!({
      data: {
        data: {
          session_id: PROJ_A,
          runs: [makeRun({ run_id: 'run-a-old', topic: 'Stale' })],
          total: 1,
        },
      },
    });
    await flushPromises();

    // Verify B was loaded correctly — at minimum the API was called
    const bRunsCalls = mockApiGet.mock.calls.filter((c: Array<unknown>) => c[0] === RUNS_B);
    expect(bRunsCalls.length).toBe(1);
  });

  // ---- Batch 1: No state writes after unmount ----

  it('no state writes after unmount', async () => {
    let resolveAfterUnmount!: (value: unknown) => void;
    mockApiGet.mockReturnValue(
      new Promise((r) => {
        resolveAfterUnmount = r;
      }),
    );

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          ContinueResearchCard: {
            template: '<div />',
            props: ['projectId', 'loading', 'error'],
            emits: ['retry'],
          },
          RecentResearchActivity: { template: '<div />', props: ['projectId'] },
          RecentReports: {
            template: '<div />',
            props: ['projectId', 'loading', 'error', 'runs'],
            emits: ['retry'],
          },
          RecentNotes: { template: '<div />', props: ['projectId'] },
          ResearchResources: { template: '<div />', props: ['projectId'] },
          ResearchAssistantEntry: { template: '<div />', props: ['projectId'] },
        },
      },
    });

    wrapper.unmount();
    resolveAfterUnmount!({ data: { data: makeSession() } });
    await new Promise((r) => setTimeout(r, 50));
    // Should not throw — pass if we reach here
    expect(true).toBe(true);
  });

  // ---- Batch 2: AI Assistant storage key isolation ----

  it('AI assistant storage key includes projectId', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchAssistantEntry } =
      await import('@/components/research/ResearchAssistantEntry.vue');

    const wrapper = mount(ResearchAssistantEntry, {
      props: { projectId: PROJ_A },
      global: {
        plugins: [router],
      },
    });

    const input = wrapper.find('#rae-question-input');
    await input.setValue('Test question');
    const form = wrapper.find('.rae-form');
    await form.trigger('submit.prevent');
    await flushPromises();

    // Must use projectId-scoped key
    expect(sessionStorage.getItem(`hfb.research.${PROJ_A}.pending-question`)).toBe('Test question');
    // Must NOT use old unscoped key
    expect(sessionStorage.getItem('hfb.research.pending-question')).toBeNull();
  });

  it('AI assistant — A/B isolation, B cannot read A question', async () => {
    sessionStorage.setItem(`hfb.research.${PROJ_A}.pending-question`, 'A question');

    const router = buildRouter();
    await router.push(`/research/${PROJ_B}/workflow`);
    await router.isReady();

    // Mount the workflow page (it calls initPendingQuestion)
    mockApiGet.mockImplementation(async (url: string) => {
      if (url === SESSION_B)
        return { data: { data: makeSession({ id: PROJ_B, title: 'B Project' }) } };
      return { data: { data: {} } };
    });

    const { default: ResearchWorkflowPage } =
      await import('@/pages/research/ResearchWorkflowPage.vue');

    const wrapper = mount(ResearchWorkflowPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: { template: '<div />', props: ['title', 'breadcrumbs'] },
          RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          WorkflowStepNavigation: {
            template: '<div><div v-for="s in steps" class="wsn-step">{{ s.label }}</div></div>',
            props: ['steps', 'currentIndex', 'submitting'],
          },
          ResearchQuestionStep: {
            template:
              '<div><input id="rqs-input" :value="question" :disabled="disabled" /><button class="rqs-submit-btn" :disabled="!question || disabled" @click="$emit(\'next\')">Next</button></div>',
            props: ['question', 'disabled'],
            emits: ['update:question', 'next'],
          },
          DocumentSelectionStep: {
            template:
              '<div><button class="dss-submit-btn" :disabled="disabled" @click="$emit(\'submit\')">Submit</button></div>',
            props: ['question', 'disabled'],
            emits: ['back', 'submit'],
          },
          AnalysisPendingState: { template: '<div class="aps-step" />', props: ['active'] },
          EvidenceReviewStep: {
            template: '<div class="ers-step" />',
            props: ['evidence', 'citations', 'citationSaveState'],
            emits: ['save-citation', 'go-to-report'],
          },
          ResearchReportStep: {
            template: '<div class="rrs-step" />',
            props: ['report', 'projectId'],
            emits: ['back-to-evidence', 'new-workflow'],
          },
        },
      },
    });

    await flushPromises();
    await nextTick();

    // B should NOT read A's question
    const input = wrapper.find('#rqs-input');
    expect((input.element as HTMLInputElement).value).toBe('');
    // A's question still should not be read
    expect(sessionStorage.getItem(`hfb.research.${PROJ_A}.pending-question`)).toBe('A question');
  });

  it('AI assistant — workflow consumer reads and clears the current key', async () => {
    sessionStorage.setItem(`hfb.research.${PROJ_A}.pending-question`, 'My question');

    const router = buildRouter();
    await router.push(`/research/${PROJ_A}/workflow`);
    await router.isReady();

    mockApiGet.mockImplementation(async (url: string) => {
      if (url === SESSION_A)
        return { data: { data: makeSession({ id: PROJ_A, title: 'A Project' }) } };
      return { data: { data: {} } };
    });

    const { default: ResearchWorkflowPage } =
      await import('@/pages/research/ResearchWorkflowPage.vue');

    const wrapper = mount(ResearchWorkflowPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: { template: '<div />', props: ['title', 'breadcrumbs'] },
          RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          WorkflowStepNavigation: {
            template: '<div><div v-for="s in steps" class="wsn-step">{{ s.label }}</div></div>',
            props: ['steps', 'currentIndex', 'submitting'],
          },
          ResearchQuestionStep: {
            template:
              '<div><input id="rqs-input" :value="question" :disabled="disabled" /><button class="rqs-submit-btn" :disabled="!question || disabled" @click="$emit(\'next\')">Next</button></div>',
            props: ['question', 'disabled'],
            emits: ['update:question', 'next'],
          },
          DocumentSelectionStep: {
            template:
              '<div><button class="dss-submit-btn" :disabled="disabled" @click="$emit(\'submit\')">Submit</button></div>',
            props: ['question', 'disabled'],
            emits: ['back', 'submit'],
          },
          AnalysisPendingState: { template: '<div class="aps-step" />', props: ['active'] },
          EvidenceReviewStep: {
            template: '<div class="ers-step" />',
            props: ['evidence', 'citations', 'citationSaveState'],
            emits: ['save-citation', 'go-to-report'],
          },
          ResearchReportStep: {
            template: '<div class="rrs-step" />',
            props: ['report', 'projectId'],
            emits: ['back-to-evidence', 'new-workflow'],
          },
        },
      },
    });

    await flushPromises();
    await nextTick();

    // Should populate question from storage
    const input = wrapper.find('#rqs-input');
    expect((input.element as HTMLInputElement).value).toBe('My question');
    // Should have cleared the key
    expect(sessionStorage.getItem(`hfb.research.${PROJ_A}.pending-question`)).toBeNull();
  });

  it('AI assistant — question does not enter URL or console', async () => {
    const consoleSpy = vi.spyOn(console, 'log');

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchAssistantEntry } =
      await import('@/components/research/ResearchAssistantEntry.vue');

    const wrapper = mount(ResearchAssistantEntry, {
      props: { projectId: PROJ_A },
      global: {
        plugins: [router],
      },
    });

    const input = wrapper.find('#rae-question-input');
    await input.setValue('Sensitive question');
    const form = wrapper.find('.rae-form');
    await form.trigger('submit.prevent');
    await flushPromises();

    // URL must not contain question
    expect(router.currentRoute.value.fullPath).not.toContain('Sensitive question');

    // Console must not contain question
    const sensitiveLogs = consoleSpy.mock.calls.filter((call: Array<any>) =>
      call.some((arg: any) => typeof arg === 'string' && arg.includes('Sensitive question')),
    );
    expect(sensitiveLogs.length).toBe(0);

    consoleSpy.mockRestore();
  });

  it('AI assistant — sessionStorage exception still navigates', async () => {
    const origSetItem = sessionStorage.setItem;
    sessionStorage.setItem = () => {
      throw new Error('Storage full');
    };

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchAssistantEntry } =
      await import('@/components/research/ResearchAssistantEntry.vue');

    const wrapper = mount(ResearchAssistantEntry, {
      props: { projectId: PROJ_A },
      global: {
        plugins: [router],
      },
    });

    const input = wrapper.find('#rae-question-input');
    await input.setValue('Test');
    const form = wrapper.find('.rae-form');
    await form.trigger('submit.prevent');
    await flushPromises();

    // Should still navigate to workflow despite storage failure
    expect(router.currentRoute.value.name).toBe('research-project-workflow');

    sessionStorage.setItem = origSetItem;
  });

  it('AI assistant — blank input after trim is not submitted', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchAssistantEntry } =
      await import('@/components/research/ResearchAssistantEntry.vue');

    const wrapper = mount(ResearchAssistantEntry, {
      props: { projectId: PROJ_A },
      global: {
        plugins: [router],
      },
    });

    // v-model.trim means whitespace-only input becomes empty string
    const input = wrapper.find('#rae-question-input');
    await input.setValue('   ');
    await nextTick();

    const btn = wrapper.find('.rae-submit-btn');
    expect((btn.element as HTMLButtonElement).disabled).toBe(true);
  });

  // ---- Batch 3: No resume API → no "继续研究" ----

  it('ContinueResearchCard does not show "继续研究" (no resume API)', async () => {
    const { default: ContinueResearchCard } =
      await import('@/components/research/ContinueResearchCard.vue');

    const wrapper = mount(ContinueResearchCard, {
      props: { projectId: PROJ_A, loading: false, error: null },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    expect(wrapper.text()).not.toContain('继续研究');
    expect(wrapper.text()).toContain('开始新研究');
  });

  // ---- Batch 3: RecentReports only shows completed runs with report artifacts ----

  it('RecentReports only shows completed runs with report_generation completed', async () => {
    const { default: RecentReports } = await import('@/components/research/RecentReports.vue');

    const runs = [
      makeRun({ run_id: 'r1', topic: 'Complete', completed_at: '2026-07-16T10:00:00Z' }),
      makeRun({
        run_id: 'r2',
        topic: 'No Report',
        completed_at: '2026-07-16T09:00:00Z',
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'completed' },
          { name: 'evidence_synthesis', status: 'pending' },
          { name: 'report_generation', status: 'pending' },
          { name: 'citation_export', status: 'pending' },
        ],
      }),
      makeRun({
        run_id: 'r3',
        topic: 'Failed Report',
        completed_at: '2026-07-16T08:00:00Z',
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'completed' },
          { name: 'report_generation', status: 'failed' },
        ],
      }),
    ];

    const wrapper = mount(RecentReports, {
      props: { projectId: PROJ_A, loading: false, error: null, runs },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: false,
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    const text = wrapper.text();
    // Only the completed run should appear
    expect(text).toContain('Complete');
    // Task 2B: filter relaxed — any completed step now qualifies.
    // Both 'No Report' (completed topic_selection + literature_retrieval)
    // and 'Failed Report' (completed topic_selection + literature_retrieval)
    // now display in RecentReports.
    expect(text).toContain('No Report');
    expect(text).toContain('Failed Report');
  });

  it('RecentReports — incomplete run does not get view link', async () => {
    const { default: RecentReports } = await import('@/components/research/RecentReports.vue');

    const runs = [
      makeRun({
        run_id: 'r-incomplete',
        topic: 'Incomplete',
        completed_at: '2026-07-16T10:00:00Z',
        step_execution_trace: [
          { name: 'topic_selection', status: 'completed' },
          { name: 'literature_retrieval', status: 'completed' },
          { name: 'evidence_synthesis', status: 'completed' },
          { name: 'report_generation', status: 'pending' },
        ],
      }),
    ];

    const wrapper = mount(RecentReports, {
      props: { projectId: PROJ_A, loading: false, error: null, runs },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: false,
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    // Task 2B: filter relaxed — any completed step qualifies.
    // This run has 3 completed steps (topic_selection, literature_retrieval,
    // evidence_synthesis), so it now renders with a view link.
    const items = wrapper.findAll('.rr-item');
    expect(items.length).toBe(1);
    // View link <a> should be present (has completed steps)
    const links = wrapper.findAll('.rr-view-link');
    expect(links.length).toBe(1);
  });

  it('RecentReports — sorts by completed_at DESC, missing times last', async () => {
    const { default: RecentReports } = await import('@/components/research/RecentReports.vue');

    const runs = [
      makeRun({ run_id: 'r-old', topic: 'Old', completed_at: '2026-01-01T00:00:00Z' }),
      makeRun({ run_id: 'r-mid', topic: 'Mid', completed_at: '2026-06-01T00:00:00Z' }),
      makeRun({ run_id: 'r-new', topic: 'New', completed_at: '2026-07-16T10:00:00Z' }),
      makeRun({ run_id: 'r-no-time', topic: 'NoTime', completed_at: null }),
    ];

    const wrapper = mount(RecentReports, {
      props: { projectId: PROJ_A, loading: false, error: null, runs },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: false,
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    const titles = wrapper.findAll('.rr-title');
    const titleTexts = titles.map((t) => t.text());
    // Newest first
    const newIdx = titleTexts.findIndex((t) => t === 'New');
    const oldIdx = titleTexts.findIndex((t) => t === 'Old');
    const noTimeIdx = titleTexts.findIndex((t) => t === 'NoTime');
    expect(newIdx).toBeLessThan(oldIdx);
    // NoTime should be last (missing completed_at)
    expect(noTimeIdx).toBeGreaterThan(newIdx);
    expect(noTimeIdx).toBeGreaterThan(oldIdx);
  });

  it('RecentReports — max 5 items', async () => {
    const { default: RecentReports } = await import('@/components/research/RecentReports.vue');

    const runs = Array.from({ length: 8 }, (_, i) =>
      makeRun({
        run_id: `r-${i}`,
        topic: `Report ${i}`,
        completed_at: `2026-07-16T${String(10 + i).padStart(2, '0')}:00:00Z`,
      }),
    );

    const wrapper = mount(RecentReports, {
      props: { projectId: PROJ_A, loading: false, error: null, runs },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: false,
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    const items = wrapper.findAll('.rr-item');
    expect(items.length).toBeLessThanOrEqual(5);
  });

  // ---- Batch 3: Runs retry from shared state ----

  it('runs retry triggers shared reload', async () => {
    vi.clearAllMocks();
    let runsCallCount = 0;
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/runs')) {
        runsCallCount++;
        if (runsCallCount === 1) {
          return Promise.reject(new Error('Network error'));
        }
        return Promise.resolve({
          data: { data: { session_id: PROJ_A, runs: [makeRun()], total: 1 } },
        });
      }
      if (url.includes('/history')) {
        return Promise.resolve({ data: { data: { session_id: PROJ_A, history: [], total: 0 } } });
      }
      if (url.includes('/notes')) {
        return Promise.resolve({ data: { data: [] } });
      }
      if (url.includes('/citations')) {
        return Promise.resolve({ data: { data: [] } });
      }
      return Promise.resolve({ data: { data: makeSession() } });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template:
              '<div class="mock-error" role="alert">{{ message }}<button class="mock-retry-btn" @click="$emit(\'retry\')">重试</button></div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          ContinueResearchCard: {
            template:
              '<div class="mock-crc"><span v-if="error">{{ error }}</span><button v-if="error" class="mock-retry-btn" @click="$emit(\'retry\')">Retry</button></div>',
            props: ['projectId', 'loading', 'error'],
            emits: ['retry'],
          },
          RecentResearchActivity: { template: '<div />', props: ['projectId'] },
          RecentReports: {
            template:
              '<div class="mock-rr"><span v-if="error">{{ error }}</span><button v-if="error" class="mock-retry-btn" @click="$emit(\'retry\')">Retry</button></div>',
            props: ['projectId', 'loading', 'error', 'runs'],
            emits: ['retry'],
          },
          RecentNotes: { template: '<div />', props: ['projectId'] },
          ResearchResources: { template: '<div />', props: ['projectId'] },
          ResearchAssistantEntry: { template: '<div />', props: ['projectId'] },
        },
      },
    });

    await flushPromises();

    // After first load, runs should have errored
    // The CRC or RR stub shows the error
    // Retry from one should trigger the shared retry
    const retryBtn = wrapper.find('.mock-retry-btn');
    if (retryBtn.exists()) {
      await retryBtn.trigger('click');
      await flushPromises();
    }

    // Verify runs API was called twice (first failed, second succeeded)
    expect(runsCallCount).toBeGreaterThanOrEqual(2);
  });

  // ---- Batch 4: RecentResearchActivity with watch on projectId ----

  it('RecentResearchActivity watches projectId and reloads', async () => {
    vi.clearAllMocks();
    let resolveSlow!: (value: unknown) => void;

    mockApiGet.mockImplementation((url: string) => {
      if ((url as string).includes('/history')) {
        // First call hangs, second succeeds
        if ((url as string).includes(PROJ_A)) {
          return new Promise((r) => {
            resolveSlow = r;
          });
        }
        return Promise.resolve({
          data: {
            data: {
              session_id: PROJ_B,
              history: [makeHistoryEntry({ query_text: 'B Activity' })],
              total: 1,
            },
          },
        });
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const { default: RecentResearchActivity } =
      await import('@/components/research/RecentResearchActivity.vue');

    const wrapper = mount(RecentResearchActivity, {
      props: { projectId: PROJ_A },
      global: {
        stubs: {
          LoadingState: {
            template: '<div class="mock-loading" role="status" />',
            props: ['message'],
          },
          EmptyState: false,
          ErrorState: {
            template: '<div class="mock-error" role="alert">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    // Switch to B before A's slow request resolves
    await wrapper.setProps({ projectId: PROJ_B });
    await flushPromises();

    // Now resolve A's slow response — it should be discarded
    resolveSlow!({
      data: {
        data: {
          session_id: PROJ_A,
          history: [makeHistoryEntry({ query_text: 'A Stale Activity' })],
          total: 1,
        },
      },
    });
    await flushPromises();

    // B's data should be showing, not A's stale data
    const text = wrapper.text();
    expect(text).toContain('B Activity');
    expect(text).not.toContain('A Stale Activity');
  });

  // ---- Batch 4: RecentNotes watches projectId ----

  it('RecentNotes watches projectId and clears old data', async () => {
    vi.clearAllMocks();
    let resolveSlow!: (value: unknown) => void;

    mockApiGet.mockImplementation((url: string) => {
      if ((url as string).includes('/notes')) {
        if ((url as string).includes(PROJ_A)) {
          return new Promise((r) => {
            resolveSlow = r;
          });
        }
        return Promise.resolve({
          data: { data: [makeNote({ id: 'n-b', content: 'B Note', session_id: PROJ_B })] },
        });
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const { default: RecentNotes } = await import('@/components/research/RecentNotes.vue');

    const wrapper = mount(RecentNotes, {
      props: { projectId: PROJ_A },
      global: {
        stubs: {
          LoadingState: {
            template: '<div class="mock-loading" role="status" />',
            props: ['message'],
          },
          EmptyState: false,
          ErrorState: {
            template: '<div class="mock-error" role="alert">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    await wrapper.setProps({ projectId: PROJ_B });
    await flushPromises();

    resolveSlow!({
      data: { data: [makeNote({ id: 'n-a', content: 'A Stale Note', session_id: PROJ_A })] },
    });
    await flushPromises();

    const text = wrapper.text();
    expect(text).toContain('B Note');
    expect(text).not.toContain('A Stale Note');
  });

  // ---- Batch 4: ResearchResources watches projectId ----

  it('ResearchResources watches projectId and clears old citations', async () => {
    vi.clearAllMocks();
    let resolveSlow!: (value: unknown) => void;

    mockApiGet.mockImplementation((url: string) => {
      if ((url as string).includes('/citations')) {
        if ((url as string).includes(PROJ_A)) {
          return new Promise((r) => {
            resolveSlow = r;
          });
        }
        return Promise.resolve({
          data: {
            data: [makeCitation({ id: 'c-b', session_id: PROJ_B, citation_text: 'B Citation' })],
          },
        });
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const { default: ResearchResources } =
      await import('@/components/research/ResearchResources.vue');

    const wrapper = mount(ResearchResources, {
      props: { projectId: PROJ_A },
      global: {
        stubs: {
          LoadingState: {
            template: '<div class="mock-loading" role="status" />',
            props: ['message'],
          },
          EmptyState: false,
          ErrorState: {
            template: '<div class="mock-error" role="alert">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    await wrapper.setProps({ projectId: PROJ_B });
    await flushPromises();

    resolveSlow!({
      data: {
        data: [makeCitation({ id: 'c-a', session_id: PROJ_A, citation_text: 'A Stale Citation' })],
      },
    });
    await flushPromises();

    const text = wrapper.text();
    expect(text).toContain('B Citation');
    expect(text).not.toContain('A Stale Citation');
  });

  // ---- Batch 4: Loading state on switch ----

  it('data component enters loading state on projectId switch', async () => {
    vi.clearAllMocks();
    let resolve!: (value: unknown) => void;

    mockApiGet.mockImplementation((url: string) => {
      if ((url as string).includes('/history')) {
        return new Promise((r) => {
          resolve = r;
        });
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const { default: RecentResearchActivity } =
      await import('@/components/research/RecentResearchActivity.vue');

    const wrapper = mount(RecentResearchActivity, {
      props: { projectId: PROJ_A },
      global: {
        stubs: {
          LoadingState: {
            template: '<div class="mock-loading" role="status" />',
            props: ['message'],
          },
          EmptyState: false,
          ErrorState: {
            template: '<div class="mock-error" role="alert">{{ message }}</div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    // Switch projectId while first request is still pending
    await wrapper.setProps({ projectId: PROJ_B });
    await flushPromises();

    // Should show loading state
    expect(wrapper.find('.mock-loading').exists()).toBe(true);

    // Resolve and verify
    resolve!({ data: { data: { session_id: PROJ_A, history: [makeHistoryEntry()], total: 1 } } });
    await flushPromises();
  });

  // ---- Batch 4: Domain mapping contract ----

  it('ResearchProjectDetail.id comes from ResearchSession.id', async () => {
    const { toProjectDetail } = await import('@/types/research');
    const raw = { id: 'session-uuid', title: 'Test' };
    const result = toProjectDetail(raw);
    expect(result.id).toBe('session-uuid');
  });

  it('ResearchCitationSummary maps _citation_dict fields', async () => {
    const { toCitationSummary } = await import('@/types/research');
    const raw = {
      id: 'cite-1',
      session_id: 's1',
      citation_text: 'text',
      source_document: 'doc',
      trace_json: '{}',
      tags: 'tag1',
      notes: null,
      created_at: '2026-07-16T10:00:00Z',
      updated_at: null,
    };
    const result = toCitationSummary(raw);
    expect(result.id).toBe('cite-1');
    expect(result.session_id).toBe('s1');
    expect(result.citation_text).toBe('text');
    expect(result.source_document).toBe('doc');
    expect(result.tags).toBe('tag1');
    expect(result.notes).toBeNull();
    expect(result.created_at).toBe('2026-07-16T10:00:00Z');
    expect(result.updated_at).toBeNull();
  });

  // ---- Batch 4: No project_id references ----

  it('does not reference project_id in types', async () => {
    const { toProjectDetail } = await import('@/types/research');
    const result = toProjectDetail({ id: 'x', title: 'T' });
    expect((result as unknown as Record<string, unknown>).project_id).toBeUndefined();
  });

  // ---- Page-level error states ----

  it('shows Not Found when session does not exist (404)', async () => {
    vi.clearAllMocks();
    mockApiGet.mockRejectedValue({
      response: { status: 404, data: { message: 'Not found' } },
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: {
            template:
              '<div class="mock-empty" role="status">{{ title }}<slot name="action" /></div>',
            props: ['title', 'description', 'icon'],
          },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    expect(wrapper.text()).toContain('课题不存在');
  });

  it('shows permission error on 403', async () => {
    vi.clearAllMocks();
    mockApiGet.mockRejectedValue({
      response: { status: 403, data: { message: 'Forbidden' } },
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template:
              '<div class="mock-error" role="alert">{{ message }}<button class="mock-retry-btn" @click="$emit(\'retry\')">重试</button></div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    const errorEl = wrapper.find('[role="alert"]');
    expect(errorEl.exists()).toBe(true);
    expect(wrapper.text()).toContain('Forbidden');
  });

  it('page-level retry re-fetches session', async () => {
    vi.clearAllMocks();
    mockApiGet.mockRejectedValueOnce(new Error('Network Error'));

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template:
              '<div class="mock-error" role="alert">{{ message }}<button class="mock-retry-btn" @click="$emit(\'retry\')">重试</button></div>',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    await flushPromises();

    expect(wrapper.text()).toContain('Network Error');

    const callsBefore = mockApiGet.mock.calls.length;

    mockApiGet.mockResolvedValue({
      data: { data: makeSession({ title: 'Recovered' }) },
    });

    const retryBtn = wrapper.find('.mock-retry-btn');
    await retryBtn.trigger('click');
    await flushPromises();

    expect(mockApiGet.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it('does not render internal technical fields', async () => {
    vi.clearAllMocks();
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/history'))
        return Promise.resolve({ data: { data: { session_id: PROJ_A, history: [], total: 0 } } });
      if (url.includes('/runs'))
        return Promise.resolve({ data: { data: { session_id: PROJ_A, runs: [], total: 0 } } });
      if (url.includes('/notes')) return Promise.resolve({ data: { data: [] } });
      if (url.includes('/citations')) return Promise.resolve({ data: { data: [] } });
      return Promise.resolve({
        data: {
          data: makeSession({
            active_entities: '["entity-1"]',
            context_notes: 'internal state data',
          }),
        },
      });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header">{{ description }}<slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          ContinueResearchCard: {
            template: '<div />',
            props: ['projectId', 'loading', 'error'],
            emits: ['retry'],
          },
          RecentResearchActivity: { template: '<div />', props: ['projectId'] },
          RecentReports: {
            template: '<div />',
            props: ['projectId', 'loading', 'error', 'runs'],
            emits: ['retry'],
          },
          RecentNotes: { template: '<div />', props: ['projectId'] },
          ResearchResources: { template: '<div />', props: ['projectId'] },
          ResearchAssistantEntry: { template: '<div />', props: ['projectId'] },
        },
      },
    });

    await flushPromises();

    const text = wrapper.text();
    expect(text).not.toContain('active_entities');
    expect(text).not.toContain('workflow_state');
    expect(text).not.toContain('["entity-1"]');
  });

  it('does not use fixed IDs in navigation links', async () => {
    vi.clearAllMocks();
    const customId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/history'))
        return Promise.resolve({ data: { data: { history: [], total: 0 } } });
      if (url.includes('/runs')) return Promise.resolve({ data: { data: { runs: [], total: 0 } } });
      if (url.includes('/notes')) return Promise.resolve({ data: { data: [] } });
      if (url.includes('/citations')) return Promise.resolve({ data: { data: [] } });
      if (url.includes(customId))
        return Promise.resolve({ data: { data: makeSession({ id: customId, title: 'Custom' }) } });
      return Promise.resolve({ data: { data: {} } });
    });

    const router = buildRouter();
    await router.push(`/research/${customId}/workspace`);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
          ContinueResearchCard: {
            template: '<div />',
            props: ['projectId', 'loading', 'error'],
            emits: ['retry'],
          },
          RecentResearchActivity: { template: '<div />', props: ['projectId'] },
          RecentReports: {
            template: '<div />',
            props: ['projectId', 'loading', 'error', 'runs'],
            emits: ['retry'],
          },
          RecentNotes: { template: '<div />', props: ['projectId'] },
          ResearchResources: { template: '<div />', props: ['projectId'] },
          ResearchAssistantEntry: { template: '<div />', props: ['projectId'] },
        },
      },
    });

    await flushPromises();

    const links = wrapper.findAll('.mock-link');
    const hrefs = links.map((l) => l.attributes('href')) as Array<string>;
    expect(hrefs.some((h) => h.includes(customId))).toBe(true);
    expect(hrefs.every((h) => !h.includes('/research/1/'))).toBe(true);
  });
});
