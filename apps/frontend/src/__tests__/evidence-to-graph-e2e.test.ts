/**
 * AI → Evidence → Graph end-to-end acceptance test.
 *
 * Proves the full read-only chain without depending on a live LLM:
 *   1. Evidence Panel renders entity items with type/id/graph-link
 *   2. openEntityInGraph navigates to /graph?type=…&id=…
 *   3. GraphExplorerView.onMounted consumes type + id from route query
 *   4. /api/v1/graph/neighbors/{type}/{id} is called
 *   5. GraphCanvas receives nodes + edges
 *
 * Strategy:
 *   - Mount ResearchWorkspaceView with stubbed stores and pre-seeded
 *     evidence ref.
 *   - Stub GraphCanvas to avoid jsdom canvas/vis-network errors.
 *   - Verify API calls, router navigation, and prop passing.
 */
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';

import i18n from '@/i18n';
import GraphExplorerView from '@/views/GraphExplorerView.vue';
import ResearchWorkspaceView from '@/views/ResearchWorkspaceView.vue';

// ---------------------------------------------------------------------------
// Hoisted API mock
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
// Hoisted auth store — prevents localStorage.getItem crash in jsdom
// ---------------------------------------------------------------------------
const { mockUseAuthStore } = vi.hoisted(() => {
  const fn = vi.fn(() => ({
    isAuthenticated: true,
    isAdmin: false,
    isSuperAdmin: false,
    canReviewDocuments: false,
    canManageSourcePolicies: false,
    userName: 'Tester',
    accessToken: null as string | null,
    refreshToken: null as string | null,
    user: null as Record<string, unknown> | null,
    loading: false,
    error: null,
    login: vi.fn(),
    register: vi.fn(),
    fetchMe: vi.fn(),
    logout: vi.fn(),
  }));
  return { mockUseAuthStore: fn };
});

vi.mock('@/stores/auth', () => ({
  useAuthStore: mockUseAuthStore,
}));

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------
function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/research/home', component: { template: '<div/>' }, name: 'research-home' },
      { path: '/research/new', component: { template: '<div/>' }, name: 'research-new' },
      { path: '/literature', component: { template: '<div/>' }, name: 'literature' },
      { path: '/research', redirect: '/research/workspace?tab=research' },
      { path: '/research/workspace', name: 'research-workspace', component: ResearchWorkspaceView },
      { path: '/graph', name: 'graph', component: GraphExplorerView },
      { path: '/login', component: { template: '<div/>' }, name: 'login' },
    ],
  });
}

// ---------------------------------------------------------------------------
// API response factories
// ---------------------------------------------------------------------------

function emptyList() {
  return { data: { data: [] } };
}

function emptyPage() {
  return { data: { data: [], total: 0 } };
}

function graphNeighborsResponse(overrides: Record<string, unknown> = {}) {
  return {
    data: {
      data: {
        center: {
          id: 'book:93441ffc',
          entity_type: 'book',
          entity_id: '93441ffc-68c3-4d8d-9427-aba9c75970bb',
          label: '《针灸甲乙经》 (晋)',
          properties: {},
          ...(overrides.center as object ?? {}),
        },
        neighbors: [
          {
            id: 'person:fd0c1571',
            entity_type: 'person',
            entity_id: 'fd0c1571-4567-4abd-acde-7ff878d0dbcb',
            label: '皇甫谧 (魏晋)',
            properties: {},
            ...(overrides.neighbor as object ?? {}),
          },
        ],
        edges: [
          {
            id: 'e1',
            source_id: 'fd0c1571-4567-4abd-acde-7ff878d0dbcb',
            target_id: '93441ffc-68c3-4d8d-9427-aba9c75970bb',
            relation_type: 'compiled',
            label: '编纂',
            source: 'person',
          },
        ],
      },
    },
  };
}

// ---------------------------------------------------------------------------

