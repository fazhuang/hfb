import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setActivePinia, createPinia } from 'pinia';
import { useSystemStore } from '@/stores/system';

// Mock the API client
vi.mock('@/api/client', () => ({
  fetchHealth: vi.fn(() =>
    Promise.resolve({
      success: true,
      timestamp: '2025-01-01T00:00:00Z',
      data: { status: 'healthy' },
      message: 'ok',
    }),
  ),
  fetchReady: vi.fn(() =>
    Promise.resolve({
      success: true,
      timestamp: '2025-01-01T00:00:00Z',
      data: {
        ready: true,
        services: {
          PostgreSQL: { healthy: true, latency_ms: 1.5, error: null },
          Redis: { healthy: true, latency_ms: 0.4, error: null },
          Elasticsearch: { healthy: true, latency_ms: 3.2, error: null },
          MinIO: { healthy: true, latency_ms: 2.1, error: null },
        },
      },
      message: 'All services healthy',
    }),
  ),
  fetchVersion: vi.fn(() =>
    Promise.resolve({
      success: true,
      timestamp: '2025-01-01T00:00:00Z',
      data: { version: '0.2.0', environment: 'test', project: 'HFB' },
      message: 'ok',
    }),
  ),
}));

describe('systemStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it('initial state should have all disconnected', () => {
    const store = useSystemStore();
    expect(store.backendConnected).toBe(false);
    expect(store.dbConnected).toBe(false);
    expect(store.redisConnected).toBe(false);
    expect(store.esConnected).toBe(false);
    expect(store.minioConnected).toBe(false);
    expect(store.version).toBe('');
  });

  it('checkHealth should set all connected on success', async () => {
    const store = useSystemStore();
    await store.checkHealth();

    expect(store.backendConnected).toBe(true);
    expect(store.dbConnected).toBe(true);
    expect(store.redisConnected).toBe(true);
    expect(store.esConnected).toBe(true);
    expect(store.minioConnected).toBe(true);
    expect(store.version).toBe('0.2.0');
    expect(store.checking).toBe(false);
    expect(store.error).toBeNull();
  });

  it('checkHealth should handle backend failure', async () => {
    const { fetchHealth } = await import('@/api/client');
    vi.mocked(fetchHealth).mockRejectedValueOnce(new Error('Connection refused'));

    const store = useSystemStore();
    await store.checkHealth();

    expect(store.backendConnected).toBe(false);
    expect(store.error).toBe('Connection refused');
    expect(store.checking).toBe(false);
  });
});
