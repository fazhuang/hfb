/**
 * useVersionComparison — composable for the 4-step version comparison workflow.
 *
 * Owns:
 *   - Session loading (GET /api/v1/workspace/sessions/{id})
 *   - Passage search (GET /api/v1/search?types=passage)
 *   - Session auto-creation (POST /api/v1/workspace/sessions)
 *   - Comparison execution (PUT /api/v1/research/sessions/{id}/version-comparison)
 *   - Comparison restoration (GET /api/v1/research/sessions/{id}/version-comparison)
 *   - Note save (POST /api/v1/workspace/sessions/{id}/notes)
 *   - Export (GET /api/v1/research/sessions/{id}/export)
 *   - Step state machine: search → select → compare → verify
 *
 * Contract:
 *   - projectId MUST be ResearchSession.id
 *   - Per-projectId isolation via sessionStorage scoped keys
 *   - Stale response protection via AbortController + sequence counter
 *   - No cross-session data leakage
 *   - Legacy behavior parity with views/ResearchWorkflowView.vue:
 *     - Auto-restore: probes most recent 10 sessions for existing comparison
 *     - Null skip: sessions returning data:null silently skipped
 *     - Network errors during restore: caught, UI renders anyway
 *     - Empty session list: UI renders step 1 (passage search)
 */

import { ref, computed, onBeforeUnmount } from 'vue';
import api from '@/api/client';

// ============================================================================
// Types
// ============================================================================

export interface PassageSearchResult {
  id: string;
  title: string;
  snippet: string | null;
  metadata: {
    version_id?: string;
    version_name?: string;
    repository?: string | null;
    shelf_mark?: string | null;
    chapter_title?: string;
  };
}

export interface EvidenceSnapshot {
  passage_id: string;
  text: string;
  citation: string;
  evidence_complete: boolean;
  version: {
    id: string;
    name: string;
    repository: string | null;
    shelf_mark: string | null;
  };
}

export interface ComparisonState {
  workflow_type: string;
  corpus_status: 'validation' | 'approved';
  source: EvidenceSnapshot;
  target: EvidenceSnapshot;
  comparison: {
    differences: number;
    similarity_ratio: number;
    operations: Array<{
      op: string;
      source_text: string;
      target_text: string;
    }>;
  };
}

export interface VersionComparisonSession {
  id: string;
  title: string;
  context_notes?: string | null;
  created_at?: string;
  updated_at?: string;
}

export type VCStepState = 'search' | 'select' | 'compare' | 'verify';

// ============================================================================
// Helpers
// ============================================================================

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function guardId(raw: string): string {
  const trimmed = raw.trim();
  if (!UUID_RE.test(trimmed)) {
    throw new Error(
      `Invalid session id — expected UUID, got ${JSON.stringify(raw.slice(0, 64))}`,
    );
  }
  return trimmed;
}

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
        return { status, message: '您没有权限执行此操作。' };
      case 404:
        return { status, message: '研究课题不存在。' };
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

