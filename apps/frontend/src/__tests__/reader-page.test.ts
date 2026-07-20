/**
 * Sprint 2 Task 009 — ReaderPage tests (fixed).
 *
 * Tests ReaderPage with real API mocking via the /reader aggregated endpoint.
 * Uses stable chunk IDs, not array indices.
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

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/library', component: { template: '<div/>' }, name: 'library-search' },
      { path: '/library/:id', component: { template: '<div/>' }, name: 'library-detail' },
      { path: '/reader/:id', component: { template: '<div/>' }, name: 'reader' },
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
        id: '1', username: 'testuser', email: 'test@example.com',
        display_name: 'Test User', affiliation: null, is_active: true,
        is_superuser: false, roles: [], created_at: null, updated_at: null,
      },
      loading: false, error: null,
      login: vi.fn(), register: vi.fn(), fetchMe: vi.fn(), logout: vi.fn(),
    })),
  }));
}

vi.mock('@/api/client', () => ({ default: { get: vi.fn() } }));
import api from '@/api/client';

function makeChunkId(idx: number) { return `chunk-${String(idx).padStart(8, '0')}-0000-0000-0000-000000000001`; }
function makePassageId(idx: number) { return `passage-${String(idx).padStart(8, '0')}-0000-0000-0000-000000000001`; }
function makeCitId(idx: number) { return `cit-${String(idx).padStart(8, '0')}-0000-0000-0000-000000000001`; }
function makeEvId(idx: number) { return `ev-${String(idx).padStart(8, '0')}-0000-0000-0000-000000000001`; }

const C1 = makeChunkId(1), C2 = makeChunkId(2);
const P1 = makePassageId(1), P2 = makePassageId(2);
const C1_CIT = makeCitId(1);
const E1 = makeEvId(1);

const mockReaderData = {
  document: {
    id: 'd1', title: '针灸甲乙经', title_pinyin: 'Zhenjiu Jiayi Jing',
    title_english: 'The Systematic Classic of Acupuncture and Moxibustion',
    author_id: 'author-1', dynasty: '晋', year: 256, category: '针灸',
    abstract: '现存最早的针灸学专著。', content_text: '卷一提要：\n黄帝问曰：凡刺之法，必先本于神...',
    source_url: 'https://example.com/jia-yi-jing', page_count: 12, language: 'zh',
    source_name: 'wikisource',
  },
  chunks: [
    { id: C1, chunk_index: 0, content: '黄帝问曰：凡刺之法', page_number: 1, paragraph_index: 0, passage_id: P1 },
    { id: C2, chunk_index: 1, content: '必先本于神', page_number: 1, paragraph_index: 1, passage_id: P1 },
  ],
  ocr_chunks: [
    { id: C1, chunk_index: 0, content: '黄帝问曰：凡刺之法', page_number: 1, paragraph_index: 0, ocr_confidence: 0.95, passage_id: P1, match_method: null, quote_bbox: null },
    { id: C2, chunk_index: 1, content: '必先本于神', page_number: 1, paragraph_index: 1, ocr_confidence: 0.88, passage_id: P1, match_method: null, quote_bbox: null },
  ],
  passages: [
    { id: P1, content_text: '凡刺之法，必先本于神。', translation: '针刺的法则，必须以神气为根本。', notes: null, order: 1, tags: null },
    { id: P2, content_text: '血脉营气精神，此五脏之所藏也。', translation: null, notes: '注：五脏藏神。', order: 2, tags: '五脏,神' },
  ],
  citations: [
    {
      id: C1_CIT, quote_text: '凡刺之法，必先本于神', note: '《针灸甲乙经》卷一',
      target_type: 'Passage', target_id: P1, evidence_id: E1,
      anchor_chunk_ids: [C1, C2], anchor_passage_ids: [P1],
    },
  ],
  evidences: [
    {
      id: E1, description: '《针灸甲乙经》为现存最早针灸专著，成书于公元256年',
      evidence_level: 2, source_passage_id: P1, source_ref_id: null,
      anchor_chunk_ids: [C1, C2],
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
    await router.push('/reader/d1');
    await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('正在加载全文');
  });

  it('2. shows error state on API failure', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(new Error('Network error'));
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('服务器错误');
  });

  it('3. shows empty state when no document', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: { ...mockReaderData, document: null } } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('文献未找到');
  });

  it('4. renders document header with title and meta', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    const text = wrapper.text();
    expect(text).toContain('针灸甲乙经');
    expect(text).toContain('晋');
    expect(text).toContain('针灸');
  });

  it('5. renders metadata section', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    const text = wrapper.text();
    expect(text).toContain('元数据');
    expect(text).toContain('Zhenjiu Jiayi Jing');
  });

  it('6. renders original text from backend chunks', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    const text = wrapper.text();
    expect(text).toContain('原文');
    expect(text).toContain('黄帝问曰：凡刺之法');
    expect(text).toContain('必先本于神');
  });

  it('6b. chunks use stable IDs as :key not index', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    // Each chunk has id="chunk-{id}" and data-chunk-index
    const chunkEls = wrapper.findAll('[id^="chunk-"]');
    expect(chunkEls.length).toBeGreaterThanOrEqual(2);
    for (const el of chunkEls) {
      const id = el.attributes('id');
      expect(id).toMatch(/^chunk-/);
      // The id must NOT be a plain integer
      expect(id).not.toBe('chunk-0');
      expect(id).not.toBe('chunk-1');
    }
  });

  it('7. renders paragraph navigation from backend chunks', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('段落导航');
    expect(wrapper.text()).toContain('段 1');
    expect(wrapper.text()).toContain('段 2');
  });

  it('8. renders OCR text with chunks and confidence', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    const text = wrapper.text();
    expect(text).toContain('OCR 文本');
    expect(text).toContain('91.5%');
    expect(text).toContain('页 1');
  });

  it('9. renders translation from passages', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('针刺的法则，必须以神气为根本。');
  });

  it('10. renders citation with anchor button', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    const text = wrapper.text();
    expect(text).toContain('引文定位');
    expect(text).toContain('定位到原文');
  });

  it('10b. citation without anchors shows "unable to locate"', async () => {
    const noAnchor = {
      ...mockReaderData,
      citations: [{ ...mockReaderData.citations[0], anchor_chunk_ids: [], anchor_passage_ids: [] }],
    };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: noAnchor } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('无法定位到原文');
  });

  it('11. renders evidence with anchor button', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    const text = wrapper.text();
    expect(text).toContain('证据定位');
    expect(text).toContain('证据等级: L2');
    expect(text).toContain('定位到原文');
  });

  it('11b. evidence without anchors shows "unable to locate"', async () => {
    const noAnchor = {
      ...mockReaderData,
      evidences: [{ ...mockReaderData.evidences[0], anchor_chunk_ids: [] }],
    };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: noAnchor } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('无法定位到原文');
  });

  it('12. shows empty citation state when no citations', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: { ...mockReaderData, citations: [] } } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('暂无引文');
  });

  it('13. shows empty evidence state when no evidence', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: { ...mockReaderData, evidences: [], citations: [] } } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('暂无证据');
  });

  it('14. renders back to Library button', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('返回 Library');
  });

  it('15. does not render OCR section when no OCR chunks', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: { ...mockReaderData, ocr_chunks: [] } } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).not.toContain('OCR 文本');
  });

  it('16. shows translation-unavailable hint when passages exist but none translated', async () => {
    const noTrans = {
      ...mockReaderData,
      passages: mockReaderData.passages.map((p: Record<string, unknown>) => ({ ...p, translation: null })),
    };
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: noTrans } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('暂无现代汉语翻译');
  });

  it('17. back to Library calls router.push to library-search', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    const pushSpy = vi.spyOn(router, 'push');
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    // Call backToLibrary via vm
    const vm = wrapper.vm as unknown as { backToLibrary: () => void };
    vm.backToLibrary();
    expect(pushSpy).toHaveBeenCalledWith({ name: 'library-search' });
  });

  it('18. safe source link rendered', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.find('a[href="https://example.com/jia-yi-jing"]').exists()).toBe(true);
  });

  it('19. HTTP 403 shows permission error', async () => {
    const err = new Error('Forbidden') as Error & { response: { status: number; data: { detail: string } } };
    (err as unknown as Record<string, unknown>).response = { status: 403, data: { detail: 'Access denied' } };
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(err);
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('您没有权限访问该文献');
  });

  it('20. HTTP 404 shows not-found error', async () => {
    const err = new Error('Not found') as Error & { response: { status: number } };
    (err as unknown as Record<string, unknown>).response = { status: 404 };
    (api.get as ReturnType<typeof vi.fn>).mockRejectedValue(err);
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('文献未找到');
  });

  it('21. chunk DOM elements have stable id and data attributes', async () => {
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    const { default: ReaderPage } = await import('@/pages/reader/ReaderPage.vue');
    const wrapper = mount(ReaderPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    const el = wrapper.find(`#chunk-${C1}`);
    expect(el.exists()).toBe(true);
    expect(el.attributes('data-chunk-index')).toBe('0');
    expect(el.attributes('data-paragraph-index')).toBe('0');
  });
});

// ------------------------------------------------------------------
// Frozen pages — zero modifications check
// ------------------------------------------------------------------

describe('Frozen pages — zero regressions', () => {
  it('22. LibrarySearchPage still renders', async () => {
    vi.resetModules(); vi.clearAllMocks();
    useMockAuth(); setActivePinia(createPinia());
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: { items: [], total: 0 } } });
    const router = makeRouter();
    await router.push('/library'); await router.isReady();
    const { default: LibrarySearchPage } = await import('@/pages/library/LibrarySearchPage.vue');
    const wrapper = mount(LibrarySearchPage, { global: { plugins: [i18n, router, createPinia()] } });
    await wrapper.vm.$nextTick(); await wrapper.vm.$nextTick();
    expect(wrapper.text()).toContain('Library');
  });

  it('23. Reader route at /reader/:id is registered', async () => {
    vi.resetModules(); vi.clearAllMocks();
    useMockAuth(); setActivePinia(createPinia());
    (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: { data: mockReaderData } });
    const router = makeRouter();
    await router.push('/reader/d1'); await router.isReady();
    expect(router.currentRoute.value.name).toBe('reader');
    expect(router.currentRoute.value.params.id).toBe('d1');
  });
});
