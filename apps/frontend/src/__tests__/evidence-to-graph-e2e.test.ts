/**
 * AI → Evidence → Graph end-to-end acceptance test.
 *
 * Drives the REAL frontend path, end to end:
 *   sendMessage()
 *     → fetch('/api/v1/ai/chat')  streaming SSE response
 *     → api.get('/api/v1/search')  evidence items
 *     → api.get('/api/v1/graph/neighbors/{type}/{id}')  graph preview
 *     → Evidence Panel renders .rw-evidence-item  with .rw-evidence-graph-link
 *     → openEntityInGraph(type, id)
 *     → router.push({ name: 'graph', query: { type, id } })
 *     → GraphExplorerView.onMounted → neighbors API → GraphCanvas receives data
 *
 * Only the HTTP/SSE fixture is deterministic — the component's own state
 * machine (sendMessage, fetch, api calls, reactive rendering) runs as in
 * production.
 */
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, expect, it, vi, beforeEach } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';

import i18n from '@/i18n';
import GraphExplorerView from '@/views/GraphExplorerView.vue';
import ResearchWorkspaceView from '@/views/ResearchWorkspaceView.vue';

// ---------------------------------------------------------------------------
// Hoisted API mock (api.get / api.post via @/api/client)
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
// Hoisted auth store (prevents localStorage crash in jsdom)
// ---------------------------------------------------------------------------
const { mockUseAuthStore } = vi.hoisted(() => {
  const fn = vi.fn(() => ({
    isAuthenticated: true,
    isAdmin: false,
    isSuperAdmin: false,
    canReviewDocuments: false,
    canManageSourcePolicies: false,
    userName: 'Tester',
    accessToken: 'mock-jwt-token',
    refreshToken: null as string | null,
    user: {
      id: 'u1', username: 'tester', email: 't@example.com',
      display_name: 'Tester', affiliation: null, is_active: true,
      is_superuser: false, roles: [],
      created_at: null, updated_at: null,
    } as unknown as null,
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
// Router — includes every route referenced by workspace template links
// ---------------------------------------------------------------------------
function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/research/home', component: { template: '<div/>' }, name: 'research-home' },
      { path: '/research/new', component: { template: '<div/>' }, name: 'research-new' },
      { path: '/literature', component: { template: '<div/>' }, name: 'literature' },
      { path: '/classical-versions', component: { template: '<div/>' }, name: 'classical-versions' },
      { path: '/research', redirect: '/research/workspace?tab=research' },
      { path: '/research/workspace', name: 'research-workspace', component: ResearchWorkspaceView },
      { path: '/graph', name: 'graph', component: GraphExplorerView },
      { path: '/login', component: { template: '<div/>' }, name: 'login' },
    ],
  });
}

// ---------------------------------------------------------------------------
// Response factories — real API shapes
// ---------------------------------------------------------------------------

function emptyList() {
  return { data: { data: [] } };
}

function emptyPage() {
  return { data: { data: [], total: 0 } };
}

/** A single chat session for the workspace */
function sessionResponse() {
  return {
    data: {
      data: [{ id: 'sess-chat-1', title: '测试会话' }],
    },
  };
}

/**
 * Build a ReadableStream SSE fixture matching the real /api/v1/ai/chat shape.
 */
function fakeSSEStream(chunks: Array<string>) {
  const encoder = new TextEncoder();
  const lines = chunks.flatMap(c => [`data: ${JSON.stringify({ content: c })}\n\n`]);
  lines.push(`data: ${JSON.stringify({ done: true })}\n\n`);
  let i = 0;
  return new ReadableStream({
    pull(controller) {
      if (i < lines.length) {
        controller.enqueue(encoder.encode(lines[i]!));
        i++;
      } else {
        controller.close();
      }
    },
  });
}

// ---------------------------------------------------------------------------

describe('AI → Evidence → Graph E2E chain (real sendMessage path)', () => {
  let router: ReturnType<typeof createRouter>;

  beforeEach(async () => {
    vi.clearAllMocks();
    setActivePinia(createPinia());
    router = makeRouter();
    await router.push('/');
  });

  // =========================================================================
  // Test 1: sendMessage → SSE → search → evidence → graph neighbors
  // =========================================================================
  it('sendMessage → SSE stream → /api/v1/search → evidence rendering → graph neighbors call', async () => {
    // ---- Wire mocks for all background GETs the workspace fires on mount ----
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') return sessionResponse();
      if (url === '/api/v1/research/materials') return emptyPage();
      if (url === '/api/v1/research/versions') return emptyPage();
      if (url === '/api/v1/workspace/notes') return emptyList();
      // search API — called AFTER SSE completes
      if (String(url).startsWith('/api/v1/search'))
        return {
          data: {
            data: {
              items: [
                {
                  id: 'passage:test-abc-1',
                  entity_type: 'passage',
                  title: 'Test passage excerpt',
                  subtitle: null,
                  snippet: '针灸理论...',
                  score: 0.9,
                },
                {
                  id: 'book:test-book-2',
                  entity_type: 'book',
                  title: '《针灸甲乙经》',
                  subtitle: null,
                  snippet: '腧穴...',
                  score: 0.8,
                },
              ],
              total: 2,
            },
          },
        };
      // graph neighbors — called AFTER search returns entities
      if (String(url).includes('/api/v1/graph/neighbors/'))
        return {
          data: {
            data: {
              center: {
                id: 'passage:test-abc-1',
                entity_type: 'passage',
                entity_id: 'passage:test-abc-1',
                label: 'Test passage excerpt',
                properties: {},
              },
              neighbors: [
                {
                  id: 'book:test-book-2',
                  entity_type: 'book',
                  entity_id: 'book:test-book-2',
                  label: '《针灸甲乙经》',
                  properties: {},
                },
              ],
              edges: [
                {
                  id: 'e-graph-1',
                  source_id: 'test-book-2',
                  target_id: 'test-abc-1',
                  relation_type: 'contains',
                  label: 'contains',
                  source: 'book',
                },
              ],
            },
          },
        };
      if (String(url).includes('/api/v1/workspace/sessions/')) return emptyList();
      return emptyList();
    });

    // ---- Mock global fetch for SSE chat stream ----
    const fetchStub = vi.fn().mockResolvedValue({
      ok: true,
      body: fakeSSEStream(['针灸甲乙经是皇甫谧', '编纂的针灸学著作。']),
    });
    vi.stubGlobal('fetch', fetchStub);

    // ---- Mount workspace ----
    const wrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: { ResearchWorkflowView: { template: '<div class="research-workflow"/>' } },
      },
    });

    // ---- Navigate to assistant tab ----
    (wrapper.vm as unknown as { activeTab: string }).activeTab = 'assistant';
    await flushPromises();

    // ---- Simulate user typing + send ----
    const vm = wrapper.vm as unknown as {
      chatInput: string;
      chatSessionId: string;
      sendMessage: () => Promise<void>;
      evidence: Array<{ entity_type: string; id: string; content: string }>;
      evidenceGraphData: { nodes: Array<unknown>; edges: Array<unknown> } | null;
    };
    vm.chatInput = '针灸甲乙经有哪些腧穴理论贡献？';
    vm.chatSessionId = 'sess-chat-1';
    await vm.sendMessage();
    await flushPromises();

    // ---- Assert: SSE fetch was called ----
    expect(fetchStub).toHaveBeenCalledWith(
      '/api/v1/ai/chat',
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({ 'Content-Type': 'application/json' }),
        body: expect.stringContaining('针灸甲乙经'),
      }),
    );

    // ---- Assert: search API was called ----
    expect(mockGet).toHaveBeenCalledWith(
      '/api/v1/search',
      { params: { q: '针灸甲乙经有哪些腧穴理论贡献？', limit: 5 } },
    );

    // ---- Assert: graph neighbors API was called for first entity ----
    // The search response id is "passage:test-abc-1" which is what the
    // evidence item carries, so the graph call uses that full id.
    expect(mockGet).toHaveBeenCalledWith(
      '/api/v1/graph/neighbors/passage/passage:test-abc-1',
    );

    // ---- Assert: evidence items are populated (real component state) ----
    expect(vm.evidence.length).toBe(2);
    expect(vm.evidence[0]!.entity_type).toBe('passage');
    expect(vm.evidence[0]!.id).toBe('passage:test-abc-1');

    // ---- Assert: evidence graph data was populated ----
    expect(vm.evidenceGraphData).not.toBeNull();
    expect(vm.evidenceGraphData!.nodes.length).toBe(2);
    expect(vm.evidenceGraphData!.edges.length).toBe(1);

    // Clean up
    vi.unstubAllGlobals();
  });

  // =========================================================================
  // Test 2: Evidence Panel renders items with graph-link after sendMessage
  // =========================================================================
  it('renders .rw-evidence-item and .rw-evidence-graph-link after sendMessage completes', async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') return sessionResponse();
      if (url === '/api/v1/research/materials') return emptyPage();
      if (url === '/api/v1/research/versions') return emptyPage();
      if (url === '/api/v1/workspace/notes') return emptyList();
      if (String(url).startsWith('/api/v1/search'))
        return {
          data: {
            data: {
              items: [
                {
                  id: 'person:test-person',
                  entity_type: 'person',
                  title: '皇甫谧',
                  subtitle: null,
                  snippet: '晋代医学家...',
                  score: 0.95,
                },
              ],
              total: 1,
            },
          },
        };
      if (String(url).includes('/api/v1/graph/neighbors/'))
        return {
          data: {
            data: {
              center: { id: 'person:test-person', entity_type: 'person', label: '皇甫谧', properties: {} },
              neighbors: [],
              edges: [],
            },
          },
        };
      if (String(url).includes('/api/v1/workspace/sessions/')) return emptyList();
      return emptyList();
    });

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: fakeSSEStream(['皇甫谧（215-282），字士安，号玄晏先生。']),
    }));

    const wrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: { ResearchWorkflowView: { template: '<div class="research-workflow"/>' } },
      },
    });

    const vm = wrapper.vm as unknown as {
      activeTab: string;
      chatInput: string;
      chatSessionId: string;
      sendMessage: () => Promise<void>;
      evidence: Array<{ entity_type: string; id: string; content: string }>;
    };
    vm.activeTab = 'assistant';
    await flushPromises();

    vm.chatInput = '皇甫谧是谁？';
    vm.chatSessionId = 'sess-chat-1';
    await vm.sendMessage();
    await flushPromises();

    // Assert: evidence items rendered in DOM
    const evidenceEls = wrapper.findAll('.rw-evidence-item');
    expect(evidenceEls.length).toBe(1);

    // Assert: graph-link button rendered inside evidence item
    const graphLink = evidenceEls[0]?.find('.rw-evidence-graph-link');
    expect(graphLink?.exists()).toBe(true);

    vi.unstubAllGlobals();
  });

  // =========================================================================
  // Test 3: graph-link click → openEntityInGraph → router.push with type+id
  // =========================================================================
  it('clicking .rw-evidence-graph-link calls router.push to /graph?type=&id=', async () => {
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') return sessionResponse();
      if (url === '/api/v1/research/materials') return emptyPage();
      if (url === '/api/v1/research/versions') return emptyPage();
      if (url === '/api/v1/workspace/notes') return emptyList();
      if (String(url).startsWith('/api/v1/search'))
        return {
          data: {
            data: {
              items: [
                {
                  id: 'book:test-book-2',
                  entity_type: 'book',
                  title: '《针灸甲乙经》',
                  subtitle: null,
                  snippet: '针灸经典...',
                  score: 0.9,
                },
              ],
              total: 1,
            },
          },
        };
      if (String(url).includes('/api/v1/graph/neighbors/'))
        return {
          data: {
            data: {
              center: { id: 'book:test-book-2', entity_type: 'book', label: '针灸甲乙经', properties: {} },
              neighbors: [],
              edges: [],
            },
          },
        };
      if (String(url).includes('/api/v1/workspace/sessions/')) return emptyList();
      return emptyList();
    });

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: fakeSSEStream(['《针灸甲乙经》是现存最早的针灸学专著。']),
    }));

    const wrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: { ResearchWorkflowView: { template: '<div class="research-workflow"/>' } },
      },
    });

    const vm = wrapper.vm as unknown as {
      activeTab: string;
      chatInput: string;
      chatSessionId: string;
      sendMessage: () => Promise<void>;
    };
    vm.activeTab = 'assistant';
    await flushPromises();

    vm.chatInput = '针灸甲乙经';
    vm.chatSessionId = 'sess-chat-1';
    await vm.sendMessage();
    await flushPromises();

    // Verify evidence rendered
    const evidenceEls = wrapper.findAll('.rw-evidence-item');
    expect(evidenceEls.length).toBe(1);

    // Click the graph-link
    const pushSpy = vi.spyOn(router, 'push');
    const graphLink = evidenceEls[0]?.find('.rw-evidence-graph-link');
    expect(graphLink?.exists()).toBe(true);
    await graphLink!.trigger('click');
    await flushPromises();

    // Assert: router.push called with correct params
    expect(pushSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'graph',
        query: { type: 'book', id: 'book:test-book-2' },
      }),
    );

    vi.unstubAllGlobals();
  });

  // =========================================================================
  // Test 4: GraphExplorerView loads neighbors when mounted with type+id
  // =========================================================================
  it('GraphExplorerView calls /api/v1/graph/neighbors/{type}/{id} on mount with query params', async () => {
    await router.push({ name: 'graph', query: { type: 'book', id: 'test-book-2' } });
    await router.isReady();

    mockGet.mockResolvedValueOnce({
      data: {
        data: {
          center: {
            id: 'book:test-book-2',
            entity_type: 'book',
            entity_id: 'test-book-2',
            label: '《针灸甲乙经》',
            properties: {},
          },
          neighbors: [
            {
              id: 'person:test-person',
              entity_type: 'person',
              entity_id: 'test-person',
              label: '皇甫谧',
              properties: {},
            },
          ],
          edges: [
            {
              id: 'e1',
              source_id: 'test-person',
              target_id: 'test-book-2',
              relation_type: 'compiled',
              label: '编纂',
              source: 'person',
            },
          ],
        },
      },
    });

    const wrapper = mount(GraphExplorerView, {
      global: {
        plugins: [router, i18n],
        stubs: { GraphCanvas: { template: '<div class="graph-canvas"/>' } },
      },
    });
    await flushPromises();

    // API called with correct params
    expect(mockGet).toHaveBeenCalledWith('/api/v1/graph/neighbors/book/test-book-2');

    // GraphCanvas rendered
    expect(wrapper.find('.graph-canvas').exists()).toBe(true);
  });

  // =========================================================================
  // Test 5: GraphExplorerView consumes trace param and searches
  // =========================================================================
  it('GraphExplorerView searches entities on mount when ?trace= is present', async () => {
    await router.push({ name: 'graph', query: { trace: 'test-trace-id' } });
    await router.isReady();

    mockGet
      .mockResolvedValueOnce({
        data: {
          data: [
            {
              id: 'book:test-book-2',
              entity_type: 'book',
              entity_id: 'test-book-2',
              label: '《针灸甲乙经》',
              properties: {},
            },
          ],
        },
      })
      .mockResolvedValueOnce({
        data: {
          data: {
            center: { id: 'book:test-book-2', entity_type: 'book', entity_id: 'test-book-2', label: '针灸甲乙经', properties: {} },
            neighbors: [],
            edges: [],
          },
        },
      });

    const wrapper = mount(GraphExplorerView, {
      global: {
        plugins: [router, i18n],
        stubs: { GraphCanvas: { template: '<div class="graph-canvas"/>' } },
      },
    });
    await flushPromises();

    // Entity search was called
    const calls = mockGet.mock.calls as Array<Array<unknown>>;
    const firstUrl = calls[0]?.[0] as string;
    expect(firstUrl).toContain('/api/v1/graph/entities');

    // Single result → auto-loaded neighborhood
    expect(mockGet).toHaveBeenCalledWith('/api/v1/graph/neighbors/book/test-book-2');

    expect(wrapper.find('.graph-canvas').exists()).toBe(true);
  });

  // =========================================================================
  // Test 6: Complete chain — sendMessage → evidence → graph click → graph loads
  // =========================================================================
  it('complete chain: sendMessage → evidence → graph-link click → GraphExplorer loads neighbors', async () => {
    // ---- Phase A: Workspace with AI + search ----
    mockGet.mockImplementation(async (url: string) => {
      if (url === '/api/v1/workspace/sessions') return sessionResponse();
      if (url === '/api/v1/research/materials') return emptyPage();
      if (url === '/api/v1/research/versions') return emptyPage();
      if (url === '/api/v1/workspace/notes') return emptyList();
      if (String(url).startsWith('/api/v1/search'))
        return {
          data: {
            data: {
              items: [
                {
                  id: 'person:c6d1f2a3',
                  entity_type: 'person',
                  title: '皇甫谧',
                  subtitle: null,
                  snippet: '晋代医学家，编纂《针灸甲乙经》...',
                  score: 0.95,
                },
              ],
              total: 1,
            },
          },
        };
      if (String(url).includes('/api/v1/graph/neighbors/'))
        return {
          data: {
            data: {
              center: { id: 'person:c6d1f2a3', entity_type: 'person', label: '皇甫谧', properties: {} },
              neighbors: [
                { id: 'book:test-book-2', entity_type: 'book', label: '针灸甲乙经', properties: {} },
              ],
              edges: [
                { id: 'e-chain', source_id: 'c6d1f2a3', target_id: 'test-book-2', relation_type: 'compiled', label: '编纂', source: 'person' },
              ],
            },
          },
        };
      if (String(url).includes('/api/v1/workspace/sessions/')) return emptyList();
      return emptyList();
    });

    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      body: fakeSSEStream(['皇甫谧是晋代著名医学家，他编纂了《针灸甲乙经》。']),
    }));

    const wsWrapper = mount(ResearchWorkspaceView, {
      global: {
        plugins: [router, i18n],
        stubs: { ResearchWorkflowView: { template: '<div class="research-workflow"/>' } },
      },
    });

    const vm = wsWrapper.vm as unknown as {
      activeTab: string;
      chatInput: string;
      chatSessionId: string;
      sendMessage: () => Promise<void>;
      evidence: Array<{ entity_type: string; id: string; content: string }>;
    };
    vm.activeTab = 'assistant';
    await flushPromises();

    // Phase 1: Send message → AI + search + graph neighbors
    vm.chatInput = '皇甫谧是谁？';
    vm.chatSessionId = 'sess-chat-1';
    await vm.sendMessage();
    await flushPromises();

    // Evidence is populated
    expect(vm.evidence.length).toBe(1);

    // Phase 2: Click graph-link on evidence item
    const evidenceEls = wsWrapper.findAll('.rw-evidence-item');
    expect(evidenceEls.length).toBe(1);
    const graphLink = evidenceEls[0]?.find('.rw-evidence-graph-link');
    expect(graphLink?.exists()).toBe(true);

    const pushSpy = vi.spyOn(router, 'push');
    await graphLink!.trigger('click');
    await flushPromises();

    expect(pushSpy).toHaveBeenCalledWith(
      expect.objectContaining({
        name: 'graph',
        query: { type: 'person', id: 'person:c6d1f2a3' },
      }),
    );

    // Phase 3: GraphExplorer loads the entity
    await router.push({ name: 'graph', query: { type: 'person', id: 'person:c6d1f2a3' } });
    await router.isReady();
    vi.clearAllMocks();
    mockGet.mockResolvedValueOnce({
      data: {
        data: {
          center: { id: 'person:c6d1f2a3', entity_type: 'person', entity_id: 'c6d1f2a3', label: '皇甫谧', properties: {} },
          neighbors: [],
          edges: [],
        },
      },
    });

    const graphWrapper = mount(GraphExplorerView, {
      global: {
        plugins: [router, i18n],
        stubs: { GraphCanvas: { template: '<div class="graph-canvas"/>' } },
      },
    });
    await flushPromises();

    // Graph API was called for the entity
    expect(mockGet).toHaveBeenCalledWith('/api/v1/graph/neighbors/person/person:c6d1f2a3');
    expect(graphWrapper.find('.graph-canvas').exists()).toBe(true);

    vi.unstubAllGlobals();
  });

  // =========================================================================
  // Test 7: /research route redirects to workspace?tab=research
  // (route-level guard)
  // =========================================================================
  it('/research route redirects to /research/workspace?tab=research', async () => {
    await router.push('/research');
    await router.isReady();
    expect(router.currentRoute.value.path).toBe('/research/workspace');
    expect(router.currentRoute.value.query.tab).toBe('research');
  });

  // =========================================================================
  // Test 8: Workspace research tab contains embedded workflow component
  // =========================================================================
  it('workspace research tab renders embedded ResearchWorkflowView', async () => {
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

    expect(wrapper.find('.research-workflow.embedded').exists()).toBe(true);
  });
});