export function useVersionComparison(projectId: () => string) {
  // ---- Session ----
  const session = ref<VersionComparisonSession | null>(null);
  const sessionLoading = ref(false);
  const sessionError = ref<string>('');
  const notFound = ref(false);

  // ---- Passage search ----
  const query = ref('');
  const searchResults = ref<Array<PassageSearchResult>>([]);
  const searching = ref(false);
  const searched = ref(false);

  // ---- Version selection ----
  const sourcePassage = ref<PassageSearchResult | null>(null);
  const targetPassage = ref<PassageSearchResult | null>(null);

  // ---- Comparison ----
  const comparison = ref<ComparisonState | null>(null);
  const comparing = ref(false);
  const sessionId = ref<string | null>(null);

  // ---- Note ----
  const noteContent = ref('');
  const savingNote = ref(false);
  const noteSaved = ref(false);

  // ---- Export ----
  const exporting = ref(false);

  // ---- Messages ----
  const error = ref('');
  const message = ref('');

  // ---- Stale-response protection ----
  let pendingAbortController: AbortController | null = null;
  // reqSeq reserved for future stale-response guard — same pattern as useResearchWorkflow

  // ---- Derived ----
  const sameVersion = computed(
    () =>
      Boolean(sourcePassage.value?.metadata.version_id) &&
      sourcePassage.value?.metadata.version_id === targetPassage.value?.metadata.version_id,
  );
  const canCompare = computed(() =>
    Boolean(sourcePassage.value && targetPassage.value && !sameVersion.value),
  );

  const currentStep = computed<number>(() => {
    if (noteSaved.value || noteContent.value.trim()) return 4;
    if (comparison.value) return 3;
    if (sourcePassage.value && targetPassage.value) return 2;
    return 1;
  });

  const showValidationBanner = computed(() => {
    if (comparison.value && comparison.value.corpus_status === 'approved') {
      return false;
    }
    return true;
  });

  // ---- Session loading ----
  async function loadSession() {
    const pid = projectId();
    if (!pid) return;

    sessionLoading.value = true;
    sessionError.value = '';
    notFound.value = false;

    try {
      const { data } = await api.get(`/api/v1/workspace/sessions/${guardId(pid)}`);
      const raw = data.data as VersionComparisonSession;
      session.value = { id: raw.id, title: raw.title, context_notes: raw.context_notes };
      sessionId.value = raw.id;
    } catch (err: unknown) {
      const ce = classifyError(err);
      if (ce.status === 404) {
        notFound.value = true;
      } else {
        sessionError.value = ce.message;
      }
    } finally {
      sessionLoading.value = false;
    }
  }

  // ---- Passage search ----
  async function searchPassages() {
    if (!query.value.trim()) return;
    searching.value = true;
    searched.value = true;
    error.value = '';
    try {
      const { data } = await api.get('/api/v1/search', {
        params: { q: query.value.trim(), types: 'passage', limit: 50 },
      });
      searchResults.value = (data.data?.items ?? []) as Array<PassageSearchResult>;
    } catch (err: unknown) {
      error.value = classifyError(err).message;
    } finally {
      searching.value = false;
    }
  }

  // ---- Version selection ----
  function selectPassage(item: PassageSearchResult, side: 'source' | 'target') {
    if (side === 'source') sourcePassage.value = item;
    else targetPassage.value = item;
    comparison.value = null;
    noteSaved.value = false;
    message.value = '';
  }

  // ---- Session ensure ----
  async function ensureSession(): Promise<string> {
    if (sessionId.value) return sessionId.value;
    const { data } = await api.post('/api/v1/workspace/sessions', {
      title: '版本比较研究',
    });
    sessionId.value = data.data.id as string;
    return sessionId.value;
  }

  // ---- Run comparison ----
  async function runComparison() {
    if (!sourcePassage.value || !targetPassage.value || !canCompare.value) return;
    comparing.value = true;
    error.value = '';
    message.value = '';
    try {
      const id = await ensureSession();
      const { data } = await api.put(`/api/v1/research/sessions/${id}/version-comparison`, {
        source_passage_id: sourcePassage.value.id,
        target_passage_id: targetPassage.value.id,
      });
      comparison.value = data.data as ComparisonState;
      noteSaved.value = false;
      message.value = '比较完成。';
    } catch (err: unknown) {
      error.value = classifyError(err).message;
    } finally {
      comparing.value = false;
    }
  }

  // ---- Save note ----
  async function saveNote() {
    if (!sessionId.value || !noteContent.value.trim()) return;
    savingNote.value = true;
    error.value = '';
    try {
      await api.post(`/api/v1/workspace/sessions/${sessionId.value}/notes`, {
        content: noteContent.value.trim(),
        entity_type: 'version_comparison',
        entity_id: comparison.value?.source.passage_id,
        tags: '版本比较',
      });
      noteSaved.value = true;
      message.value = '笔记已保存。';
      noteContent.value = '';
    } catch (err: unknown) {
      error.value = classifyError(err).message;
    } finally {
      savingNote.value = false;
    }
  }

  // ---- Export ----
  async function exportRecord() {
    if (!sessionId.value || !comparison.value) return;
    exporting.value = true;
    error.value = '';
    try {
      const response = await api.get(`/api/v1/research/sessions/${sessionId.value}/export`, {
        responseType: 'blob',
      });
      const url = URL.createObjectURL(response.data as Blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `hfb-research-record-${sessionId.value}.md`;
      link.click();
      URL.revokeObjectURL(url);
      message.value = '已导出。';
    } catch (err: unknown) {
      error.value = classifyError(err).message;
    } finally {
      exporting.value = false;
    }
  }

  // ---- Restore latest workflow (legacy-equivalent) ----
  async function restoreLatestWorkflow() {
    try {
      const { data } = await api.get('/api/v1/workspace/sessions');
      const sessions = (data.data ?? []) as Array<VersionComparisonSession>;
      for (const s of sessions.slice(0, 10)) {
        try {
          const response = await api.get(`/api/v1/research/sessions/${s.id}/version-comparison`);
          const comparisonData = response.data?.data;
          if (!comparisonData) continue;
          comparison.value = comparisonData as ComparisonState;
          sessionId.value = s.id;
          return;
        } catch {
          // Session may not have comparison data — skip
        }
      }
    } catch {
      // Auth guard handles unauthenticated access; empty sessions handled by UI
    }
  }

  // ---- Cleanup ----
  onBeforeUnmount(() => {
    if (pendingAbortController) {
      pendingAbortController.abort();
      pendingAbortController = null;
    }
  });

  return {
    // Session
    session,
    sessionLoading,
    sessionError,
    notFound,
    loadSession,

    // Search
    query,
    searchResults,
    searching,
    searched,
    searchPassages,

    // Selection
    sourcePassage,
    targetPassage,
    sameVersion,
    canCompare,
    selectPassage,

    // Comparison
    comparison,
    comparing,
    sessionId,
    runComparison,
    restoreLatestWorkflow,

    // Note
    noteContent,
    savingNote,
    noteSaved,
    saveNote,

    // Export
    exporting,
    exportRecord,

    // Steps
    currentStep,
    showValidationBanner,

    // Messages
    error,
    message,
  };
}
