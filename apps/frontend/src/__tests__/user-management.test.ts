import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { setActivePinia, createPinia } from 'pinia';
import { createI18n } from 'vue-i18n';
import zhCN from '@/i18n/locales/zh-CN';
import UserManagementView from '@/views/admin/UserManagementView.vue';
import api from '@/api/client';

const i18n = createI18n({
  legacy: false,
  locale: 'zh-CN',
  messages: { 'zh-CN': zhCN },
});

// Mock API
vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

describe('UserManagementView (用户与权限管理)', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  const mockUsers = [
    {
      id: 'user-1',
      username: 'admin',
      email: 'admin@hfb.org',
      display_name: '系统管理员',
      affiliation: '皇甫谧数字人文课题组',
      is_active: true,
      is_superuser: true,
      roles: [{ id: 'role-1', name: 'Platform Administrator', description: '平台管理员' }],
      created_at: '2026-06-01T00:00:00Z',
    },
    {
      id: 'user-2',
      username: 'researcher1',
      email: 'res1@tcm.edu.cn',
      display_name: '张仲景研究员',
      affiliation: '北京中医药大学',
      is_active: true,
      is_superuser: false,
      roles: [{ id: 'role-2', name: 'Researcher', description: '研究人员' }],
      created_at: '2026-06-15T00:00:00Z',
    },
    {
      id: 'user-3',
      username: 'disabled_user',
      email: 'disabled@test.com',
      display_name: '已停用账户',
      affiliation: '前合作单位',
      is_active: false,
      is_superuser: false,
      roles: [{ id: 'role-3', name: 'Student', description: '学生' }],
      created_at: '2026-07-01T00:00:00Z',
    },
  ];

  const mockRoles = [
    { id: 'role-1', name: 'Platform Administrator', description: '平台管理员' },
    { id: 'role-2', name: 'Researcher', description: '研究人员' },
    { id: 'role-3', name: 'Student', description: '学生' },
    { id: 'role-4', name: 'Reviewer', description: '学术审核人' },
  ];

  it('1. 正常加载并渲染用户列表与角色徽章', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/api/v1/users') {
        return { data: { data: { items: mockUsers, total: 3 } } } as unknown as ReturnType<typeof api.get>;
      }
      if (url === '/api/v1/roles') {
        return { data: { data: mockRoles } } as unknown as ReturnType<typeof api.get>;
      }
      return { data: {} } as unknown as ReturnType<typeof api.get>;
    });

    const wrapper = mount(UserManagementView, {
      global: {
        plugins: [i18n],
      },
    });

    await flushPromises();

    expect(wrapper.text()).toContain('用户与权限管理');
    expect(wrapper.text()).toContain('admin');
    expect(wrapper.text()).toContain('researcher1');
    expect(wrapper.text()).toContain('disabled_user');
    expect(wrapper.text()).toContain('Platform Administrator');
    expect(wrapper.text()).toContain('超级管理员');
  });

  it('2. 搜索过滤功能正确筛选用户名与邮箱', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/api/v1/users') {
        return { data: { data: { items: mockUsers, total: 3 } } } as unknown as ReturnType<typeof api.get>;
      }
      if (url === '/api/v1/roles') {
        return { data: { data: mockRoles } } as unknown as ReturnType<typeof api.get>;
      }
      return { data: {} } as unknown as ReturnType<typeof api.get>;
    });

    const wrapper = mount(UserManagementView, {
      global: {
        plugins: [i18n],
      },
    });

    await flushPromises();

    const searchInput = wrapper.find('input[placeholder*="搜索用户名"]');
    await searchInput.setValue('张仲景');
    await flushPromises();

    expect(wrapper.text()).toContain('researcher1');
    expect(wrapper.text()).not.toContain('admin');
    expect(wrapper.text()).not.toContain('disabled_user');
  });

  it('3. 切换启用/禁用账户触发 PATCH 请求并更新视图', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/api/v1/users') {
        return { data: { data: { items: mockUsers, total: 3 } } } as unknown as ReturnType<typeof api.get>;
      }
      if (url === '/api/v1/roles') {
        return { data: { data: mockRoles } } as unknown as ReturnType<typeof api.get>;
      }
      return { data: {} } as unknown as ReturnType<typeof api.get>;
    });

    vi.mocked(api.patch).mockResolvedValueOnce({
      data: {
        data: {
          ...mockUsers[0],
          is_active: false,
        },
      },
    } as unknown as ReturnType<typeof api.patch>);

    const wrapper = mount(UserManagementView, {
      global: {
        plugins: [i18n],
      },
    });

    await flushPromises();

    const toggleButtons = wrapper.findAll('button[aria-label="切换用户启停状态"]');
    expect(toggleButtons.length).toBeGreaterThan(0);

    const firstBtn = toggleButtons[0];
    if (firstBtn) {
      await firstBtn.trigger('click');
      await flushPromises();

      expect(api.patch).toHaveBeenCalledWith('/api/v1/users/user-1', {
        is_active: false,
      });
    }
  });

  it('4. 打开编辑弹窗并成功提交角色变更', async () => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url === '/api/v1/users') {
        return { data: { data: { items: mockUsers, total: 3 } } } as unknown as ReturnType<typeof api.get>;
      }
      if (url === '/api/v1/roles') {
        return { data: { data: mockRoles } } as unknown as ReturnType<typeof api.get>;
      }
      return { data: {} } as unknown as ReturnType<typeof api.get>;
    });

    vi.mocked(api.patch).mockResolvedValueOnce({
      data: {
        data: {
          ...mockUsers[1],
          display_name: '张仲景（教授）',
          roles: [
            { id: 'role-2', name: 'Researcher' },
            { id: 'role-4', name: 'Reviewer' },
          ],
        },
      },
    } as unknown as ReturnType<typeof api.patch>);

    const wrapper = mount(UserManagementView, {
      attachTo: document.body,
      global: {
        plugins: [i18n],
      },
    });

    await flushPromises();

    const editButtons = wrapper.findAll('button[aria-label="编辑用户角色与详情"]');
    const secondEditBtn = editButtons[1];
    if (secondEditBtn) {
      await secondEditBtn.trigger('click');
      await flushPromises();

      // Form should exist in document body (Teleport)
      const form = document.body.querySelector('.user-mgmt__dialog-form');
      expect(form).not.toBeNull();

      // Save changes
      const saveBtn = document.body.querySelector('.user-mgmt__dialog-footer button.hfb-button--primary') as HTMLButtonElement | null;
      expect(saveBtn).not.toBeNull();
      saveBtn?.click();
      await flushPromises();

      expect(api.patch).toHaveBeenCalledWith(
        '/api/v1/users/user-2',
        expect.objectContaining({
          display_name: '张仲景研究员',
          role_ids: ['role-2'],
        })
      );
    }

    wrapper.unmount();
  });
});
