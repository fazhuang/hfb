/**
 * useResearchResult — composable for the ResearchResultPage.
 *
 * Owns:
 *   - Session loading (GET /api/v1/workspace/sessions/{id})
 *   - Run-list loading (GET /api/v4/research/session/{id}/runs)
 *   - Target run lookup + validation (run.session_id === projectId)
 *   - Evidence/citation/report extraction from the target run only
 *   - Export via backend endpoint with session/run authorization
 *   - validCitationTraceIds for gating marker rendering
 *
 * Contract:
 *   - projectId MUST be ResearchSession.id
 *   - runId comes from route params, validated against session
 *   - Run MUST belong to the session (enforced client-side + implicit server-side)
 *   - Stale requests aborted via AbortController + sequence counter
 *   - No cross-session data leakage
 *   - No cross-run data leakage
 *   - No fabrication of missing fields
 */

import { ref, computed, onBeforeUnmount } from 'vue';
import api from '@/api/client';

// ============================================================================
// Types
// ============================================================================

export interface ResultEvidence {
  trace_id: string;
  document_id: string;
  chunk_id: string;
  claim_text: string;
  quote: string;
  citation_text: string;
  /** SourceRef title from retrieval_snapshot (if available) — NOT document_id */
  source_ref_title?: string;
  /** SourceRef URL from retrieval_snapshot (if available) */
  source_ref_url?: string;
  /** SourceRef ID from retrieval_snapshot (if available) */
  source_ref_id?: string;
  /** Passage ID from traces (if available) — NOT chunk_id */
  passage_id?: string;
}

export interface ResultCitation {
  trace_id: string;
  citation_text: string;
  document_id: string;
  quote: string;
}

export interface ResultReport {
  run_id: string;
  topic: string;
  title: string;
  markdown: string;
  completed_at: string | null;
  evidence_count: number;
  citation_count: number;
}

export interface ResultSession {
  id: string;
  title: string;
  context_notes?: string | null;
}

export type ResultPageStatus =
  | 'loading'
  | 'ready'
  | 'run-pending'
  | 'run-failed'
  | 'report-pending'
  | 'report-failed'
  | 'report-missing'
  | 'forbidden'
  | 'not-found'
  | 'error';

// ============================================================================
// Helpers
// ============================================================================

