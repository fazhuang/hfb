/**
 * Sprint 2 Task 008 — Research Library page tests.
 *
 * Tests LibrarySearchPage and LibraryDetailPage with real API mocking.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';

// jsdom does not supply matchMedia — stub for AppNavbar / useTheme
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// ------------------------------------------------------------------
// Helpers
// ------------------------------------------------------------------

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/library', component: { template: '<div/>' }, name: 'library-search' },
      { path: '/library/:id', component: { template: '<div/>' }, name: 'library-detail' },
      { path: '/literature/:id', component: { template: '<div/>' }, name: 'literature-detail' },
      { path: '/research', component: { template: '<div/>' }, name: 'research-project-list' },
      { path: '/research/workspace', component: { template: '<div/>' }, name: 'research-workspace' },
      { path: '/knowledge', component: { template: '<div/>' }, name: 'knowledge-explorer' },
      { path: '/reports', component: { template: '<div/>' }, name: 'report-list' },
    ],
  });
}

const i18n = createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zhCN } });

// Auth store — always authenticated for library tests
function useMockAuth() {
  vi.doMock('@/stores/auth', () => ({
    useAuthStore: vi.fn(() => ({
      isAuthenticated: true,
      isAdmin: false,
      isSuperAdmin: false,
      canReviewDocuments: false,
      canManageSourcePolicies: false,
      userName: 'TestUser',
      accessToken: 'token',
      user: {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        display_name: 'Test User',
        affiliation: null,
        is_active: true,
        is_superuser: false,
        roles: [],
        created_at: null,
        updated_at: null,
      },
      loading: false,
      error: null,
      login: vi.fn(),
      register: vi.fn(),
      fetchMe: vi.fn(),
      logout: vi.fn(),
    })),
  }));
}

// Mock API client
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import api from '@/api/client';

function mockGet(urlPattern: string, data: unknown) {
  const mock = api.get as ReturnType<typeof vi.fn>;
  mock.mockImplementation(async (url: string) => {
    if (url.includes(urlPattern)) {
      return { data: { data } };
    }
    return { data: { data: null } };
  });
}

function mockGetMulti(routes: Record<string, unknown>) {
  const mock = api.get as ReturnType<typeof vi.fn>;
  mock.mockImplementation(async (url: string) => {
    for (const [pattern, data] of Object.entries(routes)) {
      if (url.includes(pattern)) {
        return { data: { data } };
      }
    }
    return { data: { data: null } };
  });
}

// ------------------------------------------------------------------
// 1. LibrarySearchPage
// ------------------------------------------------------------------

describe('LibrarySearchPage', () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth();
    setActivePinia(createPinia());
  });

  it('1. renders page title "Library"', async () => {
    mockGet('/api/v1/documents', { items: [], total: 0 });
    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('Library');
  });

  it('2. loads document list from API on mount', async () => {
    const mockItems = [
      { id: 'd1', title: '针灸甲乙经', dynasty: '晋', category: '针灸', copyright_status: 'public_domain', review_status: 'approved', rag_enabled: true, source_name: 'wikisource', withdrawn_at: null, created_at: '2025-01-01T00:00:00Z' },
      { id: 'd2', title: '伤寒论', dynasty: '汉', category: '方剂', copyright_status: 'public_domain', review_status: 'approved', rag_enabled: true, source_name: 'user_upload', withdrawn_at: null, created_at: '2025-01-02T00:00:00Z' },
    ];
    mockGet('/api/v1/documents', { items: mockItems, total: 2 });
    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('针灸甲乙经');
    expect(wrapper.text()).toContain('伤寒论');
  });

  it('3. shows loading state', async () => {
    // Make api.get hang so loading stays true
    (api.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('加载中');
  });

  it('4. shows error state on API failure', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));
    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Network error');
  });

  it('5. shows empty state when no documents', async () => {
    mockGet('/api/v1/documents', { items: [], total: 0 });
    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('暂无文献');
  });

  it('6. pagination is visible when total > limit', async () => {
    const manyItems = Array.from({ length: 25 }, (_, i) => ({
      id: `d${i}`, title: `文献 ${i}`, dynasty: '宋', category: '本草',
      copyright_status: 'public_domain', review_status: 'approved', rag_enabled: false,
      source_name: 'test', withdrawn_at: null, created_at: '2025-01-01T00:00:00Z',
    }));
    mockGet('/api/v1/documents', { items: manyItems.slice(0, 20), total: 25 });
    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    // Pagination should show page 1/2
    expect(wrapper.text()).toContain('/ 2');
  });

  it('7. search triggers API call with q param', async () => {
    mockGet('/api/v1/documents', { items: [], total: 0 });
    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    // Simulate search
    const input = wrapper.find('input[type="text"]');
    await input.setValue('针灸');
    const searchBtn = wrapper.find('.lib-search-btn');
    await searchBtn.trigger('click');
    await wrapper.vm.$nextTick();

    const calls = (api.get as ReturnType<typeof vi.fn>).mock.calls as Array<[string, { params: Record<string, string> }]>;
    expect(calls.length).toBeGreaterThan(0);
    const lastCall = calls[calls.length - 1]!;
    expect(lastCall[1].params.q).toBe('针灸');
  });
});

// ------------------------------------------------------------------
// 2. LibraryDetailPage
// ------------------------------------------------------------------

describe('LibraryDetailPage', () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth();
    setActivePinia(createPinia());
  });

  const mockDoc = {
    id: 'd1',
    title: '针灸甲乙经',
    dynasty: '晋',
    year: 256,
    category: '针灸',
    abstract: '《针灸甲乙经》是现存最早的针灸学专著。',
    content_text: '卷一...',
    source_url: 'https://example.com',
    page_count: 12,
    language: 'zh',
    copyright_status: 'public_domain',
    license_type: 'CC0',
    authorization_basis: 'Public Domain',
    review_status: 'approved',
    reviewed_by: null,
    reviewed_at: null,
    rag_enabled: true,
    content_checksum: 'abc123',
    source_name: 'wikisource',
    withdrawn_at: null,
    withdraw_reason: null,
    title_pinyin: 'Zhenjiu Jiayi Jing',
    title_english: 'The Systematic Classic of Acupuncture and Moxibustion',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-06-01T00:00:00Z',
  };

  const mockStats = {
    total_chunks: 42,
    ocr_chunks: 30,
    ocr_text_available: true,
    avg_ocr_confidence: 0.92,
    citation_count: 15,
    evidence_count: 7,
  };

  it('8. renders document title and meta', async () => {
    mockGetMulti({
      '/api/v1/documents/d1/stats': mockStats,
      '/api/v1/documents/d1': mockDoc,
    });
    const router = makeRouter();
    await router.push('/library/d1');
    await router.isReady();

    const { default: LibraryDetailPage } = await import('@/pages/library/LibraryDetailPage.vue');
    const wrapper = mount(LibraryDetailPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('针灸甲乙经');
    expect(wrapper.text()).toContain('晋');
    expect(wrapper.text()).toContain('针灸');
  });

  it('9. renders stats panel with OCR, citation, evidence', async () => {
    mockGetMulti({
      '/api/v1/documents/d1/stats': mockStats,
      '/api/v1/documents/d1': mockDoc,
    });
    const router = makeRouter();
    await router.push('/library/d1');
    await router.isReady();

    const { default: LibraryDetailPage } = await import('@/pages/library/LibraryDetailPage.vue');
    const wrapper = mount(LibraryDetailPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('42');        // total chunks
    expect(text).toContain('可用');       // OCR available
    expect(text).toContain('92.0%');     // OCR confidence
    expect(text).toContain('15');        // citation count
    expect(text).toContain('7');         // evidence count
  });

  it('10. renders reader jump button', async () => {
    mockGetMulti({
      '/api/v1/documents/d1/stats': mockStats,
      '/api/v1/documents/d1': mockDoc,
    });
    const router = makeRouter();
    await router.push('/library/d1');
    await router.isReady();

    const { default: LibraryDetailPage } = await import('@/pages/library/LibraryDetailPage.vue');
    const wrapper = mount(LibraryDetailPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('全文阅读');
    expect(wrapper.text()).toContain('进入全文阅读');
  });

  it('11. shows loading state', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
    const router = makeRouter();
    await router.push('/library/d1');
    await router.isReady();

    const { default: LibraryDetailPage } = await import('@/pages/library/LibraryDetailPage.vue');
    const wrapper = mount(LibraryDetailPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('加载中');
  });

  it('12. shows error state on API failure', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Not found'));
    const router = makeRouter();
    await router.push('/library/d1');
    await router.isReady();

    const { default: LibraryDetailPage } = await import('@/pages/library/LibraryDetailPage.vue');
    const wrapper = mount(LibraryDetailPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Not found');
  });

  it('13. shows compliance panel', async () => {
    mockGetMulti({
      '/api/v1/documents/d1/stats': mockStats,
      '/api/v1/documents/d1': mockDoc,
    });
    const router = makeRouter();
    await router.push('/library/d1');
    await router.isReady();

    const { default: LibraryDetailPage } = await import('@/pages/library/LibraryDetailPage.vue');
    const wrapper = mount(LibraryDetailPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('合规信息');
    expect(text).toContain('公共领域');
    expect(text).toContain('已通过');
    expect(text).toContain('已启用');
  });

  it('14. shows abstract when present', async () => {
    mockGetMulti({
      '/api/v1/documents/d1/stats': mockStats,
      '/api/v1/documents/d1': mockDoc,
    });
    const router = makeRouter();
    await router.push('/library/d1');
    await router.isReady();

    const { default: LibraryDetailPage } = await import('@/pages/library/LibraryDetailPage.vue');
    const wrapper = mount(LibraryDetailPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('《针灸甲乙经》是现存最早的针灸学专著');
  });

  it('15. document card links to detail page', async () => {
    mockGet('/api/v1/documents', {
      items: [{ id: 'd1', title: '针灸甲乙经', dynasty: '晋', category: '针灸', copyright_status: 'public_domain', review_status: 'approved', rag_enabled: true, source_name: 'wikisource', withdrawn_at: null, created_at: '2025-01-01T00:00:00Z' }],
      total: 1,
    });
    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const link = wrapper.find('a[href="/library/d1"]');
    expect(link.exists()).toBe(true);
  });
});

// ------------------------------------------------------------------
// 3. Frozen pages — zero modifications check
// ------------------------------------------------------------------

describe('Frozen pages — zero regressions', () => {
  it('16. ProjectListPage still renders', async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth();
    setActivePinia(createPinia());
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: [] } });

    const router = makeRouter();
    await router.push('/research');
    await router.isReady();

    const { default: ProjectListPage } = await import('@/pages/research/ProjectListPage.vue');
    const wrapper = mount(ProjectListPage, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('研究课题');
  });

  it('17. ResearchReportsPage still renders', async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth();
    setActivePinia(createPinia());
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: { items: [], total: 0 } } });

    const router = makeRouter();
    await router.push('/reports');
    await router.isReady();

    const { default: ReportListPage } = await import('@/pages/reports/ReportListPage.vue');
    const wrapper = mount(ReportListPage, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('Reports');
  });
});