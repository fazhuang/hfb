/**
 * Unit test suite for Phase 5 & Phase 6 Landing & Auth Components
 *
 * Tests:
 *   - LoginForm.vue
 *   - CuratedLandingGraph.vue
 *   - HomeView.vue
 *   - LoginView.vue
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import LoginForm from '@/components/auth/LoginForm.vue';
import CuratedLandingGraph from '@/components/graph/CuratedLandingGraph.vue';
import HomeView from '@/views/HomeView.vue';
import LoginView from '@/views/LoginView.vue';
import { useAuthStore } from '@/stores/auth';

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  messages: {
    'zh-CN': {
      system: { title: '汉方碑版与文献研究系统' },
      auth: {
        login: '登录',
        loggingIn: '登录中...',
        username: '用户名',
        password: '密码',
        usernamePlaceholder: '请输入用户名',
        passwordPlaceholder: '请输入密码',
        usernameRequired: '请输入用户名',
        passwordRequired: '请输入密码',
        loginTitle: '登录系统',
        loginSubtitle: '进入汉方典籍考据与研究工作流',
        noAccount: '还没有账号？',
        register: '免费注册',
        logout: '退出登录',
      },
      graph: { title: '考据图谱预览' },
      onboarding: {
        welcomeAnonymous: '欢迎使用',
        loginValueTitle: '系统价值',
        loginValue1: '1',
        loginValue2: '2',
        loginValue3: '3',
      },
    },
  },
});

const mockPush = vi.fn();
const mockReplace = vi.fn();

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: mockReplace,
  }),
  useRoute: () => ({
    query: {},
    params: {},
  }),
}));

describe('Phase 5 & 6 Components', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(() => null),
      setItem: vi.fn(),
      removeItem: vi.fn(),
    });
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  describe('LoginForm.vue', () => {
    it('renders input fields for username and password', () => {
      const wrapper = mount(LoginForm, {
        global: { plugins: [i18n] },
      });
      expect(wrapper.find('#login-username').exists()).toBe(true);
      expect(wrapper.find('#login-password').exists()).toBe(true);
      expect(wrapper.find('button[type="submit"]').exists()).toBe(true);
    });

    it('validates empty inputs on submit', async () => {
      const wrapper = mount(LoginForm, {
        global: { plugins: [i18n] },
      });
      await wrapper.find('form').trigger('submit.prevent');
      expect(wrapper.find('.error-message').exists()).toBe(true);
    });

    it('emits success event when auth.login succeeds', async () => {
      const wrapper = mount(LoginForm, {
        global: { plugins: [i18n] },
      });
      const auth = useAuthStore();
      vi.spyOn(auth, 'login').mockResolvedValueOnce(true);

      await wrapper.find('#login-username').setValue('testuser');
      await wrapper.find('#login-password').setValue('password123');
      await wrapper.find('form').trigger('submit.prevent');

      expect(auth.login).toHaveBeenCalledWith('testuser', 'password123');
      expect(wrapper.emitted('success')).toBeTruthy();
    });
  });

  describe('CuratedLandingGraph.vue', () => {
    it('renders SVG graph with exact 13 nodes (<= 15 nodes requirement)', () => {
      const wrapper = mount(CuratedLandingGraph, {
        global: { plugins: [i18n] },
      });
      const nodes = wrapper.findAll('.graph-node-group');
      expect(nodes.length).toBe(13);
      expect(nodes.length).toBeLessThanOrEqual(15);
    });

    it('supports keyboard focus and active node updates', async () => {
      const wrapper = mount(CuratedLandingGraph, {
        global: { plugins: [i18n] },
      });
      const firstNode = wrapper.findAll('.graph-node-group')[0];
      if (!firstNode) throw new Error('No graph node found');
      expect(firstNode.attributes('tabindex')).toBe('0');
      expect(firstNode.attributes('role')).toBe('button');

      await firstNode.trigger('focus');
      expect(wrapper.find('.graph-info-card').text()).toContain('皇甫谧');
    });

    it('renders edges between nodes', () => {
      const wrapper = mount(CuratedLandingGraph, {
        global: { plugins: [i18n] },
      });
      const edges = wrapper.findAll('.graph-edge');
      expect(edges.length).toBeGreaterThan(0);
    });
  });

  describe('HomeView.vue', () => {
    it('renders landing hero section and CuratedLandingGraph', () => {
      const wrapper = mount(HomeView, {
        global: { plugins: [i18n] },
      });
      expect(wrapper.findComponent(CuratedLandingGraph).exists()).toBe(true);
      expect(wrapper.findComponent(LoginForm).exists()).toBe(true);
    });

    it('redirects to research-project-list if user is authenticated', () => {
      const auth = useAuthStore();
      auth.user = { id: '1', username: 'admin', email: '', display_name: null, affiliation: null, is_active: true, is_superuser: false, roles: [], created_at: null, updated_at: null };
      auth.accessToken = 'fake-jwt';

      mount(HomeView, {
        global: { plugins: [i18n] },
      });

      expect(mockReplace).toHaveBeenCalledWith({ name: 'research-project-list' });
    });
  });

  describe('LoginView.vue', () => {
    it('renders login form and curated graph layout', () => {
      const wrapper = mount(LoginView, {
        global: { plugins: [i18n] },
      });
      expect(wrapper.findComponent(LoginForm).exists()).toBe(true);
      expect(wrapper.findComponent(CuratedLandingGraph).exists()).toBe(true);
      expect(wrapper.find('.login-graph-section').exists()).toBe(true);
    });
  });
});
