<template>
  <div class="user-mgmt">
    <!-- Header -->
    <div class="user-mgmt__header">
      <div>
        <h1 class="user-mgmt__title">用户与权限管理</h1>
        <p class="user-mgmt__subtitle">
          管理系统注册用户、分配学术与管理角色、控制超级管理员与账户启停状态。
        </p>
      </div>
      <HfbButton
        variant="secondary"
        size="sm"
        :loading="loading"
        @click="fetchData"
      >
        <HfbIcon icon="settings" :size="14" />
        <span>刷新列表</span>
      </HfbButton>
    </div>

    <!-- Feedback Message -->
    <HfbAlert
      v-if="actionMsg"
      :variant="actionMsgOk ? 'success' : 'error'"
      closable
      class="user-mgmt__alert"
      @close="actionMsg = ''"
    >
      {{ actionMsg }}
    </HfbAlert>

    <!-- Filters -->
    <div class="user-mgmt__filters">
      <div class="user-mgmt__search">
        <HfbInput
          v-model="searchQuery"
          placeholder="搜索用户名、姓名、邮箱或机构..."
          aria-label="搜索用户"
          clearable
        >
          <template #prefix>
            <HfbIcon icon="search" :size="16" class="user-mgmt__search-icon" />
          </template>
        </HfbInput>
      </div>

      <div class="user-mgmt__selects">
        <HfbSelect
          v-model="roleFilter"
          :options="roleFilterOptions"
          aria-label="按角色筛选"
          class="user-mgmt__filter-select"
        />

        <HfbSelect
          v-model="statusFilter"
          :options="statusFilterOptions"
          aria-label="按状态筛选"
          class="user-mgmt__filter-select"
        />
      </div>
    </div>

    <!-- Loading / Error / Empty / Table States -->
    <LoadingState v-if="loading && users.length === 0" text="正在加载用户列表..." />

    <ErrorState
      v-else-if="error && users.length === 0"
      :message="error"
      @retry="fetchData"
    />

    <EmptyState
      v-else-if="filteredUsers.length === 0"
      icon="users"
      title="未找到匹配用户"
      description="请尝试调整筛选条件或搜索关键词。"
    />

    <div v-else class="user-mgmt__table-wrapper">
      <table class="user-mgmt__table">
        <thead>
          <tr>
            <th>用户账号</th>
            <th>姓名 / 机构</th>
            <th>邮箱</th>
            <th>所属角色</th>
            <th>特权身份</th>
            <th>状态</th>
            <th>注册时间</th>
            <th class="user-mgmt__th-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="u in filteredUsers"
            :key="u.id"
            class="user-mgmt__tr"
            :class="{ 'user-mgmt__tr--disabled': !u.is_active }"
          >
            <!-- Username -->
            <td>
              <div class="user-mgmt__user-cell">
                <span class="user-mgmt__avatar">{{ userInitial(u) }}</span>
                <span class="user-mgmt__username font-semibold">{{ u.username }}</span>
              </div>
            </td>

            <!-- Display Name & Affiliation -->
            <td>
              <div class="user-mgmt__name-cell">
                <div class="user-mgmt__display-name">{{ u.display_name || '—' }}</div>
                <div v-if="u.affiliation" class="user-mgmt__affiliation text-xs">
                  {{ u.affiliation }}
                </div>
              </div>
            </td>

            <!-- Email -->
            <td>
              <span class="user-mgmt__email">{{ u.email || '—' }}</span>
            </td>

            <!-- Roles -->
            <td>
              <div class="user-mgmt__roles-cell">
                <template v-if="u.roles && u.roles.length > 0">
                  <HfbBadge
                    v-for="r in u.roles"
                    :key="r.id"
                    :variant="getRoleBadgeVariant(r.name)"
                    size="sm"
                  >
                    {{ r.name }}
                  </HfbBadge>
                </template>
                <span v-else class="text-xs text-muted">未分配角色</span>
              </div>
            </td>

            <!-- Super Admin Badge -->
            <td>
              <HfbBadge
                v-if="u.is_superuser"
                variant="warning"
                size="sm"
                class="user-mgmt__super-badge"
              >
                <HfbIcon icon="shield" :size="12" />
                <span>超级管理员</span>
              </HfbBadge>
              <span v-else class="text-xs text-muted">标准用户</span>
            </td>

            <!-- Status -->
            <td>
              <HfbBadge
                :variant="u.is_active ? 'success' : 'neutral'"
                dot
                size="sm"
              >
                {{ u.is_active ? '正常' : '已禁用' }}
              </HfbBadge>
            </td>

            <!-- Created At -->
            <td>
              <span class="text-xs text-secondary">
                {{ formatDateTime(u.created_at) }}
              </span>
            </td>

            <!-- Actions -->
            <td>
              <div class="user-mgmt__actions-cell">
                <HfbButton
                  variant="ghost"
                  size="sm"
                  aria-label="编辑用户角色与详情"
                  @click="openEditDialog(u)"
                >
                  <HfbIcon icon="pen-line" :size="14" />
                  <span>编辑</span>
                </HfbButton>

                <HfbButton
                  v-if="u.id !== auth.user?.id"
                  variant="ghost"
                  size="sm"
                  :class="u.is_active ? 'text-danger' : 'text-success'"
                  aria-label="切换用户启停状态"
                  @click="toggleUserActive(u)"
                >
                  <HfbIcon :icon="u.is_active ? 'x' : 'check'" :size="14" />
                  <span>{{ u.is_active ? '禁用' : '启用' }}</span>
                </HfbButton>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Edit User Dialog -->
    <HfbDialog
      v-model:open="editDialogOpen"
      :title="`编辑用户 - ${editingUser?.username ?? ''}`"
      description="分配学术与系统角色，调整账户权限与基本信息。"
      size="md"
    >
      <form v-if="editingUser" class="user-mgmt__dialog-form" @submit.prevent="saveUserChanges">
        <!-- Display Name -->
        <div class="user-mgmt__form-group">
          <label for="edit-display-name" class="user-mgmt__label">真实姓名 / 显示名称</label>
          <HfbInput
            id="edit-display-name"
            v-model="editForm.displayName"
            placeholder="如：李时珍"
          />
        </div>

        <!-- Affiliation -->
        <div class="user-mgmt__form-group">
          <label for="edit-affiliation" class="user-mgmt__label">所属机构 / 课题组</label>
          <HfbInput
            id="edit-affiliation"
            v-model="editForm.affiliation"
            placeholder="如：北京中医药大学 / 古籍文献研究所"
          />
        </div>

        <!-- Email -->
        <div class="user-mgmt__form-group">
          <label for="edit-email" class="user-mgmt__label">联系邮箱</label>
          <HfbInput
            id="edit-email"
            v-model="editForm.email"
            type="email"
            placeholder="user@example.com"
          />
        </div>

        <!-- Role Assignment -->
        <div class="user-mgmt__form-group">
          <label class="user-mgmt__label">分配平台角色 (可多选)</label>
          <div class="user-mgmt__roles-checkboxes">
            <label
              v-for="role in allRoles"
              :key="role.id"
              class="user-mgmt__role-checkbox-item"
            >
              <input
                type="checkbox"
                :value="role.id"
                :checked="editForm.roleIds.includes(role.id)"
                @change="toggleRoleSelection(role.id)"
              />
              <div class="user-mgmt__role-desc">
                <span class="user-mgmt__role-name font-medium">{{ role.name }}</span>
                <span v-if="role.description" class="user-mgmt__role-info text-xs text-muted">
                  {{ role.description }}
                </span>
              </div>
            </label>
          </div>
        </div>

        <!-- Super Admin Privileges -->
        <div class="user-mgmt__form-group user-mgmt__privilege-box">
          <label class="user-mgmt__checkbox-label">
            <input
              type="checkbox"
              v-model="editForm.isSuperuser"
              :disabled="!auth.isSuperAdmin"
            />
            <span class="font-semibold">超级管理员身份 (is_superuser)</span>
          </label>
          <p class="text-xs text-muted user-mgmt__privilege-hint">
            <template v-if="auth.isSuperAdmin">
              授予该用户全系统 RBAC Bypass 特权、来源策略管理与最高系统控制权。
            </template>
            <template v-else>
              ⚠️ 仅当前以超级管理员身份登录时才可调整此标志。
            </template>
          </p>
        </div>

        <!-- Active Status -->
        <div class="user-mgmt__form-group">
          <label class="user-mgmt__checkbox-label">
            <input
              type="checkbox"
              v-model="editForm.isActive"
              :disabled="editingUser.id === auth.user?.id"
            />
            <span>允许登录与访问 (账户正常启用)</span>
          </label>
          <p v-if="editingUser.id === auth.user?.id" class="text-xs text-muted">
            不可禁用当前登录的自身账户。
          </p>
        </div>
      </form>

      <template #footer>
        <div class="user-mgmt__dialog-footer">
          <HfbButton
            variant="secondary"
            size="sm"
            @click="editDialogOpen = false"
          >
            取消
          </HfbButton>
          <HfbButton
            variant="primary"
            size="sm"
            :loading="saveLoading"
            @click="saveUserChanges"
          >
            保存变更
          </HfbButton>
        </div>
      </template>
    </HfbDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue';
