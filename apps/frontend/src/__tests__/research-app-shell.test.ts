import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';

// Mock auth store — ResearchPrimaryNav gates Administration on auth capabilities
vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    isAuthenticated: true,
    canReviewDocuments: true,
    canReadSourceAdmissions: true,
    canManageSourcePolicies: true,
    userName: 'TestUser',
  })),
}));

const i18n = createI18n({ legacy: false, locale: 'zh-CN', messages: { 'zh-CN': zhCN } });

// ================================================================
// Test 1-2: ResearchPrimaryNav — four research modules and
//            no Dashboard/Workspace/Graph in new nav
// ================================================================
import ResearchPrimaryNav from '@/components/layout/ResearchPrimaryNav.vue';

describe('ResearchPrimaryNav', () => {
  async function createMockRouteAndNavigate(section: string) {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/',
          component: { template: '<div />' },
          meta: { section },
          children: [
            { path: 'research', component: { template: '<div />' }, meta: { section: 'research' } },
            { path: 'library', component: { template: '<div />' }, meta: { section: 'library' } },
            {
              path: 'knowledge',
              component: { template: '<div />' },
              meta: { section: 'knowledge' },
            },
            { path: 'reports', component: { template: '<div />' }, meta: { section: 'reports' } },
          ],
        },
        { path: '/research', component: { template: '<div />' } },
        { path: '/library', component: { template: '<div />' } },
        { path: '/knowledge', component: { template: '<div />' } },
        { path: '/reports', component: { template: '<div />' } },
        { path: '/admin/literature-review', component: { template: '<div />' } },
      ],
    });
    await router.push('/' + section).catch(() => {});
    return router;
  }

  it('displays the four research module navigation items', async () => {
    const router = await createMockRouteAndNavigate('research');
    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: false },
    });

    const labels = wrapper.findAll('.rpn-link-label');
    const labelTexts = labels.map((el) => el.text());

    expect(labelTexts).toContain('开始研究');
    expect(labelTexts).toContain('文献中心');
    expect(labelTexts).toContain('知识图谱');
    expect(labelTexts).toContain('研究报告');
  });

  it('does NOT display Dashboard, Workspace, or V4 in the nav', async () => {
    const router = await createMockRouteAndNavigate('research');
    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: false },
    });

    const allText = wrapper.text();
    expect(allText).not.toContain('Dashboard');
    expect(allText).not.toContain('工作台');
    expect(allText).not.toContain('V4');
  });

  it('activates Research nav item when section is "research"', async () => {
    const router = await createMockRouteAndNavigate('research');
    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: false },
    });

    const activeLinks = wrapper.findAll('.rpn-link--active');
    const activeLabels = activeLinks.map((el) => el.find('.rpn-link-label')?.text() || el.text());
    expect(activeLabels.some((l) => l.includes('开始研究'))).toBe(true);
  });

  it('activates Library nav item when section is "library"', async () => {
    const router = await createMockRouteAndNavigate('library');
    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: false },
    });

    const activeLinks = wrapper.findAll('.rpn-link--active');
    const activeLabels = activeLinks.map((el) => el.find('.rpn-link-label')?.text() || el.text());
    expect(activeLabels.some((l) => l.includes('文献中心'))).toBe(true);
  });

  it('activates Knowledge nav item when section is "knowledge"', async () => {
    const router = await createMockRouteAndNavigate('knowledge');
    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: false },
    });

    const activeLinks = wrapper.findAll('.rpn-link--active');
    const activeLabels = activeLinks.map((el) => el.find('.rpn-link-label')?.text() || el.text());
    expect(activeLabels.some((l) => l.includes('知识图谱'))).toBe(true);
  });

  it('activates Reports nav item when section is "reports"', async () => {
    const router = await createMockRouteAndNavigate('reports');
    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: false },
    });

    const activeLinks = wrapper.findAll('.rpn-link--active');
    const activeLabels = activeLinks.map((el) => el.find('.rpn-link-label')?.text() || el.text());
    expect(activeLabels.some((l) => l.includes('研究报告'))).toBe(true);
  });

  it('has Administration as a gated, visually separated section', async () => {
    const router = await createMockRouteAndNavigate('research');
    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: false },
    });

    expect(wrapper.text()).toContain('后台管理');
    expect(wrapper.find('.rpn-separator').exists()).toBe(true);
  });

  it('renders collapsed state without labels', async () => {
    const router = await createMockRouteAndNavigate('research');
    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: true },
    });

    expect(wrapper.findAll('.rpn-link-label').length).toBe(7);
    expect(wrapper.findAll('.rpn-link-icon').length).toBe(7);
  });
});

// ================================================================
// Test 3: ResearchPageHeader
// ================================================================
import ResearchPageHeader from '@/components/layout/ResearchPageHeader.vue';

