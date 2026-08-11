---
title: 'ADR-0012 皇甫谧研究域主锚点准入与三态隔离机制'
document_id: HFB-ADR-0012
version: '1.0.0'
status: Approved
date: 2026-08-10
decision_date: '2026-08-10'
last_updated: '2026-08-10'
owner: 'Academic Committee & Architecture Team'
domain: 'domain-admission'
related:
  - 'docs/00-governance/0001-project-charter.md'
  - 'docs/08-domain/0801_Person_Knowledge_Model.md'
  - 'docs/04-ai/0403_GraphRAG_Specification.md'
  - 'docs/03-data/0305_Relation_Specification.md'
---

# ADR-0012：皇甫谧研究域主锚点准入与三态隔离机制

## Status

**Approved** — 已通过学术委员会与架构组联合终审（2026-08-10）。

## Context

根据《项目治理宪章》（`docs/00-governance/0001-project-charter.md`），本平台的核心研究对象明确界定为皇甫谧及其核心文献《针灸甲乙经》。

在前期数据抽取与关系图谱构建过程中，由于缺乏严格的领域准入边界与锚点可达性约束，大量无域归属实体（例如通用历史人物、非相关地理节点、无确切证据链接的跨领域实体）被引入知识图谱。这导致以下关键痛点：
1. **GraphRAG 语义漂移（Semantic Drift）**：在 RAG 上下文检索与图漫游时，检索路径扩散至无关节点，引发 AI 响应生成偏离学术主题。
2. **图谱无序膨胀与计算开销上升**：未受限的关联节点降低了图数据库索引效能，增加了子图抽取与向量检索的噪音。
3. **未考证假说的污染**：缺乏隔离机制使得未经充分考据的待考数据直接暴露给全局 RAG 和匿名视图。

为此，必须明确以皇甫谧为中心的研究域准入规范，建立图拓扑级别的锚点约束与三态隔离生命周期。

## Decision

经架构组与学术委员会研究，决定实施以下五项核心准入与隔离决策：

### 1. 唯一主锚点固定 (Primary Domain Anchor)
固定 **皇甫谧** (`person:huangfu_mi` / `ENTITY-PER-0001`) 作为整个平台研究域的全局唯一主锚点。平台内所有知识实体（Person、Book、Location 等）及关系的准入合法性，均需基于其与主锚点的图拓扑可达性与学术关联度进行判定。

### 2. 三态隔离模型 (Tri-State Lifecycle Isolation)
所有入库的数据实体及实体间关系统一采用三态隔离机制管理：
- **`pending`（待考）**：新录入、人工草稿或暂未建立可靠主锚点证据链的实体与关系。
- **`verified`（已验证）**：通过古籍证据校验、符合主锚点可达性约束并通过学术审核的正式实体与关系。
- **`excluded`（排除）**：经考据认定为与皇甫谧及《针灸甲乙经》无关、伪作或被废弃的节点与关系。

### 3. 强约束锚点可达路径步长 $N \le 3$ 与预计算 `anchor_path`
- **步长硬约束**：实体/关系获准标记为 `verified` 的硬性必要条件之一为：在图拓扑中必须存在至少一条连接至主锚点 `ENTITY-PER-0001` 的有效关系链，且最短路径步长 $N \le 3$（即：主锚点 $\xrightarrow{1}$ 邻接实体 $\xrightarrow{2}$ 二度实体 $\xrightarrow{3}$ 三度实体）。
- **预计算与持久化**：在审核发布（Publish）阶段，后台图计算引擎负责校验可达性，并将计算所得的锚点可达路径序列预计算持久化保存于实体的 `anchor_path` 字段中（例如：`["ENTITY-PER-0001", "REL-0023", "ENTITY-PER-0042"]`），避免在线检索时的漫游开销。

### 4. 古籍证据分级隔离与撤销自动降级机制
- **分级隔离**：学术层面的古籍证据分级（A级-正史/原典，B级-类书/地方志，C级-后世论著/野史）与底层存储引擎中 `EntityRelation.evidence_level` (0-4) 保持隔离与确定性映射。
- **动态降级**：当某一实体的支撑古籍证据被学术撤销、判定失效或删除时，系统自动触发可达性重新校验。若该实体失去所有满足 $N \le 3$ 的主锚点可达路径，其状态自动降级重置为 `pending`。

### 5. `pending` 数据检索隔离与 RAG 硬过滤屏蔽
- **特定工作台受控可见**：`pending` 状态的数据仅面向已登录且具备“研究员”或“管理员”权限的内部用户，在专用“待考工作台”（Pending Workbench）中提供显式过滤检索，用于学术协作研讨与考据补全。
- **全局 RAG 与 anonymous 视图硬硬过滤**：在全局 RAG 向量检索、GraphRAG 子图抽取、API 导出及匿名/普通访问视图中，底层必须在数据库与引擎层面实施硬过滤（例如 SQL/Cypher 查询显式附带 `WHERE status = 'verified'`），绝对禁止 `pending` 与 `excluded` 数据泄漏至生成式 AI 上下文中。

## Consequences

### Positive
- **根治 GraphRAG 漂移**：严格限制图漫游范围在皇甫谧 $N \le 3$ 拓扑邻域内，确保 AI 上下文的高相关性与学术严谨度。
- **控制图谱规模**：有效拦截无关噪音实体入库，显著提升图数据库查询与向量检索效率。
- **支持安全研讨**：三态隔离使得研究员可在 `pending` 区灵活录入待考假说与试探性关系，而不影响公开生产环境的稳定性。

### Negative
- **审核开销增加**：发布流程需集成 `anchor_path` 的拓扑计算与校验。
- **查询条件强制化**：所有检索与 RAG 接口必须统一注入状态硬过滤条件，需对全站查询层进行审计。

## Alternatives

| 方案 | 优点 | 缺点 | 结论 |
| :--- | :--- | :--- | :--- |
| **无锚点约束的全量混合图** | 无需拓扑计算 | GraphRAG 产生严重语义漂移，无关实体污染回答 | 拒绝 |
| **无步长限制 ($N \to \infty$) 的全连通** | 可覆盖任意远端实体 | 小世界网络导致几乎所有实体被关联，准入失效 | 拒绝 |
| **静态手工白名单** | 实现极简单 | 无法应对动态关系扩充与证据链自动追踪 | 拒绝 |
| **主锚点 $N \le 3$ 预计算 + 三态隔离 (本决策)** | 高准确度、可追溯、防漂移、支持学术协同 | 部署发布时需增加拓扑校验逻辑 | **采纳** |

## Implementation Plan

1. **Phase 0 (已完成)**：决策冻结与规范发布 (ADR-0012)。
2. **Phase 1 (进行中)**：更新 `docs/08-domain/0801_Person_Knowledge_Model.md`，定义 2.1 节领域准入与关系回溯规则。
3. **Phase 2**：更新元数据与实体关系规范（`0304_Entity_Specification.md`, `0305_Relation_Specification.md`），支持 `anchor_path` 与三态枚举。
4. **Phase 3**：后端与 AI pipeline 实施状态硬过滤及 `anchor_path` 预计算工具函数。
