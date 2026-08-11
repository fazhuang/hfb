# HFB 皇甫谧数字人文研究平台 UI/UX Sprint 2 落地执行计划方案

**文档性质：** UI Sprint 2 落地执行与流程控制计划  
**版本号：** v1.0 (基于 v4.2 终极冻结规格书)  
**三方协作分工机制：**  
- **Gemini：** 方案下达、流程控制与阶段门禁决策（Governance & Workflow Dispatcher）  
- **Claude：** 具体代码重构、组件封装与原型实施（Implementation Engine）  
- **Codex：** 第一性原理白盒审计、契约校验与测试验收（Audit & Acceptance Engine）  

---

## 一、 协作机制与流程控制铁律

1. **单向阶段解锁（Gate-Driven Pipeline）：**  
   任何阶段必须由 Claude 提交产出 ➔ Codex 执行严苛审计 ➔ Gemini 确认满足解锁门禁后，方可发出指令进入下一 Phase。严禁跨阶段提前编码！
2. **零业务破坏与代码契约保障：**  
   严格遵循 `RESTYLE / RESTRUCTURE` 优先于 `REBUILD`。禁止修改后端 API 接口契约，禁止改动已发布的学术引用 URL。
3. **彻底遵守 v4.2 防伪矩阵：**  
   全站 Evidence/Citation 语境下**严禁出现“已核验/已证实”字样及成功绿样式**。严禁在前端凭空发明不存在的后端字段。

---

## 二、 阶段执行计划与三方分工矩阵

