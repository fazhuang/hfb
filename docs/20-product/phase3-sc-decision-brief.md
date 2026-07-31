# Phase 3 Steering Committee 决策情况说明书

**目标 HEAD**: `eab6687`
**合同冻结基线**: `74cee05` — 2026-07-25
**准备日期**: 2026-07-30
**状态**: 等待指导委员会逐项书面决定

---

## 决策 A：教育模式与可视化工作流 — RELEASE_READY 的必要项？

### 当前状态

合同冻结日 2026-07-25（约五天前）将两项功能推迟至 `KnowledgeExplorerPage` 的后续 Sprint 实现，理由如下：

| 功能                                                                   | 旧版位置                                  | 推迟去向                          |
| ---------------------------------------------------------------------- | ----------------------------------------- | --------------------------------- |
| 教育模式 — 主题 + 级别（初级/中级/高级） → 概念学习（段落 + 引用计数） | `V4ResearchView.vue` education 标签页     | KnowledgeExplorerPage 后续 Sprint |
| 可视化工作流 — graph_type 选择（概念/引用/时间线/文档） → 知识图谱渲染 | `V4ResearchView.vue` visualization 标签页 | KnowledgeExplorerPage 后续 Sprint |

**自冻结以来规范前端方面没有任何变化**：

- `KnowledgeExplorerPage.vue`（627 行）是一个功能完整的**实体图谱浏览器**（搜索 → 邻域 → 子图 → 边证据检查）。它只调用 V1 图谱 API。它不渲染教育标签页、可视化工作流标签页、级别选择器或 graph_type 选择器。
- 标记为规范页面（`/knowledge`，路由名称 `knowledge-explorer`），对所有已认证用户可见，通过两个导航组件（`ResearchPrimaryNav` + `AppNavbar`）暴露。
- 旧版 `V4ResearchView.vue` 仍然存在于磁盘上（40KB），包含教育 + 可视化标签页及其 `POST /api/v4/education/learn` 和 `POST /api/v4/visualization/graph` 的客户端代码，但**未导入到任何路由中** — 没有 HTTP 路径可以从前端应用程序访问它。

### 每个选项的发布影响

|                       | 选项 1：保留为阻塞项                                                                       | 选项 2：从本版本发布范围排除                                                                |
| --------------------- | ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `/knowledge` 用户体验 | 继续缺少教育模式与可视化工作流这两项能力；现有实体图谱浏览器不受影响                       | 继续缺少教育模式与可视化工作流这两项能力；现有实体图谱浏览器不受影响                        |
| 旧版残留              | `V4ResearchView.vue` 保留在磁盘上；其路由已断开，标签页在规范知识页面中不可用              | `V4ResearchView.vue` 保留在磁盘上；是否可删除需等待其依赖图（遗留测试引用等）的单独回归评估 |
| 后端端点              | `/api/v4/education/learn` + `/api/v4/visualization/graph` 保持孤儿状态 — 由决策 B 另行处理 | 与决策 B 正交                                                                               |
| BLOCK_RELEASE         | **持续**直到两项能力在 `KnowledgeExplorerPage` 中实现                                      | **移除**（假设已提供书面排除并定义用户可见边界）                                            |
| Sprint 范围           | 需要规范 UI 设计 + 实现 + 测试                                                             | 教育 + 可视化不再属于 Phase 3 Sprint 范围                                                   |

### 所需的 SC 决定

> **"教育模式和可视化工作流 [ 是 / 不是 ] 本次 RELEASE_READY 的必要能力。如不是，授权排除并定义用户可见边界。"**

---

## 决策 B：`/api/v4/education/learn` 和 `/api/v4/visualization/graph` 的最终状态

### 当前状态

两个端点无条件挂载（`main.py:80` → `app.api.v4.__init__`），并在每个环境中公开提供。

| 端点                           | 路由                          | 方法 | 权限               | 有效调用方                                            |
| ------------------------------ | ----------------------------- | ---- | ------------------ | ----------------------------------------------------- |
| `education_learn`              | `/api/v4/education/learn`     | POST | `ai.read`（学生+） | 无 — 仅在已断开路由的 `V4ResearchView.vue:754` 中调用 |
| `generate_visualization_graph` | `/api/v4/visualization/graph` | POST | `ai.read`（学生+） | 无 — 仅在已断开路由的 `V4ResearchView.vue:792` 中调用 |

