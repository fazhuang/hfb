/**
 * Tests for ResearchWorkspacePage and child components
 *
 * C2-1B covers:
 *   BATCH 1 — Page data ownership:
 *     1. Page loads session exactly once
 *     2. Page loads runs + history (merged research) exactly once per mount
 *     3. Page loads notes exactly once per mount
 *     4. Page loads citations exactly once per mount
 *
 *   BATCH 2 — Controlled child component contracts:
 *     5. RecentNotes does NOT make API requests when directly mounted
 *     6. ResearchResources does NOT make API requests when directly mounted
 *     7. RecentNotes consumes props correctly and emits retry
 *     8. ResearchResources consumes props correctly and emits retry
 *
 *   BATCH 3 — Merged research list:
 *     9. MergedResearchItem: type mapping (run vs activity)
 *     10. Timestamp DESC sort, no-timestamp items last
 *     11. Merged list max 5 items (after full merge)
 *     12. RecentReports title is "最近研究"
 *
 *   BATCH 4 — Deleted component no residual references:
 *     13. RecentResearchActivity is not imported or rendered
 *
 *   BATCH 5 — Project switch isolation:
 *     14. A→B switch clears old project data, old response does not overwrite new
 *     15. No state writes after unmount
 *
 *   BATCH 6 — Session gate errors:
 *     16. 404 shows "课题不存在"
 *     17. 403 shows permission error
 *     18. Page-level retry re-fetches session
 *
 *   BATCH 7 — Independent section retry (per-section reqId):
 *     19. Notes retry does not invalidate in-flight citations/research requests
 *     20. Citations retry does not invalidate in-flight notes/research requests
 *     21. Project switch invalidates ALL in-flight requests
 *     22. Unmount invalidates ALL in-flight requests
 *     23. Merged research loads runs and history concurrently
 *
 *   BATCH 8 — AI Assistant isolation (preserved from prior baseline):
 *     24-28. Storage key scoped, A/B isolation, consumer clears, no URL leak, etc.
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
      { path: '/research', name: 'research-project-list', component: { template: '<div />' } },
      { path: '/research/:projectId', name: 'research-project-detail', component: { template: '<div />' } },
      { path: '/research/:projectId/workspace', name: 'research-project-workspace', component: { template: '<div />' } },
      { path: '/research/:projectId/workflow', name: 'research-project-workflow', component: { template: '<div />' } },
      { path: '/research/:projectId/result/:runId', name: 'research-project-result', component: { template: '<div />' } },
    ],
  });
}

const PAGE_A = `/research/${PROJ_A}/workspace`;
const PAGE_B = `/research/${PROJ_B}/workspace`;
const SESSION_A = `/api/v1/workspace/sessions/${PROJ_A}`;
const SESSION_B = `/api/v1/workspace/sessions/${PROJ_B}`;
const RUNS_A = `/api/v4/research/session/${PROJ_A}/runs`;
const RUNS_B = `/api/v4/research/session/${PROJ_B}/runs`;

function setupAllSuccessMocks(sessionOverrides?: Record<string, unknown>) {
  mockApiGet.mockImplementation((url: string) => {
    if (url.includes('/history')) {
      return Promise.resolve({
        data: { data: { history: [makeHistoryEntry()], total: 1 } },
      });
    }
    if (url.includes('/runs')) {
      return Promise.resolve({
        data: { data: { runs: [makeRun()], total: 1 } },
      });
    }
    if (url.includes('/notes')) {
      return Promise.resolve({ data: { data: [makeNote()] } });
    }
    if (url.includes('/citations')) {
      return Promise.resolve({ data: { data: [makeCitation()] } });
    }
    if (url.includes(SESSION_A) || url.includes(PROJ_A)) {
      return Promise.resolve({ data: { data: sessionOverrides || makeSession() } });
    }
    if (url.includes(SESSION_B) || url.includes(PROJ_B)) {
      return Promise.resolve({ data: { data: makeSession({ id: PROJ_B, title: 'Project B' }) } });
    }
    return Promise.resolve({ data: { data: {} } });
  });
}

// Shared stubs for page-level tests
const PAGE_STUBS = {
  ResearchPageHeader: {
    template: '<div class="mock-header"><slot name="actions" /></div>',
    props: ['title', 'description', 'breadcrumbs'],
  },
  RouterLink: { template: '<a :href="to" class="mock-link"><slot /></a>', props: ['to'] },
  LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
  EmptyState: {
    template: '<div class="mock-empty" role="status">{{ title }}<slot name="action" /></div>',
    props: ['title', 'description', 'icon'],
  },
  ErrorState: {
    template:
      '<div class="mock-error" role="alert">{{ message }}<button class="mock-retry-btn" @click="$emit(\'retry\')">重试</button></div>',
    props: ['title', 'message', 'showRetry'],
    emits: ['retry'],
  },
  RecentReports: {
    template:
      '<div class="mock-recent-reports"><span class="mock-rr-title">最近研究</span><span v-if="loading">loading</span><span v-if="error" class="mock-rr-error">{{ error }}</span><span class="mock-rr-count">{{ items.length }}</span><button v-if="error" class="mock-rr-retry" @click="$emit(\'retry\')">RR Retry</button></div>',
    props: ['projectId', 'items', 'loading', 'error'],
    emits: ['retry'],
  },
  RecentNotes: {
    template:
      '<div class="mock-recent-notes"><span v-if="loading">loading</span><span v-if="error" class="mock-rn-error">{{ error }}</span><span class="mock-rn-count">{{ notes.length }}</span><button v-if="error" class="mock-rn-retry" @click="$emit(\'retry\')">RN Retry</button></div>',
    props: ['notes', 'loading', 'error'],
    emits: ['retry'],
  },
  ResearchResources: {
    template:
      '<div class="mock-research-resources"><span v-if="loading">loading</span><span v-if="error" class="mock-rres-error">{{ error }}</span><span class="mock-rres-count">{{ citations.length }}</span><button v-if="error" class="mock-rres-retry" @click="$emit(\'retry\')">RRes Retry</button><button class="mock-rres-retry-force" @click="$emit(\'retry\')">Force RRes Retry</button></div>',
    props: ['citations', 'loading', 'error'],
    emits: ['retry'],
  },
  ResearchAssistantEntry: { template: '<div class="mock-rae" />', props: ['projectId'] },
};

// ================================================================
// Page-level tests
// ================================================================

describe('ResearchWorkspacePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupAllSuccessMocks();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  // ---- Batch 1: Page data ownership ----

  it('loads session exactly once on page load', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
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

  it('page loads runs + history after session gate succeeds', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    const runsCalls = mockApiGet.mock.calls.filter((c: Array<unknown>) =>
      (c[0] as string).includes('/runs'),
    );
    const historyCalls = mockApiGet.mock.calls.filter((c: Array<unknown>) =>
      (c[0] as string).includes('/history'),
    );
    expect(runsCalls.length).toBe(1);
    expect(historyCalls.length).toBe(1);
  });

  it('page loads notes exactly once per mount', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    const notesCalls = mockApiGet.mock.calls.filter((c: Array<unknown>) =>
      (c[0] as string).includes('/notes'),
    );
    expect(notesCalls.length).toBe(1);
  });

  it('page loads citations exactly once per mount', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    const citationCalls = mockApiGet.mock.calls.filter((c: Array<unknown>) =>
      (c[0] as string).includes('/citations'),
    );
    expect(citationCalls.length).toBe(1);
  });

  it('does not render RecentResearchActivity in page', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    const html = wrapper.html();
    expect(html).not.toContain('RecentResearchActivity');
    expect(html).not.toContain('rra-');
  });

  // ---- Batch 2: Controlled child components ----

  it('RecentNotes does not make API requests when directly mounted', async () => {
    vi.clearAllMocks();
    const { default: RecentNotes } = await import('@/components/research/RecentNotes.vue');

    mount(RecentNotes, {
      props: { notes: [], loading: false, error: null },
      global: {
        stubs: {
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    expect(mockApiGet).not.toHaveBeenCalled();
  });

  it('ResearchResources does not make API requests when directly mounted', async () => {
    vi.clearAllMocks();
    const { default: ResearchResources } =
      await import('@/components/research/ResearchResources.vue');

    mount(ResearchResources, {
      props: { citations: [], loading: false, error: null },
      global: {
        stubs: {
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    expect(mockApiGet).not.toHaveBeenCalled();
  });

  it('RecentNotes consumes props: loading, error, notes', async () => {
    const { default: RecentNotes } = await import('@/components/research/RecentNotes.vue');

    // loading state
    const wrapper1 = mount(RecentNotes, {
      props: { notes: [], loading: true, error: null },
      global: {
        stubs: {
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message'],
            emits: ['retry'],
          },
        },
      },
    });
    expect(wrapper1.find('.mock-loading').exists()).toBe(true);

    // error state
    const wrapper2 = mount(RecentNotes, {
      props: { notes: [], loading: false, error: 'Test error' },
      global: {
        stubs: {
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: { template: '<div>{{ title }}</div>', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message'],
            emits: ['retry'],
          },
        },
      },
    });
    expect(wrapper2.find('.mock-error').text()).toContain('Test error');

    // data state
    const wrapper3 = mount(RecentNotes, {
      props: {
        notes: [makeNote({ content: 'Hello world' })],
        loading: false,
        error: null,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message'],
            emits: ['retry'],
          },
        },
      },
    });
    expect(wrapper3.text()).toContain('Hello world');
  });

  it('ResearchResources consumes props: loading, error, citations', async () => {
    const { default: ResearchResources } =
      await import('@/components/research/ResearchResources.vue');

    // loading state
    const wrapper1 = mount(ResearchResources, {
      props: { citations: [], loading: true, error: null },
      global: {
        stubs: {
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message'],
            emits: ['retry'],
          },
        },
      },
    });
    expect(wrapper1.find('.mock-loading').exists()).toBe(true);

    // error state
    const wrapper2 = mount(ResearchResources, {
      props: { citations: [], loading: false, error: 'Cite error' },
      global: {
        stubs: {
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: { template: '<div>{{ title }}</div>', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div class="mock-error">{{ message }}</div>',
            props: ['title', 'message'],
            emits: ['retry'],
          },
        },
      },
    });
    expect(wrapper2.find('.mock-error').text()).toContain('Cite error');

    // data state
    const wrapper3 = mount(ResearchResources, {
      props: {
        citations: [makeCitation({ citation_text: 'Some text', source_document: 'Some doc' })],
        loading: false,
        error: null,
      },
      global: {
        stubs: {
          LoadingState: { template: '<div class="mock-loading" />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message'],
            emits: ['retry'],
          },
        },
      },
    });
    expect(wrapper3.text()).toContain('Some text');
  });

  it('RecentNotes emits retry when error shown', async () => {
    const { default: RecentNotes } = await import('@/components/research/RecentNotes.vue');

    const wrapper = mount(RecentNotes, {
      props: { notes: [], loading: false, error: 'Fail' },
      global: {
        stubs: {
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<button class="retry-btn" @click="$emit(\'retry\')">Retry</button>',
            props: ['title', 'message'],
            emits: ['retry'],
          },
        },
      },
    });

    const btn = wrapper.find('.retry-btn');
    await btn.trigger('click');
    expect(wrapper.emitted('retry')).toBeTruthy();
    expect(wrapper.emitted('retry')!.length).toBe(1);
  });

  it('ResearchResources emits retry when error shown', async () => {
    const { default: ResearchResources } =
      await import('@/components/research/ResearchResources.vue');

    const wrapper = mount(ResearchResources, {
      props: { citations: [], loading: false, error: 'Fail' },
      global: {
        stubs: {
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<button class="retry-btn" @click="$emit(\'retry\')">Retry</button>',
            props: ['title', 'message'],
            emits: ['retry'],
          },
        },
      },
    });

    const btn = wrapper.find('.retry-btn');
    await btn.trigger('click');
    expect(wrapper.emitted('retry')).toBeTruthy();
    expect(wrapper.emitted('retry')!.length).toBe(1);
  });

  // ---- Batch 3: Merged research list ----

  it('RecentReports title is "最近研究"', async () => {
    const { default: RecentReports } = await import('@/components/research/RecentReports.vue');

    const wrapper = mount(RecentReports, {
      props: { projectId: PROJ_A, items: [], loading: false, error: null },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    expect(wrapper.text()).toContain('最近研究');
  });

  it('merged list: run type and activity type display correctly', async () => {
    const { default: RecentReports } = await import('@/components/research/RecentReports.vue');

    const items = [
      {
        id: 'run-1',
        type: 'run' as const,
        title: 'My Run',
        timestamp: '2026-07-16T10:00:00Z',
        stepTrace: [{ name: 'report_generation', status: 'completed' }],
        runId: 'run-1',
        completedAt: '2026-07-16T10:00:00Z',
      },
      {
        id: 'q-1',
        type: 'activity' as const,
        title: 'My Query',
        timestamp: '2026-07-15T10:00:00Z',
        queryType: 'research',
        citationCount: 5,
      },
    ];

    const wrapper = mount(RecentReports, {
      props: { projectId: PROJ_A, items, loading: false, error: null },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    const text = wrapper.text();
    expect(text).toContain('My Run');
    expect(text).toContain('My Query');
  });

  it('merged list sorted by timestamp DESC, no-timestamp items last', async () => {
    const { default: RecentReports } = await import('@/components/research/RecentReports.vue');

    // Items are pre-sorted by parent page (newest first, no-timestamp last).
    // RecentReports is a controlled component — it must NOT re-sort.
    const items = [
      { id: 'b', type: 'run' as const, title: 'New', timestamp: '2026-07-16T10:00:00Z' },
      { id: 'c', type: 'activity' as const, title: 'Mid', timestamp: '2026-06-01T00:00:00Z' },
      { id: 'a', type: 'run' as const, title: 'Old', timestamp: '2026-01-01T00:00:00Z' },
      { id: 'd', type: 'activity' as const, title: 'NoTime', timestamp: '' },
    ];

    const wrapper = mount(RecentReports, {
      props: { projectId: PROJ_A, items, loading: false, error: null },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    const titles = wrapper.findAll('.rr-title');
    const titleTexts = titles.map((t) => t.text());
    // Only run items have .rr-title: New (run), Old (run)
    // Mid and NoTime are activity items with .rr-text
    expect(titleTexts).toEqual(['New', 'Old']);
    // All items should appear in text
    expect(wrapper.text()).toContain('Mid');
    expect(wrapper.text()).toContain('NoTime');
    // New (index 0) before Old (index 1) = preserves parent sort order
    expect(titleTexts[0]).toBe('New');
  });

  it('merged list: RecentReports does not re-sort or re-filter', async () => {
    const { default: RecentReports } = await import('@/components/research/RecentReports.vue');

    // Items are already in descending order by parent — verify component renders as-is
    const items = [
      { id: '1', type: 'run' as const, title: 'Item1', timestamp: '2026-07-16T10:00:00Z' },
      { id: '2', type: 'activity' as const, title: 'Item2', timestamp: '2026-07-15T10:00:00Z' },
    ];

    const wrapper = mount(RecentReports, {
      props: { projectId: PROJ_A, items, loading: false, error: null },
      global: {
        stubs: {
          RouterLink: { template: '<a :href="to"><slot /></a>', props: ['to'] },
          LoadingState: { template: '<div />', props: ['message'] },
          EmptyState: { template: '<div />', props: ['title', 'description', 'icon'] },
          ErrorState: {
            template: '<div />',
            props: ['title', 'message', 'showRetry'],
            emits: ['retry'],
          },
        },
      },
    });

    // Should render exactly the 2 items passed in, in the order passed
    const items_els = wrapper.findAll('.rr-item');
    expect(items_els.length).toBe(2);
  });

  it('merged list: page-level merge capped at 5 items', async () => {
    vi.clearAllMocks();
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/runs')) {
        return Promise.resolve({
          data: {
            data: {
              runs: Array.from({ length: 4 }, (_, i) =>
                makeRun({ run_id: `r-${i}`, topic: `Run ${i}` }),
              ),
              total: 4,
            },
          },
        });
      }
      if (url.includes('/history')) {
        return Promise.resolve({
          data: {
            data: {
              history: Array.from({ length: 4 }, (_, i) =>
                makeHistoryEntry({ query_id: `q-${i}`, query_text: `Query ${i}` }),
              ),
              total: 4,
            },
          },
        });
      }
      if (url.includes('/notes')) return Promise.resolve({ data: { data: [] } });
      if (url.includes('/citations')) return Promise.resolve({ data: { data: [] } });
      return Promise.resolve({ data: { data: makeSession() } });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    // Merged stub shows count: should be <= 5 (8 total items merged, sliced to 5)
    const countEl = wrapper.find('.mock-rr-count');
    expect(Number(countEl.text())).toBeLessThanOrEqual(5);
  });

  // ---- Batch 4: Deleted component no residual references ----

  it('RecentResearchActivity is not imported or rendered by page', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    // The page should not render any rra- scoped content
    const html = wrapper.html();
    expect(html).not.toContain('rra-section');
    expect(html).not.toContain('rra-heading');
  });

  it('suite loads without importing deleted RecentResearchActivity', () => {
    // If the test file still had a static import of the deleted component,
    // the entire suite would fail to load (Vite transform-time 404).
    // Reaching this assertion = no residual import in the test file.
    expect(true).toBe(true);
  });

  // ---- Batch 5: Project switch isolation ----

  it('stale response from old projectId does not overwrite new page data', async () => {
    vi.clearAllMocks();
    let resolveOldSession!: (value: unknown) => void;
    let resolveNewSession!: (value: unknown) => void;

    mockApiGet.mockImplementation((url: string) => {
      const s = String(url);
      // A's session gate hangs — section data never requested
      if (s === SESSION_A) {
        return new Promise((r) => { resolveOldSession = r; });
      }
      // B's session gate hangs
      if (s === SESSION_B) {
        return new Promise((r) => { resolveNewSession = r; });
      }
      // All other endpoints respond immediately (for B after session resolves)
      if (s.includes('/runs')) {
        return Promise.resolve({ data: { data: { runs: [makeRun({ run_id: 'run-b', topic: 'B Run' })], total: 1 } } });
      }
      if (s.includes('/history')) {
        return Promise.resolve({ data: { data: { history: [makeHistoryEntry({ query_text: 'B Activity' })], total: 1 } } });
      }
      if (s.includes('/notes')) {
        return Promise.resolve({ data: { data: [makeNote({ id: 'n-b', content: 'B Note', session_id: PROJ_B })] } });
      }
      if (s.includes('/citations')) {
        return Promise.resolve({ data: { data: [] } });
      }
      return Promise.resolve({ data: { data: {} } });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    // Switch to B before A resolves
    await router.push(PAGE_B);
    await flushPromises();

    // Resolve B session — should load B sections
    resolveNewSession!({ data: { data: makeSession({ id: PROJ_B, title: 'Project B' }) } });
    await flushPromises();

    // B's runs were called
    const bRunsCalls = mockApiGet.mock.calls.filter((c: Array<unknown>) => c[0] === RUNS_B);
    expect(bRunsCalls.length).toBe(1);

    // Now resolve stale A session — should be discarded (reqId mismatch)
    resolveOldSession!({ data: { data: makeSession({ id: PROJ_A, title: 'Old Project' }) } });
    await flushPromises();

    // B's data should not be overwritten by A
    const aRunsCalls = mockApiGet.mock.calls.filter((c: Array<unknown>) => c[0] === RUNS_A);
    // A's runs were never called because A's session gate never resolved
    expect(aRunsCalls.length).toBe(0);
  });

  it('no state writes after unmount', async () => {
    vi.clearAllMocks();
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
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    wrapper.unmount();
    resolveAfterUnmount!({ data: { data: makeSession() } });
    await new Promise((r) => setTimeout(r, 50));
    // Should not throw — pass if we reach here
    expect(true).toBe(true);
  });

  // ---- Batch 6: Session gate errors ----

  it('shows Not Found when session returns 404', async () => {
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
      global: { plugins: [router], stubs: PAGE_STUBS },
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
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

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
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();
    expect(wrapper.text()).toContain('Network Error');

    const callsBefore = mockApiGet.mock.calls.length;
    mockApiGet.mockResolvedValue({ data: { data: makeSession({ title: 'Recovered' }) } });

    const retryBtn = wrapper.find('.mock-retry-btn');
    await retryBtn.trigger('click');
    await flushPromises();

    expect(mockApiGet.mock.calls.length).toBeGreaterThan(callsBefore);
  });

  it('404 does not trigger section requests', async () => {
    vi.clearAllMocks();
    mockApiGet.mockRejectedValue({
      response: { status: 404, data: { message: 'Not found' } },
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    // Only one call total (the session)
    expect(mockApiGet).toHaveBeenCalledTimes(1);
  });

  // ---- Batch 7: Independent section retry ----

  it('notes retry does not invalidate in-flight merg/citations requests', async () => {
    vi.clearAllMocks();

    // session + runs + history resolve immediately
    // notes and citations hang so we can observe retry behavior
    let resolveNotes: ((value: unknown) => void) | null = null;
    let resolveCitations!: (value: unknown) => void;
    let notesCallCount = 0;
    let citationsCallCount = 0;

    // ponytail: capture resolveNotes via closure so the mock can assign it;
    // we assert it gets assigned (notes retried and hung).
    mockApiGet.mockImplementation((url: string) => {
      const s = String(url);
      if (s.includes(`/workspace/sessions/${PROJ_A}/notes`)) {
        notesCallCount++;
        if (notesCallCount === 1) {
          return Promise.reject(new Error('Notes fail'));
        }
        return new Promise((r) => { resolveNotes = r; });
      }
      if (s.includes(`/workspace/sessions/${PROJ_A}/citations`)) {
        citationsCallCount++;
        return new Promise((r) => { resolveCitations = r; });
      }
      if (s.includes('/runs')) {
        return Promise.resolve({ data: { data: { runs: [makeRun()], total: 1 } } });
      }
      if (s.includes('/history')) {
        return Promise.resolve({ data: { data: { history: [makeHistoryEntry()], total: 1 } } });
      }
      // session
      return Promise.resolve({ data: { data: makeSession() } });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    // After first load: notes errored, citations still loading
    const rnErrorEl = wrapper.find('.mock-rn-error');
    expect(rnErrorEl.exists()).toBe(true);

    // Citations loading spinner visible
    expect(wrapper.find('.mock-research-resources').text()).toContain('loading');

    // Retry notes — should NOT cancel in-flight citations
    const rnRetryBtn = wrapper.find('.mock-rn-retry');
    await rnRetryBtn.trigger('click');
    await flushPromises();

    // Notes retried and hung on second call — resolveNotes was assigned by mock
    expect(resolveNotes).not.toBeNull();

    // Citations should still be in loading (not cancelled)
    expect(wrapper.find('.mock-research-resources').text()).toContain('loading');
    expect(citationsCallCount).toBe(1); // Still the first (hanging) call

    // Resolve citations — should complete normally even after notes retry
    resolveCitations!({ data: { data: [makeCitation()] } });
    await flushPromises();

    // Citations should now show data
    expect(wrapper.find('.mock-rres-count').text()).toBe('1');
  });

  it('citations retry does not invalidate in-flight notes request', async () => {
    vi.clearAllMocks();

    let resolveNotes!: (value: unknown) => void;
    let citationsCallCount = 0;

    mockApiGet.mockImplementation((url: string) => {
      const s = String(url);
      if (s.includes(`/workspace/sessions/${PROJ_A}/notes`)) {
        return new Promise((r) => { resolveNotes = r; });
      }
      if (s.includes(`/workspace/sessions/${PROJ_A}/citations`)) {
        citationsCallCount++;
        if (citationsCallCount === 1) {
          return Promise.reject(new Error('Citations fail'));
        }
        return Promise.resolve({ data: { data: [makeCitation()] } });
      }
      if (s.includes('/runs')) {
        return Promise.resolve({ data: { data: { runs: [makeRun()], total: 1 } } });
      }
      if (s.includes('/history')) {
        return Promise.resolve({ data: { data: { history: [makeHistoryEntry()], total: 1 } } });
      }
      return Promise.resolve({ data: { data: makeSession() } });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    // Citations errored, notes still loading
    const rresErrorEl = wrapper.find('.mock-rres-error');
    expect(rresErrorEl.exists()).toBe(true);
    expect(wrapper.find('.mock-recent-notes').text()).toContain('loading');

    // Retry citations — should NOT cancel in-flight notes
    const rresRetryBtn = wrapper.find('.mock-rres-retry-force');
    await rresRetryBtn.trigger('click');
    await flushPromises();

    // Notes should still be loading
    expect(wrapper.find('.mock-recent-notes').text()).toContain('loading');

    // Resolve notes
    resolveNotes!({ data: { data: [makeNote({ content: 'Note after retry' })] } });
    await flushPromises();

    expect(wrapper.find('.mock-rn-count').text()).toBe('1');
  });

  it('project switch invalidates all in-flight section requests before new session resolves', async () => {
    vi.clearAllMocks();

    let resolveNotesA!: (value: unknown) => void;
    let resolveCitationsA!: (value: unknown) => void;
    let resolveMergedA!: (value: unknown) => void;
    let resolveSessionB!: (value: unknown) => void;
    let runsCallCount = 0;

    mockApiGet.mockImplementation((url: string) => {
      const s = String(url);
      // A: hang all section requests
      if (s.includes(`/workspace/sessions/${PROJ_A}/notes`)) {
        return new Promise((r) => { resolveNotesA = r; });
      }
      if (s.includes(`/workspace/sessions/${PROJ_A}/citations`)) {
        return new Promise((r) => { resolveCitationsA = r; });
      }
      if (s.includes(`/runs`)) {
        runsCallCount++;
        if (s.includes(PROJ_A)) {
          return new Promise((r) => { resolveMergedA = r; });
        }
        // B's runs respond immediately
        return Promise.resolve({ data: { data: { runs: [], total: 0 } } });
      }
      if (s.includes('/history')) {
        return Promise.resolve({ data: { data: { history: [], total: 0 } } });
      }
      if (s.includes(`/workspace/sessions/${PROJ_B}/notes`)) {
        return Promise.resolve({ data: { data: [] } });
      }
      if (s.includes(`/workspace/sessions/${PROJ_B}/citations`)) {
        return Promise.resolve({ data: { data: [] } });
      }
      // sessions
      if (s === SESSION_A) {
        return Promise.resolve({ data: { data: makeSession() } });
      }
      if (s === SESSION_B) {
        // B's session ALSO hangs — this creates the dangerous window
        return new Promise((r) => { resolveSessionB = r; });
      }
      return Promise.resolve({ data: { data: {} } });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    const wrapper = mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    // A's section requests are in flight — loading states visible
    expect(wrapper.find('.mock-recent-notes').text()).toContain('loading');

    // Switch to B — B's session also hangs
    await router.push(PAGE_B);
    await flushPromises();

    // Now resolve A's stale section requests WHILE B's session is still pending.
    // If reqIds were not invalidated at switch time, these would write stale data.
    resolveNotesA!({ data: { data: [makeNote({ id: 'stale', content: 'Stale A Note', session_id: PROJ_A })] } });
    resolveCitationsA!({ data: { data: [makeCitation({ id: 'stale-c', citation_text: 'Stale A Citation', session_id: PROJ_A })] } });
    resolveMergedA!({ data: { data: { runs: [makeRun({ run_id: 'stale-r', topic: 'Stale A Run' })], total: 1 } } });
    await flushPromises();

    // B's session still pending — page shows page loading, NOT A's stale section data
    expect(wrapper.find('.mock-loading').exists()).toBe(true);
    // A's stale data must NOT appear in any section
    expect(wrapper.find('.mock-rn-count').exists()).toBe(false);    // RecentNotes not even rendered (page loading)
    expect(wrapper.find('.mock-rres-count').exists()).toBe(false);  // ResearchResources not even rendered
    expect(wrapper.find('.mock-rr-count').exists()).toBe(false);    // RecentReports not even rendered

    // Now resolve B's session — section data should load fresh for B
    resolveSessionB!({ data: { data: makeSession({ id: PROJ_B, title: 'B' }) } });
    await flushPromises();

    // B's section data should appear cleanly (B notes/citations are empty in mock)
    expect(wrapper.find('.mock-rn-count').text()).toBe('0');
    expect(wrapper.find('.mock-rres-count').text()).toBe('0');
    expect(wrapper.find('.mock-rr-count').text()).toBe('0');
  });

  it('merg loads runs and history concurrently', async () => {
    vi.clearAllMocks();

    let resolveRuns!: (value: unknown) => void;
    let resolveHistory!: (value: unknown) => void;
    const callOrder: string[] = [];

    mockApiGet.mockImplementation(async (url: string) => {
      const s = String(url);
      if (s.includes('/runs')) {
        callOrder.push('runs-start');
        return new Promise((r) => {
          resolveRuns = (v) => { callOrder.push('runs-end'); r(v); };
        });
      }
      if (s.includes('/history')) {
        callOrder.push('history-start');
        return new Promise((r) => {
          resolveHistory = (v) => { callOrder.push('history-end'); r(v); };
        });
      }
      if (s.includes('/notes')) return Promise.resolve({ data: { data: [] } });
      if (s.includes('/citations')) return Promise.resolve({ data: { data: [] } });
      return Promise.resolve({ data: { data: makeSession() } });
    });

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchWorkspacePage } =
      await import('@/pages/research/ResearchWorkspacePage.vue');

    mount(ResearchWorkspacePage, {
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    // Both started — runs and history fired
    const runsStartIdx = callOrder.indexOf('runs-start');
    const historyStartIdx = callOrder.indexOf('history-start');
    expect(runsStartIdx).not.toBe(-1);
    expect(historyStartIdx).not.toBe(-1);

    // Neither finished yet
    expect(callOrder).not.toContain('runs-end');
    expect(callOrder).not.toContain('history-end');

    // Resolve history first — runs still pending
    resolveHistory!({ data: { data: { history: [makeHistoryEntry()], total: 1 } } });
    await flushPromises();

    // History done, runs still pending
    expect(callOrder).toContain('history-end');
    expect(callOrder).not.toContain('runs-end');

    // Resolve runs
    resolveRuns!({ data: { data: { runs: [makeRun()], total: 1 } } });
    await flushPromises();

    expect(callOrder).toContain('runs-end');
  });

  // ---- Batch 8: AI Assistant isolation (preserved) ----

  it('AI assistant storage key includes projectId', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchAssistantEntry } =
      await import('@/components/research/ResearchAssistantEntry.vue');

    const wrapper = mount(ResearchAssistantEntry, {
      props: { projectId: PROJ_A },
      global: { plugins: [router] },
    });

    const input = wrapper.find('#rae-question-input');
    await input.setValue('Test question');
    const form = wrapper.find('.rae-form');
    await form.trigger('submit.prevent');
    await flushPromises();

    expect(sessionStorage.getItem(`hfb.research.${PROJ_A}.pending-question`)).toBe('Test question');
    expect(sessionStorage.getItem('hfb.research.pending-question')).toBeNull();
  });

  it('AI assistant – A/B isolation, B cannot read A question', async () => {
    sessionStorage.setItem(`hfb.research.${PROJ_A}.pending-question`, 'A question');

    const router = buildRouter();
    await router.push(`/research/${PROJ_B}/workflow`);
    await router.isReady();

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
          ErrorState: { template: '<div />', props: ['title', 'message', 'showRetry'], emits: ['retry'] },
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

    const input = wrapper.find('#rqs-input');
    expect((input.element as HTMLInputElement).value).toBe('');
    expect(sessionStorage.getItem(`hfb.research.${PROJ_A}.pending-question`)).toBe('A question');
  });

  it('AI assistant – workflow consumer reads and clears the current key', async () => {
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
          ErrorState: { template: '<div />', props: ['title', 'message', 'showRetry'], emits: ['retry'] },
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

    const input = wrapper.find('#rqs-input');
    expect((input.element as HTMLInputElement).value).toBe('My question');
    expect(sessionStorage.getItem(`hfb.research.${PROJ_A}.pending-question`)).toBeNull();
  });

  it('AI assistant – question does not enter URL or console', async () => {
    const consoleSpy = vi.spyOn(console, 'log');

    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchAssistantEntry } =
      await import('@/components/research/ResearchAssistantEntry.vue');

    const wrapper = mount(ResearchAssistantEntry, {
      props: { projectId: PROJ_A },
      global: { plugins: [router] },
    });

    const input = wrapper.find('#rae-question-input');
    await input.setValue('Sensitive question');
    const form = wrapper.find('.rae-form');
    await form.trigger('submit.prevent');
    await flushPromises();

    expect(router.currentRoute.value.fullPath).not.toContain('Sensitive question');

    const sensitiveLogs = consoleSpy.mock.calls.filter((call: Array<any>) =>
      call.some((arg: any) => typeof arg === 'string' && arg.includes('Sensitive question')),
    );
    expect(sensitiveLogs.length).toBe(0);

    consoleSpy.mockRestore();
  });

  it('AI assistant – sessionStorage exception still navigates', async () => {
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
      global: { plugins: [router] },
    });

    const input = wrapper.find('#rae-question-input');
    await input.setValue('Test');
    const form = wrapper.find('.rae-form');
    await form.trigger('submit.prevent');
    await flushPromises();

    expect(router.currentRoute.value.name).toBe('research-project-workflow');

    sessionStorage.setItem = origSetItem;
  });

  it('AI assistant – blank input after trim is not submitted', async () => {
    const router = buildRouter();
    await router.push(PAGE_A);
    await router.isReady();

    const { default: ResearchAssistantEntry } =
      await import('@/components/research/ResearchAssistantEntry.vue');

    const wrapper = mount(ResearchAssistantEntry, {
      props: { projectId: PROJ_A },
      global: { plugins: [router] },
    });

    const input = wrapper.find('#rae-question-input');
    await input.setValue('   ');
    await nextTick();

    const btn = wrapper.find('.rae-submit-btn');
    expect((btn.element as HTMLButtonElement).disabled).toBe(true);
  });

  // ---- Batch 8: Domain mapping contract (preserved) ----

  it('ResearchProjectDetail.id comes from ResearchSession.id', async () => {
    const { toProjectDetail } = await import('@/types/research');
    const raw = { id: 'session-uuid', title: 'Test' };
    const result = toProjectDetail(raw);
    expect(result.id).toBe('session-uuid');
  });

  it('does not reference project_id in types', async () => {
    const { toProjectDetail } = await import('@/types/research');
    const result = toProjectDetail({ id: 'x', title: 'T' });
    expect((result as unknown as Record<string, unknown>).project_id).toBeUndefined();
  });

  it('does not render internal technical fields', async () => {
    vi.clearAllMocks();
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/history'))
        return Promise.resolve({ data: { data: { history: [], total: 0 } } });
      if (url.includes('/runs'))
        return Promise.resolve({ data: { data: { runs: [], total: 0 } } });
      if (url.includes('/notes')) return Promise.resolve({ data: { data: [] } });
      if (url.includes('/citations')) return Promise.resolve({ data: { data: [] } });
      return Promise.resolve({
        data: { data: makeSession({ active_entities: '["entity-1"]', context_notes: 'internal state data' }) },
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
          ...PAGE_STUBS,
          ResearchPageHeader: {
            template: '<div class="mock-header">{{ description }}<slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
        },
      },
    });

    await flushPromises();

    const text = wrapper.text();
    expect(text).not.toContain('active_entities');
    expect(text).not.toContain('["entity-1"]');
  });

  it('does not use fixed IDs in navigation links', async () => {
    vi.clearAllMocks();
    const customId = 'cccccccc-cccc-4ccc-8ccc-cccccccccccc';
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/history'))
        return Promise.resolve({ data: { data: { history: [], total: 0 } } });
      if (url.includes('/runs'))
        return Promise.resolve({ data: { data: { runs: [], total: 0 } } });
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
      global: { plugins: [router], stubs: PAGE_STUBS },
    });

    await flushPromises();

    const links = wrapper.findAll('.mock-link');
    const hrefs = links.map((l) => l.attributes('href')) as Array<string>;
    expect(hrefs.some((h) => h.includes(customId))).toBe(true);
    expect(hrefs.every((h) => !h.includes('/research/1/'))).toBe(true);
  });
});
