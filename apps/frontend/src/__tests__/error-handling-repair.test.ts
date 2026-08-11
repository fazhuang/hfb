/**
 * Error Handling Repair Unit Tests.
 *
 * Verifies that getErrorMessage, useApi composables, PersonListView, and PersonDetailView
 * correctly extract localized friendly Chinese error messages for 401 / 403 / 404 / 500 status codes,
 * provide a "前往登录" button for authentication errors, and never expose raw Axios technical error text like
 * "Request failed with status code 401".
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';

import { getErrorMessage } from '@/api/client';
import { useEntityList, useEntityDetail } from '@/composables/useApi';
import PersonListView from '@/views/PersonListView.vue';
import PersonDetailView from '@/views/PersonDetailView.vue';

// ---------------------------------------------------------------------------
// Mock API Client
// ---------------------------------------------------------------------------
const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<any>();
  return {
    ...actual,
    default: {
      defaults: { baseURL: '' },
      get: mockGet,
    },
  };
});

// ---------------------------------------------------------------------------
// Helpers & Test Setup
// ---------------------------------------------------------------------------
function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div/>' }, name: 'home' },
      { path: '/login', component: { template: '<div>Login Page</div>' }, name: 'login' },
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

describe('Error Handling Repair — getErrorMessage', () => {
  it('maps HTTP 401 to friendly Chinese notice', () => {
    const error401 = {
      response: {
        status: 401,
        data: { message: 'Unauthorized' },
      },
    };
    expect(getErrorMessage(error401)).toBe('未登录或登录会话已过期，请登录后继续');
  });

  it('maps HTTP 403 to friendly Chinese notice', () => {
    const error403 = {
      response: {
        status: 403,
        data: { detail: 'Forbidden' },
      },
    };
    expect(getErrorMessage(error403)).toBe('暂无权限访问该学术资源');
  });

  it('maps HTTP 404 to friendly Chinese notice', () => {
    const error404 = {
      response: {
        status: 404,
        data: {},
      },
    };
    expect(getErrorMessage(error404)).toBe('未找到相关的学术数据');
  });

  it('maps HTTP >= 500 to server error notice', () => {
    const error500 = {
      response: {
        status: 500,
        data: { message: 'Internal Server Error' },
      },
    };
    expect(getErrorMessage(error500)).toBe('服务器响应异常，请稍后重试');
  });

  it('reads response.data.message / response.data.detail for other non-auth error codes', () => {
    const error400 = {
      response: {
        status: 400,
        data: { message: '请求参数格式非法' },
      },
    };
    expect(getErrorMessage(error400)).toBe('请求参数格式非法');

    const error422 = {
      response: {
        status: 422,
        data: { detail: '字段校验未通过' },
      },
    };
    expect(getErrorMessage(error422)).toBe('字段校验未通过');
  });

  it('prevents exposing raw "Request failed with status code 401" Error text', () => {
    const rawAxiosError = new Error('Request failed with status code 401');
    const msg = getErrorMessage(rawAxiosError);
    expect(msg).toBe('未登录或登录会话已过期，请登录后继续');
    expect(msg).not.toContain('Request failed with status code 401');
  });

  it('prevents exposing generic raw Axios Error text for other status codes', () => {
    const rawAxiosError = new Error('Request failed with status code 400');
    const msg = getErrorMessage(rawAxiosError, '自定义兜底错误');
    expect(msg).toBe('自定义兜底错误');
    expect(msg).not.toContain('Request failed with status code 400');
  });
});

describe('Error Handling Repair — Composables (useEntityList & useEntityDetail)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('useEntityList populates error with friendly message on 401', async () => {
    mockGet.mockRejectedValueOnce({
      response: { status: 401 },
    });

    const { items, error, fetch } = useEntityList('/api/v1/test-list');
    await fetch();

    expect(items.value).toEqual([]);
    expect(error.value).toBe('未登录或登录会话已过期，请登录后继续');
  });

  it('useEntityDetail populates error with friendly message on 401', async () => {
    mockGet.mockRejectedValueOnce({
      response: { status: 401 },
    });

    const { entity, error, fetch } = useEntityDetail((id) => `/api/v1/test/${id}`);
    await fetch('123');

    expect(entity.value).toBeNull();
    expect(error.value).toBe('未登录或登录会话已过期，请登录后继续');
  });
});

describe('Error Handling Repair — Views (PersonListView & PersonDetailView)', () => {
  const router = makeRouter();
  const i18n = makeI18n();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('PersonListView renders friendly 401 error and login button, clicking navigates to /login', async () => {
    mockGet.mockRejectedValueOnce({
      response: { status: 401 },
    });

    router.push('/persons');
    await router.isReady();

    const wrapper = mount(PersonListView, {
      global: {
        plugins: [router, i18n],
      },
    });

    await flushPromises();

    expect(wrapper.find('.error-state').exists()).toBe(true);
    expect(wrapper.text()).toContain('未登录或登录会话已过期，请登录后继续');
    expect(wrapper.text()).not.toContain('Request failed with status code 401');

    const loginBtn = wrapper.find('.login-redirect-btn');
    expect(loginBtn.exists()).toBe(true);
    expect(loginBtn.text()).toContain('前往登录');

    await loginBtn.trigger('click');
    await flushPromises();

    expect(router.currentRoute.value.name).toBe('login');
    expect(router.currentRoute.value.query.redirect).toBe('/persons');
  });

  it('PersonDetailView renders friendly 401 error and login button', async () => {
    mockGet.mockRejectedValueOnce({
      response: { status: 401 },
    });

    router.push('/persons/p-test-id');
    await router.isReady();

    const wrapper = mount(PersonDetailView, {
      global: {
        plugins: [router, i18n],
      },
    });

    await flushPromises();

    expect(wrapper.find('.error-state').exists()).toBe(true);
    expect(wrapper.text()).toContain('未登录或登录会话已过期，请登录后继续');
    expect(wrapper.text()).not.toContain('Request failed with status code 401');

    const loginBtn = wrapper.find('.login-redirect-btn');
    expect(loginBtn.exists()).toBe(true);
    expect(loginBtn.text()).toContain('前往登录');

    await loginBtn.trigger('click');
    await flushPromises();

    expect(router.currentRoute.value.name).toBe('login');
  });
});