import api from '@/api/client';
import { useAuthStore, type UserBrief, type RoleBrief } from '@/stores/auth';
import HfbButton from '@/components/common/HfbButton.vue';
import HfbInput from '@/components/common/HfbInput.vue';
import HfbSelect from '@/components/common/HfbSelect.vue';
import HfbBadge from '@/components/common/HfbBadge.vue';
import HfbDialog from '@/components/common/HfbDialog.vue';
import HfbAlert from '@/components/common/HfbAlert.vue';
import HfbIcon from '@/components/common/HfbIcon.vue';
import LoadingState from '@/components/common/LoadingState.vue';
import ErrorState from '@/components/common/ErrorState.vue';
import EmptyState from '@/components/common/EmptyState.vue';

const auth = useAuthStore();

// State
const users = ref<Array<UserBrief>>([]);
const allRoles = ref<Array<RoleBrief>>([]);
const loading = ref(false);
const saveLoading = ref(false);
const error = ref<string | null>(null);
const actionMsg = ref('');
const actionMsgOk = ref(true);

// Filters
const searchQuery = ref('');
const roleFilter = ref('all');
const statusFilter = ref('all');

// Dialog State
const editDialogOpen = ref(false);
const editingUser = ref<UserBrief | null>(null);

const editForm = reactive({
  displayName: '',
  affiliation: '',
  email: '',
  isActive: true,
  isSuperuser: false,
  roleIds: [] as Array<string>,
});