describe('ResearchPageHeader', () => {
  function mountWithRouter(component: any, options: Record<string, unknown> = {}) {
    const router = createRouter({
      history: createWebHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/research', component: { template: '<div />' } },
        { path: '/research/:id', component: { template: '<div />' } },
      ],
    });
    return mount(component, {
      ...options,
      global: { ...((options.global as object) || {}), plugins: [router] },
    });
  }

  it('renders the title prop correctly', () => {
    const wrapper = mountWithRouter(ResearchPageHeader, {
      props: { title: '研究工作台' },
    });

    expect(wrapper.find('.rph-title').text()).toBe('研究工作台');
  });

  it('renders the description prop when provided', () => {
    const wrapper = mountWithRouter(ResearchPageHeader, {
      props: { title: 'Test', description: 'A description of this page' },
    });

    expect(wrapper.find('.rph-description').text()).toBe('A description of this page');
  });

  it('does not render description paragraph when description is omitted', () => {
    const wrapper = mountWithRouter(ResearchPageHeader, {
      props: { title: 'Test' },
    });

    expect(wrapper.find('.rph-description').exists()).toBe(false);
  });

  it('renders breadcrumbs when provided', () => {
    const wrapper = mountWithRouter(ResearchPageHeader, {
      props: {
        title: 'Test',
        breadcrumbs: [
          { label: 'Research', to: '/research' },
          { label: 'Project', to: '/research/1' },
          { label: 'Workspace' },
        ],
      },
    });

    const crumbs = wrapper.findAll('.rph-breadcrumb-link, .rph-breadcrumb-current');
    expect(crumbs.length).toBe(3);
    expect(crumbs[0]!.text()).toBe('Research');
    expect(crumbs[2]!.text()).toBe('Workspace');
  });

  it('renders actions slot content', () => {
    const wrapper = mountWithRouter(ResearchPageHeader, {
      props: { title: 'Test' },
      slots: {
        actions: '<button class="test-action-btn">New Project</button>',
      },
    });

    const slotContent = wrapper.find('.test-action-btn');
    expect(slotContent.exists()).toBe(true);
    expect(slotContent.text()).toBe('New Project');
    expect(wrapper.find('.rph-actions').exists()).toBe(true);
  });

  it('does not render actions container when slot is empty', () => {
    const wrapper = mountWithRouter(ResearchPageHeader, {
      props: { title: 'Test' },
    });

    const actionsEl = wrapper.find('.rph-actions');
    if (actionsEl.exists()) {
      expect(actionsEl.html()).not.toContain('test-action-btn');
    }
  });
});

// ================================================================
// Test 4: Router — all research pages accessible via routes
// ================================================================
import ResearchAppLayout from '@/layouts/ResearchAppLayout.vue';
import ProjectListPage from '@/pages/research/ProjectListPage.vue';
import ProjectDetailPage from '@/pages/research/ProjectDetailPage.vue';
import ResearchWorkspacePage from '@/pages/research/ResearchWorkspacePage.vue';
import ResearchWorkflowPage from '@/pages/research/ResearchWorkflowPage.vue';
import ResearchResultPage from '@/pages/research/ResearchResultPage.vue';

describe('Research App Shell Routing', () => {
  function buildRouter() {
    return createRouter({
      history: createWebHistory(),
      routes: [
        {
          path: '/',
          component: ResearchAppLayout,
          children: [
            {
              path: 'research',
              name: 'research-project-list',
              component: ProjectListPage,
              meta: { section: 'research' },
            },
            {
              path: 'research/:projectId',
              name: 'research-project-detail',
              component: ProjectDetailPage,
              meta: { section: 'research' },
            },
            {
              path: 'research/:projectId/workspace',
              name: 'research-project-workspace',
              component: ResearchWorkspacePage,
              meta: { section: 'research' },
            },
            {
              path: 'research/:projectId/workflow',
              name: 'research-project-workflow',
              component: ResearchWorkflowPage,
              meta: { section: 'research' },
            },
            {
              path: 'research/:projectId/result/:runId',
              name: 'research-project-result',
              component: ResearchResultPage,
              meta: { section: 'research' },
            },
          ],
        },
        { path: '/library', component: { template: '<div />' } },
        { path: '/knowledge', component: { template: '<div />' } },
        { path: '/reports', component: { template: '<div />' } },
        { path: '/admin/literature-review', component: { template: '<div />' } },
      ],
    });
  }

  const pageCases = [
    { name: 'research-project-list', path: '/research', component: ProjectListPage },
    { name: 'research-project-detail', path: '/research/123', component: ProjectDetailPage },
    {
      name: 'research-project-workspace',
      path: '/research/123/workspace',
      component: ResearchWorkspacePage,
    },
    {
      name: 'research-project-workflow',
      path: '/research/123/workflow',
      component: ResearchWorkflowPage,
    },
    {
      name: 'research-project-result',
      path: '/research/123/result/run-1',
      component: ResearchResultPage,
    },
  ];

  for (const { name, path } of pageCases) {
    it(`resolves "${path}" to ${name}`, async () => {
      const router = buildRouter();
      await router.push(path);
      await router.isReady();

      const route = router.currentRoute.value;
      expect(route.name).toBe(name);
      const matched = route.matched[route.matched.length - 1];
      expect(matched).toBeDefined();

      const comp = matched!.components?.default;
      expect(comp).toBeTruthy();
    });
  }

  it('sets section meta to "research" on all research pages', async () => {
    const router = buildRouter();
    await router.push('/research/123/workflow');
    await router.isReady();

    const route = router.currentRoute.value;
    const hasSection = route.matched.some((r) => r.meta.section === 'research');
    expect(hasSection).toBe(true);
  });

  it('activates Research nav for /research/123/workflow sub-route', async () => {
    const router = buildRouter();
    await router.push({ name: 'research-project-workflow', params: { projectId: '123' } });
    await router.isReady();

    const wrapper = mount(ResearchPrimaryNav, {
      global: { plugins: [router, i18n] },
      props: { collapsed: false },
    });

    const activeLinks = wrapper.findAll('.rpn-link--active');
    const researchActive = activeLinks.some((el) => {
      const label = el.find('.rpn-link-label');
      return label.exists() && label.text() === '开始研究';
    });
    expect(researchActive).toBe(true);
  });
});
