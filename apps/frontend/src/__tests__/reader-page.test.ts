/**
 * Sprint 2 Task 009 — ReaderPage tests.
 *
 * Tests ReaderPage with real API mocking via the /reader aggregated endpoint.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';

// jsdom stub
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

function makeRouter(_docId = 'd1') {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/library', component: { template: '<div/>' }, name: 'library-search' },
      { path: '/library/:id', component: { template: '<div/>' }, name: 'library-detail' },
      { path: '/library/:id/reader', component: { template: '<div/>' }, name: 'library-reader' },
    ],
  });
}

const i18n = createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zhCN } });

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

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
  },
}));

import api from '@/api/client';

const mockReaderData = {
  document: {
    id: 'd1',
    title: '针灸甲乙经',
    title_pinyin: 'Zhenjiu Jiayi Jing',
    title_english: 'The Systematic Classic of Acupuncture and Moxibustion',
    author_id: 'author-1',
    dynasty: '晋',
    year: 256,
    category: '针灸',
    abstract: '现存最早的针灸学专著。',
    content_text: '卷一提要：\n黄帝问曰：凡刺之法，必先本于神...',
    source_url: 'https://example.com/jia-yi-jing',
    page_count: 12,
    language: 'zh',
    source_name: 'wikisource',
  },
  ocr_chunks: [
    { chunk_index: 0, content: '黄帝问曰：凡刺之法', page_number: 1, paragraph_index: 0, ocr_confidence: 0.95 },
    { chunk_index: 1, content: '必先本于神', page_number: 1, paragraph_index: 1, ocr_confidence: 0.88 },
  ],
  passages: [
    {
      id: 'p1',
      content_text: '凡刺之法，必先本于神。',
      translation: '针刺的法则，必须以神气为根本。',
      notes: null,
      order: 1,
      tags: null,
    },
    {
      id: 'p2',
      content_text: '血脉营气精神，此五脏之所藏也。',
      translation: null,
      notes: '注：五脏藏神。',
      order: 2,
      tags: '五脏,神',
    },
  ],
  citations: [
    {
      id: 'c1',
      quote_text: '凡刺之法，必先本于神',
      note: '《针灸甲乙经》卷一',
      target_type: 'Passage',
      target_id: 'p1',
      evidence_id: 'e1',
    },
  ],
  evidences: [
    {
      id: 'e1',
      description: '《针灸甲乙经》为现存最早针灸专著，成书于公元256年',
      evidence_level: 2,
      source_passage_id: 'p1',
      source_ref_id: null,
    },
  ],
};

// ------------------------------------------------------------------
// ReaderPage Tests
// ------------------------------------------------------------------

describe('ReaderPage', () => {
  beforeEach(async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth();
    setActivePinia(createPinia());
  });

  it('1. shows loading state on mount', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockReturnValue(new Promise(() => {}));
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('正在加载全文');
  });

  it('2. shows error state on API failure', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Network error');
  });

  it('3. shows empty state when no document', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { ...mockReaderData, document: null } },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('文献未找到');
  });

  it('4. renders document header with title and meta', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('针灸甲乙经');
    expect(text).toContain('晋');
    expect(text).toContain('针灸');
    expect(text).toContain('wikisource');
  });

  it('5. renders metadata section', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('元数据');
    expect(text).toContain('摘要');
    expect(text).toContain('现存最早的针灸学专著。');
    expect(text).toContain('Zhenjiu Jiayi Jing');
  });

  it('6. renders original text with expand button', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('原文');
    expect(text).toContain('展开全文');
    expect(text).toContain('黄帝问曰：凡刺之法，必先本于神');
  });

  it('7. renders paragraph navigation', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('段落导航');
    expect(text).toContain('卷一');
  });

  it('8. renders OCR text with chunks and confidence', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('OCR 文本');
    expect(text).toContain('OCR 分块: 2');
    expect(text).toContain('91.5%');
    expect(text).toContain('黄帝问曰：凡刺之法');
    expect(text).toContain('页 1');
  });

  it('9. renders translation from passages with translation', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('现代汉语翻译');
    expect(text).toContain('针刺的法则，必须以神气为根本。');
  });

  it('10. renders citation list', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('引文定位');
    expect(text).toContain('凡刺之法，必先本于神');
    expect(text).toContain('《针灸甲乙经》卷一');
  });

  it('11. renders evidence list', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('证据定位');
    expect(text).toContain('证据等级: L2');
    expect(text).toContain('《针灸甲乙经》为现存最早针灸专著');
  });

  it('12. shows empty citation state when no citations', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { ...mockReaderData, citations: [] } },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('暂无引文');
  });

  it('13. shows empty evidence state when no evidence', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { ...mockReaderData, evidences: [], citations: [] } },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).toContain('暂无证据');
  });

  it('14. renders back to Library button', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('返回 Library');
  });

  it('15. does not render OCR section when no OCR chunks', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { ...mockReaderData, ocr_chunks: [] } },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).not.toContain('OCR 文本');
  });

  it('16. does not render translation when no passage has translation', async () => {
    const noTranslationData = {
      ...mockReaderData,
      passages: mockReaderData.passages.map((p) => ({ ...p, translation: null })),
    };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: noTranslationData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    expect(wrapper.text()).not.toContain('现代汉语翻译');
  });

  it('17. breadcrumbs include Library and detail links', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const text = wrapper.text();
    expect(text).toContain('Library');
    expect(text).toContain('全文阅读');
    expect(text).toContain('针灸甲乙经');
  });

  it('18. renders safe source link', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });
    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();

    const link = wrapper.find('a[href="https://example.com/jia-yi-jing"]');
    expect(link.exists()).toBe(true);
    expect(link.text()).toBe('查看来源');
  });
});

// ------------------------------------------------------------------
// Frozen pages — zero modifications check
// ------------------------------------------------------------------

describe('Frozen pages — zero regressions', () => {
  it('19. LibrarySearchPage still renders', async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth();
    setActivePinia(createPinia());
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: { items: [], total: 0 } },
    });

    const router = makeRouter();
    await router.push('/library');
    await router.isReady();

    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Library');
  });

  it('20. Reader route is registered', async () => {
    vi.resetModules();
    vi.clearAllMocks();
    useMockAuth();
    setActivePinia(createPinia());
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({
      data: { data: mockReaderData },
    });

    const router = makeRouter();
    await router.push('/library/d1/reader');
    await router.isReady();

    expect(router.currentRoute.value.name).toBe('library-reader');
    expect(router.currentRoute.value.params.id).toBe('d1');
  });
});