**调用方详情**：

- 没有规范前端 API 客户端模块（`apps/frontend/src/api/` 仅包含 `client.ts` + `graph.ts`；均未引用 V4 education 或 visualization）。
- `/api/v4/education/learn` 或 `/api/v4/visualization/graph` 在 `apps/frontend/src/` 的非测试、非旧版源代码中**零次命中**。
- 旧版测试文件 `v4-research.test.ts` 使用自己的测试路由器模型（包括 `V4ResearchView`）来测试它们，并针对 mock 服务器发出请求。E2E 测试不会命中这些端点。

**RBAC 范围**：`ai.read` 权限授予 Student+ 角色。在生产环境中，这意味着任何已认证用户都可以 POST 到这些端点 — 每个注册用户，而非仅仅是研究人员。

### 每个选项的发布影响

|                 | 选项 1：保留为内部兼容 API            | 选项 2：标记废弃                                  | 选项 3：纳入规范 UI                            |
| --------------- | ------------------------------------- | ------------------------------------------------- | ---------------------------------------------- |
| 端点状态        | Active、公开、无文档                  | 已弃用，包含 sunset 日期 + 退出计划               | Active → 获得调用方                            |
| 安全性          | `ai.read` 授权仍有可发现端点，无消费  | sunset 后移除，缩小攻击面                         | 与现状相同但合法                               |
| 前端工作        | 无                                    | 无（仅后端废弃头部 / OpenAPI 标记）               | 在 KnowledgeExplorer 中构建教育 + 可视化标签页 |
| 阻塞发布？      | 否 — 选项 1 明确声明端点有意保留      | 否 — 仅需声明即可发布；实际删除在后续进行         | **是** — 直到 UI 构建、测试并验证              |
| 与决策 A 的关系 | 正交：端点保留且无 UI；需产品明确认可 | 正交：若决策 A 接受缺失调用方，保持端点不产生价值 | 若决策 A 选择选项 1（阻塞），成为依赖项        |

### 所需的 SC 决定

> **"`/api/v4/education/learn` 和 `/api/v4/visualization/graph` 在本版本中的最终状态应声明为：[ 内部兼容 — 定义访问边界与退出计划 / 已弃用 — 定义删除前提 / 规范 UI — 在本次发布范围内实现 ]。"**

---

## 相关性索引

| 文件 / 位置                                                        | 相关性                                                                     |
| ------------------------------------------------------------------ | -------------------------------------------------------------------------- |
| `apps/frontend/src/pages/knowledge/KnowledgeExplorerPage.vue`      | 决策 A：唯一的规范知识页面 — 不包含教育或可视化标签页                      |
| `apps/frontend/src/views/V4ResearchView.vue`                       | 决策 A+B：断开连接的旧版组件，包含两个延迟功能唯一的调用方                 |
| `apps/frontend/src/router/index.ts:169-181,237-240`                | 决策 A：`/knowledge` 路由已激活 + `/v4/research-internal` → LegacyRedirect |
| `apps/frontend/src/components/layout/ResearchPrimaryNav.vue:92-97` | 决策 A：任何已认证用户均可发现知识图谱                                     |
| `apps/backend/app/api/v4/__init__.py`                              | 决策 B：两个端点均已上线并公开挂载                                         |
| `apps/backend/app/api/v4/education.py`                             | 决策 B：`POST /learn`，`ai.read` 权限，无规范调用方                        |
| `apps/backend/app/api/v4/visualization.py`                         | 决策 B：`POST /graph`，`ai.read` 权限，无规范调用方                        |
| `docs/20-product/phase3-migration-contract.md §3`                  | 决策 A+B：合同推迟声明 — 2026-07-25 冻结，未修订                           |
| `docs/20-product/phase3-migration-contract.md §6`                  | 决策 A：合同仍读取为 BLOCK_RELEASE                                         |

---

## 状态

- 等待决策 A：两项能力保留为发布必要项，或经书面批准排除出本版本范围。
- 等待决策 B：两个 V4 孤儿端点保留兼容、标记废弃，或纳入规范 UI。
- 3B/3C 仍等待真实的 Research Lead。

在指导委员会做出书面决定之前，不提出代码变更、旧版删除或合同更新。