/** UUID v4 pattern — exact length and hex positions, no regex DOS surface. */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function guardId(raw: string, label: string): string {
  const trimmed = raw.trim();
  if (!UUID_RE.test(trimmed)) {
    throw new Error(`Invalid ${label} — expected UUID v4, got ${JSON.stringify(raw.slice(0, 64))}`);
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
        return { status, message: '您没有权限访问此研究结果。' };
      case 404:
        return { status, message: '研究课题或运行记录不存在。' };
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

/**
 * Extract evidence and citations from a SINGLE run only.
 * Mirrors extractEvidenceFromSingleRun in useResearchWorkflow.ts.
 * Does NOT aggregate across runs — strict run-scoped isolation.
 */
function extractEvidenceFromSingleRun(
  run: Record<string, unknown>,
): { evidence: Array<ResultEvidence>; citations: Array<ResultCitation> } {
  const evidenceList: Array<ResultEvidence> = [];
  const citationList: Array<ResultCitation> = [];
  const evidenceSeen = new Set<string>();
  const citationSeen = new Set<string>();

  const manifest = run.replay_manifest as Record<string, unknown> | undefined;

  // Build trace_id → snapshot entry map
  const snapshotMap = new Map<string, Record<string, unknown>>();
  const traceMap = new Map<string, Record<string, unknown>>();
  if (manifest?.retrieval_snapshot && Array.isArray(manifest.retrieval_snapshot)) {
    for (const rec of manifest.retrieval_snapshot as Array<Record<string, unknown>>) {
      const tid = rec.trace_id as string;
      if (tid) snapshotMap.set(tid, rec);
    }
  }
  if (manifest?.traces && Array.isArray(manifest.traces)) {
    for (const tr of manifest.traces as Array<Record<string, unknown>>) {
      const tid = tr.trace_id as string;
      if (tid) traceMap.set(tid, tr);
    }
  }

  // Path 1: output_artifacts.citations
  const artifacts = run.output_artifacts as Record<string, unknown> | undefined;
  if (artifacts?.citations && Array.isArray(artifacts.citations)) {
    for (const c of artifacts.citations as Array<Record<string, unknown>>) {
      const tid = (c.trace_id as string) || '';
      if (!tid || citationSeen.has(tid)) continue;
      citationSeen.add(tid);
      citationList.push({
        trace_id: tid,
        citation_text: (c.citation_text as string) || '',
        document_id: (c.document_id as string) || '',
        quote: (c.quote as string) || '',
      });
    }
  }

  // Path 2: replay_manifest.traces + snapshot cross-reference
  if (manifest?.traces && Array.isArray(manifest.traces)) {
    for (const tr of manifest.traces as Array<Record<string, unknown>>) {
      const tid = tr.trace_id as string;
      if (!tid || evidenceSeen.has(tid)) continue;
      const snap = snapshotMap.get(tid) || {};
      const claimText = (snap.claim_text as string) || '';
      const citText = (snap.citation_text as string) || '';
      const quoteText = (snap.quote as string) || '';
      if (!claimText && !citText && !quoteText) continue;

      evidenceSeen.add(tid);
      evidenceList.push({
        trace_id: tid,
        document_id: (snap.document_id as string) || (tr.document_id as string) || '',
        chunk_id: (snap.chunk_id as string) || (tr.chunk_id as string) || '',
        claim_text: claimText,
        quote: quoteText,
        citation_text: citText,
        source_ref_title: (snap.source_ref_title as string) || undefined,
        source_ref_url: (snap.source_ref_url as string) || undefined,
        source_ref_id: (snap.source_ref_id as string) || undefined,
        passage_id: (tr.passage_id as string) || undefined,
      });
    }
  }

  // Fallback: snapshot-only
  if (evidenceList.length === 0 && snapshotMap.size > 0) {
    for (const [tid, snap] of snapshotMap) {
      if (evidenceSeen.has(tid)) continue;
      evidenceSeen.add(tid);
      evidenceList.push({
        trace_id: tid,
        document_id: (snap.document_id as string) || '',
        chunk_id: (snap.chunk_id as string) || '',
        claim_text: (snap.claim_text as string) || '',
        quote: (snap.quote as string) || '',
        citation_text: (snap.citation_text as string) || '',
        source_ref_title: (snap.source_ref_title as string) || undefined,
        source_ref_url: (snap.source_ref_url as string) || undefined,
        source_ref_id: (snap.source_ref_id as string) || undefined,
        passage_id: undefined,
      });
    }
  }

  return { evidence: evidenceList, citations: citationList };
}

// ============================================================================
// Composable
// ============================================================================

export function useResearchResult(projectId: () => string, runId: () => string) {
  // ---- Status ----
  const status = ref<ResultPageStatus>('loading');
  const statusMessage = ref('');

  // ---- Data ----
  const session = ref<ResultSession | null>(null);
  const report = ref<ResultReport | null>(null);
  const evidenceList = ref<Array<ResultEvidence>>([]);
  const citationList = ref<Array<ResultCitation>>([]);
  const rawRun = ref<Record<string, unknown> | null>(null);

  // ---- Export ----
  const exporting = ref(false);
  const exportError = ref('');

  // ---- Citation selection ----
  const selectedCitationTraceId = ref<string | null>(null);

  // ---- Dedup & stale-response protection ----
  let reqSeq = 0;
  let pendingAbortController: AbortController | null = null;

  // ---- Derived ----
  const hasReport = computed(() => report.value !== null && report.value.markdown.length > 0);
  const hasEvidence = computed(() => evidenceList.value.length > 0);
  const hasCitations = computed(() => citationList.value.length > 0);
  /** Set of trace_ids from the current run's real citations — used to gate marker rendering. */
  const validCitationTraceIds = computed(() => new Set(citationList.value.map((c) => c.trace_id)));
  const runStatus = computed(() => {
    if (!rawRun.value) return 'unknown';
    const steps = rawRun.value.step_execution_trace as Array<Record<string, unknown>> | undefined;
    if (!steps || steps.length === 0) return 'pending';
    const hasFailed = steps.some((s) => s.status === 'failed');
    if (hasFailed) return 'failed';
    const allCompleted = steps.every((s) => s.status === 'completed');
    if (allCompleted) return 'completed';
    return 'pending';
  });

  // ---- Load ----
  async function load() {
    // Cancel any pending request
    if (pendingAbortController) {
      pendingAbortController.abort();
    }
    pendingAbortController = new AbortController();
    const abortSignal = pendingAbortController.signal;

    const mySeq = ++reqSeq;

    // Reset all state for fresh load
    status.value = 'loading';
    statusMessage.value = '';
    session.value = null;
    report.value = null;
    evidenceList.value = [];
    citationList.value = [];
    rawRun.value = null;
    selectedCitationTraceId.value = null;
    exportError.value = '';
    releaseExportBlob();

    // Validate IDs
    let pid: string;
    let rid: string;
    try {
      pid = guardId(projectId(), 'projectId');
    } catch {
      if (mySeq === reqSeq) {
        status.value = 'not-found';
        statusMessage.value = '无效的研究课题标识。';
      }
      return;
    }
    try {
      rid = guardId(runId(), 'runId');
    } catch {
      if (mySeq === reqSeq) {
        status.value = 'not-found';
        statusMessage.value = '无效的运行记录标识。';
      }
      return;
    }

    // Step 1: Load session
    try {
      const { data } = await api.get(`/api/v1/workspace/sessions/${pid}`, {
        signal: abortSignal,
      });
      if (mySeq !== reqSeq || abortSignal.aborted) return;

      const raw = (data.data ?? data) as Record<string, unknown>;
      session.value = {
        id: String(raw.id || ''),
        title: String(raw.title || '未命名研究'),
        context_notes: typeof raw.context_notes === 'string' ? raw.context_notes : null,
      };
    } catch (e: unknown) {
      if (mySeq !== reqSeq || abortSignal.aborted) return;
      const { status: code } = classifyError(e);
      if (code === 404) {
        status.value = 'not-found';
        statusMessage.value = '研究课题不存在。';
      } else if (code === 401 || code === 403) {
        status.value = 'forbidden';
        statusMessage.value = '您没有权限访问此研究课题。';
      } else {
        status.value = 'error';
        statusMessage.value = classifyError(e).message;
      }
      return;
    }

    // Step 2: Load runs and find target
    try {
      const { data } = await api.get(`/api/v4/research/session/${pid}/runs`, {
        signal: abortSignal,
      });
      if (mySeq !== reqSeq || abortSignal.aborted) return;

      const runs = (data.data?.runs ?? []) as Array<Record<string, unknown>>;
      const targetRun = runs.find((r) => (r.run_id as string) === rid);

      if (!targetRun) {
        status.value = 'not-found';
        statusMessage.value = '运行记录不存在或不属于此研究课题。';
        return;
      }

      rawRun.value = targetRun;

      // Extract evidence and citations ONLY from the target run
      const { evidence, citations } = extractEvidenceFromSingleRun(targetRun);
      evidenceList.value = evidence;
      citationList.value = citations;

      // Build report from output artifacts
      const artifacts = targetRun.output_artifacts as Record<string, unknown> | undefined;
      const markdown = (artifacts?.markdown as string) || '';
      const completedAt = (targetRun.completed_at as string) || null;
      const topic = (targetRun.topic as string) || '';

      report.value = {
        run_id: rid,
        topic,
        title: (artifacts?.title as string) || `研究报告：${topic}`,
        markdown,
        completed_at: completedAt,
        evidence_count: evidence.length,
        citation_count: citations.length,
      };

      // Determine status based on step_execution_trace
      const steps = targetRun.step_execution_trace as Array<Record<string, unknown>> | undefined;

      // Helper to find a specific step by name
      const findStep = (name: string) =>
        steps?.find((s) => (s.name as string) === name);

      if (!steps || steps.length === 0) {
        // Rule 1: no run / no step trace
        status.value = 'run-pending';
        statusMessage.value = '此运行记录尚未开始执行。';
      } else {
        const reportStep = findStep('report_generation');
        const hasFailedStep = steps.some((s) => s.status === 'failed');
        const hasPendingStep = steps.some((s) => s.status === 'pending');
        const allCompleted = steps.every((s) => s.status === 'completed');

        if (reportStep && reportStep.status === 'failed') {
          // Rule 3: report_generation explicitly failed
          status.value = 'report-failed';
          statusMessage.value = '报告生成失败，请检查研究流程后重试。';
        } else if (hasFailedStep) {
          // Rule 4: non-report_generation critical step failed
          status.value = 'run-failed';
          statusMessage.value = '研究流程执行失败。';
        } else if (reportStep && (reportStep.status === 'pending' || reportStep.status === 'running')) {
          // Rule 2: report_generation step not yet completed
          status.value = 'report-pending';
          statusMessage.value = '报告正在生成中，请稍后刷新查看。';
        } else if (!allCompleted && !reportStep) {
          // Workflow in progress but no report_generation step yet
          status.value = 'report-pending';
          statusMessage.value = '报告生成步骤尚未开始，请等待流程继续。';
        } else if (!allCompleted && hasPendingStep) {
          // Other steps pending — still report-pending if report step hasn't completed
          status.value = 'report-pending';
          statusMessage.value = '报告生成步骤尚未完成，请稍后刷新。';
        } else if (reportStep && reportStep.status === 'completed' && !markdown) {
          // Rule 5: report_generation completed but markdown empty
          status.value = 'report-missing';
          statusMessage.value = '报告尚未生成。';
        } else if (!markdown) {
          status.value = 'report-missing';
          statusMessage.value = '报告尚未生成。';
        } else {
          // Rule 6: report_generation completed + markdown non-empty
          status.value = 'ready';
        }
      }
    } catch (e: unknown) {
      if (mySeq !== reqSeq || abortSignal.aborted) return;
      const { status: code } = classifyError(e);
      if (code === 401 || code === 403) {
        status.value = 'forbidden';
        statusMessage.value = '您没有权限访问此运行记录。';
      } else {
        status.value = 'error';
        statusMessage.value = classifyError(e).message;
      }
    }
  }

  // ---- Export ----
  // Guard against concurrent exports and stale results after route change
  let exportBlobUrl: string | null = null;

  async function exportMarkdown(): Promise<boolean> {
    if (!report.value || !report.value.markdown) return false;
    if (exporting.value) return false; // prevent double-click

    exporting.value = true;
    exportError.value = '';

    try {
      const pid = guardId(projectId(), 'projectId');
      const rid = guardId(runId(), 'runId');

      // Use real backend export endpoint with session/run authorization.
      // axios config for blob response.
      const response = await api.get(
        `/api/v4/research/session/${pid}/runs/${rid}/export`,
        { responseType: 'blob', params: { format: 'markdown' } },
      );

      // Extract filename from Content-Disposition header
      const disposition = (response.headers as Record<string, string>)?.['content-disposition'] || '';
      const filenameMatch = disposition.match(/filename="?(.+?)"?$/);
      const filename = filenameMatch?.[1] || `hfb-research-report-${rid.slice(0, 8)}.md`;

      // Download via Blob URL, then release
      const blob = response.data as Blob;
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

      // The export endpoint returns errors as JSON, but axios with
      // responseType:'blob' puts the parsed body in a Blob. Try to extract it.
      if (err && typeof err === 'object') {
        const e = err as Record<string, unknown>;
        const resp = e.response as Record<string, unknown> | undefined;
        const data = resp?.data;
        if (data instanceof Blob && data.type.includes('json')) {
          try {
            const text = await data.text();
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

      // Distinguish error types for safe presentation.
      // Always override the raw server message for security boundaries.
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

  /** Release any dangling Blob URL (called on unmount / route change). */
  function releaseExportBlob() {
    if (exportBlobUrl) {
      URL.revokeObjectURL(exportBlobUrl);
      exportBlobUrl = null;
    }
  }

  // ---- Citation selection ----
  function selectCitation(traceId: string | null) {
    selectedCitationTraceId.value = traceId;
  }

  /** Find evidence entries for a given citation trace_id */
  function evidenceForCitation(traceId: string): Array<ResultEvidence> {
    return evidenceList.value.filter((e) => e.trace_id === traceId);
  }

  // ---- Retry ----
  function retry() {
    load();
  }

  // ---- Cleanup ----
  onBeforeUnmount(() => {
    reqSeq = -1;
    releaseExportBlob();
    if (pendingAbortController) {
      pendingAbortController.abort();
      pendingAbortController = null;
    }
  });

  return {
    // Status
    status,
    statusMessage,

    // Data
    session,
    report,
    evidenceList,
    citationList,
    rawRun,

    // Derived
    hasReport,
    hasEvidence,
    hasCitations,
    validCitationTraceIds,
    runStatus,

    // Actions
    load,
    retry,
    exportMarkdown,
    exporting,
    exportError,
    releaseExportBlob,

    // Citation
    selectedCitationTraceId,
    selectCitation,
    evidenceForCitation,
  };
}
