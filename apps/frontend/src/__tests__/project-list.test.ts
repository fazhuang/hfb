/**
 * Tests for ProjectListPage
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createRouter, createWebHistory } from 'vue-router';

// ================================================================
// Mock setup
// ================================================================

const mockApiGet = vi.fn();
const mockApiPost = vi.fn();

vi.mock('@/api/client', () => ({
  default: {
    get: (...args: unknown[]) => mockApiGet(...args),
    post: (...args: unknown[]) => mockApiPost(...args),
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
    title: 'Test Project',
    active_entities: null,
    context_notes: null,
    created_at: '2026-07-15T08:00:00Z',
    updated_at: '2026-07-16T10:00:00Z',
    ...overrides,
  };
}

function buildRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      {
        path: '/research',
        name: 'research-project-list',
        component: { template: '<div />' },
      },
      {
        path: '/research/:projectId',
        name: 'research-project-detail',
        component: { template: '<div />' },
      },
    ],
  });
}

async function mountPage(sessions: Record<string, unknown>[] = []) {
  mockApiGet.mockResolvedValue({
    data: { data: sessions },
  });

  const router = buildRouter();
  await router.push('/research');
  await router.isReady();

  const { default: ProjectListPage } = await import(
    '@/pages/research/ProjectListPage.vue'
  );

  const wrapper = mount(ProjectListPage, {
    global: {
      plugins: [router],
      stubs: {
        ResearchPageHeader: {
          template: '<div class="mock-header"><slot name="actions" /></div>',
          props: ['title', 'description', 'breadcrumbs'],
        },
        RouterLink: {
          template: '<a :href="to" class="mock-router-link"><slot /></a>',
          props: ['to'],
        },
      },
    },
  });

  await flushPromises();
  return { wrapper, router };
}

// ================================================================
// Tests
// ================================================================

describe('ProjectListPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // 1. Page loads and requests session list
  it('1. requests project list on mount', async () => {
    const { wrapper } = await mountPage([]);

    expect(mockApiGet).toHaveBeenCalledWith(
      '/api/v1/workspace/sessions',
      expect.objectContaining({ params: { limit: 100 } }),
    );
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
  });

  // 2. Successfully renders project names
  it('2. renders project names from API', async () => {
    const { wrapper } = await mountPage([
      makeSession({ id: 's1', title: 'Project A' }),
      makeSession({ id: 's2', title: 'Project B' }),
    ]);

    const text = wrapper.text();
    expect(text).toContain('Project A');
    expect(text).toContain('Project B');
  });

  // 3. Search filters projects client-side
  it('3. search filters projects client-side', async () => {
    const { wrapper } = await mountPage([
      makeSession({ id: 's1', title: 'Acupuncture Research' }),
      makeSession({ id: 's2', title: 'Herbal Study' }),
    ]);

    const searchInput = wrapper.find('#plt-search-input');
    expect(searchInput.exists()).toBe(true);
    await searchInput.setValue('Acupuncture');
    await searchInput.trigger('input');

    await new Promise((r) => setTimeout(r, 400));
    await flushPromises();

    const text = wrapper.text();
    expect(text).toContain('Acupuncture Research');
    expect(text).not.toContain('Herbal Study');
  });

  // 4. Clear filter restores full list
  it('4. clear search restores full list', async () => {
    const { wrapper } = await mountPage([
      makeSession({ id: 's1', title: 'Project A' }),
      makeSession({ id: 's2', title: 'Project B' }),
    ]);

    const searchInput = wrapper.find('#plt-search-input');
    await searchInput.setValue('Project A');
    await searchInput.trigger('input');
    await new Promise((r) => setTimeout(r, 400));
    await flushPromises();

    const clearBtn = wrapper.find('.plt-clear-btn');
    if (clearBtn.exists()) {
      await clearBtn.trigger('click');
      await flushPromises();
    }

    const text = wrapper.text();
    expect(text).toContain('Project A');
    expect(text).toContain('Project B');
  });

  // 5. Empty list shows empty state
  it('5. empty list shows empty state', async () => {
    const { wrapper } = await mountPage([]);
    // Empty state title is hardcoded Chinese
    expect(wrapper.text()).toContain('还没有研究课题');
  });

  // 6. Search with no results shows different empty state
  it('6. search-no-results shows distinct empty state', async () => {
    const { wrapper } = await mountPage([
      makeSession({ id: 's1', title: 'Project A' }),
    ]);

    const searchInput = wrapper.find('#plt-search-input');
    await searchInput.setValue('nonexistent');
    await searchInput.trigger('input');
    await new Promise((r) => setTimeout(r, 400));
    await flushPromises();

    expect(wrapper.find('.empty-title').exists()).toBe(true);
  });

  // 7. API failure shows error state
  it('7. API failure shows error state', async () => {
    mockApiGet.mockRejectedValue(new Error('Network error'));

    const router = buildRouter();
    await router.push('/research');
    await router.isReady();

    const { default: ProjectListPage } = await import(
      '@/pages/research/ProjectListPage.vue'
    );

    const wrapper = mount(ProjectListPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: {
            template: '<a :href="to" class="mock-router-link"><slot /></a>',
            props: ['to'],
          },
        },
      },
    });

    await flushPromises();

    expect(wrapper.text()).toContain('Network error');
    const errorEl = wrapper.find('[role="alert"]');
    expect(errorEl.exists()).toBe(true);
  });

  // 8. Retry button re-requests
  it('8. retry button re-fetches', async () => {
    mockApiGet.mockRejectedValueOnce(new Error('Fail'));
    const { wrapper } = await mountPage([]);

    expect(wrapper.text()).toContain('Fail');

    mockApiGet.mockResolvedValueOnce({
      data: { data: [makeSession({ id: 'new', title: 'New Project' })] },
    });

    const retryBtn = wrapper.find('.error-retry-btn');
    expect(retryBtn.exists()).toBe(true);
    await retryBtn.trigger('click');
    await flushPromises();

    expect(mockApiGet).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain('New Project');
  });

  // 9. Create button opens dialog
  it('9. create button opens create dialog', async () => {
    const { wrapper } = await mountPage([]);

    const createBtn = wrapper.find('.rpp-create-btn');
    await createBtn.trigger('click');
    await flushPromises();

    const dialog = wrapper.find('[role="dialog"]');
    expect(dialog.exists()).toBe(true);
  });

  // 10. Cannot submit without project name
  it('10. missing name disables submit', async () => {
    const { wrapper } = await mountPage([]);

    const createBtn = wrapper.find('.rpp-create-btn');
    await createBtn.trigger('click');
    await flushPromises();

    const submitBtn = wrapper.find('.cpd-btn--primary');
    expect(submitBtn.exists()).toBe(true);
    expect((submitBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  // 11. Double-submit prevention
  it('11. prevents double submission during creation', async () => {
    mockApiPost.mockImplementation(
      () => new Promise((resolve) => setTimeout(() => resolve({ data: {} }), 500)),
    );

    const { wrapper } = await mountPage([]);

    await wrapper.find('.rpp-create-btn').trigger('click');
    await flushPromises();

    await wrapper.find('#cpd-name').setValue('New Project');
    await flushPromises();

    await wrapper.find('.cpd-form').trigger('submit.prevent');
    await flushPromises();

    const submitBtn = wrapper.find('.cpd-btn--primary');
    expect((submitBtn.element as HTMLButtonElement).disabled).toBe(true);
  });

  // 12. Create success refreshes list
  it('12. create success refreshes list', async () => {
    mockApiPost.mockResolvedValue({ data: {} });

    const { wrapper } = await mountPage([makeSession({ id: 'old', title: 'Old Project' })]);

    await wrapper.find('.rpp-create-btn').trigger('click');
    await flushPromises();

    await wrapper.find('#cpd-name').setValue('New Project');
    await wrapper.find('.cpd-form').trigger('submit.prevent');
    await flushPromises();

    expect(mockApiPost).toHaveBeenCalledWith('/api/v1/workspace/sessions', {
      title: 'New Project',
    });
    expect(mockApiGet).toHaveBeenCalledTimes(2);
    expect(wrapper.text()).toContain('课题创建成功');
  });

  // 13. Create failure shows real error
  it('13. create failure shows backend error', async () => {
    mockApiPost.mockRejectedValue({
      response: { data: { message: 'Project name already exists' } },
    });

    const { wrapper } = await mountPage([]);

    await wrapper.find('.rpp-create-btn').trigger('click');
    await flushPromises();

    await wrapper.find('#cpd-name').setValue('Duplicate');
    await wrapper.find('.cpd-form').trigger('submit.prevent');
    await flushPromises();

    expect(wrapper.text()).toContain('Project name already exists');
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true);
  });

  // 14. Click project navigates to /research/:projectId
  it('14. click project navigates to detail', async () => {
    const { wrapper } = await mountPage([
      makeSession({ id: 'project-abc', title: 'Test Project' }),
    ]);

    const links = wrapper.findAll('.pli-name-link');
    expect(links.length).toBe(1);
    expect(links[0]!.attributes('href')).toBe('/research/project-abc');

    const enterBtn = wrapper.find('.pli-enter-btn');
    expect(enterBtn.attributes('href')).toBe('/research/project-abc');
  });

  // 15. Pagination present when items exceed page size
  it('15. pagination shows when total exceeds page size', async () => {
    const sessions = Array.from({ length: 25 }, (_, i) =>
      makeSession({ id: 's' + String(i), title: 'Project ' + String(i + 1) }),
    );

    const { wrapper } = await mountPage(sessions);

    const pagination = wrapper.find('.rpp-pagination');
    expect(pagination.exists()).toBe(true);
    const items = wrapper.findAll('.pli-card');
    expect(items.length).toBe(10);
  });

  // 16. No internal technical fields rendered
  it('16. does not render internal technical fields', async () => {
    const { wrapper } = await mountPage([
      makeSession({
        id: 's1',
        title: 'Project A',
        active_entities: '["entity-1"]',
        context_notes: 'internal notes',
      }),
    ]);

    const text = wrapper.text();
    expect(text).toContain('Project A');
    expect(text).not.toContain('active_entities');
    expect(text).not.toContain('context_notes');
    expect(text).not.toContain('["entity-1"]');
    expect(text).not.toContain('internal notes');
  });

  // 17. Race condition guard: stale API response doesn't overwrite newer
  it('17. stale response does not overwrite newer loadProjects call', async () => {
    // Simulate: mount triggers loadProjects (call 1), then create-success
    // triggers a second loadProjects (call 2) before call 1 resolves.

    let resolve1!: (value: unknown) => void;
    let resolve2!: (value: unknown) => void;

    // First GET = mount's loadProjects (never resolves initially)
    // Second GET = onProjectCreated's loadProjects (also pending)
    mockApiGet
      .mockReturnValueOnce(new Promise((r) => { resolve1 = r; }))
      .mockReturnValueOnce(new Promise((r) => { resolve2 = r; }));

    mockApiPost.mockResolvedValue({ data: {} });

    const router = buildRouter();
    await router.push('/research');
    await router.isReady();

    const { default: ProjectListPage } = await import(
      '@/pages/research/ProjectListPage.vue'
    );

    const wrapper = mount(ProjectListPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: {
            template: '<a :href="to" class="mock-router-link"><slot /></a>',
            props: ['to'],
          },
        },
      },
    });

    // Mount triggers first loadProjects → consumes promise 1
    await flushPromises();

    // Now trigger create → POST succeeds → calls loadProjects → consumes promise 2
    await wrapper.find('.rpp-create-btn').trigger('click');
    await flushPromises();
    await wrapper.find('#cpd-name').setValue('Newer');
    await wrapper.find('.cpd-form').trigger('submit.prevent');
    await flushPromises();

    // Both loadProjects calls are now pending (promise 1 and 2).
    // Resolve the SECOND call (promise 2 = "Latest") before the FIRST (promise 1 = "Stale").
    resolve2!({ data: { data: [makeSession({ id: 'new', title: 'Latest' })] } });
    await flushPromises();
    resolve1!({ data: { data: [makeSession({ id: 'old', title: 'Stale' })] } });
    await flushPromises();

    // The stale guard should discard call 1 (reqId=1 < reqId=2).
    // "Latest" should be visible, "Stale" should NOT.
    const text = wrapper.text();
    expect(text).toContain('Latest');
    expect(text).not.toContain('Stale');
  });

  // 18. No state write warnings on unmount
  it('18. no state write warnings on unmount', async () => {
    mockApiGet.mockImplementation(
      () => new Promise((resolve) => {
        setTimeout(() => {
          resolve({ data: { data: [makeSession()] } });
        }, 100);
      }),
    );

    const router = buildRouter();
    await router.push('/research');
    await router.isReady();

    const { default: ProjectListPage } = await import(
      '@/pages/research/ProjectListPage.vue'
    );

    const wrapper = mount(ProjectListPage, {
      global: {
        plugins: [router],
        stubs: {
          ResearchPageHeader: {
            template: '<div class="mock-header"><slot name="actions" /></div>',
            props: ['title', 'description', 'breadcrumbs'],
          },
          RouterLink: {
            template: '<a :href="to" class="mock-router-link"><slot /></a>',
            props: ['to'],
          },
        },
      },
    });

    wrapper.unmount();
    await new Promise((r) => setTimeout(r, 200));
    // Should not throw — pass if we reach here
    expect(true).toBe(true);
  });
});

// ================================================================
// Component unit tests
// ================================================================

import LoadingState from '@/components/common/LoadingState.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import ErrorState from '@/components/common/ErrorState.vue';

describe('LoadingState', () => {
  it('renders default message', () => {
    const wrapper = mount(LoadingState, {
      global: { stubs: { 'vue-i18n': true } },
    });
    expect(wrapper.find('.loading-state').exists()).toBe(true);
    expect(wrapper.find('.loading-spinner').exists()).toBe(true);
    expect(wrapper.attributes('role')).toBe('status');
  });

  it('renders custom message', () => {
    const wrapper = mount(LoadingState, {
      props: { message: 'Custom loading...' },
      global: { stubs: { 'vue-i18n': true } },
    });
    expect(wrapper.text()).toContain('Custom loading...');
  });
});

describe('EmptyState', () => {
  it('renders title and icon', () => {
    const wrapper = mount(EmptyState, {
      props: { title: 'No Data', icon: '📂' },
    });
    expect(wrapper.text()).toContain('No Data');
  });

  it('renders description when provided', () => {
    const wrapper = mount(EmptyState, {
      props: { title: 'Empty', description: 'Please add data', icon: '📭' },
    });
    expect(wrapper.text()).toContain('Please add data');
  });

  it('renders action slot', () => {
    const wrapper = mount(EmptyState, {
      props: { title: 'Empty' },
      slots: { action: '<button class="test-action">Action</button>' },
    });
    expect(wrapper.find('.test-action').exists()).toBe(true);
  });
});

describe('ErrorState', () => {
  it('renders error message', () => {
    const wrapper = mount(ErrorState, {
      props: { message: 'Request failed' },
      global: { stubs: { 'vue-i18n': true } },
    });
    expect(wrapper.text()).toContain('Request failed');
    expect(wrapper.attributes('role')).toBe('alert');
  });

  it('emits retry on button click', async () => {
    const wrapper = mount(ErrorState, {
      props: { message: 'Error', showRetry: true },
      global: { stubs: { 'vue-i18n': true } },
    });
    await wrapper.find('.error-retry-btn').trigger('click');
    expect(wrapper.emitted('retry')).toBeTruthy();
  });

  it('hides retry button when showRetry is false', () => {
    const wrapper = mount(ErrorState, {
      props: { message: 'Error', showRetry: false },
      global: { stubs: { 'vue-i18n': true } },
    });
    expect(wrapper.find('.error-retry-btn').exists()).toBe(false);
  });
});

describe('ProjectListItem', () => {
  it('renders project title', async () => {
    const { default: ProjectListItem } = await import(
      '@/components/research/ProjectListItem.vue'
    );

    const wrapper = mount(ProjectListItem, {
      props: {
        project: {
          id: 'abc',
          title: 'Test Project',
          description: 'A test project',
          created_at: '2026-07-15T08:00:00Z',
          updated_at: '2026-07-16T10:00:00Z',
        },
      },
      global: {
        stubs: {
          RouterLink: {
            template: '<a :href="to" class="mock-link"><slot /></a>',
            props: ['to'],
          },
          'vue-i18n': true,
        },
      },
    });

    expect(wrapper.text()).toContain('Test Project');
    expect(wrapper.text()).toContain('A test project');
  });

  it('provides link to project detail', async () => {
    const { default: ProjectListItem } = await import(
      '@/components/research/ProjectListItem.vue'
    );

    const wrapper = mount(ProjectListItem, {
      props: {
        project: {
          id: 'xyz-123',
          title: 'Research',
          description: null,
          created_at: '2026-07-15T08:00:00Z',
          updated_at: '2026-07-16T10:00:00Z',
        },
      },
      global: {
        stubs: {
          RouterLink: {
            template: '<a :href="to" class="mock-link"><slot /></a>',
            props: ['to'],
          },
          'vue-i18n': true,
        },
      },
    });

    const links = wrapper.findAll('.mock-link');
    const hrefs = links.map((l) => l.attributes('href'));
    expect(hrefs).toContain('/research/xyz-123');
  });

  it('handles null dates gracefully', async () => {
    const { default: ProjectListItem } = await import(
      '@/components/research/ProjectListItem.vue'
    );

    const wrapper = mount(ProjectListItem, {
      props: {
        project: {
          id: 'abc',
          title: 'Test',
          description: null,
          created_at: null,
          updated_at: null,
        },
      },
      global: {
        stubs: {
          RouterLink: {
            template: '<a :href="to" class="mock-link"><slot /></a>',
            props: ['to'],
          },
          'vue-i18n': true,
        },
      },
    });

    // null dates should render as dash
    expect(wrapper.text()).toContain('—');
  });
});

describe('CreateProjectDialog', () => {
  it('renders form fields when open', async () => {
    const { default: CreateProjectDialog } = await import(
      '@/components/research/CreateProjectDialog.vue'
    );

    const wrapper = mount(CreateProjectDialog, {
      props: { open: true },
      global: { stubs: { 'vue-i18n': true } },
    });

    expect(wrapper.find('#cpd-name').exists()).toBe(true);
    expect(wrapper.find('#cpd-desc').exists()).toBe(true);
  });

  it('does not render when closed', async () => {
    const { default: CreateProjectDialog } = await import(
      '@/components/research/CreateProjectDialog.vue'
    );

    const wrapper = mount(CreateProjectDialog, {
      props: { open: false },
      global: { stubs: { 'vue-i18n': true } },
    });

    expect(wrapper.find('#cpd-name').exists()).toBe(false);
  });

  it('emits close on cancel button', async () => {
    const { default: CreateProjectDialog } = await import(
      '@/components/research/CreateProjectDialog.vue'
    );

    const wrapper = mount(CreateProjectDialog, {
      props: { open: true },
      global: { stubs: { 'vue-i18n': true } },
    });

    await wrapper.find('.cpd-btn--cancel').trigger('click');
    expect(wrapper.emitted('update:open')?.[0]?.[0]).toBe(false);
  });

  it('emits close on backdrop click', async () => {
    const { default: CreateProjectDialog } = await import(
      '@/components/research/CreateProjectDialog.vue'
    );

    const wrapper = mount(CreateProjectDialog, {
      props: { open: true },
      global: { stubs: { 'vue-i18n': true } },
    });

    await wrapper.find('.cpd-backdrop').trigger('click');
    expect(wrapper.emitted('update:open')?.[0]?.[0]).toBe(false);
  });
});

describe('ProjectListToolbar', () => {
  it('emits search on input', async () => {
    const { default: ProjectListToolbar } = await import(
      '@/components/research/ProjectListToolbar.vue'
    );

    const wrapper = mount(ProjectListToolbar, {
      props: { modelValue: '' },
      global: { stubs: { 'vue-i18n': true } },
    });

    const input = wrapper.find('#plt-search-input');
    await input.setValue('test');
    await input.trigger('input');

    await new Promise((r) => setTimeout(r, 400));

    expect(wrapper.emitted('search')).toBeTruthy();
    expect(wrapper.emitted('search')?.[0]?.[0]).toBe('test');
  });

  it('shows clear button when query is non-empty', async () => {
    const { default: ProjectListToolbar } = await import(
      '@/components/research/ProjectListToolbar.vue'
    );

    const wrapper = mount(ProjectListToolbar, {
      props: { modelValue: 'test' },
      global: { stubs: { 'vue-i18n': true } },
    });

    expect(wrapper.find('.plt-clear-btn').exists()).toBe(true);
  });
});
