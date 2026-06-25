import { defineStore } from 'pinia';
import { ref } from 'vue';
import { fetchHealth, fetchReady, fetchVersion } from '@/api/client';
import type { ServiceStatus } from '@/api/client';

export const useSystemStore = defineStore('system', () => {
  const backendConnected = ref<boolean>(false);
  const dbConnected = ref<boolean>(false);
  const redisConnected = ref<boolean>(false);
  const esConnected = ref<boolean>(false);
  const minioConnected = ref<boolean>(false);
  const version = ref<string>('');
  const environment = ref<string>('');
  const checking = ref<boolean>(false);
  const error = ref<string | null>(null);

  function mapService(services: Record<string, ServiceStatus> | undefined, key: string): boolean {
    return services?.[key]?.healthy ?? false;
  }

  async function checkHealth() {
    checking.value = true;
    error.value = null;
    try {
      // Check basic health first
      const health = await fetchHealth();
      backendConnected.value = health.success;

      if (backendConnected.value) {
        // Check readiness (all infra)
        try {
          const ready = await fetchReady();
          const s = ready.data.services;
          dbConnected.value = mapService(s, 'PostgreSQL');
          redisConnected.value = mapService(s, 'Redis');
          esConnected.value = mapService(s, 'Elasticsearch');
          minioConnected.value = mapService(s, 'MinIO');
        } catch {
          // Ready might fail if some services are down — that's expected info
        }

        // Check version
        try {
          const ver = await fetchVersion();
          version.value = ver.data.version;
          environment.value = ver.data.environment;
        } catch {
          // ignore
        }
      }
    } catch (e: unknown) {
      error.value = e instanceof Error ? e.message : 'Unknown error';
      backendConnected.value = false;
    } finally {
      checking.value = false;
    }
  }

  return {
    backendConnected,
    dbConnected,
    redisConnected,
    esConnected,
    minioConnected,
    version,
    environment,
    checking,
    error,
    checkHealth,
  };
});
