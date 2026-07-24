/**
 * useLibrary — composable for Library data fetching.
 *
 * All data comes from real backend endpoints:
 *   GET /api/v1/documents               → list/search
 *   GET /api/v1/documents/{id}          → detail
 *   GET /api/v1/documents/{id}/stats     → citation/evidence/OCR stats
 */
import { ref, type Ref } from 'vue';
import api from '@/api/client';
import type {
  LibraryDocument,
  LibraryDocumentDetail,
  LibraryDocumentStats,
  LibraryFilters,
} from '@/types/library';

/** Shared paginated list result */
export interface LibraryListResult {
  items: Array<LibraryDocument>;
  total: number;
}

/** Return type of useLibraryList */
export interface UseLibraryList {
  items: Ref<Array<LibraryDocument>>;
  total: Ref<number>;
  loading: Ref<boolean>;
  error: Ref<string | null>;
  page: Ref<number>;
  limit: Ref<number>;
  totalPages: Ref<number>;
  fetchPage: (p: number) => Promise<void>;
}

/** Return type of useLibraryDetail */
export interface UseLibraryDetail {
  doc: Ref<LibraryDocumentDetail | null>;
  stats: Ref<LibraryDocumentStats | null>;
  loading: Ref<boolean>;
  error: Ref<string | null>;
  fetch: () => Promise<void>;
}

/** Return type of useLibraryStats */
export interface UseLibraryStats {
  stats: Ref<LibraryDocumentStats | null>;
  loading: Ref<boolean>;
  error: Ref<string | null>;
  fetch: () => Promise<void>;
}

// ---- List ----

export function useLibraryList(filters: Ref<LibraryFilters>): UseLibraryList {
  const items = ref<Array<LibraryDocument>>([]) as Ref<Array<LibraryDocument>>;
  const total = ref(0);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const page = ref(1);
  const limit = ref(20);

  const totalPages = ref(1);

  let reqId = 0;

  async function fetchPage(p: number) {
    const myReqId = ++reqId;
    page.value = p;
    loading.value = true;
    error.value = null;
    try {
      const params: Record<string, unknown> = { page: p, limit: limit.value };
      const f = filters.value;
      if (f.query.trim()) params.q = f.query.trim();
      if (f.copyrightStatus) params.copyright_status = f.copyrightStatus;
      if (f.reviewStatus) params.review_status = f.reviewStatus;
      if (f.dynasty) params.dynasty = f.dynasty;
      if (f.category) params.category = f.category;
      if (f.sourceName) params.source_name = f.sourceName;

      const { data } = await api.get('/api/v1/documents', { params });
      if (myReqId !== reqId) return;
      const body = data.data ?? data;
      items.value = (body.items ?? []) as Array<LibraryDocument>;
      total.value = body.total ?? 0;
      totalPages.value = Math.max(1, Math.ceil(total.value / limit.value));
    } catch (e: unknown) {
      if (myReqId !== reqId) return;
      error.value = (e as Error).message ?? 'Failed to fetch';
    } finally {
      if (myReqId === reqId) {
        loading.value = false;
      }
    }
  }

  return { items, total, loading, error, page, limit, totalPages, fetchPage };
}

// ---- Detail ----

export function useLibraryDetail(id: Ref<string>): UseLibraryDetail {
  const doc = ref<LibraryDocumentDetail | null>(null);
  const stats = ref<LibraryDocumentStats | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  let reqId = 0;

  async function fetch() {
    const myReqId = ++reqId;
    loading.value = true;
    error.value = null;
    try {
      const [{ data: docData }, { data: statsData }] = await Promise.all([
        api.get(`/api/v1/documents/${id.value}`),
        api.get(`/api/v1/documents/${id.value}/stats`),
      ]);
      if (myReqId !== reqId) return;
      doc.value = (docData.data ?? docData) as LibraryDocumentDetail;
      stats.value = (statsData.data ?? statsData) as LibraryDocumentStats;
    } catch (e: unknown) {
      if (myReqId !== reqId) return;
      error.value = (e as Error).message ?? 'Failed to fetch';
    } finally {
      if (myReqId === reqId) {
        loading.value = false;
      }
    }
  }

  return { doc, stats, loading, error, fetch };
}

// ---- Stats only ----

export function useLibraryStats(id: Ref<string>): UseLibraryStats {
  const stats = ref<LibraryDocumentStats | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  let reqId = 0;

  async function fetch() {
    const myReqId = ++reqId;
    loading.value = true;
    error.value = null;
    try {
      const { data } = await api.get(`/api/v1/documents/${id.value}/stats`);
      if (myReqId !== reqId) return;
      stats.value = (data.data ?? data) as LibraryDocumentStats;
    } catch (e: unknown) {
      if (myReqId !== reqId) return;
      error.value = (e as Error).message ?? 'Failed to fetch';
    } finally {
      if (myReqId === reqId) loading.value = false;
    }
  }

  return { stats, loading, error, fetch };
}
