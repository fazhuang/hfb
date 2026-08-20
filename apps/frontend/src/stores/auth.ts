import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/api/client';

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

export interface UserBrief {
  id: string;
  username: string;
  email?: string | null;
  display_name: string | null;
  affiliation: string | null;
  is_active: boolean;
  is_superuser?: boolean;
  roles?: Array<RoleBrief>;
  created_at: string | null;
}

export interface RoleBrief {
  id: string;
  name: string;
  description: string | null;
}

export interface CurrentUser {
  id: string;
  username: string;
  email: string;
  display_name: string | null;
  affiliation: string | null;
  is_active: boolean;
  is_superuser: boolean;
  roles: Array<RoleBrief>;
  created_at: string | null;
  updated_at: string | null;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

// Role names that confer admin powers (case-insensitive match)
const ADMIN_ROLE_NAMES = new Set([
  'platform administrator',
  'academic administrator',
  'research leader',
  'reviewer',
]);

// Roles that may view (read) the source-admission checklist.
const SOURCE_ADMISSION_READ_ROLES = new Set([
  'researcher',
  'reviewer',
  'research leader',
  'academic administrator',
  'steering committee',
]);

// ------------------------------------------------------------------
// Store
// ------------------------------------------------------------------

export const useAuthStore = defineStore('auth', () => {
  // State
  const user = ref<CurrentUser | null>(null);
  const accessToken = ref<string | null>(null);
  const refreshToken = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  /** Field-level validation errors from 422 responses, keyed by field name. */
  const validationErrors = ref<Record<string, string>>({});

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value);

  /** Super admin = is_superuser flag from backend (full bypass). */
  const isSuperAdmin = computed(() => user.value?.is_superuser ?? false);

  /** Platform Administrator = role granted ALL permissions by seed (full bypass). */
  const isPlatformAdministrator = computed(() =>
    (user.value?.roles ?? []).some(
      (r) => r.name.toLowerCase() === 'platform administrator',
    ),
  );

  /** Admin role = has a recognized admin role name OR is superuser. */
  const isAdminRole = computed(() => {
    if (isSuperAdmin.value) return true;
    const roles = user.value?.roles ?? [];
    return roles.some((r) => ADMIN_ROLE_NAMES.has(r.name.toLowerCase()));
  });

  /** Can review documents = admin or reviewer role. */
  const canReviewDocuments = computed(() => isAdminRole.value);

  /** Steering Committee = dedicated governance review role for source admission. */
  const isSteeringCommittee = computed(() =>
    (user.value?.roles ?? []).some(
      (r) => r.name.toLowerCase() === 'steering committee',
    ),
  );

  /** Can review source-admission entries = Steering Committee, Platform Administrator or superuser. */
  const canReviewSourceAdmissions = computed(
    () =>
      isSuperAdmin.value ||
      isPlatformAdministrator.value ||
      isSteeringCommittee.value,
  );

  /** Can read source-admission entries = any read-granted role, Platform Administrator or superuser. */
  const canReadSourceAdmissions = computed(
    () =>
      isSuperAdmin.value ||
      isPlatformAdministrator.value ||
      (user.value?.roles ?? []).some((r) =>
        SOURCE_ADMISSION_READ_ROLES.has(r.name.toLowerCase()),
      ),
  );

  /** Can fill source-admission entries = Research Leader / Academic Admin, Platform Administrator or superuser. */
  const canFillSourceAdmissions = computed(
    () =>
      isSuperAdmin.value ||
      isPlatformAdministrator.value ||
      (user.value?.roles ?? []).some((r) =>
        ['research leader', 'academic administrator'].includes(
          r.name.toLowerCase(),
        ),
      ),
  );

  /** Can manage source policies = super admin only. */
  const canManageSourcePolicies = computed(() => isSuperAdmin.value);

  const userName = computed(() => user.value?.display_name ?? user.value?.username ?? '');

  // Note: existing components/stores still use `isAdmin` — keep it for
  // backward compatibility but point it at isAdminRole instead of isSuperAdmin.
  const isAdmin = computed(() => isAdminRole.value);

  // Helpers
  function setTokens(access: string, refresh: string): void {
    accessToken.value = access;
    refreshToken.value = refresh;
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('hfb-access-token', access);
      localStorage.setItem('hfb-refresh-token', refresh);
    }
  }

  function clearTokens(): void {
    accessToken.value = null;
    refreshToken.value = null;
    if (typeof localStorage !== 'undefined') {
      localStorage.removeItem('hfb-access-token');
      localStorage.removeItem('hfb-refresh-token');
    }
  }

