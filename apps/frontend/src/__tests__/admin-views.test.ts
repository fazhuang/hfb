import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';

// jsdom doesn't ship matchMedia — stub it for AppNavbar/useTheme
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
      { path: '/login', component: { template: '<div/>' }, name: 'login' },
      { path: '/books', component: { template: '<div/>' }, name: 'books' },
      { path: '/literature', component: { template: '<div/>' }, name: 'literature' },
      { path: '/literature/:id', component: { template: '<div/>' }, name: 'literature-detail' },
      { path: '/classical-versions', component: { template: '<div/>' }, name: 'classical-versions' },
      { path: '/persons', component: { template: '<div/>' }, name: 'persons' },
      { path: '/graph', component: { template: '<div/>' }, name: 'graph' },
      { path: '/search', component: { template: '<div/>' }, name: 'search' },
      { path: '/about', component: { template: '<div/>' }, name: 'about' },
      { path: '/dashboard', component: { template: '<div/>' }, name: 'dashboard' },
      { path: '/research/new', component: { template: '<div/>' }, name: 'research-new' },
      { path: '/research/home', component: { template: '<div/>' }, name: 'research-home' },
      { path: '/research', component: { template: '<div/>' }, name: 'research-workflow' },
      { path: '/research/workspace', component: { template: '<div/>' }, name: 'research-workspace' },
      { path: '/v4/research-internal', component: { template: '<div/>' }, name: 'v4-research' },
      { path: '/admin/literature-review', component: { template: '<div/>' }, name: 'admin-literature-review', meta: { requiresAuth: true, requiresAdmin: true } },
      { path: '/admin/ingestion-tasks', component: { template: '<div/>' }, name: 'admin-ingestion-tasks', meta: { requiresAuth: true, requiresAdmin: true } },
      { path: '/admin/source-policy', component: { template: '<div/>' }, name: 'admin-source-policy', meta: { requiresAuth: true, requiresSuperAdmin: true } },
    ],
  });
}

const i18n = createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zhCN } });

// ------------------------------------------------------------------
// Auth store override helper
// ------------------------------------------------------------------

function useMockAuth(user: { is_superuser: boolean; roles: Array<{ name: string }> } | null) {
  const isAuthed = user !== null;
  const isSuperAdmin = user?.is_superuser ?? false;
  const ADMIN_ROLE_NAMES = new Set(['platform administrator', 'academic administrator', 'research leader', 'reviewer']);
  const hasAdminRole = user ? (isSuperAdmin || user.roles.some((r) => ADMIN_ROLE_NAMES.has(r.name.toLowerCase()))) : false;

  vi.doMock('@/stores/auth', () => ({
    useAuthStore: vi.fn(() => ({
      isAuthenticated: isAuthed,
      isAdmin: hasAdminRole,
      isSuperAdmin,
      isAdminRole: hasAdminRole,
      canReviewDocuments: hasAdminRole,
      canManageSourcePolicies: isSuperAdmin,
      userName: user ? 'TestUser' : '',
      accessToken: isAuthed ? 'token' : null,
      user: user ? {
        id: '1',
        username: 'testuser',
        email: 'test@example.com',
        display_name: 'Test User',
        affiliation: null,
        is_active: true,
        is_superuser: user.is_superuser,
        roles: user.roles.map((r, i) => ({ id: `${i}`, name: r.name, description: null })),
        created_at: null,
        updated_at: null,
      } : null,
      loading: false,
      error: null,
      login: vi.fn(),
      register: vi.fn(),
      fetchMe: vi.fn(),
      logout: vi.fn(),
    })),
  }));
}

// ------------------------------------------------------------------
// Mock API client
// ------------------------------------------------------------------

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    patch: vi.fn(),
    post: vi.fn(),
    delete: vi.fn(),
  },
}));

import api from '@/api/client';

function mockGet(data: unknown) {
  (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data } });
}

// ==================================================================
// 1. 普通用户 (Visitor)
// ==================================================================

