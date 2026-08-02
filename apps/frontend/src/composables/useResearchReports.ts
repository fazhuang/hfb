/**
 * useResearchReports — composable for the ResearchReportsPage.
 *
 * Owns:
 *   - Fetching paginated report list (GET /api/v4/research/reports)
 *   - Status filtering via HfbToolbar-integrated filterValues
 *   - Export via backend endpoint with session/run authorization
 *   - Race protection via request sequence counter
 *
 * C1-1: Replaced statusFilter/setStatusFilter with unified filterValues pattern
 *   that feeds directly into HfbToolbar's v-model:filterValues.
 *   API contract unchanged: GET /api/v4/research/reports?page&limit&status.
 *
 * Contract:
 *   - Stale responses must not overwrite newer requests
 *   - Export guards: double-click, permission failure, report missing,
 *     correct MIME, safe filename, Blob URL release
 *   - No fake data, no fake IDs, no fake formats
 */

import { ref, computed, onBeforeUnmount } from 'vue';
import api from '@/api/client';
import type { ToolbarFilter, ToolbarFilterValues, ToolbarSearchPayload } from '@/types/toolbar';

// ============================================================================
// Types
// ============================================================================

export interface ReportItem {
  session_id: string;
  session_title: string;
  run_id: string;
  topic: string;
  run_status: string;
  report_status: string;
  created_at: string;
  completed_at: string | null;
  workflow_type: string;
}

export type ReportStatusFilter = '' | 'ready' | 'missing' | 'failed' | 'pending';

// ============================================================================
// Status filter definition for HfbToolbar
// ============================================================================

export const REPORT_STATUS_FILTER: ToolbarFilter = {
  key: 'status',
  label: '状态',
  placeholder: '— 状态 —',
  options: [
    { value: '', label: '全部' },
    { value: 'ready', label: '报告就绪' },
    { value: 'missing', label: '报告缺失' },
    { value: 'failed', label: '报告失败' },
    { value: 'pending', label: '待生成' },
  ],
};

export const REPORT_TOOLBAR_FILTERS: ToolbarFilter[] = [REPORT_STATUS_FILTER];

// ============================================================================
// Helpers
// ============================================================================

export const REPORT_STATUS_LABELS: Record<string, string> = {
  '': '全部',
  ready: '报告就绪',
  missing: '报告缺失',
  failed: '报告失败',
  pending: '待生成',
};

function classifyError(err: unknown): { status: number; message: string } {
  if (typeof err !== 'object' || err === null) {
    return { status: 0, message: '未知错误' };
  }
  const e = err as Record<string, unknown>;

  if (e.code === 'ECONNABORTED' || e.code === 'ETIMEDOUT') {
    return { status: 0, message: '请求超时，请检查网络后重试。' };
  }
  if (e.code === 'ERR_NETWORK' || e.message === 'Network Error') {
    return { status: 0, message: '网络连接失败，请检查网络后重试。' };
  }

  const resp = e.response as Record<string, unknown> | undefined;
  if (resp) {
    const status = (resp.status as number) || 0;
    const data = resp.data as Record<string, unknown> | undefined;
    const detail = (data?.detail as string) || (data?.message as string) || '';

    switch (status) {
      case 401:
        return { status, message: '登录已过期，请重新登录。' };
      case 403:
        return { status, message: '您没有权限访问此页面。' };
      case 404:
        return { status, message: '请求的资源不存在。' };
      case 422:
        return { status, message: detail || '请求参数无效。' };
      default:
        if (status >= 500) {
          return { status, message: detail || '服务端错误，请稍后重试。' };
        }
        return { status, message: detail || `请求失败 (${status})` };
    }
  }

  return { status: 0, message: (e.message as string) || '未知错误' };
}

// ============================================================================
// Composable
// ============================================================================