  // Extract user-readable error message from Axios error.
  // FastAPI returns 422 with the project's unified error envelope:
  //   { meta: { metadata: { validation_errors: [...] } } }  (custom handler)
  //   — or — { detail: [...] }  (default FastAPI, should not occur with our handler)
  // Other endpoints return `detail` (string) or `message` (string).
  function extractErrorMessage(e: unknown, fallback: string): string {
    const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
    if (!data) return (e as Error).message ?? fallback;

    // Custom handler 422: meta.metadata.validation_errors → join per-field messages
    const meta = data.meta as Record<string, unknown> | undefined;
    const metadata = meta?.metadata as Record<string, unknown> | undefined;
    const ve = metadata?.validation_errors as
      | Array<{ loc: Array<string>; msg: string }>
      | undefined;
    if (ve?.length) {
      return ve.map((e) => `${e.loc.filter((s) => s !== 'body').join('.')}: ${e.msg}`).join('; ');
    }

    // Also check the legacy path (meta.validation_errors) for backward compat
    const legacyVe = meta?.validation_errors as
      | Array<{ loc: Array<string>; msg: string }>
      | undefined;
    if (legacyVe?.length) {
      return legacyVe
        .map((e) => `${e.loc.filter((s) => s !== 'body').join('.')}: ${e.msg}`)
        .join('; ');
    }

    // Standard error: detail field
    if (data.detail) return String(data.detail);

    // Fallback: message field
    if (data.message) return String(data.message);

    return (e as Error).message ?? fallback;
  }

  /** Extract per-field validation errors keyed by field name (last element of loc). */
  function extractFieldErrors(e: unknown): Record<string, string> {
    const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
    if (!data) return {};

    const meta = data.meta as Record<string, unknown> | undefined;
    const metadata = meta?.metadata as Record<string, unknown> | undefined;
    const ve = metadata?.validation_errors as
      | Array<{ loc: Array<string>; msg: string }>
      | undefined;
    if (!ve?.length) return {};

    const result: Record<string, string> = {};
    for (const err of ve) {
      // loc is e.g. ["body", "username"] — take the last element as field name
      const field = err.loc[err.loc.length - 1];
      if (field && !result[field]) {
        result[field] = err.msg;
      }
    }
    return result;
  }

  function loadTokens(): void {
    if (typeof localStorage !== 'undefined') {
      accessToken.value = localStorage.getItem('hfb-access-token');
      refreshToken.value = localStorage.getItem('hfb-refresh-token');
    }
  }

  function setAuthHeader(token: string | null): void {
    if (token) {
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete api.defaults.headers.common['Authorization'];
    }
  }

  // Actions
  async function login(username: string, password: string): Promise<boolean> {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await api.post('/api/v1/auth/login', { username, password });
      const body = data.data ?? data;
      user.value = body.user;
      setTokens(body.access_token, body.refresh_token);
      setAuthHeader(body.access_token);
      return true;
    } catch (e: unknown) {
      error.value = extractErrorMessage(e, 'Login failed');
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function register(
    username: string,
    email: string,
    password: string,
    displayName?: string,
  ): Promise<boolean> {
    loading.value = true;
    error.value = null;
    validationErrors.value = {};
    try {
      await api.post('/api/v1/auth/register', {
        username,
        email,
        password,
        display_name: displayName,
      });
      return true;
    } catch (e: unknown) {
      validationErrors.value = extractFieldErrors(e);
      error.value = extractErrorMessage(e, 'Registration failed');
      return false;
    } finally {
      loading.value = false;
    }
  }

  async function fetchMe(): Promise<boolean> {
    if (!accessToken.value) return false;
    loading.value = true;
    try {
      setAuthHeader(accessToken.value);
      const { data } = await api.get('/api/v1/auth/me');
      user.value = data.data as CurrentUser;
      return true;
    } catch {
      // Token invalid or expired — try refresh
      if (refreshToken.value) {
        try {
          const { data: r } = await api.post('/api/v1/auth/refresh', {
            refresh_token: refreshToken.value,
          });
          const body = r.data ?? r;
          setTokens(body.access_token, body.refresh_token);
          setAuthHeader(body.access_token);
          const { data: me } = await api.get('/api/v1/auth/me');
          user.value = me.data as CurrentUser;
          return true;
        } catch {
          logout();
          return false;
        }
      }
      logout();
      return false;
    } finally {
      loading.value = false;
    }
  }

  function logout(): void {
    user.value = null;
    clearTokens();
    setAuthHeader(null);
  }

  // Initialize from localStorage
  loadTokens();
  if (accessToken.value) {
    setAuthHeader(accessToken.value);
  }

  return {
    user,
    accessToken,
    refreshToken,
    loading,
    error,
    validationErrors,
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    isPlatformAdministrator,
    isAdminRole,
    canReviewDocuments,
    canReviewSourceAdmissions,
    canReadSourceAdmissions,
    canFillSourceAdmissions,
    isSteeringCommittee,
    canManageSourcePolicies,
    userName,
    login,
    register,
    fetchMe,
    logout,
  };
});