describe('普通用户 (Visitor)', () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth({ is_superuser: false, roles: [{ name: 'Visitor' }] });
    setActivePinia(createPinia());
  });

  it('可见文献入口', async () => {
    mockGet({ items: [], total: 0 });
    const router = makeRouter();
    await router.push('/literature');
    await router.isReady();

    const { default: LiteratureListView } = await import('@/views/literature/LiteratureListView.vue');
    const wrapper = mount(LiteratureListView, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('文献库');
  });

  it('不可见全文审核、采集任务、来源白名单菜单', async () => {
    const { default: AppNavbar } = await import('@/components/layout/AppNavbar.vue');
    const router = makeRouter();
    await router.push('/');
    await router.isReady();

    const wrapper = mount(AppNavbar, { global: { plugins: [i18n, router, createPinia()] } });
    const text = wrapper.text();
    expect(text).not.toContain('全文审核');
    expect(text).not.toContain('采集任务');
    expect(text).not.toContain('来源白名单');
  });

  it('文献详情页不显示管理操作', async () => {
    mockGet({
      id: '1', title: '测试', dynasty: null, category: null,
      copyright_status: 'unknown', license_type: null, authorization_basis: null,
      review_status: 'pending_review', reviewed_by: null, reviewed_at: null,
      rag_enabled: false, content_checksum: null, source_name: null,
      withdrawn_at: null, withdraw_reason: null,
      title_pinyin: null, title_english: null, year: null, language: 'zh',
      content_text: null, abstract: null, source_url: null, page_count: null,
      created_at: null, updated_at: null,
    });
    const router = makeRouter();
    await router.push('/literature/1');
    await router.isReady();

    const { default: LiteratureDetailView } = await import('@/views/literature/LiteratureDetailView.vue');
    const wrapper = mount(LiteratureDetailView, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).not.toContain('管理操作');
    expect(wrapper.text()).not.toContain('提交审核');
    expect(wrapper.text()).not.toContain('确认撤回');
  });
});

// ==================================================================
// 2. 管理员 (Reviewer role)
// ==================================================================

describe('管理员 (Reviewer)', () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth({ is_superuser: false, roles: [{ name: 'Reviewer' }] });
    setActivePinia(createPinia());
  });

  it('可见全文审核、采集任务菜单', async () => {
    const { default: AppNavbar } = await import('@/components/layout/AppNavbar.vue');
    const router = makeRouter();
    await router.push('/');
    await router.isReady();

    const wrapper = mount(AppNavbar, { global: { plugins: [i18n, router, createPinia()] } });
    const text = wrapper.text();
    expect(text).toContain('全文审核');
    expect(text).toContain('采集任务');
  });

  it('不可见来源白名单菜单', async () => {
    const { default: AppNavbar } = await import('@/components/layout/AppNavbar.vue');
    const router = makeRouter();
    await router.push('/');
    await router.isReady();

    const wrapper = mount(AppNavbar, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).not.toContain('来源白名单');
  });

  it('文献详情页可见管理操作', async () => {
    mockGet({
      id: '1', title: '测试', dynasty: null, category: null,
      copyright_status: 'unknown', license_type: null, authorization_basis: null,
      review_status: 'pending_review', reviewed_by: null, reviewed_at: null,
      rag_enabled: false, content_checksum: null, source_name: null,
      withdrawn_at: null, withdraw_reason: null,
      title_pinyin: null, title_english: null, year: null, language: 'zh',
      content_text: null, abstract: null, source_url: null, page_count: null,
      created_at: null, updated_at: null,
    });
    const router = makeRouter();
    await router.push('/literature/1');
    await router.isReady();

    const { default: LiteratureDetailView } = await import('@/views/literature/LiteratureDetailView.vue');
    const wrapper = mount(LiteratureDetailView, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    const text = wrapper.text();
    expect(text).toContain('管理操作');
    expect(text).toContain('提交审核');
    expect(text).toContain('确认撤回');
  });
});

// ==================================================================
// 3. 超级管理员 (is_superuser = true)
// ==================================================================