export function useResearchReports() {
  // ---- Data ----
  const items = ref<Array<ReportItem>>([]);
  const total = ref(0);
  const page = ref(1);
  const limit = ref(20);

  // ---- UI state ----
  const loading = ref(false);
  const error = ref<string | null>(null);

  /** Active filter values (keyed by filter.key). Shared with HfbToolbar via v-model:filterValues. */
  const filterValues = ref<ToolbarFilterValues>({ status: '' });

  // ---- Export state ----
  const exporting = ref(false);
  const exportError = ref('');

  // ---- Race protection ----
  let reqSeq = 0;

  // ---- Derived ----
  const totalPages = computed(() => Math.max(1, Math.ceil(total.value / limit.value)));

  /** Human-readable label for the current status filter (used in EmptyState message). */
  const statusFilterLabel = computed(() => {
    const val = filterValues.value.status;
    return REPORT_STATUS_LABELS[String(val)] || '';
  });

  // ---- Fetch reports ----
  /**
   * Fetch reports from the server.
   *
   * API contract (unchanged from pre-C1-1):
   *   GET /api/v4/research/reports?page=N&limit=N&status=...
   */
  async function fetchReports() {
    const mySeq = ++reqSeq;

    loading.value = true;
    error.value = null;

    try {
      const params: Record<string, string | number> = {
        page: page.value,
        limit: limit.value,
      };
      const statusVal = filterValues.value.status;
      if (statusVal) {
        params.status = String(statusVal);
      }

      const { data } = await api.get('/api/v4/research/reports', { params });
      if (mySeq !== reqSeq) return;

      const body = data.data ?? data;
      items.value = (body.items ?? []) as Array<ReportItem>;
      total.value = (body.total ?? 0) as number;
    } catch (e: unknown) {
      if (mySeq !== reqSeq) return;
      error.value = classifyError(e).message;
    } finally {
      if (mySeq === reqSeq) {
        loading.value = false;
      }
    }
  }

  // ---- Handle HfbToolbar search event ----
  function onSearch(_payload: ToolbarSearchPayload) {
    // filterValues are already synced via v-model:filterValues on HfbToolbar.
    // When the status filter changes, the parent calls onFilterValuesChange
    // which resets to page=1 and re-fetches.
  }

  // ---- Pagination ----
  function setPage(p: number) {
    if (p < 1 || p > totalPages.value) return;
    page.value = p;
    fetchReports();
  }

  // ---- Status filter ----
  function setStatusFilter(f: ReportStatusFilter) {
    filterValues.value.status = f;
    page.value = 1; // reset to first page on filter change
    fetchReports();
  }

  // ---- Export ----
  let exportBlobUrl: string | null = null;

  async function exportReport(sessionId: string, runId: string): Promise<boolean> {
    if (exporting.value) return false; // double-click prevention
    if (!sessionId || !runId) return false;

    exporting.value = true;
    exportError.value = '';

    try {
      // Real backend export endpoint with session/run authorization
      const response = await api.get(`/api/v4/research/session/${sessionId}/runs/${runId}/export`, {
        responseType: 'blob',
        params: { format: 'markdown' },
      });

      // Extract filename from Content-Disposition header
      const disposition =
        (response.headers as Record<string, string>)?.['content-disposition'] || '';
      const filenameMatch = disposition.match(/filename="?(.+?)"?$/);
      const filename = filenameMatch?.[1] || `hfb-research-report-${runId.slice(0, 8)}.md`;

      // Verify MIME type
      const blob = response.data as Blob;
      const allowedTypes = ['text/markdown', 'text/plain', 'application/octet-stream'];
      if (blob.type && !allowedTypes.some((t) => blob.type.startsWith(t)) && blob.type !== '') {
        exportError.value = '导出文件格式异常，请重试。';
        return false;
      }

      // Download via Blob URL, then release
      const url = URL.createObjectURL(blob);
      exportBlobUrl = url;
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
      exportBlobUrl = null;
      return true;
    } catch (err: unknown) {
      const { status: code, message } = classifyError(err);

      // Try to extract JSON error from blob response
      if (err && typeof err === 'object') {
        const e = err as Record<string, unknown>;
        const resp = e.response as Record<string, unknown> | undefined;
        const blobData = resp?.data;
        if (blobData instanceof Blob && blobData.type && blobData.type.includes('json')) {
          try {
            const text = await blobData.text();
            const parsed = JSON.parse(text);
            exportError.value = (parsed.detail as string) || message;
          } catch {
            exportError.value = message;
          }
        } else {
          exportError.value = message;
        }
      } else {
        exportError.value = message;
      }

      // Security-safe error messages — override server messages
      if (code === 401 || code === 403) {
        exportError.value = '您没有权限导出此报告。';
      } else if (code === 404) {
        exportError.value = '报告不存在或无权访问。';
      } else if (code === 409) {
        exportError.value = '报告为空，无法导出。';
      } else if (code >= 500) {
        exportError.value = '导出失败，请重试。';
      } else if (!exportError.value) {
        exportError.value = '导出失败，请重试。';
      }
      return false;
    } finally {
      exporting.value = false;
    }
  }

  /** Release any dangling Blob URL (called on unmount). */
  function releaseExportBlob() {
    if (exportBlobUrl) {
      URL.revokeObjectURL(exportBlobUrl);
      exportBlobUrl = null;
    }
  }

  // ---- Retry ----
  function retry() {
    fetchReports();
  }

  // ---- Cleanup ----
  onBeforeUnmount(() => {
    reqSeq = -1;
    releaseExportBlob();
  });

  return {
    // Data
    items,
    total,
    page,
    limit,
    totalPages,

    // UI state
    loading,
    error,
    filterValues,
    statusFilterLabel,

    // Export
    exporting,
    exportError,
    exportReport,
    releaseExportBlob,

    // Actions
    fetchReports,
    onSearch,
    setPage,
    setStatusFilter,
    retry,
  };
}
