/**
 * KnowledgeExplorerPage unit tests — Task 2A.
 *
 * Covers: entity search, entity selection, neighborhood loading,
 * subgraph loading, edge click → evidence display, error/empty states.
 */
import { flushPromises, mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { createRouter, createWebHistory } from 'vue-router';

import i18n from '@/i18n';
import KnowledgeExplorerPage from '@/pages/knowledge/KnowledgeExplorerPage.vue';

// ---------------------------------------------------------------------------
// Hoisted API mock
// ---------------------------------------------------------------------------
const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: {
    defaults: { baseURL: '' },
    get: mockGet,
  },
}));

// ---------------------------------------------------------------------------
// Hoisted auth store
// ---------------------------------------------------------------------------
const { mockUseAuthStore } = vi.hoisted(() => {
  const fn = vi.fn(() => ({
    isAuthenticated: true,
    isAdmin: false,
    isSuperAdmin: false,
    canReviewDocuments: false,
    canManageSourcePolicies: false,
    userName: 'Tester',
    accessToken: 'mock-jwt',
    refreshToken: null as string | null,
    user: {
      id: 'u1',
      username: 'tester',
      email: 't@test.com',
      display_name: 'Tester',
      affiliation: null,
      is_active: true,
      is_superuser: false,
      roles: [],
      created_at: null,
      updated_at: null,
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
// Stub GraphCanvas — vis-network uses Canvas2D which crashes in jsdom
// ---------------------------------------------------------------------------
const GraphCanvasStub = {
  name: 'GraphCanvas',
  template: `
    <div class="graph-canvas-stub">
      <div v-if="loading" class="graph-state--loading">Loading</div>
      <div v-else-if="error" class="graph-state--error">
        {{ error }}
        <button class="graph-retry-btn" @click="$emit('retry')">Retry</button>
      </div>
      <div v-else-if="nodes && nodes.length === 0" class="graph-state--empty">{{ emptyText }}</div>
      <div v-else class="graph-network--ready">
        <span v-for="n in nodes" :key="n.id" class="stub-node" :data-node-id="n.id"
              @click="$emit('node-click', n)"
              @dblclick="$emit('node-double-click', n)">
          {{ n.label }}
        </span>
        <span v-for="e in edges" :key="e.id" class="stub-edge" :data-edge-id="e.id"
              @click="$emit('edge-click', e)">
          {{ e.label }}
        </span>
      </div>
    </div>
  `,
  props: {
    nodes: { type: Array, default: () => [] },
    edges: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    error: { type: String, default: null },
    emptyText: { type: String, default: '' },
    centerNodeId: { type: String, default: null },
  },
  emits: ['retry', 'node-click', 'node-double-click', 'edge-click'],
};

// ---------------------------------------------------------------------------
// Router
// ---------------------------------------------------------------------------
function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', name: 'home', component: { template: '<div />' } },
      {
        path: '/app/knowledge',
        name: 'knowledge-explorer',
        component: KnowledgeExplorerPage,
      },
      {
        path: '/app/library/:id',
        name: 'library-detail',
        component: { template: '<div />' },
      },
    ],
  });
}

// ---------------------------------------------------------------------------
// Shared mount helper — stitches GraphCanvas stub into every mount
// ---------------------------------------------------------------------------
function mountPage() {
  return mount(KnowledgeExplorerPage, {
    global: {
      plugins: [makeRouter(), i18n],
      stubs: { GraphCanvas: GraphCanvasStub },
    },
  });
}

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------
const mockPersonNode = {
  id: 'person:p1',
  entity_type: 'person',
  entity_id: 'p1',
  label: '皇甫谧',
  properties: { name: '皇甫谧', dynasty: '晋', era: '西晋' },
};

const mockBookNode = {
  id: 'book:b1',
  entity_type: 'book',
  entity_id: 'b1',
  label: '针灸甲乙经',
  properties: { title: '针灸甲乙经', category: '医经' },
};

const mockEdge = {
  id: 'edge-1',
  source_id: 'person:p1',
  target_id: 'book:b1',
  relation_type: 'authored',
  label: '作者',
  source: 'explicit',
  evidence: {
    document_id: 'doc-1',
    chunk_id: 'chunk-1',
    exact_quote: '皇甫谧撰针灸甲乙经',
    citation: '[doc-1:chunk-1]',
    version_id: '',
    passage_id: '',
    source_uri: 'https://example.com/source',
    claim_text: '皇甫谧是针灸甲乙经的作者',
  },
};

const MOCK_SEARCH_RESPONSE = (nodes: unknown[]) => ({
  data: { success: true, data: nodes, message: 'ok' },
});

const MOCK_NEIGHBORS_RESPONSE = (center: unknown, neighbors: unknown[], edges: unknown[]) => ({
  data: {
    success: true,
    data: { center, neighbors, edges },
    message: 'ok',
  },
});

describe('KnowledgeExplorerPage', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // -----------------------------------------------------------------------
  // Rendering
  // -----------------------------------------------------------------------

  it('renders the page header with title', async () => {
    const wrapper = mountPage();
    await flushPromises();
    expect(wrapper.text()).toContain('知识图谱');
  });

  it('renders the search input and type filter chips', () => {
    const wrapper = mountPage();
    const input = wrapper.find('input.search-input');
    expect(input.exists()).toBe(true);
    expect(input.attributes('placeholder')).toContain('搜索');

    const chips = wrapper.findAll('.type-chip');
    expect(chips.length).toBe(4); // person, book, version, passage
  });

  it('shows empty hint when no graph data is loaded', () => {
    const wrapper = mountPage();
    expect(wrapper.text()).toContain('选择');
  });

  // -----------------------------------------------------------------------
  // Entity search
  // -----------------------------------------------------------------------

  it('searches entities on Enter and displays results', async () => {
    mockGet.mockResolvedValueOnce(MOCK_SEARCH_RESPONSE([mockPersonNode, mockBookNode]));

    const wrapper = mountPage();
    const input = wrapper.find('input.search-input');
    await input.setValue('皇甫谧');
    await input.trigger('keyup.enter');
    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith(
      '/api/v1/graph/entities',
      expect.objectContaining({
        params: expect.objectContaining({ q: '皇甫谧' }),
      }),
    );

    expect(wrapper.text()).toContain('皇甫谧');
    expect(wrapper.text()).toContain('针灸甲乙经');
  });

  it('shows no-data message when search returns empty', async () => {
    mockGet.mockResolvedValueOnce(MOCK_SEARCH_RESPONSE([]));

    const wrapper = mountPage();
    const input = wrapper.find('input.search-input');
    await input.setValue('nonexistent');
    await input.trigger('keyup.enter');
    await flushPromises();

    expect(wrapper.text()).toContain('暂无数据');
  });

  it('dismisses stale search responses', async () => {
    let resolveFirst: (v: unknown) => void = () => {};
    const firstPromise = new Promise((resolve) => {
      resolveFirst = resolve;
    });

    mockGet
      .mockReturnValueOnce(firstPromise)
      .mockResolvedValueOnce(MOCK_SEARCH_RESPONSE([mockBookNode]));

    const wrapper = mountPage();

    // Fire first search
    const input = wrapper.find('input.search-input');
    await input.setValue('first');
    await input.trigger('keyup.enter');

    // Fire second search (different query)
    await input.setValue('second');
    await input.trigger('keyup.enter');
    await flushPromises();

    // Now resolve the first (stale) search
    resolveFirst(MOCK_SEARCH_RESPONSE([mockPersonNode]));
    await flushPromises();

    // Should show results from second search (bookNode), not first (personNode)
    expect(wrapper.text()).toContain('针灸甲乙经');
    expect(wrapper.text()).not.toContain('皇甫谧');
  });

  // -----------------------------------------------------------------------
  // Entity selection → neighborhood loading
  // -----------------------------------------------------------------------

  it('loads neighborhood when selecting a search result', async () => {
    mockGet.mockResolvedValueOnce(MOCK_SEARCH_RESPONSE([mockPersonNode]));

    const wrapper = mountPage();

    // Search
    const input = wrapper.find('input.search-input');
    await input.setValue('皇甫谧');
    await input.trigger('keyup.enter');
    await flushPromises();

    // Neighbors response
    mockGet.mockResolvedValueOnce(
      MOCK_NEIGHBORS_RESPONSE(mockPersonNode, [mockBookNode], [mockEdge]),
    );

    // Click the search result
    const resultItem = wrapper.find('.result-item');
    await resultItem.trigger('click');
    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith('/api/v1/graph/neighbors/person/p1');

    // Entity detail should show
    expect(wrapper.text()).toContain('皇甫谧');
    expect(wrapper.text()).toContain('晋');
  });

  // -----------------------------------------------------------------------
  // Subgraph loading
  // -----------------------------------------------------------------------

  it('loads subgraph when expand button is clicked', async () => {
    mockGet.mockResolvedValueOnce(MOCK_SEARCH_RESPONSE([mockPersonNode]));
    mockGet.mockResolvedValueOnce(
      MOCK_NEIGHBORS_RESPONSE(mockPersonNode, [mockBookNode], [mockEdge]),
    );

    const wrapper = mountPage();

    // Search and select
    const input = wrapper.find('input.search-input');
    await input.setValue('皇甫谧');
    await input.trigger('keyup.enter');
    await flushPromises();

    const resultItem = wrapper.find('.result-item');
    await resultItem.trigger('click');
    await flushPromises();

    // Subgraph response
    mockGet.mockResolvedValueOnce({
      data: {
        success: true,
        data: { nodes: [mockPersonNode, mockBookNode], edges: [mockEdge] },
        message: 'ok',
      },
    });

    // Click "展开子图" button
    const expandBtn = wrapper.findAll('.action-btn').find((b) => b.text().includes('展开'));
    expect(expandBtn).toBeTruthy();
    await expandBtn!.trigger('click');
    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith('/api/v1/graph/entity/person/p1');
  });

  // -----------------------------------------------------------------------
  // Edge evidence display
  // -----------------------------------------------------------------------

  it('shows edge evidence when clicking an edge', async () => {
    mockGet.mockResolvedValueOnce(MOCK_SEARCH_RESPONSE([mockPersonNode]));
    mockGet.mockResolvedValueOnce(
      MOCK_NEIGHBORS_RESPONSE(mockPersonNode, [mockBookNode], [mockEdge]),
    );

    const wrapper = mountPage();

    // Search and select
    const input = wrapper.find('input.search-input');
    await input.setValue('皇甫谧');
    await input.trigger('keyup.enter');
    await flushPromises();

    const resultItem = wrapper.find('.result-item');
    await resultItem.trigger('click');
    await flushPromises();

    // Simulate edge click via GraphCanvas stub emit
    const graphCanvas = wrapper.findComponent({ name: 'GraphCanvas' });
    expect(graphCanvas.exists()).toBe(true);
    expect(graphCanvas.props('edges')).toEqual([mockEdge]);

    await graphCanvas.vm.$emit('edge-click', mockEdge);
    await flushPromises();

    // Evidence details should show
    expect(wrapper.text()).toContain('皇甫谧撰针灸甲乙经');
    expect(wrapper.text()).toContain('[doc-1:chunk-1]');
    expect(wrapper.text()).toContain('doc-1');
  });

  // -----------------------------------------------------------------------
  // Error handling
  // -----------------------------------------------------------------------

  it('shows error when neighborhood load fails', async () => {
    mockGet.mockResolvedValueOnce(MOCK_SEARCH_RESPONSE([mockPersonNode]));
    mockGet.mockRejectedValueOnce(new Error('Network Error'));

    const wrapper = mountPage();

    const input = wrapper.find('input.search-input');
    await input.setValue('皇甫谧');
    await input.trigger('keyup.enter');
    await flushPromises();

    const resultItem = wrapper.find('.result-item');
    await resultItem.trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('Network Error');
  });

  // -----------------------------------------------------------------------
  // Type filter toggling
  // -----------------------------------------------------------------------

  it('toggles entity type filters on chip click', async () => {
    const wrapper = mountPage();

    const chips = wrapper.findAll('.type-chip');
    expect(chips.length).toBe(4);

    // Click the first chip to deselect it
    await chips[0]!.trigger('click');
    const updatedChips = wrapper.findAll('.type-chip');
    expect(updatedChips[0]!.classes('type-chip--active')).toBe(false);
  });

  // -----------------------------------------------------------------------
  // Retry on error
  // -----------------------------------------------------------------------

  it('retries the last action on retry event', async () => {
    mockGet.mockResolvedValueOnce(MOCK_SEARCH_RESPONSE([mockPersonNode]));
    mockGet.mockRejectedValueOnce(new Error('Fail'));
    mockGet.mockResolvedValueOnce(
      MOCK_NEIGHBORS_RESPONSE(mockPersonNode, [], []),
    );

    const wrapper = mountPage();

    // Search and select — triggers failing neighbors
    const input = wrapper.find('input.search-input');
    await input.setValue('皇甫谧');
    await input.trigger('keyup.enter');
    await flushPromises();

    const resultItem = wrapper.find('.result-item');
    await resultItem.trigger('click');
    await flushPromises();

    expect(wrapper.text()).toContain('Fail');

    // Click retry button on GraphCanvas stub
    const graphCanvas = wrapper.findComponent({ name: 'GraphCanvas' });
    await graphCanvas.vm.$emit('retry');
    await flushPromises();

    // Error should be cleared, retry should have been called
    expect(wrapper.text()).not.toContain('Fail');
    expect(mockGet).toHaveBeenCalledTimes(3); // search + failed neighbors + retry neighbors
  });
});
