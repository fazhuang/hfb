import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';

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

// Mock auth store
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    isAuthenticated: true,
    isAdmin: true,
    userName: 'admin',
    accessToken: 'test-token',
    user: { id: '1', username: 'admin', is_superuser: true },
    logout: vi.fn(),
  })),
}));

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  messages: { 'zh-CN': zhCN },
});

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div/>' } },
    { path: '/literature', component: { template: '<div/>' } },
    { path: '/literature/:id', component: { template: '<div/>' } },
    { path: '/admin/literature-review', component: { template: '<div/>' } },
    { path: '/admin/ingestion-tasks', component: { template: '<div/>' } },
    { path: '/admin/source-policy', component: { template: '<div/>' } },
  ],
});

function makeWrapper(component: object) {
  return mount(component, {
    global: { plugins: [i18n, router, createPinia()] },
  });
}

// ------------------------------------------------------------------
// LiteratureListView
// ------------------------------------------------------------------

describe('LiteratureListView', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { items: [], total: 0 } },
    });
    const { default: LiteratureListView } = await import('@/views/literature/LiteratureListView.vue');
    const wrapper = makeWrapper(LiteratureListView);
    expect(wrapper.text()).toContain('文献库');
  });

  it('displays fetched items in table', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: {
          items: [
            {
              id: '1', title: '针灸甲乙经', dynasty: '晋', category: '针灸',
              copyright_status: 'public_domain', review_status: 'approved',
              rag_enabled: true, source_name: 'user_upload', withdrawn_at: null, created_at: '2025-01-01T00:00:00Z',
            },
          ],
          total: 1,
        },
      },
    });
    const { default: LiteratureListView } = await import('@/views/literature/LiteratureListView.vue');
    const wrapper = makeWrapper(LiteratureListView);
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('针灸甲乙经');
  });
});

// ------------------------------------------------------------------
// LiteratureDetailView
// ------------------------------------------------------------------

describe('LiteratureDetailView', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('displays document detail fields', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: {
          id: '1', title: '伤寒论', dynasty: '汉', category: '方剂',
          copyright_status: 'public_domain', license_type: null, authorization_basis: null,
          review_status: 'approved', reviewed_by: null, reviewed_at: null,
          rag_enabled: true, content_checksum: null, source_name: 'user_upload',
          withdrawn_at: null, withdraw_reason: null,
          title_pinyin: null, title_english: null, year: null, language: 'zh',
          content_text: '太阳之为病，脉浮，头项强痛而恶寒。',
          abstract: '《伤寒论》为张仲景所著', source_url: null, page_count: null,
          created_at: '2025-01-01T00:00:00Z', updated_at: null,
        },
      },
    });
    router.push('/literature/1');
    await router.isReady();
    const { default: LiteratureDetailView } = await import('@/views/literature/LiteratureDetailView.vue');
    const wrapper = makeWrapper(LiteratureDetailView);
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('伤寒论');
    expect(wrapper.text()).toContain('太阳之为病');
  });

  it('shows admin actions for admin users', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: {
          id: '1', title: '测试文献', dynasty: null, category: null,
          copyright_status: 'unknown', license_type: null, authorization_basis: null,
          review_status: 'pending_review', reviewed_by: null, reviewed_at: null,
          rag_enabled: false, content_checksum: null, source_name: null,
          withdrawn_at: null, withdraw_reason: null,
          title_pinyin: null, title_english: null, year: null, language: 'zh',
          content_text: null, abstract: null, source_url: null, page_count: null,
          created_at: '2025-01-01T00:00:00Z', updated_at: null,
        },
      },
    });
    router.push('/literature/1');
    await router.isReady();
    const { default: LiteratureDetailView } = await import('@/views/literature/LiteratureDetailView.vue');
    const wrapper = makeWrapper(LiteratureDetailView);
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('管理操作');
    expect(wrapper.text()).toContain('提交审核');
    expect(wrapper.text()).toContain('确认撤回');
  });
});

// ------------------------------------------------------------------
// ClassicalVersionListView
// ------------------------------------------------------------------

describe('ClassicalVersionListView', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { items: [], total: 0 } },
    });
    const { default: ClassicalVersionListView } = await import('@/views/classical-versions/ClassicalVersionListView.vue');
    const wrapper = makeWrapper(ClassicalVersionListView);
    expect(wrapper.text()).toContain('古籍版本库');
  });

  it('displays version items', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: {
          items: [
            {
              id: '1', work_title: '针灸甲乙经', version_name: '明刻本',
              dynasty: '明', edition_type: '刻本', repository: '国家图书馆',
              public_domain_status: 'confirmed_public_domain', review_status: 'approved',
              created_at: '2025-01-01T00:00:00Z',
            },
          ],
          total: 1,
        },
      },
    });
    const { default: ClassicalVersionListView } = await import('@/views/classical-versions/ClassicalVersionListView.vue');
    const wrapper = makeWrapper(ClassicalVersionListView);
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('针灸甲乙经');
    expect(wrapper.text()).toContain('明刻本');
  });
});

// ------------------------------------------------------------------
// LiteratureReviewQueue
// ------------------------------------------------------------------

describe('LiteratureReviewQueue', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('renders page title with default pending filter', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { items: [], total: 0 } },
    });
    const { default: LiteratureReviewQueue } = await import('@/views/admin/LiteratureReviewQueue.vue');
    const wrapper = makeWrapper(LiteratureReviewQueue);
    expect(wrapper.text()).toContain('全文审核队列');
  });
});

// ------------------------------------------------------------------
// IngestionTasksView
// ------------------------------------------------------------------

describe('IngestionTasksView', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { items: [], total: 0 } },
    });
    const { default: IngestionTasksView } = await import('@/views/admin/IngestionTasksView.vue');
    const wrapper = makeWrapper(IngestionTasksView);
    expect(wrapper.text()).toContain('采集任务记录');
  });

  it('displays audit records', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: {
          items: [
            {
              id: '1', created_at: '2025-01-15T08:00:00Z', action: 'fulltext_ingest', status: 'success',
              source_url: null, source_name: 'crossref', copyright_status: 'open_access',
              license_type: 'CC-BY', review_status: 'approved', result_entity_type: 'document',
              result_entity_id: 'doc-1', reject_reason: null, skipped_reason: null,
              actor_id: 'user-1', details: { title: 'Test Document' },
            },
          ],
          total: 1,
        },
      },
    });
    const { default: IngestionTasksView } = await import('@/views/admin/IngestionTasksView.vue');
    const wrapper = makeWrapper(IngestionTasksView);
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('crossref');
  });
});

// ------------------------------------------------------------------
// SourcePolicyView
// ------------------------------------------------------------------

describe('SourcePolicyView', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('renders page title', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { items: [], total: 0 } },
    });
    const { default: SourcePolicyView } = await import('@/views/admin/SourcePolicyView.vue');
    const wrapper = makeWrapper(SourcePolicyView);
    expect(wrapper.text()).toContain('来源白名单管理');
  });

  it('displays source policies', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: {
        data: {
          items: [
            {
              id: '1', source_name: 'openalex', enabled: true,
              created_at: '2025-01-01T00:00:00Z', updated_at: '2025-01-01T00:00:00Z',
            },
          ],
          total: 1,
        },
      },
    });
    const { default: SourcePolicyView } = await import('@/views/admin/SourcePolicyView.vue');
    const wrapper = makeWrapper(SourcePolicyView);
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('openalex');
  });
});
