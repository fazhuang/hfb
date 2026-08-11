/**
 * usePrototypeDraft — Phase 2 prototype draft state machine.
 *
 * Owns the temp-key → canonical-key migration for the 4-page prototype flow:
 *   Page 1: Anonymous user writes question → sessionStorage hfb_temp_pending_question
 *   Page 2: Login + project select → 3-step deterministic migration
 *   Page 3: Read canonical key → submit workflow
 *   Page 4: Result → Reader jump for readerAddressable entries
 *
 * Contract:
 *   - Temp key: hfb_temp_pending_question (no projectId, anonymous)
 *   - Canonical key: hfb.research.<projectId>.pending-question (per-project)
 *   - Migration: write canonical → read-verify → destroy temp + verify (exactly 3 steps, all physically verified)
 *   - Detection: readerAddressable = !!document_id && !!chunk_id
 *   - Max question length: 2000 chars
 *   - Never read cross-project: canonical key always scoped to projectId
 *
 * Does NOT:
 *   - Modify backend API
 *   - Persist beyond sessionStorage lifetime
 *   - Share keys between projects
 */

import { ref, computed } from 'vue';

// ============================================================================
// Constants
// ============================================================================

const TEMP_KEY = 'hfb_temp_pending_question';
const CANONICAL_KEY_PREFIX = 'hfb.research.';
const CANONICAL_KEY_SUFFIX = '.pending-question';
const MAX_QUESTION_LENGTH = 2000;

// ============================================================================
// Types
// ============================================================================

export interface DraftMigrationStep {
  name: string;
  status: 'idle' | 'running' | 'done' | 'failed';
  detail?: string;
}

export type MigrationState = 'idle' | 'writing' | 'reading' | 'destroying' | 'done' | 'failed';

// ============================================================================
// Helpers
// ============================================================================

/** UUID v4 pattern — exact length and hex positions, no regex DOS surface. */
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

function guardId(raw: string): string {
  const trimmed = raw.trim();
  if (!UUID_RE.test(trimmed)) {
    throw new Error(`Invalid project id — expected UUID v4, got ${JSON.stringify(raw.slice(0, 64))}`);
  }
  return trimmed;
}

function makeCanonicalKey(projectId: string): string {
  return `${CANONICAL_KEY_PREFIX}${guardId(projectId)}${CANONICAL_KEY_SUFFIX}`;
}

// ============================================================================
// Composable
// ============================================================================

