# Sprint 2.5 — UI 资产运营化执行计划

> **状态**：Review Draft；已纳入 Gemini 审计第一轮与 PO 裁决。
> **范围**：最小 MVP 的 Workspace、Workflow/Result/Reports、Library、Reader。
> **排除**：Knowledge Explorer、新业务/API/RBAC/数据模型、真实学术数据导入。
> **治理**：Codex 提出方案与独立验收；PO 作最终裁决；Claude 按原子卡实施。

## 1. 目标与当前判断

IA、研究主流程和主要页面迁移已形成可收敛的骨架。当前短板不是从零缺少 Design System：代码已有 token、Hfb 基础组件、组件标准和设计合规检查；短板是这些资产尚未形成可审计的采用账本、组件契约、跨页模式和真实研究者验证闭环。

本计划禁止以视觉进展替代生产准入。任一子项 PASS 均不改变整体 **`BLOCK_RELEASE`**，只有 HFB-PS-1710 的当前 HEAD 全量准入才可解除。

```text
轨道 A：发布质量门禁
测试收集/行为证据 → 静态质量 → 完整 1710 准入

轨道 B：Sprint 2.5 UI 资产
资产账本 → 组件契约 → 模式库 → 高保真收敛 → 研究生测试
```

**硬性卡口**：轨道 A 的 WP-0 未由 Codex PASS 前，轨道 B 只能做只读盘点、规范与候选研究；不得向主分支提交 UI/CSS/组件实现。

## 2. 事实源与产品裁决

| 项目               | 权威性/裁决                                                                                                        |
| ------------------ | ------------------------------------------------------------------------------------------------------------------ |
| Token、组件、测试  | 代码实现行为事实源：`apps/frontend/src/styles/tokens/`、`components/common/`、测试文件                             |
| UI 资产账本        | `docs/20-product/UI_ASSET_LEDGER.md` 是资产清单与采用状态权威文档，不替代代码事实                                  |
| Design System      | `docs/06-ui/0601_Design_System.md` 与 `0602_UI_Component_Standard.md` 为规范基线                                   |
| V4 处置            | PO 批准：canonical 等价验证后删除 `V4ResearchView.vue` 及仅服务它的遗留实现/测试                                   |
| Canonical 目标     | `ResearchWorkspacePage`、`ResearchWorkflowPage`、`ResearchResultPage`；不得回退到 `ResearchWorkspaceView.vue` 单体 |
| Knowledge Explorer | MVP UI 工作冻结，不投入高保真或样式重构                                                                            |
| 覆盖率             | 后端 ≥90%、前端 ≥80% 是 **Phase 10** 最终硬门禁，不是 WP-0 结束条件                                                |
| 图标               | PO 允许引入统一 SVG 包，但须先完成一手许可证、维护、构建/tree-shaking、无障碍与替换映射审查                        |

## 3. 工作包

### WP-0：可信工程基线（P0）

1. 令 SourceRef 浏览器测试在正确的 E2E fixture 层收集并进入真实业务断言；不得用 mock、seed、skip 或 API-only 代替。
2. 分批消除当前 HEAD 的 Ruff/ESLint errors；不得修改 lint 配置、ignore、严重度、测试断言或阈值以取得绿色。
3. 在本阶段仅记录覆盖率证据缺口；不得降低现有门槛，Phase 10 再验证 90%/80%。

**通过条件**：真实 SourceRef 浏览器链路通过、Ruff/ESLint/typecheck 当前命令 exit 0、完整原始输出可复跑。否则 `BLOCK_RELEASE`。

### WP-1：UI 资产账本（P0，只读）

建立 `UI_ASSET_LEDGER.md`，逐项记录事实源、变体/状态、采用页面、重复/偏离、处置和验证证据。除 Foundation 和 Hfb 组件外，必须包含：

- 古籍/中西文混排 Typography：字体族、异体字回退、行高、字号、注疏/双行小字；
- SVG 图标资产；
- Pinia UI 状态持久化（例如 Reader 面板折叠、恢复和清理边界）；
- Search/Filter、列表/Card、详情头、Citation/Evidence/SourceRef、Empty/Loading/Error/Skeleton 模式。

