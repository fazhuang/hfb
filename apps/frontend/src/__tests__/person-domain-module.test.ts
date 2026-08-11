/**
 * Person Domain Module Unit Tests — Task 5.
 *
 * Covers PersonRoleBadge, AnchorPathBreadcrumb, PersonListView, PersonDetailView.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';

import PersonRoleBadge from '@/components/person/PersonRoleBadge.vue';
import AnchorPathBreadcrumb from '@/components/person/AnchorPathBreadcrumb.vue';
import PersonListView from '@/views/PersonListView.vue';
import PersonDetailView from '@/views/PersonDetailView.vue';

// ---------------------------------------------------------------------------
// Mock API Client
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
// Helpers & Test Setup
// ---------------------------------------------------------------------------
function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/persons', component: PersonListView, name: 'persons' },
      { path: '/persons/:id', component: PersonDetailView, name: 'person-detail' },
    ],
  });
}

function makeI18n() {
  return createI18n({
    legacy: false,
    locale: 'zh-CN',
    messages: {
      'zh-CN': zhCN,
    },
  });
}

describe('Person Domain Module — PersonRoleBadge.vue', () => {
  it('renders correct labels for all research relation roles', () => {
    const rolesMap: Array<{ role: string; expectedLabel: string }> = [
      { role: 'huangfu_mi_self', expectedLabel: '皇甫谧本人' },
      { role: 'master_predecessor', expectedLabel: '师承渊源' },
      { role: 'friend_contemporary', expectedLabel: '魏晋交游' },
      { role: 'annotator_editor', expectedLabel: '历代注校' },
      { role: 'transmission_scholar', expectedLabel: '学术传播' },
      { role: 'modern_researcher', expectedLabel: '现代研究' },
    ];

    for (const { role, expectedLabel } of rolesMap) {
      const wrapper = mount(PersonRoleBadge, {
        props: { role },
      });
      expect(wrapper.text()).toContain(expectedLabel);
    }
  });

  it('renders fallback for raw or custom role strings', () => {
    const wrapper = mount(PersonRoleBadge, {
      props: { role: 'custom_scholar_role' },
    });
    expect(wrapper.text()).toContain('custom_scholar_role');
  });

  it('renders nothing when role prop is null or empty', () => {
    const wrapper = mount(PersonRoleBadge, {
      props: { role: null },
    });
    expect(wrapper.find('.person-role-badge').exists()).toBe(false);
  });
});

describe('Person Domain Module — AnchorPathBreadcrumb.vue', () => {
  it('parses array of anchor path strings and formats known entities', () => {
    const wrapper = mount(AnchorPathBreadcrumb, {
      props: {
        anchorPath: ['person:huangfu_mi', 'book:zhenjiu_jiayi_jing', 'person:lin_yi'],
      },
    });

    expect(wrapper.text()).toContain('皇甫谧研究域回溯链');
    expect(wrapper.text()).toContain('[人物]');
    expect(wrapper.text()).toContain('皇甫谧');
    expect(wrapper.text()).toContain('[典籍]');
    expect(wrapper.text()).toContain('《针灸甲乙经》');
    expect(wrapper.text()).toContain('林亿');
  });

  it('parses JSON string anchor path', () => {
    const jsonStr = '["person:huangfu_mi", "book:shanghan_zabing_lun", "person:zhang_zhongjing"]';
    const wrapper = mount(AnchorPathBreadcrumb, {
      props: { anchorPath: jsonStr },
    });

    expect(wrapper.text()).toContain('皇甫谧');
    expect(wrapper.text()).toContain('《伤寒杂病论》');
    expect(wrapper.text()).toContain('张仲景');
  });

  it('renders nothing when anchorPath is empty or null', () => {
    const wrapper = mount(AnchorPathBreadcrumb, {
      props: { anchorPath: null },
    });
    expect(wrapper.find('.anchor-path-breadcrumb').exists()).toBe(false);
  });
});

describe('Person Domain Module — PersonListView.vue', () => {
  const router = makeRouter();
  const i18n = makeI18n();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('fetches person list with default domain_status=verified', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        data: {
          items: [
            {
              id: 'p-1',
              name: '皇甫谧',
              name_zh: '皇甫謐',
              dynasty: '西晋',
              domain_status: 'verified',
              research_relation_role: 'huangfu_mi_self',
              domain_relation_summary: '皇甫谧研究域核心人物，《针灸甲乙经》原作者',
              anchor_path: '["person:huangfu_mi"]',
            },
          ],
          total: 1,
        },
      },
    });

    const wrapper = mount(PersonListView, {
      global: {
        plugins: [router, i18n],
      },
    });

    await flushPromises();

    expect(mockGet).toHaveBeenCalledWith(
      '/api/v1/persons',
      expect.objectContaining({
        params: expect.objectContaining({
          domain_status: 'verified',
        }),
      }),
    );

    expect(wrapper.text()).toContain('皇甫谧');
    expect(wrapper.text()).toContain('皇甫谧本人');
    expect(wrapper.text()).toContain('已验证研究域');
    expect(wrapper.text()).toContain('皇甫谧研究域关系摘要');
    expect(wrapper.text()).toContain('《针灸甲乙经》原作者');
  });

  it('switches role filter and status filter tabs', async () => {
    mockGet.mockResolvedValue({
      data: {
        data: {
          items: [],
          total: 0,
        },
      },
    });

    const wrapper = mount(PersonListView, {
      global: {
        plugins: [router, i18n],
      },
    });

    await flushPromises();

    // Click 历代注校 filter button
    const roleBtns = wrapper.findAll('.filter-tab-btn');
    const annotatorBtn = roleBtns.find((b) => b.text().includes('历代注校'));
    expect(annotatorBtn).toBeDefined();
    await annotatorBtn!.trigger('click');
    await flushPromises();

    expect(mockGet).toHaveBeenLastCalledWith(
      '/api/v1/persons',
      expect.objectContaining({
        params: expect.objectContaining({
          research_relation_role: 'annotator_editor',
        }),
      }),
    );

    // Click 待考资料 status button
    const pendingBtn = roleBtns.find((b) => b.text().includes('待考资料'));
    expect(pendingBtn).toBeDefined();
    await pendingBtn!.trigger('click');
    await flushPromises();

    expect(mockGet).toHaveBeenLastCalledWith(
      '/api/v1/persons',
      expect.objectContaining({
        params: expect.objectContaining({
          domain_status: 'pending',
        }),
      }),
    );
  });
});

describe('Person Domain Module — PersonDetailView.vue', () => {
  const router = makeRouter();
  const i18n = makeI18n();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders detail view with PersonRoleBadge, domain_relation_summary, and backtrace chain', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        data: {
          id: 'p-lin-yi',
          name: '林亿',
          name_zh: '林億',
          dynasty: '北宋',
          birth_year: 1000,
          death_year: 1075,
          biography: '北宋掌先医官、校正医书局核心学者。',
          biography_source: '《宋史·艺文志》',
          notable_works: '校正针灸甲乙经, 新校备急千金要方',
          expertise: '医籍校勘',
          external_ref: 'https://baike.baidu.com/item/林亿',
          domain_status: 'verified',
          research_relation_role: 'annotator_editor',
          domain_relation_summary: '北宋校正医书局学者，主持校定《针灸甲乙经》并刊行于世。',
          anchor_path: '["person:huangfu_mi", "book:zhenjiu_jiayi_jing", "person:lin_yi"]',
        },
      },
    });

    router.push('/persons/p-lin-yi');
    await router.isReady();

    const wrapper = mount(PersonDetailView, {
      global: {
        plugins: [router, i18n],
      },
    });

    await flushPromises();

    expect(wrapper.text()).toContain('林亿');
    expect(wrapper.text()).toContain('历代注校');
    expect(wrapper.text()).toContain('已验证研究域');
    expect(wrapper.text()).toContain('皇甫谧研究域关系摘要');
    expect(wrapper.text()).toContain('北宋校正医书局学者');
    expect(wrapper.text()).toContain('皇甫谧研究域回溯链');
    expect(wrapper.text()).toContain('古籍证据与考据出处');
    expect(wrapper.find('.pending-alert-banner').exists()).toBe(false);
  });

  it('displays yellow "待考资料" alert when domain_status is pending', async () => {
    mockGet.mockResolvedValueOnce({
      data: {
        data: {
          id: 'p-daikao',
          name: '待考学术论者',
          dynasty: '魏晋',
          domain_status: 'pending',
          research_relation_role: 'friend_contemporary',
          domain_relation_summary: '魏晋文献记载人物，相关史料仍在进一步审核研判中。',
          anchor_path: '["person:huangfu_mi", "person:daikao_scholar"]',
        },
      },
    });

    router.push('/persons/p-daikao');
    await router.isReady();

    const wrapper = mount(PersonDetailView, {
      global: {
        plugins: [router, i18n],
      },
    });

    await flushPromises();

    expect(wrapper.find('.pending-alert-banner').exists()).toBe(true);
    expect(wrapper.text()).toContain('待考资料：');
    expect(wrapper.text()).toContain('待考学术论者');
    expect(wrapper.text()).toContain('魏晋交游');
  });
});
