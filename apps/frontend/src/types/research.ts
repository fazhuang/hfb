/** Shared research types used across research components and pages. */

/**
 * ResearchProjectSummary — 研究课题列表项
 *
 * 产品层名称：研究课题
 * 后端实体名称：ResearchSession
 * 当前路由参数 projectId 实际承载 ResearchSession.id
 *
 * This is NOT a separate database entity. It is a view-model mapped from
 * the ResearchSession aggregate root — the only research-scoping entity
 * in the current system. There is no independent Project table, Project
 * model, or project_id column.
 */
export interface ResearchProjectSummary {
  /** ResearchSession.id — UUID, the sole identifier for routing and lookups */
  id: string;
  /** ResearchSession.title */
  title: string;
  /** ResearchSession.description — NOT present in current API response.
   *  Optional because the backend does not provide this field. */
  description?: string | null;
  /** ISO timestamp from ResearchSession.created_at */
  created_at: string | null;
  /** ISO timestamp from ResearchSession.updated_at */
  updated_at: string | null;
}

/**
 * ResearchProjectDetail — 研究课题详情
 *
 * Mapped from GET /api/v1/workspace/sessions/{session_id} response
 * (_session_dict). Contains all fields the backend returns for a
 * single-session lookup beyond the list-summary fields.
 *
 * No independent Project entity exists. This is the ResearchSession
 * aggregate root viewed through the product-layer "研究课题" lens.
 */
export interface ResearchProjectDetail {
  /** ResearchSession.id — UUID */
  id: string;
  /** ResearchSession.title */
  title: string;
  /** ResearchSession.context_notes — Markdown research notes */
  context_notes?: string | null;
  /** ResearchSession.created_at ISO timestamp */
  created_at: string | null;
  /** ResearchSession.updated_at ISO timestamp */
  updated_at: string | null;
}

/**
 * Map a raw _session_dict API response object to ResearchProjectDetail.
 *
 * Centralised mapping — never duplicated across components.
 */
export function toProjectDetail(raw: Record<string, unknown>): ResearchProjectDetail {
  return {
    id: String(raw.id || ''),
    title: String(raw.title || ''),
    context_notes: typeof raw.context_notes === 'string' ? raw.context_notes : null,
    created_at: typeof raw.created_at === 'string' ? raw.created_at : null,
    updated_at: typeof raw.updated_at === 'string' ? raw.updated_at : null,
  };
}

// ============================================================================
// Research Workspace — supplementary types
// ============================================================================

/**
 * ResearchCitationSummary — 研究资源/引用摘要
 *
 * Mapped from GET /api/v1/workspace/sessions/{id}/citations response
 * (_citation_dict). Used in ResearchWorkspacePage research-resources block.
 */
export interface ResearchCitationSummary {
  id: string;
  session_id: string;
  citation_text: string;
  source_document: string;
  tags?: string | null;
  notes?: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/**
 * Map a raw _citation_dict API response object to ResearchCitationSummary.
 */
export function toCitationSummary(raw: Record<string, unknown>): ResearchCitationSummary {
  return {
    id: String(raw.id || ''),
    session_id: String(raw.session_id || ''),
    citation_text: String(raw.citation_text || ''),
    source_document: String(raw.source_document || ''),
    tags: typeof raw.tags === 'string' ? raw.tags : null,
    notes: typeof raw.notes === 'string' ? raw.notes : null,
    created_at: typeof raw.created_at === 'string' ? raw.created_at : null,
    updated_at: typeof raw.updated_at === 'string' ? raw.updated_at : null,
  };
}
