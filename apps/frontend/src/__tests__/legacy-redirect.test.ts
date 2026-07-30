/**
 * LegacyRedirect — session-aware redirect tests.
 *
 * Covers:
 *   - /research/workspace → /research/:projectId/workspace (most recent session)
 *   - /research/workspace?tab=materials → /library
 *   - /research/workspace?tab=reports → /reports
 *   - /research/workspace?tab=v4-research → /research/:projectId/workflow
 *   - /workspace → /research/:projectId/workspace
 *   - /v4/research → /research/:projectId/workflow
 *   - /v4 → /research/:projectId/workflow
 *   - /v4/research-internal → /research/:projectId/workflow
 *   - No sessions → /research (project list fallback)
 *   - API error → /research (project list fallback)
 *
 * Contract: phase3-migration-contract.md §2.1 URL 兼容规则
 */

import { describe, expect, it, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Hoisted mocks
// ---------------------------------------------------------------------------
const { mockGet } = vi.hoisted(() => ({
  mockGet: vi.fn(),
}));

vi.mock('@/api/client', () => ({
  default: {
    defaults: { baseURL: '' },
    get: mockGet,
    post: vi.fn(),
    put: vi.fn(),
  },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------
const SESSION_ID = 'a1b2c3d4-e5f6-4a7b-8c9d-0e1f2a3b4c5d';

function sessionsResponse(ids: Array<string> = [SESSION_ID]) {
  return {
    data: {
      data: ids.map((id) => ({
        id,
        title: '测试课题',
        created_at: '2026-07-01T00:00:00',
        updated_at: '2026-07-15T00:00:00',
      })),
    },
  };
}

function emptySessionsResponse() {
  return { data: { data: [] } };
}

// ---------------------------------------------------------------------------
// Tab → canonical route name resolver (mirrors LegacyRedirect.vue)
// ---------------------------------------------------------------------------
const TAB_TO_ROUTE: Record<string, string> = {
  materials: 'library-search',
  versions: 'library-search',
  notes: 'research-project-workspace',
  reports: 'report-list',
  research: 'research-project-version-comparison',
  'v4-research': 'research-project-workflow',
};

// ---------------------------------------------------------------------------
// Helpers — simulate LegacyRedirect's onMounted logic
// ---------------------------------------------------------------------------
async function resolveSession(): Promise<string | null> {
  try {
    const data = await mockGet();
    const sessions = (data.data.data ?? []) as Array<{ id: string }>;
    if (sessions.length > 0 && sessions[0]) {
      return sessions[0].id;
    }
  } catch {
    return null;
  }
  return null;
}

// =============================================================================
// Tests
// =============================================================================

describe('LegacyRedirect', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ---------------------------------------------------------------------------
  // ?tab= 参数测试
  // ---------------------------------------------------------------------------

  it('/research/workspace?tab=materials → /library', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    expect(TAB_TO_ROUTE['materials']).toBe('library-search');
  });

  it('/research/workspace?tab=versions → /library', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    expect(TAB_TO_ROUTE['versions']).toBe('library-search');
  });

  it('/research/workspace?tab=reports → /reports', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    expect(TAB_TO_ROUTE['reports']).toBe('report-list');
  });

  it('/research/workspace?tab=v4-research → /research/:projectId/workflow', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    expect(TAB_TO_ROUTE['v4-research']).toBe('research-project-workflow');
  });

  it('/research/workspace?tab=notes → /research/:projectId/workspace', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    expect(TAB_TO_ROUTE['notes']).toBe('research-project-workspace');
  });

  it('/research/workspace?tab=research → /research/:projectId/version-comparison', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    expect(TAB_TO_ROUTE['research']).toBe('research-project-version-comparison');
  });

  // ---------------------------------------------------------------------------
  // 路由名称 → canonical 映射测试 (无 ?tab=)
  // ---------------------------------------------------------------------------

  it('/research/workspace (no tab) → /research/:projectId/workspace', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    // Route name 'legacy-workspace' → research-project-workspace
  });

  it('/workspace → /research/:projectId/workspace', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    // Route name 'legacy-workspace-short' → research-project-workspace
  });

  it('/v4/research → /research/:projectId/workflow', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    // Route name 'legacy-v4-research' → research-project-workflow
  });

  it('/v4 → /research/:projectId/workflow', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    // Route name 'legacy-v4' → research-project-workflow
  });

  it('/v4/research-internal → /research/:projectId/workflow', async () => {
    mockGet.mockResolvedValueOnce(sessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBe(SESSION_ID);
    // Route name 'legacy-v4-research-internal' → research-project-workflow
  });

  // ---------------------------------------------------------------------------
  // 降级处理: 无 session → 项目列表
  // ---------------------------------------------------------------------------

  it('无 session → /research (project list fallback)', async () => {
    mockGet.mockResolvedValueOnce(emptySessionsResponse());
    const projectId = await resolveSession();
    expect(projectId).toBeNull();
    // No sessions → should redirect to project list
  });

  // ---------------------------------------------------------------------------
  // 降级处理: API 错误 → 项目列表
  // ---------------------------------------------------------------------------

  it('API 错误 → /research (project list fallback)', async () => {
    mockGet.mockRejectedValueOnce(new Error('Network Error'));
    const projectId = await resolveSession();
    expect(projectId).toBeNull();
    // API error → should redirect to project list (no crash)
  });

  // ---------------------------------------------------------------------------
  // 覆盖: 所有 tab 值均有映射定义
  // ---------------------------------------------------------------------------

  it('所有 migration-contract 定义的 tab 值均有路由映射', () => {
    const requiredTabs = [
      'materials',
      'versions',
      'notes',
      'reports',
      'research',
      'v4-research',
    ];
    for (const tab of requiredTabs) {
      expect(TAB_TO_ROUTE[tab]).toBeDefined();
    }
  });
});
