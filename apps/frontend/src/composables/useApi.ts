/**
 * Shared composable for fetching paginated entity lists from the API.
 */
import { ref, type Ref } from 'vue';
import api from '@/api/client';

export interface PaginatedResult<T> {
  items: Array<T>;
  total: number;
}

export interface EntityBrief {
  id: string;
  [key: string]: unknown;
}

export function useEntityList<T extends EntityBrief>(endpoint: string) {
  const items: Ref<Array<T>> = ref([]);
  const total = ref(0);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetch(page = 1, limit = 20, q = ''): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await api.get(endpoint, { params: { page, limit, q } });
      const body = data.data ?? data;
      items.value = body.items ?? [];
      total.value = body.total ?? 0;
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to fetch';
    } finally {
      loading.value = false;
    }
  }

  return { items, total, loading, error, fetch };
}

export function useEntityDetail<T>(endpoint: (id: string) => string) {
  const entity: Ref<T | null> = ref(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function fetch(id: string): Promise<void> {
    loading.value = true;
    error.value = null;
    try {
      const { data } = await api.get(endpoint(id));
      entity.value = (data.data ?? data) as T;
    } catch (e: unknown) {
      error.value = (e as Error).message ?? 'Failed to fetch';
    } finally {
      loading.value = false;
    }
  }

  return { entity, loading, error, fetch };
}
