/**
 * Unit Tests for Person Intro View & Person Domain Intro Banner
 *
 * Testing PersonIntroView.vue and PersonDomainIntroBanner.vue
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';

import PersonIntroView from '@/views/PersonIntroView.vue';
import PersonDomainIntroBanner from '@/components/person/PersonDomainIntroBanner.vue';
import PersonListView from '@/views/PersonListView.vue';

// Mock API Client
const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: {
    defaults: { baseURL: '' },
    get: mockGet,
  },
}));

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/persons', component: PersonListView, name: 'persons' },
      { path: '/persons/intro', component: PersonIntroView, name: 'person-intro' },
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

describe('Person Module — PersonIntroView.vue', () => {
  const router = makeRouter();
  const i18n = makeI18n();

  beforeEach(async () => {
    vi.clearAllMocks();
    router.push('/persons/intro');
    await router.isReady();
  });

  it('renders Hero overview banner and Huangfu Mi biography text', () => {
    const wrapper = mount(PersonIntroView, {
      global: {
        plugins: [router, i18n],
      },
    });

    expect(wrapper.text()).toContain('皇甫谧学术人物网络与中医经典传播考据');
    expect(wrapper.text()).toContain('玄晏先生');
    expect(wrapper.text()).toContain('215 - 282');
    expect(wrapper.text()).toContain('《针灸甲乙经》');
    expect(wrapper.text()).toContain('耽玩典籍');
  });

  it('renders all 5 research dimension cards with category titles', () => {
    const wrapper = mount(PersonIntroView, {
      global: {
        plugins: [router, i18n],
      },
    });

    expect(wrapper.text()).toContain('皇甫谧主锚点');
    expect(wrapper.text()).toContain('魏晋师承与渊源');
    expect(wrapper.text()).toContain('魏晋交游与名士');
    expect(wrapper.text()).toContain('历代注校与辑佚');
    expect(wrapper.text()).toContain('学术传播与现代研究');

    const cardBtns = wrapper.findAll('.explore-btn');
    expect(cardBtns.length).toBe(5);
  });

  it('renders Domain Admission Standard section with N <= 3 backtrace logic and A/B/C evidence grades', () => {
    const wrapper = mount(PersonIntroView, {
      global: {
        plugins: [router, i18n],
      },
    });

    expect(wrapper.text()).toContain('学术准入与证据分级指南');
    expect(wrapper.text()).toContain('N \\le 3');
    expect(wrapper.text()).toContain('三态隔离机制');
    expect(wrapper.text()).toContain('verified 已验证');
    expect(wrapper.text()).toContain('pending 待考资料');
    expect(wrapper.text()).toContain('A 级证据');
    expect(wrapper.text()).toContain('B 级证据');
    expect(wrapper.text()).toContain('C 级证据');
  });

  it('navigates to PersonListView with role filter when clicking "探索该维度人物"', async () => {
    const pushSpy = vi.spyOn(router, 'push');

    const wrapper = mount(PersonIntroView, {
      global: {
        plugins: [router, i18n],
      },
    });

    const exploreBtns = wrapper.findAll('.explore-btn');
    expect(exploreBtns.length).toBeGreaterThan(0);

    // Click the first card: huangfu_mi_self
    const firstBtn = exploreBtns[0];
    if (!firstBtn) throw new Error('No explore button found');
    await firstBtn.trigger('click');

    expect(pushSpy).toHaveBeenCalledWith({
      path: '/persons',
      query: { role: 'huangfu_mi_self' },
    });
  });
});

describe('Person Module — PersonDomainIntroBanner.vue', () => {
  const router = makeRouter();

  beforeEach(async () => {
    vi.clearAllMocks();
    router.push('/persons');
    await router.isReady();
  });

  it('renders PersonDomainIntroBanner and triggers navigation to /persons/intro', async () => {
    const pushSpy = vi.spyOn(router, 'push');

    const wrapper = mount(PersonDomainIntroBanner, {
      global: {
        plugins: [router],
      },
    });

    expect(wrapper.text()).toContain('皇甫谧学术人物网络');
    expect(wrapper.text()).toContain('数字人文考据');

    const primaryBtn = wrapper.find('.primary-btn');
    expect(primaryBtn.exists()).toBe(true);

    await primaryBtn.trigger('click');
    expect(pushSpy).toHaveBeenCalledWith('/persons/intro');
  });

  it('opens admission standard dialog on clicking "查看准入规则"', async () => {
    const wrapper = mount(PersonDomainIntroBanner, {
      global: {
        plugins: [router],
      },
    });

    const secondaryBtn = wrapper.find('.secondary-btn');
    expect(secondaryBtn.exists()).toBe(true);

    await secondaryBtn.trigger('click');
    await flushPromises();

    // Teleport or dialog body contains standard text
    expect(document.body.innerHTML).toContain('皇甫谧研究域学术准入与证据分级标准');
    expect(document.body.innerHTML).toContain('verified 已验证');
    expect(document.body.innerHTML).toContain('A 级证据');
  });
});