describe('超级管理员 (Super Admin)', () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth({ is_superuser: true, roles: [] });
    setActivePinia(createPinia());
  });

  it('可见全文审核、采集任务、来源白名单菜单', async () => {
    const { default: AppNavbar } = await import('@/components/layout/AppNavbar.vue');
    const router = makeRouter();
    await router.push('/');
    await router.isReady();

    const wrapper = mount(AppNavbar, { global: { plugins: [i18n, router, createPinia()] } });
    const text = wrapper.text();
    expect(text).toContain('全文审核');
    expect(text).toContain('采集任务');
    expect(text).toContain('来源白名单');
  });

  it('可访问来源白名单页面', async () => {
    mockGet({ items: [], total: 0 });
    const router = makeRouter();
    await router.push('/admin/source-policy');
    await router.isReady();

    const { default: SourcePolicyView } = await import('@/views/admin/SourcePolicyView.vue');
    const wrapper = mount(SourcePolicyView, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('来源白名单管理');
  });
});

// ==================================================================
// 4. Legacy coverage — views render correctly
// ==================================================================

describe('View render smoke tests', () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth({ is_superuser: true, roles: [] });
    setActivePinia(createPinia());
  });

  it('LiteratureListView renders title', async () => {
    mockGet({ items: [], total: 0 });
    const router = makeRouter();
    await router.push('/literature');
    await router.isReady();

    const { default: LiteratureListView } = await import('@/views/literature/LiteratureListView.vue');
    const wrapper = mount(LiteratureListView, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('文献库');
  });

  it('LiteratureDetailView renders admin panel for super admin', async () => {
    mockGet({
      id: '1', title: '伤寒论', dynasty: '汉', category: '方剂',
      copyright_status: 'public_domain', license_type: null, authorization_basis: null,
      review_status: 'approved', reviewed_by: null, reviewed_at: null,
      rag_enabled: true, content_checksum: null, source_name: 'user_upload',
      withdrawn_at: null, withdraw_reason: null,
      title_pinyin: null, title_english: null, year: null, language: 'zh',
      content_text: '太阳之为病', abstract: null, source_url: null, page_count: null,
      created_at: null, updated_at: null,
    });
    const router = makeRouter();
    await router.push('/literature/1');
    await router.isReady();

    const { default: LiteratureDetailView } = await import('@/views/literature/LiteratureDetailView.vue');
    const wrapper = mount(LiteratureDetailView, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('伤寒论');
    expect(wrapper.text()).toContain('管理操作');
  });

  it('ClassicalVersionListView renders', async () => {
    mockGet({ items: [], total: 0 });
    const router = makeRouter();
    await router.push('/');
    await router.isReady();

    const { default: ClassicalVersionListView } = await import('@/views/classical-versions/ClassicalVersionListView.vue');
    const wrapper = mount(ClassicalVersionListView, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('古籍版本库');
  });

  it('LiteratureReviewQueue renders', async () => {
    mockGet({ items: [], total: 0 });
    const router = makeRouter();
    await router.push('/admin/literature-review');
    await router.isReady();

    const { default: LiteratureReviewQueue } = await import('@/views/admin/LiteratureReviewQueue.vue');
    const wrapper = mount(LiteratureReviewQueue, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('全文审核队列');
  });

  it('IngestionTasksView renders', async () => {
    mockGet({ items: [], total: 0 });
    const router = makeRouter();
    await router.push('/admin/ingestion-tasks');
    await router.isReady();

    const { default: IngestionTasksView } = await import('@/views/admin/IngestionTasksView.vue');
    const wrapper = mount(IngestionTasksView, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('采集任务记录');
  });

  it('SourcePolicyView renders', async () => {
    mockGet({ items: [], total: 0 });
    const router = makeRouter();
    await router.push('/admin/source-policy');
    await router.isReady();

    const { default: SourcePolicyView } = await import('@/views/admin/SourcePolicyView.vue');
    const wrapper = mount(SourcePolicyView, { global: { plugins: [i18n, router, createPinia()] } });
    expect(wrapper.text()).toContain('来源白名单管理');
  });
});