// Filter Options
const roleFilterOptions = computed(() => {
  const options = [{ label: '全部角色', value: 'all' }];
  for (const r of allRoles.value) {
    options.push({ label: r.name, value: r.name });
  }
  return options;
});

const statusFilterOptions = [
  { label: '全部状态', value: 'all' },
  { label: '仅正常启用', value: 'active' },
  { label: '仅已禁用', value: 'disabled' },
  { label: '仅超级管理员', value: 'superuser' },
];

// Computed Filtered List
const filteredUsers = computed(() => {
  return users.value.filter((u) => {
    // Search keyword
    if (searchQuery.value.trim()) {
      const q = searchQuery.value.trim().toLowerCase();
      const matchUsername = u.username.toLowerCase().includes(q);
      const matchName = (u.display_name || '').toLowerCase().includes(q);
      const matchEmail = (u.email || '').toLowerCase().includes(q);
      const matchAffiliation = (u.affiliation || '').toLowerCase().includes(q);
      if (!matchUsername && !matchName && !matchEmail && !matchAffiliation) {
        return false;
      }
    }

    // Role filter
    if (roleFilter.value !== 'all') {
      const userRoleNames = (u.roles || []).map((r) => r.name.toLowerCase());
      if (!userRoleNames.includes(roleFilter.value.toLowerCase())) {
        return false;
      }
    }

    // Status filter
    if (statusFilter.value === 'active' && !u.is_active) return false;
    if (statusFilter.value === 'disabled' && u.is_active) return false;
    if (statusFilter.value === 'superuser' && !u.is_superuser) return false;

    return true;
  });
});

