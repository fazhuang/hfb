import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import api from '@/api/client';

// ------------------------------------------------------------------
// Types
// ------------------------------------------------------------------

export interface UserBrief {
  id: string;
  username: string;
  display_name: string | null;
  affiliation: string | null;
  is_active: boolean;
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

  // Getters
  const isAuthenticated = computed(() => !!accessToken.value && !!user.value);

  /** Super admin = is_superuser flag from backend (full bypass). */
  const isSuperAdmin = computed(() => user.value?.is_superuser ?? false);

  /** Admin role = has a recognized admin role name OR is superuser. */
  const isAdminRole = computed(() => {
    if (isSuperAdmin.value) return true;
    const roles = user.value?.roles ?? [];
    return roles.some((r) => ADMIN_ROLE_NAMES.has(r.name.toLowerCase()));
  });

  /** Can review documents = admin or reviewer role. */
  const canReviewDocuments = computed(() => isAdminRole.value);

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
    localStorage.setItem('hfb-access-token', access);
    localStorage.setItem('hfb-refresh-token', refresh);
  }

  function clearTokens(): void {
    accessToken.value = null;
    refreshToken.value = null;
    localStorage.removeItem('hfb-access-token');
    localStorage.removeItem('hfb-refresh-token');
  }

  // Extract user-readable error message from Axios error.
  // FastAPI returns 422 with `detail` (string) OR `meta.validation_errors` (array of {loc,msg,type}).
  // Other endpoints return `detail` (string) or `message` (string).
  function extractErrorMessage(e: unknown, fallback: string): string {
    const data = (e as { response?: { data?: Record<string, unknown> } })?.response?.data;
    if (!data) return (e as Error).message ?? fallback;

    // FastAPI 422: meta.validation_errors → join per-field messages
    const meta = data.meta as Record<string, unknown> | undefined;
    const validationErrors = meta?.validation_errors as Array<{ loc: string[]; msg: string }> | undefined;
    if (validationErrors?.length) {
      return validationErrors.map((ve) => `${ve.loc.filter(s => s !== 'body').join('.')}: ${ve.msg}`).join('; ');
    }

    // Standard error: detail field
    if (data.detail) return String(data.detail);

    // Fallback: message field
    if (data.message) return String(data.message);

    return (e as Error).message ?? fallback;
  }

  function loadTokens(): void {
    accessToken.value = localStorage.getItem('hfb-access-token');
    refreshToken.value = localStorage.getItem('hfb-refresh-token');
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
    try {
      await api.post('/api/v1/auth/register', {
        username,
        email,
        password,
        display_name: displayName,
      });
      return true;
    } catch (e: unknown) {
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
    isAuthenticated,
    isAdmin,
    isSuperAdmin,
    isAdminRole,
    canReviewDocuments,
    canManageSourcePolicies,
    userName,
    login,
    register,
    fetchMe,
    logout,
  };
});