```text
┌─────────────────────────────────────────────────────────────────────────┐
│ Phase 1: Existing Tokens & Primitive Gap Audit (缺口审计)               │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 2: Primary Loop Clickable Prototype (主链路原型与规范验证)         │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 3: Minimal Domain Modules Extraction (按需抽取领域模块)           │
├─────────────────────────────────────────────────────────────────────────┤
│ Phase 4: Vue Page Restyle & Master Loop E2E Validation (工程落地与发布)  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

### Phase 1 — Existing Tokens & Primitive Gap Audit (样式与既有组件缺口审计)

**目标：** 厘清 `apps/frontend` 中已有的 CSS Tokens 与 `Hfb*` 基础组件，列出缺口，杜绝重复造轮子。

| 步骤 | 负责角色 | 具体任务 | 交付产出 |
| :--- | :--- | :--- | :--- |
| **1.1** | **Claude** | 审计 `src/styles/tokens/*.css` 与 `src/components/common/` 现有 `HfbButton`, `HfbBadge`, `HfbDrawer`, `HfbSelect`, `HfbInput` | 撰写 `docs/sprint2-phase1-gap-audit.md` |
| **1.2** | **Codex** | 检查 Token 缺口报告，确认无重复 Primitive 计划；校验无自定义 class 冲突 | 提交 Phase 1 审计判定 (`PASS` / `FAIL`) |
| **1.3** | **Gemini** | 审核 Codex 判定，确认 Token 与 Primitive 范围锁死，发布 Phase 2 启动指令 | 解锁 Phase 2 指令 |

- **Phase 1 解锁门禁：** `docs/sprint2-phase1-gap-audit.md` 通过 Codex 审计，确认**无需新建任何底层 Primitive 组件**。

---

### Phase 2 — Primary Loop Clickable Prototype (主链路原型与规范验证)

**目标：** 验证基于真实数据的主链路交互流与响应式断点（不涉及完整页面重构）。

| 步骤 | 负责角色 | 具体任务 | 交付产出 |
| :--- | :--- | :--- | :--- |
| **2.1** | **Claude** | 搭建主链路 Prototype 或原型视图，验证 4 页交互：<br>1) 首页草稿输入<br>2) 登录/项目确定与三步顺次草稿迁移<br>3) POST workflow(runId)<br>4) Result(runId) ➔ Reader(chunk) 跳转 | 原型实现与交互测试页面 |
| **2.2** | **Claude** | 验证 Responsive 规则：`< 1024px` 覆盖式 Drawer；`1024px-1439px` 悬浮 Drawer (保障 40 字行宽)；`≥ 1440px` Docked 模式；验证 200% 缩放 | 响应式测试记录 |
| **2.3** | **Codex** | 审查原型的 `sessionStorage` 状态机迁移日志、断点表现与选区触发逻辑 | 提交 Phase 2 审计判定 (`PASS` / `FAIL`) |
| **2.4** | **Gemini** | 确认原型流顺畅，无因果倒置与假假想，下达 Phase 3 抽取指令 | 解锁 Phase 3 指令 |

- **Phase 2 解锁门禁：** 原型在 200% 缩放与各屏宽下无溢出、草稿迁移顺畅且完全遵循 v4.2 响应式规范。

---

### Phase 3 — Minimal Domain Modules Extraction (按需抽取领域模块)

**目标：** 仅对在 Phase 2 原型中**证明跨 2 处以上复用**的模块进行强类型 Domain 组件抽取。

| 步骤 | 负责角色 | 具体任务 | 交付产出 |
| :--- | :--- | :--- | :--- |
| **3.1** | **Claude** | 按需抽取 `EvidenceBadge.vue` (包装 `HfbBadge`)，严禁赋予不存在的分类语义；包装 `SourceReferenceCard.vue` 适配 `/reader/:documentId#chunk-<id>` 路由构造 | 领域组件代码 |
| **3.2** | **Codex** | 审查 Domain Component 接口，断言其**100% 匹配 v4.2 字段—文案映射大表**，绝对无“已核验”赋权 | 提交 Phase 3 审计判定 (`PASS` / `FAIL`) |
| **3.3** | **Gemini** | 审核组件类型定义与文案契约，下达 Phase 4 最终工程迁移指令 | 解锁 Phase 4 指令 |

- **Phase 3 解锁门禁：** 所有领域组件均通过 TypeScript 严格类型检查 (`vue-tsc --noEmit`)，API 不超越现有 API 返回字段。

---

### Phase 4 — Vue Page Restyle & Master Loop E2E Validation (工程落地与全量测试)

**目标：** 主链路命中的页面 Restyle，跑通 9 大物理断言 E2E 测试套件，准备发布。

| 步骤 | 负责角色 | 具体任务 | 交付产出 |
| :--- | :--- | :--- | :--- |
| **4.1** | **Claude** | 对主链路命中的页面 (`HomeView`, `ProjectListPage`, `ResultPage`, `ReaderPage`) 执行基于 Tokens 的最小 Restyle/Restructure | Vue 视图重构代码 |
| **4.2** | **Claude** | 替换/补充 `SourceReferenceCard` 内的跳转逻辑：<br>- `readerAddressable === true` ➔ 跳转 `/reader/:documentId#chunk-<chunk_id>`<br>- 无 `chunk_id` 时 ➔ 保留跳转 `/library/:documentId` | 路由跳转代码更新 |
| **4.3** | **Claude** | 编写并运行 Playwright 自动化测试套件（覆盖 v4.2 要求的 9 大物理断言） | `tests/e2e/sprint2-main-loop.spec.ts` |
| **4.4** | **Codex** | 执行终极 Release 门禁审计：<br>1) 运行 `npx eslint`<br>2) 运行 `npx vue-tsc --noEmit`<br>3) 运行 `npx vitest run`<br>4) 运行 Playwright E2E 套件并逐一核对 9 大物理断言 | 终极 Release 审计报告 |
| **4.5** | **Gemini** | 审阅 Codex 终极报告，确认 9 大物理断言全量通过，正式下达 Sprint 2 验收完成通知 | 确认 Sprint 2 最终完成 |

---

## 三、 Phase 4 终极 Release E2E 物理断言清单 (Codex 验收依据)

Playwright E2E 测试套件（`sprint2-main-loop.spec.ts`）必须 100% 包含并跑通以下 9 项断言：

1. **[缺标题可跳 Reader 断言]** `source_ref_title` 为空但 `document_id` + `chunk_id` 存在时，按键可用，且精确构造 `/reader/:documentId#chunk-<chunk_id>` 路由；
2. **[无 quote 无摘录框断言]** `quote` 为空时，不渲染摘录框，但跳转按钮不受影响；
3. **[无 anchor 无按钮断言]** `chunk_id` 缺失时，正确显示状态，且跳转按钮禁用；
4. **[存储失败无迁移假像断言]** `sessionStorage` 禁用时，断言展示“草稿未保存”提示，且不发生假迁移；
5. **[无成功绿断言]** Evidence/Claim 区块内绝无“已核验”字样或成功绿样式；
6. **[非当前 Project 隔离断言]** 使用异构数据库 run 数据，断言 UI 拒绝渲染非当前 `projectId` 的 Report 对象；
7. **[物理请求唯一性断言]** 断言提交后，浏览器发送了**恰好一次** `POST /api/v4/research/workflow` 物理请求；
8. **[Reader 成功定位断言]** 跳转至 `/reader/:documentId#chunk-<id>` 后，在 `.reader-highlight` 动画淡出前断言 DOM 被赋予高亮 class，且顶部提示“已定位至原文”；
9. **[Reader 定位失效断言]** 若目标 `chunk` 不存在，断言顶部提示“目标定位点不可用”，且绝不显示“已定位至原文”。

---

## 四、 立即执行指令 (Current Action)

- **当前状态：** Phase 0 规格已冻结，进入 **Phase 1（Existing Tokens & Primitive Gap Audit）**。
- **Gemini 指令给 Claude：**  
  请 Claude 立即启动 **Phase 1 任务 (1.1)**：对 `apps/frontend/src/styles/tokens/*.css` 与 `src/components/common/` 现有 `HfbButton`, `HfbBadge`, `HfbDrawer`, `HfbSelect`, `HfbInput` 组件进行全面缺口审计，并产出 `docs/sprint2-phase1-gap-audit.md`。
- **Gemini 指令给 Codex：**  
  请 Codex 待 Claude 提交 Phase 1 报告后，执行 1.2 缺口审计验证。
