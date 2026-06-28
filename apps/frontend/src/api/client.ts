import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface ServiceStatus {
  healthy: boolean;
  latency_ms: number | null;
  error: string | null;
}

export interface ReadyResponse {
  success: boolean;
  timestamp: string;
  data: {
    ready: boolean;
    services: Record<string, ServiceStatus>;
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

export async function fetchVersion(): Promise<VersionResponse> {
  const { data } = await api.get<VersionResponse>('/version');
  return data;
}

export default api;
