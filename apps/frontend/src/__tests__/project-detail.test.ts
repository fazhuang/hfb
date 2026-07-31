/**
 * Tests for ProjectDetailPage
 *
 * Covers:
 *  1. Load real ResearchSession via route projectId
 *  2. projectId === ResearchSession.id
 *  3. Render title correctly
 *  4. No description when missing
 *  5. created_at and updated_at displayed independently
 *  6. No status field rendered (backend has none)
 *  7. "Continue Research" links to workspace route
 *  8. Not Found for missing ID
 *  9. Page-level error on API failure
 * 10. Retry re-requests
 * 11. Empty reports state
 * 12. Empty notes state
 * 13. Empty activity state
 * 14. Report failure doesn't affect project info
 * 15. Notes failure doesn't affect project info
 * 16. Activity failure doesn't affect project info
 * 17. No technical fields rendered
 * 18. Race condition: fast switches don't overwrite
 * 19. No state write on unmount
 * 20. No independent project_id mapping
 * 21. Edit visible only with real API
 * 22. Delete visible only with real API
 * 23. Delete success navigates to /research
 * 24. 403 vs 404 distinguished
 * 25. Direct detail route access recovers data
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';
import { nextTick } from 'vue';

// ================================================================
// Mock setup
// ================================================================

const mockApiGet = vi.fn();
const mockApiPatch = vi.fn();
const mockApiDelete = vi.fn();

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: Array<unknown>) => mockApiGet(...args),
    patch: (...args: Array<unknown>) => mockApiPatch(...args),
    delete: (...args: Array<unknown>) => mockApiDelete(...args),
  },
}));

vi.mock('vue-i18n', () => ({
  useI18n: () => ({
    t: (key: string): string => key,
  }),
}));

// ================================================================
// Helpers
// ================================================================

function makeSession(overrides: Record<string, unknown> = {}) {
  return {
    id: 'session-1',
    title: 'Test Research Project',
    active_entities: null,
    context_notes: null,
    created_at: '2026-07-15T08:00:00Z',
    updated_at: '2026-07-16T10:00:00Z',
    ...overrides,
  };
}

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/research',
        name: 'research-project-list',
        component: { template: '<div>list</div>' },
      },
      {
        path: '/research/:projectId',
        name: 'research-project-detail',
        component: { template: '<div />' },
      },
    ],
  });
}

/**
 * Set up default success mocks for a happy-path project.
 * Individual tests override specific URLs to inject errors.
 */
function setupDefaultMocks(overrides: Record<string, unknown> = {}) {
  mockApiGet.mockImplementation((url: string) => {
    if (url.includes('/api/v4/research/session/') && url.includes('/history')) {
      return Promise.resolve({
        data: { data: { session_id: 'session-1', history: [], total: 0 } },
      });
    }
    if (url.includes('/api/v4/research/session/') && url.includes('/runs')) {
      return Promise.resolve({ data: { data: { session_id: 'session-1', runs: [], total: 0 } } });
    }
    if (url.includes('/api/v1/workspace/sessions/') && url.includes('/notes')) {
      return Promise.resolve({ data: { data: [] } });
    }
    if (url.startsWith('/api/v1/workspace/sessions/')) {
      return Promise.resolve({ data: { data: makeSession(overrides) } });
    }
    return Promise.reject(new Error(`Unmocked URL: ${url}`));
  });
}

async function mountPage(projectId = 'session-1', sessionOverride: Record<string, unknown> = {}) {
  const router = makeRouter();
  await router.push(`/research/${projectId}`);
  await router.isReady();

  setupDefaultMocks(sessionOverride);

  const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

  const wrapper = mount(ProjectDetailPage, {
    global: {
      plugins: [router],
      stubs: {
        ResearchPageHeader: {
          template: `
            <header>
              <h1>{{ title }}</h1>
              <p v-if="description">{{ description }}</p>
              <div class="actions"><slot name="actions" /></div>
            </header>
          `,
          props: ['title', 'description', 'breadcrumbs'],
        },
        'router-link': {
          template: '<a :href="to"><slot /></a>',
          props: ['to'],
        },
      },
    },
  });

  await flushPromises();
  await nextTick();
  return { wrapper, router };
}