### WP-2：组件契约与图标治理（P0）

优先 Button、Input、Select、Dialog、Table、Card、Search、Toolbar/Filter、Badge 与状态组件。每个契约定义用途/禁用场景、props/slots/events、变体、hover/active/focus/disabled/loading/error、键盘、焦点恢复、ARIA、响应式、浅深色和 reduced motion。

对本 Sprint 新增/修改的 Vue/TypeScript 执行：

- 禁止 `any`，使用具名类型或安全泛型；
- 禁止直接 Hex 色值，只能引用定义的 token；
- `check-design-compliance.mjs` 进入 CI/提交门禁且 fail-closed；
- 历史债务记入账本，不允许通过 disable/ignore 或降低门槛隐藏。

SVG 图标包先形成最多三个候选的审计记录；具体包须 PO 选择后才安装。

### WP-3：Pattern Library（P1）

每次只收敛一个模式和明确页面白名单，先验证真实数据路径再删除重复实现。模式迁移不得改变来源链接、证据可见性、API 请求、RBAC 和错误恢复。

### WP-4：核心页面高保真收敛（P1）

固定顺序：

1. Workspace：研究上下文、入口、主要/次要操作；
2. Workflow/Result/Reports：步骤、证据、引文、报告与导出；
3. Library/Reader：检索、元数据、阅读节奏、段落与证据定位。

验证标题/核心数据/操作层级、留白、语义色、Card、状态、375×812、200% zoom、键盘、繁简转换、字号放大、弱网和 AI 超时/失败的局部重试。

V4 删除仅在 canonical 真实浏览器证明 Workflow → Result → Citation/Evidence/SourceRef → Export 与历史重定向均可用后进行；V4 API 不在本工作包删除范围。

### WP-5：研究生专家测试（P1）

由客户安排研究生，以学术研究者角色完成：

```text
课题 → 搜索 → Reader 阅读/段落定位 → AI → Citation/Evidence/SourceRef → 报告/导出
```

采集匿名化的完成率、时长、阻塞点、错误恢复、证据理解、主观信心和严重性；不得将测试数据写入正式学术数据集或替代安全、性能、RBAC、数据准入验证。

### WP-6：最终 UI QA 与 Phase 10（P0）

最终候选必须在当前 clean HEAD 留存命令、环境、原始输出和 exit code。除静态、构建、全量测试和真实浏览器外，必须验证：

- Citation 与同一 `trace_id`/`passage_id` Evidence 绑定，SourceRef 有真实标题、稳定标识与可访问链接；
- 匿名/普通研究者/管理员三身份真实 RBAC，不能只靠隐藏按钮；
- 后端 ≥90%、前端 ≥80% 覆盖率；
- 1710 的安全、性能、运维与恢复门禁。

不得凭空指定 `data-source-ref` 为既有契约；若需要新的 DOM 属性，须先做 PO 批准的可测试性设计。

## 4. AI 执行协议与完成定义

每张 Claude 卡只允许一个目标、紧白名单、一个提交、无 push/历史改写；遇到权限、凭据、产品裁决、外部数据或白名单逃逸立即停止。Codex 独立只读验收，单卡 PASS 才可开始下一卡。

Sprint 2.5 仅在 WP-0 通过、账本/契约/模式均有事实源与证据、四个页面组真实路径验证完成、研究生问题形成可复现卡片，且 Phase 10 当前 HEAD 全量准入通过后结束。在此之前：**`BLOCK_RELEASE`**。

## 5. Gemini 后续审计问题

1. 是否遗漏古籍排版、图标或 UI 状态等未闭环资产？
2. WP-0 的只读卡口是否足以阻止视觉工作掩盖质量问题？
3. 无 `any`、无直接 Hex、设计门禁是否可约束纯 AI/vibe code？
4. Citation/Evidence/SourceRef 与三身份 RBAC 不变量是否足够？
5. 除已裁决事项外，是否存在必须交由 PO 决定的范围或产品冲突？
