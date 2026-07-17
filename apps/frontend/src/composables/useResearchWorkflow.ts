/**
 * useResearchWorkflow — single-source-of-truth composable for the 5-step
 * research workflow.
 *
 * Owns:
 *   - session loading (GET /api/v1/workspace/sessions/{id})
 *   - pending question read + clear from sessionStorage
 *   - workflow submission (POST /api/v4/research/workflow)
 *   - run fetching (GET /api/v4/research/session/{id}/runs)
 *   - evidence/citation extraction from run artifacts
 *   - citation save (POST /api/v1/workspace/sessions/{id}/citations)
 *   - note save (POST /api/v1/workspace/sessions/{id}/notes)
 *   - step state machine: question → selection → submitting → evidence → report
 *
 * Contract:
 *   - projectId MUST be ResearchSession.id
 *   - Exactly ONE active submission per instance
 *   - sessionStorage key includes projectId (never cross-reads)
 *   - Backend workflow is synchronous — no polling, no pause/resume
 *   - Document selection is not supported by backend — system auto-retrieves
 *   - AI results are 100% from backend response — nothing client-generated
 */

import { ref, computed, onBeforeUnmount } from 'vue';
import api from '@/api/client';

// ============================================================================
// Types
// ============================================================================

export interface WorkflowStep {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: Record<string, unknown> | null;
  trace_ids?: string[];
}

export interface WorkflowEvidence {
  trace_id: string;
  document_id: string;
  chunk_id: string;
  claim_text: string;
  quote: string;
  citation_text: string;
}

export interface WorkflowCitation {
  trace_id: string;
  citation_text: string;
  document_id: string;
  quote: string;
}

export interface WorkflowReport {
  run_id: string;
  topic: string;
  title: string;
  markdown: string;
  completed_at: string | null;
  artifact_id?: string;
  evidence_count: number;
  citation_count: number;
}

export type StepState = 'question' | 'selection' | 'submitting' | 'evidence' | 'report' | 'error';

export interface ResearchSession {
  id: string;
  title: string;
  context_notes?: string | null;
}

// ============================================================================
// Helpers
// ============================================================================

function makeStorageKey(projectId: string): string {
  return `hfb.research.${projectId}.pending-question`;
}

function extractEvidenceFromRuns(
  runs: Record<string, unknown>[],
): { evidence: WorkflowEvidence[]; citations: WorkflowCitation[] } {
  const evidenceList: WorkflowEvidence[] = [];
  const citationList: WorkflowCitation[] = [];
  const seen = new Set<string>();

  for (const run of runs) {
    const manifest = run.replay_manifest as Record<string, unknown> | undefined;

    // Build trace_id → snapshot entry map
    const snapshotMap = new Map<string, Record<string, unknown>>();
    if (manifest?.retrieval_snapshot && Array.isArray(manifest.retrieval_snapshot)) {
      for (const rec of manifest.retrieval_snapshot as Array<Record<string, unknown>>) {
        const tid = rec.trace_id as string;
        if (tid) snapshotMap.set(tid, rec);
      }
    }

    // Path 1: output_artifacts.citations
    const artifacts = run.output_artifacts as Record<string, unknown> | undefined;
    if (artifacts?.citations && Array.isArray(artifacts.citations)) {
      for (const c of artifacts.citations as Array<Record<string, unknown>>) {
        const tid = (c.trace_id as string) || '';
        if (!tid || seen.has(tid)) continue;
        seen.add(tid);
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
        if (!tid || seen.has(tid)) continue;
        const snap = snapshotMap.get(tid) || {};
        // Only add if we have real content
        const claimText = (snap.claim_text as string) || '';
        const citText = (snap.citation_text as string) || '';
        const quoteText = (snap.quote as string) || '';
        if (!claimText && !citText && !quoteText) continue;

        seen.add(tid);
        evidenceList.push({
          trace_id: tid,
          document_id: (snap.document_id as string) || (tr.document_id as string) || '',
          chunk_id: (snap.chunk_id as string) || (tr.chunk_id as string) || '',
          claim_text: claimText,
          quote: quoteText,
          citation_text: citText,
        });
      }
    }

    // Fallback: snapshot-only
    if (evidenceList.length === 0 && citationList.length === 0 && snapshotMap.size > 0) {
      for (const [tid, snap] of snapshotMap) {
        if (seen.has(tid)) continue;
        seen.add(tid);
        evidenceList.push({
          trace_id: tid,
          document_id: (snap.document_id as string) || '',
          chunk_id: (snap.chunk_id as string) || '',
          claim_text: (snap.claim_text as string) || '',
          quote: (snap.quote as string) || '',
          citation_text: (snap.citation_text as string) || '',
        });
      }
    }
  }

  return { evidence: evidenceList, citations: citationList };
}

