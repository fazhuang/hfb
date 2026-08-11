import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: auto-inject Bearer token from localStorage.
// Catches cross-page navigations where auth store hasn't initialized yet.
api.interceptors.request.use((config) => {
  if (!config.headers.Authorization) {
    const token = localStorage.getItem('hfb-access-token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Response error interceptor: pass through business status codes silently.
// Callers use classifyError() to convert to user-facing messages.
// Never log to console — all errors surface through UI.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Reject without console — caller handles via try/catch + classifyError
    return Promise.reject(error);
  },
);

export interface ServiceStatus {
  name?: string;
  healthy: boolean;
  latency_ms: number | null;
  error: string | null;
}

export interface ReadyResponse {
  success: boolean;
  timestamp: string;
  data: {
    status?: string;
    ready: boolean;
    services?: Record<string, ServiceStatus>;
  };
  message: string;
}

export interface AdminHealthDetailsResponse {
  success: boolean;
  timestamp: string;
  data: {
    status: string;
    ready: boolean;
    services: Record<string, ServiceStatus>;
    timestamp?: string;
  };
  message: string;
}

export interface VersionResponse {
  success: boolean;
  timestamp: string;
  data: {
    version: string;
    environment: string;
    project: string;
  };
  message: string;
}

export interface HealthResponse {
  success: boolean;
  timestamp: string;
  data: { status: string };
  message: string;
}

export async function fetchHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>('/health');
  return data;
}

export async function fetchReady(): Promise<ReadyResponse> {
  const { data } = await api.get<ReadyResponse>('/ready');
  return data;
}

export async function fetchAdminHealthDetails(): Promise<AdminHealthDetailsResponse> {
  const { data } = await api.get<AdminHealthDetailsResponse>('/api/v1/admin/health-details');
  return data;
}

export async function fetchVersion(): Promise<VersionResponse> {
  const { data } = await api.get<VersionResponse>('/version');
  return data;
}

/**
 * Unified error message extractor.
 * Converts API / network exceptions into user-friendly localized error strings.
 */
export function getErrorMessage(e: unknown, fallbackMessage = '请求失败，请稍后重试'): string {
  if (typeof e === 'object' && e !== null) {
    const res = (
      e as {
        response?: {
          status?: number;
          data?: { message?: string; detail?: string };
        };
      }
    ).response;

    if (res) {
      const status = res.status;
      if (status === 401) {
        return '未登录或登录会话已过期，请登录后继续';
      }
      if (status === 403) {
        return '暂无权限访问该学术资源';
      }
      if (status === 404) {
        return '未找到相关的学术数据';
      }
      if (status !== undefined && status >= 500) {
        return '服务器响应异常，请稍后重试';
      }

      const dataMsg = res.data?.message || res.data?.detail;
      if (typeof dataMsg === 'string' && dataMsg.trim()) {
        return dataMsg.trim();
      }
    }
  }

  if (e instanceof Error || (typeof e === 'object' && e !== null && 'message' in e)) {
    const msg = String((e as { message?: string }).message || '');
    if (msg.includes('401')) {
      return '未登录或登录会话已过期，请登录后继续';
    }
    if (msg.includes('403')) {
      return '暂无权限访问该学术资源';
    }
    if (msg.includes('404')) {
      return '未找到相关的学术数据';
    }
    if (/5\d\d/.test(msg)) {
      return '服务器响应异常，请稍后重试';
    }
    if (msg && !msg.startsWith('Request failed with status code')) {
      return msg;
    }
  }

  if (typeof e === 'string' && e.trim()) {
    if (e.includes('401')) {
      return '未登录或登录会话已过期，请登录后继续';
    }
    if (e.includes('403')) {
      return '暂无权限访问该学术资源';
    }
    if (e.includes('404')) {
      return '未找到相关的学术数据';
    }
    if (/5\d\d/.test(e)) {
      return '服务器响应异常，请稍后重试';
    }
    return e;
  }

  return fallbackMessage;
}

export default api;