export function usePrototypeDraft() {
  // ---- Temp key (anonymous) ----
  const tempQuestion = ref('');
  const tempExists = ref(false);

  // ---- Canonical key (per-project) ----
  const canonicalQuestion = ref('');

  // ---- Migration state machine ----
  const migrationState = ref<MigrationState>('idle');
  const migrationSteps = ref<[DraftMigrationStep, DraftMigrationStep, DraftMigrationStep]>([
    { name: '写入并校验', status: 'idle' },
    { name: '读取比对', status: 'idle' },
    { name: '销毁并校验', status: 'idle' },
  ]);
  const migrationError = ref('');

  // ---- Derived ----
  const canMigrate = computed(() => tempExists.value);
  const migrationDone = computed(() => migrationState.value === 'done');
  const hasCanonicalQuestion = computed(() => canonicalQuestion.value.trim().length > 0);

  // ==========================================================================
  // Temp key operations
  // ==========================================================================

  /** Write anonymous question to temp key. Returns false if sessionStorage unavailable. */
  function writeTempQuestion(question: string): boolean {
    const trimmed = question.trim().slice(0, MAX_QUESTION_LENGTH);
    if (!trimmed) {
      tempQuestion.value = '';
      tempExists.value = false;
      return false;
    }
    try {
      sessionStorage.setItem(TEMP_KEY, trimmed);
      tempQuestion.value = trimmed;
      tempExists.value = true;
      return true;
    } catch {
      return false;
    }
  }

  /** Read temp key and populate local state. Does NOT destroy the key. */
  function readTempQuestion(): string | null {
    try {
      const stored = sessionStorage.getItem(TEMP_KEY);
      if (stored) {
        tempQuestion.value = stored;
        tempExists.value = true;
        return stored;
      }
    } catch {
      // sessionStorage unavailable
    }
    tempQuestion.value = '';
    tempExists.value = false;
    return null;
  }

  /** Destroy temp key (step 3 of migration). */
  function destroyTempQuestion(): boolean {
    try {
      sessionStorage.removeItem(TEMP_KEY);
      tempQuestion.value = '';
      tempExists.value = false;
      return true;
    } catch {
      return false;
    }
  }

  // ==========================================================================
  // Canonical key operations
  // ==========================================================================

  /** Write to canonical key for specific project. */
  function writeCanonicalQuestion(projectId: string, question: string): boolean {
    try {
      const key = makeCanonicalKey(projectId);
      sessionStorage.setItem(key, question.trim().slice(0, MAX_QUESTION_LENGTH));
      canonicalQuestion.value = question.trim();
      return true;
    } catch {
      return false;
    }
  }

  /** Read canonical key for specific project. */
  function readCanonicalQuestion(projectId: string): string | null {
    try {
      const key = makeCanonicalKey(projectId);
      const stored = sessionStorage.getItem(key);
      if (stored) {
        canonicalQuestion.value = stored;
        return stored;
      }
    } catch {
      // sessionStorage unavailable
    }
    canonicalQuestion.value = '';
    return null;
  }

  /** Clear canonical key for specific project. */
  function clearCanonicalQuestion(projectId: string): void {
    try {
      const key = makeCanonicalKey(projectId);
      sessionStorage.removeItem(key);
      canonicalQuestion.value = '';
    } catch {
      // sessionStorage unavailable
    }
  }

  // ==========================================================================
  // 3-step deterministic migration
  // ==========================================================================

  /**
   * Execute the 3-step deterministic migration with physical verification:
   *   1. Write to hfb.research.<projectId>.pending-question
   *   2. Read-verify the canonical key matches what was written
   *   3. Destroy hfb_temp_pending_question AND verify destruction
   *
   * Returns the migrated question string on success, null on failure.
   * Steps are sequential — each step must physically verify before proceeding.
   * ANY step failure (including destroy-verify) sets migrationState=failed.
   * Only all 3 steps physically verified → migrationState=done.
   */
  function migrateTempToCanonical(projectId: string): string | null {
    // Reset
    migrationState.value = 'idle';
    migrationError.value = '';
    migrationSteps.value.forEach((s) => {
      s.status = 'idle';
      s.detail = '';
    });

    const [step1, step2, step3] = migrationSteps.value;

    // ---- Step 1: Write canonical key ----
    migrationState.value = 'writing';
    step1.status = 'running';
    let temp: string | null = null;
    try {
      temp = sessionStorage.getItem(TEMP_KEY);
    } catch {
      step1.status = 'failed';
      step1.detail = '无法读取临时草稿（存储不可用）';
      migrationError.value = '草稿迁移失败：浏览器存储不可用。请检查浏览器设置。';
      migrationState.value = 'failed';
      return null;
    }
    if (!temp || !temp.trim()) {
      step1.status = 'failed';
      step1.detail = '临时草稿不存在或为空';
      migrationError.value = '未找到临时草稿。请返回首页输入研究问题。';
      migrationState.value = 'failed';
      return null;
    }

    const canonicalKey = makeCanonicalKey(projectId);
    try {
      sessionStorage.setItem(canonicalKey, temp.trim().slice(0, MAX_QUESTION_LENGTH));
    } catch {
      step1.status = 'failed';
      step1.detail = '浏览器存储不可用';
      migrationError.value = '草稿迁移失败：浏览器存储不可用。请检查浏览器设置。';
      migrationState.value = 'failed';
      return null;
    }
    step1.status = 'done';
    step1.detail = `写入成功 (${temp.length} 字)`;

    // ---- Step 2: Read-verify canonical key ----
    migrationState.value = 'reading';
    step2.status = 'running';
    let verified: string | null = null;
    try {
      verified = sessionStorage.getItem(canonicalKey);
    } catch {
      step2.status = 'failed';
      step2.detail = '存储读取失败';
      migrationError.value = '草稿校验失败：无法读取已写入的草稿。';
      migrationState.value = 'failed';
      return null;
    }
    if (verified !== temp) {
      step2.status = 'failed';
      step2.detail = `校验不匹配 (期望 ${temp.length} 字, 实际 ${verified ? verified.length : 0} 字)`;
      migrationError.value = '草稿校验失败：写入内容与读取内容不匹配。请重试。';
      migrationState.value = 'failed';
      return null;
    }
    step2.status = 'done';
    step2.detail = '读取校验通过';
    canonicalQuestion.value = verified;

    // ---- Step 3: Destroy temp key AND verify destruction ----
    migrationState.value = 'destroying';
    step3.status = 'running';
    try {
      sessionStorage.removeItem(TEMP_KEY);
      // Physical verification: destruction MUST be confirmed
      if (sessionStorage.getItem(TEMP_KEY) !== null) {
        // Destruction failed — MUST set failed, NEVER done
        step3.status = 'failed';
        step3.detail = '临时草稿清理失败：移除后仍然存在';
        migrationError.value = '临时草稿清理失败，请手动清除浏览器存储。';
        migrationState.value = 'failed';
        tempQuestion.value = '';
        tempExists.value = false;
        return null;
      }
    } catch {
      step3.status = 'failed';
      step3.detail = '临时草稿清理失败：存储不可用';
      migrationError.value = '临时草稿清理失败，请手动清除浏览器存储。';
      migrationState.value = 'failed';
      return null;
    }
    step3.status = 'done';
    step3.detail = '已清除临时草稿并校验通过';
    tempQuestion.value = '';
    tempExists.value = false;

    // Only when all 3 steps physically verified → done
    migrationState.value = 'done';
    return temp;
  }

  // ==========================================================================
  // readerAddressable detection
  // ==========================================================================

  /**
   * An evidence/citation entry is reader-addressable when:
   *   - document_id is non-empty (identifies a document in the library)
   *   - chunk_id is non-empty (identifies a specific passage)
   *
   * The Reader route is: /reader/:documentId#chunk-<chunk_id>
   */
  function isReaderAddressable(documentId: string, chunkId: string): boolean {
    return !!documentId && !!chunkId && documentId.length > 0 && chunkId.length > 0;
  }

  /** Build Reader jump URL from evidence. Returns null if not addressable. */
  function buildReaderUrl(
    documentId: string,
    chunkId: string,
  ): string | null {
    if (!isReaderAddressable(documentId, chunkId)) return null;
    const chunkFragment = chunkId.startsWith('chunk-') ? chunkId : `chunk-${chunkId}`;
    return `/reader/${encodeURIComponent(documentId)}#${encodeURIComponent(chunkFragment)}`;
  }

  // ==========================================================================
  // Init
  // ==========================================================================

  /** Initialize — check temp key on mount. */
  function init() {
    readTempQuestion();
  }

  return {
    // Temp key
    tempQuestion,
    tempExists,
    writeTempQuestion,
    readTempQuestion,
    destroyTempQuestion,

    // Canonical key
    canonicalQuestion,
    writeCanonicalQuestion,
    readCanonicalQuestion,
    clearCanonicalQuestion,

    // Migration
    migrationState,
    migrationSteps,
    migrationError,
    migrateTempToCanonical,
    canMigrate,
    migrationDone,

    // readerAddressable
    isReaderAddressable,
    buildReaderUrl,

    // Init
    init,
    hasCanonicalQuestion,

    // Constants
    MAX_QUESTION_LENGTH,
  };
}