function classifyError(err: unknown): { status: number; message: string } {
  if (typeof err !== 'object' || err === null) {
    return { status: 0, message: '未知错误' };
  }
  const e = err as Record<string, unknown>;

  if (e.code === 'ECONNABORTED' || e.code === 'ETIMEDOUT') {
    return {
      status: 0,
      message: '请求超时。请注意：服务端可能已完成处理，但因为超时未能返回结果。请勿重复提交，可尝试刷新页面查看运行记录。',
    };
  }
  if (e.code === 'ERR_NETWORK' || e.message === 'Network Error') {
    return { status: 0, message: '网络连接失败，请检查网络后重试。' };
  }

  const resp = e.response as Record<string, unknown> | undefined;
  if (resp) {
    const status = (resp.status as number) || 0;
    const data = resp.data as Record<string, unknown> | undefined;
    const detail = (data?.detail as string) || (data?.message as string) || '';
    const serverMsg = (e.message as string) || '';

    switch (status) {
      case 400:
        return { status, message: detail || '输入不合法，请检查研究问题后重试。' };
      case 401:
        return { status, message: '登录已过期，请重新登录。' };
      case 403:
        return { status, message: '您没有权限执行此操作。' };
      case 404:
        return { status, message: '研究课题或文献不存在。' };
      case 409:
        return { status, message: detail || '状态冲突，该工作流可能已在执行中。' };
      case 422:
        return { status, message: detail || '输入格式校验失败，请检查后重试。' };
      case 429:
        return { status, message: '请求过于频繁，请稍后再试。' };
      default:
        if (status >= 500) {
          return { status, message: detail || '服务端错误，请稍后重试。' };
        }
        return { status, message: detail || serverMsg || `请求失败 (${status})` };
    }
  }

  return { status: 0, message: (e.message as string) || '未知错误' };
}

// ============================================================================
// Composable
// ============================================================================