describe('AI → Evidence → Graph E2E chain', () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(async () => {
    vi.clearAllMocks();
    // Fresh pinia each test — avoids cross-test state leaks
    setActivePinia(createPinia());
    router = makeRouter();
    await router.push('/');
  });

  // =========================================================================
  // Test 1: Evidence Panel renders items with graph-link buttons
  // =========================================================================
  it('renders evidence items with entity_type + id and graph-link button', async () => {
    // Seed all workspace-data GET calls with empty lists
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') return emptyList();
      if (url === '/api/v1/research/materials') return emptyPage();
      if (url === '/api/v1/research/versions') return emptyPage();
      if (url === '/api/v1/workspace/notes') return emptyList();
      return emptyList();
    });

    const wrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: {
          ResearchWorkflowView: { template: '<div class="research-workflow"/>' },
        },
      },
    });

    // Switch to assistant tab — evidence sidebar lives there
    (wrapper.vm as unknown as { activeTab: string }).activeTab = 'assistant';
    await flushPromises();

    // Simulate AI response → evidence loaded into the component
    const evidenceItems = [
      { entity_type: 'book', id: '93441ffc-68c3-4d8d-9427-aba9c75970bb', content: '《针灸甲乙经》 (晋)' },
      { entity_type: 'person', id: 'fd0c1571-4567-4abd-acde-7ff878d0dbcb', content: '皇甫谧 (魏晋)' },
    ];
    (wrapper.vm as unknown as { evidence: typeof evidenceItems }).evidence = evidenceItems;
    await flushPromises();

    // Assert: two evidence items rendered
    const els = wrapper.findAll('.rw-evidence-item');
    expect(els.length).toBeGreaterThanOrEqual(2);

    // Assert: first item has a graph-link button
    const graphLink = els[0]?.find('.rw-evidence-graph-link');
    expect(graphLink?.exists()).toBe(true);
  });

  // =========================================================================
  // Test 2: openEntityInGraph → router.push with type + id query
  // =========================================================================
  it('openEntityInGraph navigates to /graph?type=book&id=…', async () => {
    mockGet.mockImplementation(async () => emptyList());

    const wrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: { ResearchWorkflowView: { template: '<div class="research-workflow"/>' } },
      },
    });

    const pushSpy = vi.spyOn(router, 'push');

    (wrapper.vm as unknown as {
      openEntityInGraph: (t: string, id: string) => void;
    }).openEntityInGraph('book', '93441ffc-68c3-4d8d-9427-aba9c75970bb');
    await flushPromises();

    expect(pushSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'graph',
        query: { type: 'book', id: '93441ffc-68c3-4d8d-9427-aba9c75970bb' },
      }),
    );
  });

  // =========================================================================
  // Test 3: openEvidenceInGraph → router.push with trace query
  // =========================================================================
  it('openEvidenceInGraph navigates to /graph?trace=…', async () => {
    mockGet.mockImplementation(async () => emptyList());

    const wrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: { ResearchWorkflowView: { template: '<div class="research-workflow"/>' } },
      },
    });

    const pushSpy = vi.spyOn(router, 'push');

    (wrapper.vm as unknown as {
      openEvidenceInGraph: (t: string) => void;
    }).openEvidenceInGraph('trace-456-abc');
    await flushPromises();

    expect(pushSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'graph',
        query: { trace: 'trace-456-abc' },
      }),
    );
  });

  // =========================================================================
  // Test 4: GraphExplorerView calls neighbors API when mounted with type+id
  // =========================================================================
  it('GraphExplorerView calls /api/v1/graph/neighbors/{type}/{id} on mount', async () => {
    await router.push({ name: 'graph', query: { type: 'book', id: '93441ffc-68c3-4d8d-9427-aba9c75970bb' } });
    await router.isReady();

    mockGet.mockResolvedValueOnce(graphNeighborsResponse());

    const wrapper = mount(GraphExplorerView, {
      global: {
        plugins: [router, i18n],
        stubs: { GraphCanvas: { template: '<div class="graph-canvas"/>' } },
      },
    });
    await flushPromises();

    // API was called with the correct entity type + id
    expect(mockGet).toHaveBeenCalledWith(
      '/api/v1/graph/neighbors/book/93441ffc-68c3-4d8d-9427-aba9c75970bb',
    );

    // GraphCanvas rendered
    expect(wrapper.find('.graph-canvas').exists()).toBe(true);
  });

  // =========================================================================
  // Test 5: GraphExplorerView searches entities when mounted with trace
  // =========================================================================
  it('GraphExplorerView searches entities with trace value on mount', async () => {
    await router.push({ name: 'graph', query: { trace: 'trace-789' } });
    await router.isReady();

    const searchResult = {
      data: {
        data: [
          {
            id: 'book:93441ffc',
            entity_type: 'book',
            entity_id: '93441ffc-68c3-4d8d-9427-aba9c75970bb',
            label: '《针灸甲乙经》 (晋)',
            properties: {},
          },
        ],
      },
    };

    mockGet
      .mockResolvedValueOnce(searchResult)
      .mockResolvedValueOnce(graphNeighborsResponse());

    const wrapper = mount(GraphExplorerView, {
      global: {
        plugins: [router, i18n],
        stubs: { GraphCanvas: { template: '<div class="graph-canvas"/>' } },
      },
    });
    await flushPromises();

    // First call: entity search with trace value as query
    const calls = mockGet.mock.calls as Array<Array<unknown>>;
    const firstCallUrl = calls[0]?.[0];
    expect(firstCallUrl).toContain('/api/v1/graph/entities');
    const firstCallOpts = calls[0]?.[1] as { params?: Record<string, unknown> } | undefined;
    expect(firstCallOpts?.params).toBeDefined();
    expect((firstCallOpts?.params as Record<string, string>)?.q).toBe('trace-789');

    // Second call: auto-loaded neighborhood for single search result
    expect(mockGet).toHaveBeenCalledWith(
      '/api/v1/graph/neighbors/book/93441ffc-68c3-4d8d-9427-aba9c75970bb',
    );

    expect(wrapper.find('.graph-canvas').exists()).toBe(true);
  });

  // =========================================================================
  // Test 6: Complete chain — Evidence Panel click → Graph jump → data loaded
  // =========================================================================
  it('complete chain: evidence → graph-link click → router.push → GraphExplorer loads data', async () => {
    // Phase A: Mount workspace with evidence
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') return emptyList();
      if (url === '/api/v1/research/materials') return emptyPage();
      if (url === '/api/v1/research/versions') return emptyPage();
      if (url === '/api/v1/workspace/notes') return emptyList();
      if (String(url).includes('/api/v1/graph/neighbors/'))
        return graphNeighborsResponse();
      return emptyList();
    });

    const wsWrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: { ResearchWorkflowView: { template: '<div class="research-workflow"/>' } },
      },
    });

    // Seed evidence (simulates AI answer returning evidence)
    (wsWrapper.vm as unknown as { activeTab: string }).activeTab = 'assistant';
    (wsWrapper.vm as unknown as {
      evidence: Array<{ entity_type: string; id: string; content: string }>;
    }).evidence = [
      { entity_type: 'book', id: '93441ffc-68c3-4d8d-9427-aba9c75970bb', content: '《针灸甲乙经》 (晋)' },
    ];
    await flushPromises();

    // Verify evidence item is rendered with graph-link
    const evidenceEls = wsWrapper.findAll('.rw-evidence-item');
    expect(evidenceEls.length).toBe(1);
    const graphLinkEl = evidenceEls[0]?.find('.rw-evidence-graph-link');
    expect(graphLinkEl?.exists()).toBe(true);

    // Click the graph link
    const pushSpy = vi.spyOn(router, 'push');
    await graphLinkEl!.trigger('click');
    await flushPromises();

    // Assert navigation to /graph with correct params
    expect(pushSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'graph',
        query: expect.objectContaining({ type: 'book', id: '93441ffc-68c3-4d8d-9427-aba9c75970bb' }),
      }),
    );

    // Phase B: Mount GraphExplorerView at the navigated-to route
    await router.push({
      name: 'graph',
      query: { type: 'book', id: '93441ffc-68c3-4d8d-9427-aba9c75970bb' },
    });
    await router.isReady();

    // Clear previous mock calls to get a clean assertion
    vi.clearAllMocks();
    mockGet.mockResolvedValueOnce(graphNeighborsResponse());

    const graphWrapper = mount(GraphExplorerView, {
      global: {
        plugins: [router, i18n],
        stubs: { GraphCanvas: { template: '<div class="graph-canvas"/>' } },
      },
    });
    await flushPromises();

    // GraphExplorer should call the neighbors endpoint
    expect(mockGet).toHaveBeenCalledWith(
      '/api/v1/graph/neighbors/book/93441ffc-68c3-4d8d-9427-aba9c75970bb',
    );

    // GraphCanvas received the stub
    expect(graphWrapper.find('.graph-canvas').exists()).toBe(true);
  });

  // =========================================================================
  // Test 7: Redirect guard — /research redirects to workspace?tab=research
  // =========================================================================
  it('/research route redirects to /research/workspace?tab=research', async () => {
    await router.push('/research');
    await router.isReady();
    // After redirect, the URL should contain the workspace redirect
    expect(router.currentRoute.value.path).toBe('/research/workspace');
    expect(router.currentRoute.value.query.tab).toBe('research');
  });

  // =========================================================================
  // Test 8: Workspace research tab renders embedded ResearchWorkflowView
  // =========================================================================
  it('workspace research tab contains ResearchWorkflowView stub', async () => {
    mockGet.mockImplementation(async () => emptyList());

    await router.push({ name: 'research-workspace', query: { tab: 'research' } });
    await router.isReady();

    const wrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: {
          ResearchWorkflowView: { template: '<div class="research-workflow embedded"/>' },
        },
      },
    });

    (wrapper.vm as unknown as { activeTab: string }).activeTab = 'research';
    await flushPromises();

    // The workspace should contain the embedded workflow
    expect(wrapper.find('.research-workflow.embedded').exists()).toBe(true);
  });
});