// Methods
async function fetchData() {
  loading.value = true;
  error.value = null;
  try {
    const [usersRes, rolesRes] = await Promise.all([
      api.get('/api/v1/users', { params: { limit: 100 } }),
      api.get('/api/v1/roles'),
    ]);

    const usersData = usersRes.data.data ?? usersRes.data;
    users.value = usersData.items || [];

    const rolesData = rolesRes.data.data ?? rolesRes.data;
    allRoles.value = rolesData || [];
  } catch (e: unknown) {
    error.value =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      (e as Error).message ??
      '获取用户列表失败';
  } finally {
    loading.value = false;
  }
}

function userInitial(u: UserBrief): string {
  const name = u.display_name || u.username;
  return name ? name.charAt(0).toUpperCase() : '?';
}

function getRoleBadgeVariant(roleName: string): 'info' | 'success' | 'warning' | 'neutral' {
  const norm = roleName.toLowerCase();
  if (norm.includes('platform administrator')) return 'warning';
  if (norm.includes('academic administrator')) return 'info';
  if (norm.includes('research leader')) return 'warning';
  if (norm.includes('reviewer')) return 'success';
  return 'neutral';
}

function formatDateTime(isoStr: string | null | undefined): string {
  if (!isoStr) return '—';
  try {
    const d = new Date(isoStr);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  } catch {
    return '—';
  }
}

function openEditDialog(user: UserBrief) {
  editingUser.value = user;
  editForm.displayName = user.display_name || '';
  editForm.affiliation = user.affiliation || '';
  editForm.email = user.email || '';
  editForm.isActive = user.is_active;
  editForm.isSuperuser = user.is_superuser ?? false;
  editForm.roleIds = (user.roles || []).map((r) => r.id);
  editDialogOpen.value = true;
}

function toggleRoleSelection(roleId: string) {
  const idx = editForm.roleIds.indexOf(roleId);
  if (idx > -1) {
    editForm.roleIds.splice(idx, 1);
  } else {
    editForm.roleIds.push(roleId);
  }
}

async function saveUserChanges() {
  if (!editingUser.value) return;
  saveLoading.value = true;
  actionMsg.value = '';

  try {
    const payload: Record<string, unknown> = {
      display_name: editForm.displayName.trim() || null,
      affiliation: editForm.affiliation.trim() || null,
      email: editForm.email.trim() || undefined,
      is_active: editForm.isActive,
      role_ids: editForm.roleIds,
    };

    if (auth.isSuperAdmin) {
      payload.is_superuser = editForm.isSuperuser;
    }

    const { data } = await api.patch(`/api/v1/users/${editingUser.value.id}`, payload);
    const updated = data.data ?? data;

    // Update in local state
    const idx = users.value.findIndex((u) => u.id === editingUser.value?.id);
    if (idx > -1) {
      users.value[idx] = {
        ...users.value[idx],
        ...updated,
      };
    }

    actionMsgOk.value = true;
    actionMsg.value = `用户 ${editingUser.value.username} 权限与信息已成功更新`;
    editDialogOpen.value = false;
  } catch (e: unknown) {
    actionMsgOk.value = false;
    actionMsg.value =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      (e as Error).message ??
      '更新用户失败';
  } finally {
    saveLoading.value = false;
  }
}

async function toggleUserActive(user: UserBrief) {
  const nextState = !user.is_active;
  const actionText = nextState ? '启用' : '禁用';

  try {
    const { data } = await api.patch(`/api/v1/users/${user.id}`, {
      is_active: nextState,
    });
    const updated = data.data ?? data;
    user.is_active = updated.is_active;

    actionMsgOk.value = true;
    actionMsg.value = `用户 ${user.username} 已成功${actionText}`;
  } catch (e: unknown) {
    actionMsgOk.value = false;
    actionMsg.value =
      (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
      (e as Error).message ??
      `${actionText}用户失败`;
  }
}

onMounted(() => {
  fetchData();
});
</script>

<style scoped>
.user-mgmt {
  padding: var(--space-6);
  max-width: 1300px;
  margin: 0 auto;
}

.user-mgmt__header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--space-6);
}