// ================================================================
// Tests
// ================================================================

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // -- 1: Load real ResearchSession via route projectId --
  it('loads ResearchSession by route projectId', async () => {
    const { wrapper } = await mountPage('session-1');
    expect(mockApiGet).toHaveBeenCalledWith('/api/v1/workspace/sessions/session-1');
    expect(wrapper.text()).toContain('Test Research Project');
  });

  // -- 2: projectId equals ResearchSession.id --
  it('uses projectId as ResearchSession.id directly', async () => {
    const { wrapper } = await mountPage('session-abc-123', {
      id: 'session-abc-123',
      title: 'ABC Project',
    });
    const calls = mockApiGet.mock.calls.filter(
      (c: Array<string>) => c[0] === '/api/v1/workspace/sessions/session-abc-123',
    );
    expect(calls.length).toBeGreaterThanOrEqual(1);
    expect(wrapper.text()).toContain('ABC Project');
  });

  // -- 3: Renders project title --
  it('renders the project title', async () => {
    const { wrapper } = await mountPage('session-1', {
      title: '针灸甲乙经校注研究',
    });
    expect(wrapper.text()).toContain('针灸甲乙经校注研究');
  });

  // -- 4: No description when context_notes is missing --
  it('does not generate fake description when context_notes is null', async () => {
    const { wrapper } = await mountPage('session-1', {
      context_notes: null,
    });
    expect(wrapper.text()).not.toMatch(/description/);
  });

  // -- 5: created_at and updated_at displayed independently --
  it('shows created_at and updated_at as separate fields', async () => {
    const { wrapper } = await mountPage('session-1', {
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-07-16T00:00:00Z',
    });
    const text = wrapper.text();
    expect(text).toContain('创建时间');
    expect(text).toContain('更新时间');
    expect(text).toMatch(/2026/);
  });

  // -- 6: No status field (backend has none) --
  it('does not render a status field', async () => {
    const { wrapper } = await mountPage('session-1');
    expect(wrapper.text()).not.toMatch(/状态/);
  });

  // -- 7: Continue Research links to workspace route --
  it('"Continue Research" links to /research/:projectId/workspace', async () => {
    const { wrapper } = await mountPage('session-1');
    const links = wrapper.findAll('a');
    const workspaceLink = links.find((l) => l.text().includes('继续研究'));
    expect(workspaceLink).toBeTruthy();
    expect(workspaceLink!.attributes('href')).toBe('/research/session-1/workspace');
  });

  // -- 8: Not Found when session doesn't exist --
  it('shows Not Found state when session returns 404', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.startsWith('/api/v1/workspace/sessions/')) {
        const err: any = new Error('Not Found');
        err.response = { status: 404, data: { message: 'Session not found' } };
        return Promise.reject(err);
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const router = makeRouter();
    await router.push('/research/nonexistent');
    await router.isReady();

    const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

    const wrapper = mount(ProjectDetailPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<header><h1>{{ title }}</h1></header>',
            props: ['title'],
          },
          'router-link': { template: '<a><slot /></a>', props: ['to'] },
        },
      },
    });

    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('课题不存在');
  });

  // -- 9: Page-level error on network failure --
  it('shows page-level error on network failure', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.startsWith('/api/v1/workspace/sessions/')) {
        return Promise.reject(new Error('Network Error'));
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const router = makeRouter();
    await router.push('/research/session-1');
    await router.isReady();

    const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

    const wrapper = mount(ProjectDetailPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<header><h1>{{ title }}</h1></header>',
            props: ['title'],
          },
          'router-link': { template: '<a><slot /></a>', props: ['to'] },
        },
      },
    });

    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('加载失败');
  });

  // -- 10: Retry re-requests --
  it('retry button re-requests the session', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.startsWith('/api/v1/workspace/sessions/')) {
        return Promise.reject(new Error('Network Error'));
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const router = makeRouter();
    await router.push('/research/session-1');
    await router.isReady();

    const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

    const wrapper = mount(ProjectDetailPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<header><h1>{{ title }}</h1></header>',
            props: ['title'],
          },
          'router-link': { template: '<a><slot /></a>', props: ['to'] },
        },
      },
    });

    await flushPromises();
    await nextTick();

    mockApiGet.mockClear();
    // Reset to success for retry
    mockApiGet.mockImplementation((url: string) => {
      if (url.startsWith('/api/v1/workspace/sessions/')) {
        return Promise.resolve({ data: { data: makeSession() } });
      }
      return Promise.resolve({ data: { data: [] } });
    });

    // Find the retry button inside ErrorState
    const retryBtn = wrapper.find('.error-retry-btn');
    expect(retryBtn.exists()).toBe(true);
    await retryBtn.trigger('click');
    await flushPromises();
    await nextTick();
    expect(mockApiGet).toHaveBeenCalledWith('/api/v1/workspace/sessions/session-1');
  });

  // -- 11: Empty reports state --
  it('shows empty reports state when no runs exist', async () => {
    const { wrapper } = await mountPage('session-1');
    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('暂无报告');
  });

  // -- 12: Empty notes state --
  it('shows empty notes state when no notes exist', async () => {
    const { wrapper } = await mountPage('session-1');
    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('暂无笔记');
  });

  // -- 13: Empty activity state --
  it('shows empty activity state when no history exists', async () => {
    const { wrapper } = await mountPage('session-1');
    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('暂无研究活动');
  });

  // -- 14: Report failure doesn't affect project info --
  it('keeps project info visible when reports fail', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/runs')) {
        return Promise.reject(new Error('Report fetch failed'));
      }
      if (url.startsWith('/api/v1/workspace/sessions/')) {
        return Promise.resolve({ data: { data: makeSession() } });
      }
      if (url.includes('/history')) {
        return Promise.resolve({
          data: { data: { session_id: 'session-1', history: [], total: 0 } },
        });
      }
      if (url.includes('/notes')) {
        return Promise.resolve({ data: { data: [] } });
      }
      return Promise.reject(new Error(`Unmocked: ${url}`));
    });

    const router = makeRouter();
    await router.push('/research/session-1');
    await router.isReady();

    const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

    const wrapper = mount(ProjectDetailPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template:
              '<header><h1>{{ title }}</h1><div class="actions"><slot name="actions" /></div></header>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          'router-link': { template: '<a :href="to"><slot /></a>', props: ['to'] },
        },
      },
    });

    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('Test Research Project');
    expect(wrapper.text()).toContain('报告加载失败');
  });

  // -- 15: Notes failure doesn't affect project info --
  it('keeps project info visible when notes fail', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/notes')) {
        return Promise.reject(new Error('Notes fetch failed'));
      }
      if (url.startsWith('/api/v1/workspace/sessions/')) {
        return Promise.resolve({ data: { data: makeSession() } });
      }
      if (url.includes('/history')) {
        return Promise.resolve({
          data: { data: { session_id: 'session-1', history: [], total: 0 } },
        });
      }
      if (url.includes('/runs')) {
        return Promise.resolve({ data: { data: { session_id: 'session-1', runs: [], total: 0 } } });
      }
      return Promise.reject(new Error(`Unmocked: ${url}`));
    });

    const router = makeRouter();
    await router.push('/research/session-1');
    await router.isReady();

    const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

    const wrapper = mount(ProjectDetailPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template:
              '<header><h1>{{ title }}</h1><div class="actions"><slot name="actions" /></div></header>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          'router-link': { template: '<a :href="to"><slot /></a>', props: ['to'] },
        },
      },
    });

    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('Test Research Project');
    expect(wrapper.text()).toContain('笔记加载失败');
  });

  // -- 16: Activity failure doesn't affect project info --
  it('keeps project info visible when activity fails', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.includes('/history')) {
        return Promise.reject(new Error('Activity fetch failed'));
      }
      if (url.startsWith('/api/v1/workspace/sessions/')) {
        return Promise.resolve({ data: { data: makeSession() } });
      }
      if (url.includes('/runs')) {
        return Promise.resolve({ data: { data: { session_id: 'session-1', runs: [], total: 0 } } });
      }
      if (url.includes('/notes')) {
        return Promise.resolve({ data: { data: [] } });
      }
      return Promise.reject(new Error(`Unmocked: ${url}`));
    });

    const router = makeRouter();
    await router.push('/research/session-1');
    await router.isReady();

    const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

    const wrapper = mount(ProjectDetailPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template:
              '<header><h1>{{ title }}</h1><div class="actions"><slot name="actions" /></div></header>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          'router-link': { template: '<a :href="to"><slot /></a>', props: ['to'] },
        },
      },
    });

    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('Test Research Project');
    expect(wrapper.text()).toContain('活动加载失败');
  });

  // -- 17: No technical fields --
  it('does not render technical identifiers', async () => {
    const { wrapper } = await mountPage('session-1');
    const text = wrapper.text();
    expect(text).not.toMatch(/research_sessions/);
    expect(text).not.toMatch(/ResearchSession/);
    expect(text).not.toMatch(/active_entities/);
    expect(text).not.toMatch(/workflow_state/);
    expect(text).not.toMatch(/chat_history/);
    expect(text).not.toMatch(/UUID/);
    expect(text).not.toMatch(/project_id/);
  });

  // -- 18: Fast route switch doesn't overwrite --
  it('guards against stale responses on fast route switch', async () => {
    let resolveSlow: (v: unknown) => void = () => {};
    mockApiGet.mockImplementation((url: string) => {
      if (url === '/api/v1/workspace/sessions/session-1') {
        return new Promise((resolve) => {
          resolveSlow = resolve;
        });
      }
      if (url === '/api/v1/workspace/sessions/session-2') {
        return Promise.resolve({
          data: {
            data: makeSession({ id: 'session-2', title: 'Fast Project' }),
          },
        });
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const router = makeRouter();
    await router.push('/research/session-1');
    await router.isReady();

    const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

    const wrapper = mount(ProjectDetailPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<header><h1>{{ title }}</h1></header>',
            props: ['title'],
          },
          'router-link': { template: '<a><slot /></a>', props: ['to'] },
        },
      },
    });

    await flushPromises();

    // Switch to session-2 before session-1 resolves
    await router.push('/research/session-2');
    await flushPromises();
    await nextTick();

    // Now resolve session-1 (stale)
    resolveSlow({ data: { data: makeSession({ id: 'session-1', title: 'Stale Project' }) } });
    await flushPromises();
    await nextTick();

    // Should show session-2 title, not session-1
    expect(wrapper.text()).toContain('Fast Project');
    expect(wrapper.text()).not.toContain('Stale Project');
  });

  // -- 19: No state write on unmount --
  it('does not error on unmount during pending requests', async () => {
    const { wrapper } = await mountPage('session-1');
    wrapper.unmount();
    // No error — test passes if no crash
  });

  // -- 20: No independent project_id mapping --
  it('never references project_id', async () => {
    const { wrapper } = await mountPage('session-1');
    expect(wrapper.html()).not.toContain('project_id');
  });

  // -- 21: Edit is visible (real API exists) --
  it('shows edit option in more menu', async () => {
    const { wrapper } = await mountPage('session-1');
    const moreBtn = wrapper.find('button[aria-label="更多操作"]');
    if (moreBtn.exists()) {
      await moreBtn.trigger('click');
      await nextTick();
    }
    expect(wrapper.text()).toContain('编辑课题');
  });

  // -- 22: Delete is visible (real API exists) --
  it('shows delete option in more menu', async () => {
    const { wrapper } = await mountPage('session-1');
    const moreBtn = wrapper.find('button[aria-label="更多操作"]');
    if (moreBtn.exists()) {
      await moreBtn.trigger('click');
      await nextTick();
    }
    expect(wrapper.text()).toContain('删除课题');
  });

  // -- 23: Delete success navigates to /research --
  it('navigates to /research after successful delete', async () => {
    mockApiDelete.mockResolvedValue({ data: { data: null, message: 'Deleted' } });

    const { wrapper, router } = await mountPage('session-1');

    // Open more menu
    const moreBtn = wrapper.find('button[aria-label="更多操作"]');
    if (moreBtn.exists()) {
      await moreBtn.trigger('click');
      await nextTick();
    }

    // Find and click delete button
    const deleteBtn = wrapper.find('.pdp-more-item--danger');
    expect(deleteBtn.exists()).toBe(true);
    await deleteBtn.trigger('click');
    await nextTick();

    // Now the DeleteProjectDialog should be open
    const confirmBtn = wrapper.find('.dpd-btn--danger');
    expect(confirmBtn.exists()).toBe(true);
    await confirmBtn.trigger('click');
    await flushPromises();
    await nextTick();

    expect(mockApiDelete).toHaveBeenCalledWith('/api/v1/workspace/sessions/session-1');
    expect(router.currentRoute.value.path).toBe('/research');
  });

  // -- 24: 403 vs 404 distinguished --
  it('distinguishes 403 from 404', async () => {
    mockApiGet.mockImplementation((url: string) => {
      if (url.startsWith('/api/v1/workspace/sessions/')) {
        const err: any = new Error('Forbidden');
        err.response = { status: 403, data: { message: 'Forbidden' } };
        return Promise.reject(err);
      }
      return Promise.resolve({ data: { data: [] } });
    });

    const router = makeRouter();
    await router.push('/research/session-1');
    await router.isReady();

    const { default: ProjectDetailPage } = await import('@/pages/research/ProjectDetailPage.vue');

    const wrapper = mount(ProjectDetailPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<header><h1>{{ title }}</h1></header>',
            props: ['title'],
          },
          'router-link': { template: '<a><slot /></a>', props: ['to'] },
        },
      },
    });

    await flushPromises();
    await nextTick();
    expect(wrapper.text()).toContain('权限不足');
    expect(wrapper.text()).not.toContain('课题不存在');
  });

  // -- 25: Direct detail route access recovers data --
  it('recovers project data on direct route access', async () => {
    const { wrapper } = await mountPage('direct-access-id', {
      id: 'direct-access-id',
      title: 'Direct Access Project',
    });
    expect(wrapper.text()).toContain('Direct Access Project');
  });
});
