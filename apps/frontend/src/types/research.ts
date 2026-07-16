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