.user-mgmt__title {
  font-size: var(--text-2xl);
  font-weight: var(--font-bold);
  color: var(--color-text-primary);
  margin: 0 0 var(--space-1) 0;
}

.user-mgmt__subtitle {
  font-size: var(--text-sm);
  color: var(--color-text-secondary);
  margin: 0;
}

.user-mgmt__alert {
  margin-bottom: var(--space-4);
}

.user-mgmt__filters {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
  flex-wrap: wrap;
  align-items: center;
}

.user-mgmt__search {
  flex: 1;
  min-width: 260px;
}

.user-mgmt__search-icon {
  color: var(--color-text-muted);
}

.user-mgmt__selects {
  display: flex;
  gap: var(--space-3);
}

.user-mgmt__filter-select {
  min-width: 140px;
}

.user-mgmt__table-wrapper {
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  overflow-x: auto;
  box-shadow: var(--shadow-sm);
}

.user-mgmt__table {
  width: 100%;
  border-collapse: collapse;
  text-align: left;
  font-size: var(--text-sm);
}

.user-mgmt__table th {
  background: var(--color-bg-sunken);
  color: var(--color-text-secondary);
  padding: var(--space-3) var(--space-4);
  font-weight: var(--font-semibold);
  border-bottom: 1px solid var(--color-border);
  white-space: nowrap;
}

.user-mgmt__table td {
  padding: var(--space-3) var(--space-4);
  border-bottom: 1px solid var(--color-border);
  color: var(--color-text-primary);
  vertical-align: middle;
}

.user-mgmt__tr:hover td {
  background: var(--color-bg-hover);
}

.user-mgmt__tr--disabled td {
  opacity: 0.6;
}

.user-mgmt__user-cell {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.user-mgmt__avatar {
  width: 28px;
  height: 28px;
  border-radius: var(--radius-full);
  background: var(--color-accent-light);
  color: var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: var(--font-bold);
  font-size: var(--text-xs);
  flex-shrink: 0;
}

.user-mgmt__name-cell {
  display: flex;
  flex-direction: column;
}

.user-mgmt__affiliation {
  color: var(--color-text-muted);
}

.user-mgmt__email {
  color: var(--color-text-secondary);
}

.user-mgmt__roles-cell {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.user-mgmt__super-badge {
  display: inline-flex;
  align-items: center;
  gap: var(--space-1);
}

.user-mgmt__actions-cell {
  display: flex;
  gap: var(--space-1);
  white-space: nowrap;
}

.user-mgmt__th-actions {
  text-align: right;
  padding-right: var(--space-6);
}

/* Dialog form styles */
.user-mgmt__dialog-form {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  padding: var(--space-2) 0;
}

.user-mgmt__form-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.user-mgmt__label {
  font-size: var(--text-sm);
  font-weight: var(--font-medium);
  color: var(--color-text-primary);
}

.user-mgmt__roles-checkboxes {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-height: 180px;
  overflow-y: auto;
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-sunken);
}

.user-mgmt__role-checkbox-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-2);
  cursor: pointer;
  padding: var(--space-1) 0;
}

.user-mgmt__role-desc {
  display: flex;
  flex-direction: column;
}

.user-mgmt__role-name {
  font-size: var(--text-sm);
  color: var(--color-text-primary);
}

.user-mgmt__role-info {
  color: var(--color-text-muted);
}

.user-mgmt__privilege-box {
  background: var(--color-accent-light);
  border: 1px solid var(--color-accent);
  border-radius: var(--radius-md);
  padding: var(--space-3);
}

.user-mgmt__checkbox-label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-sm);
  cursor: pointer;
}

.user-mgmt__privilege-hint {
  margin: var(--space-1) 0 0 calc(var(--space-4) + 2px);
}

.user-mgmt__dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
}
</style>