export function useResearchWorkflow(projectId: () => string) {
  // ---- Session ----
  const session = ref<ResearchSession | null>(null);
  const sessionLoading = ref(false);
  const sessionError = ref<string>('');
  const notFound = ref(false);

  // ---- Question ----
  const question = ref('');

  // ---- Step state machine ----
  const stepState = ref<StepState>('question');
  const currentStepIndex = ref(0); // 0=question, 1=selection, 2+=submitting/evidence/report
  const submitting = ref(false);
  const submitError = ref('');
  const submitStatusCode = ref(0);

  // ---- Workflow result ----
  const workflowResult = ref<Record<string, unknown> | null>(null);
  const steps = ref<WorkflowStep[]>([]);
  const evidenceList = ref<WorkflowEvidence[]>([]);
  const citationList = ref<WorkflowCitation[]>([]);
  const report = ref<WorkflowReport | null>(null);
  const runId = ref('');
  const workflowSuccess = ref(false);

  // ---- Action state ----
  const saving = ref(false);
  const savingMessage = ref('');
  const citationSaveState = ref<Record<string, 'idle' | 'saving' | 'saved'>>({});

  // ---- Dedup ----
  let reqId = 0;
  let submitToken = 0;

  // ---- Derived ----
  const hasEvidence = computed(() => evidenceList.value.length > 0);
  const hasReport = computed(() => report.value !== null);
  const canSubmit = computed(() => question.value.trim().length > 0 && !submitting.value);

  // ---- Session loading ----
  async function loadSession() {
    const id = projectId();
    if (!id || id === 'undefined' || id === 'null') {
      notFound.value = true;
      return;
    }

    const myReqId = ++reqId;
    sessionLoading.value = true;
    sessionError.value = '';
    notFound.value = false;
    session.value = null;

    try {
      const { data } = await api.get(`/api/v1/workspace/sessions/${id}`);
      if (myReqId !== reqId) return;
      const raw = (data.data ?? data) as Record<string, unknown>;
      session.value = {
        id: String(raw.id || ''),
        title: String(raw.title || '未命名研究'),
        context_notes: typeof raw.context_notes === 'string' ? raw.context_notes : null,
      };
    } catch (e: unknown) {
      if (myReqId !== reqId) return;
      const status = (e as any)?.response?.status;
      if (status === 404) {
        notFound.value = true;
      } else {
        sessionError.value = classifyError(e).message;
      }
    } finally {
      if (myReqId === reqId) {
        sessionLoading.value = false;
      }
    }
  }

  // ---- Pending question from sessionStorage ----
  function readPendingQuestion(): string | null {
    const id = projectId();
    if (!id) return null;
    const key = makeStorageKey(id);
    try {
      const stored = sessionStorage.getItem(key);
      if (stored) {
        sessionStorage.removeItem(key);
        return stored;
      }
    } catch {
      // sessionStorage unavailable
    }
    return null;
  }

  function initPendingQuestion() {
    const pending = readPendingQuestion();
    if (pending) {
      question.value = pending;
    }
  }

  // ---- Workflow submission ----
  async function submitWorkflow() {
    const id = projectId();
    const topic = question.value.trim();
    if (!id || !topic) return;

    const token = ++submitToken;
    submitting.value = true;
    submitError.value = '';
    submitStatusCode.value = 0;
    stepState.value = 'submitting';
    currentStepIndex.value = 2;

    try {
      const { data } = await api.post(
        '/api/v4/research/workflow',
        {
          session_id: id,
          topic,
          workflow_type: 'full_research_flow',
        },
        { timeout: 120000 },
      );

      if (token !== submitToken) return;

      workflowSuccess.value = data.success === true;

      if (!data.success) {
        const serverSteps = (data.data?.steps as WorkflowStep[]) || [];
        steps.value = serverSteps;
        submitError.value = data.message || '工作流执行失败';
        stepState.value = 'error';
        return;
      }

      workflowResult.value = data.data as Record<string, unknown>;
      runId.value = (data.data?.run_id as string) || '';
      steps.value = (data.data?.steps as WorkflowStep[]) || [];

      // Fetch runs for evidence/report
      await fetchRuns();

      if (token !== submitToken) return;

      if (hasEvidence.value || hasReport.value) {
        stepState.value = 'evidence';
        currentStepIndex.value = 3;
      } else {
        // Workflow succeeded but no evidence found
        submitError.value = '工作流已完成，但未找到相关文献证据。';
        stepState.value = 'evidence'; // still let user review (with warning)
        currentStepIndex.value = 3;
      }
    } catch (e: unknown) {
      if (token !== submitToken) return;
      const { status, message } = classifyError(e);
      submitStatusCode.value = status;

      // For timeout: workflow may have completed server-side
      if (status === 0 && message.includes('超时')) {
        submitError.value = message;
        // Try to fetch runs in case the server completed
        try {
          await fetchRuns();
          if (runId.value) {
            stepState.value = 'evidence';
            currentStepIndex.value = 3;
            return;
          }
        } catch {
          // fall through to error
        }
      }

      submitError.value = message;
      stepState.value = 'error';
    } finally {
      if (token === submitToken) {
        submitting.value = false;
      }
    }
  }

  // ---- Fetch runs ----
  async function fetchRuns() {
    const id = projectId();
    if (!id) return;

    const { data } = await api.get(`/api/v4/research/session/${id}/runs`);
    const runs = (data.data?.runs ?? []) as Record<string, unknown>[];

    // Find the latest run
    const sorted = [...runs].sort((a, b) =>
      (b.completed_at as string || '').localeCompare(a.completed_at as string || ''),
    );
    const lastRun = sorted[0];

    if (lastRun) {
      if (!runId.value) {
        runId.value = (lastRun.run_id as string) || '';
      }

      const artifacts = lastRun.output_artifacts as Record<string, unknown> | undefined;
      const markdown = (artifacts?.markdown as string) || '';
      const completedAt = (lastRun.completed_at as string) || null;
      const topic = (lastRun.topic as string) || question.value;

      // Count evidence and citations
      const { evidence, citations } = extractEvidenceFromRuns(runs);
      evidenceList.value = evidence;
      citationList.value = citations;

      report.value = {
        run_id: runId.value,
        topic,
        title: artifacts?.title as string || `研究报告：${topic}`,
        markdown,
        completed_at: completedAt,
        artifact_id: (artifacts?.artifact_id as string) || '',
        evidence_count: evidence.length,
        citation_count: citations.length,
      };
    }
  }

  // ---- Retry ----
  function retry() {
    submitError.value = '';
    submitStatusCode.value = 0;
    stepState.value = 'question';
    currentStepIndex.value = 0;
    // Keep user input
    submitting.value = false;
  }

  // ---- Step navigation ----
  function goToQuestion() {
    if (submitting.value) return;
    stepState.value = 'question';
    currentStepIndex.value = 0;
    submitError.value = '';
  }

  function goToSelection() {
    if (submitting.value || !question.value.trim()) return;
    stepState.value = 'selection';
    currentStepIndex.value = 1;
  }

  function goToEvidence() {
    if (submitting.value) return;
    stepState.value = 'evidence';
    currentStepIndex.value = 3;
  }

  function goToReport() {
    if (submitting.value) return;
    stepState.value = 'report';
    currentStepIndex.value = 4;
  }

  // ---- Citation save ----
  async function saveCitation(ev: WorkflowEvidence) {
    const id = projectId();
    if (!id || !ev.trace_id) return;

    citationSaveState.value = { ...citationSaveState.value, [ev.trace_id]: 'saving' };
    try {
      await api.post(`/api/v1/workspace/sessions/${id}/citations`, {
        trace_json: JSON.stringify({
          trace_id: ev.trace_id,
          claim_text: ev.claim_text,
          quote: ev.quote,
          citation_text: ev.citation_text,
          document_id: ev.document_id,
        }),
        citation_text: ev.citation_text || ev.claim_text || ev.quote || '—',
        source_document: ev.document_id || 'unknown',
      });
      citationSaveState.value = { ...citationSaveState.value, [ev.trace_id]: 'saved' };
    } catch {
      // silently fail
    } finally {
      if (citationSaveState.value[ev.trace_id] === 'saving') {
        citationSaveState.value = { ...citationSaveState.value, [ev.trace_id]: 'idle' };
      }
    }
  }

  // ---- Note save ----
  async function saveNote(content: string, entityId?: string): Promise<boolean> {
    const id = projectId();
    if (!id || !content.trim()) return false;

    saving.value = true;
    savingMessage.value = '';
    try {
      await api.post(`/api/v1/workspace/sessions/${id}/notes`, {
        content: content.trim(),
        entity_type: 'v4_research_workflow',
        entity_id: entityId || runId.value || id,
        tags: 'V4研究',
      });
      savingMessage.value = '笔记已保存';
      return true;
    } catch {
      savingMessage.value = '笔记保存失败';
      return false;
    } finally {
      saving.value = false;
    }
  }

  // ---- Reset (start new workflow) ----
  function reset() {
    submitToken++;
    question.value = '';
    stepState.value = 'question';
    currentStepIndex.value = 0;
    submitting.value = false;
    submitError.value = '';
    submitStatusCode.value = 0;
    workflowResult.value = null;
    steps.value = [];
    evidenceList.value = [];
    citationList.value = [];
    report.value = null;
    runId.value = '';
    workflowSuccess.value = false;
    citationSaveState.value = {};
    savingMessage.value = '';
  }

  // ---- Cleanup ----
  onBeforeUnmount(() => {
    reqId = -1;
    submitToken = -1;
  });

  return {
    // Session
    session,
    sessionLoading,
    sessionError,
    notFound,
    loadSession,

    // Question
    question,
    initPendingQuestion,

    // Step state
    stepState,
    currentStepIndex,
    submitting,
    submitError,
    submitStatusCode,
    canSubmit,

    // Workflow result
    steps,
    evidenceList,
    citationList,
    report,
    runId,
    workflowSuccess,
    hasEvidence,
    hasReport,

    // Actions
    submitWorkflow,
    retry,
    goToQuestion,
    goToSelection,
    goToEvidence,
    goToReport,
    reset,

    // Save
    saving,
    savingMessage,
    saveCitation,
    saveNote,
    citationSaveState,
  };
}
