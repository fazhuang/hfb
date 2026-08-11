# HFB 皇甫谧数字人文研究平台 UI/UX 重构方案 v4.2
## —— UI Sprint 2 终极冻结规格书（物理真相对齐版）

**文档性质：** UI Sprint 2 终极冻结规格书  
**版本号：** v4.2 (最终通过定稿版)  
**阶段状态：** `PHASE_0_FROZEN`（Phase 0 规格已冻结，允许正式进入 Phase 1 审计）  
**验收结论：** `CONDITIONAL PASS`（Phase 0 审计通过，作为后续实施与 E2E 验收唯一标准）  

---

## 一、 战略定位与视觉终极原则

HFB 平台的 UI/UX 重构定位保持四合一核心骨架：

> **Modern Academic Research Workspace**  
> **× TCM Knowledge Infrastructure**  
> **× Scholarly Reading**  
> **× Evidence-grounded AI**

### 视觉终极原则
1. **现代骨架：** 界面框架、导航、工具栏、数据表格与工作台完全遵循现代高效率 SaaS 标准。
2. **克制中医：** 朱砂、黛青、墨色、宋体等传统文化视觉元素**仅在知识对象、古籍阅读及人文专题中语义化局部点缀**，绝不在全站大面积使用宣纸纹理、毛笔字或水墨堆叠。

---

## 二、 第一性原理核心学术与数据契约

### 1. 学术出处描述 (sourceDescribed) 与 阅读器可直达 (readerAddressable)

根据 Reader 路由物理上依赖 `/reader/:documentId#chunk-<chunk_id>` 及既有 Library 路由 `/library/:documentId` 的现实，确立两个独立解耦的维度：

#### A. 维度定义
- **`sourceDescribed`（来源信息已描述）：**
  $$\text{sourceDescribed} \iff \text{nonEmpty}(\text{source\_ref\_title}) \land (\text{passage\_id} \lor \text{chunk\_id})$$
- **`readerAddressable`（阅读器可构造直达）：**
  $$\text{readerAddressable} \iff \text{nonEmpty}(\text{document\_id}) \land \text{nonEmpty}(\text{chunk\_id})$$

#### B. 替代与降级路由规则 (Phase 4 实施澄清)
- 当前代码中 `SourceReferenceCard` 仅跳转 `/library/:documentId`。
- Phase 4 实施时：**当 `readerAddressable === true` 时，必须以新路由 `/reader/:documentId#chunk-<chunk_id>` 替换/补充现有链接；当仅具备 `document_id` 但缺乏 `chunk_id` 时，保留并回退至 `/library/:documentId` 来源入口。**

#### C. 精准 UI 呈现与交互矩阵

| 来源与跳转状态 | UI 精准展现文案与交互行为 |
| :--- | :--- |
| `sourceDescribed === true` 且 `readerAddressable === true` | 渲染来源标题；渲染按钮 **“打开原文并定位”**（跳转 `/reader/:documentId#chunk-<chunk_id>`） |
| **`sourceDescribed === false` 且 `readerAddressable === true`** | **渲染文案：“来源信息未提供；可打开文档定位”；按钮保持可用，绝不阻断学者核对原文路径！** |
| `sourceDescribed === true` 且 `readerAddressable === false` | 渲染来源标题；渲染文案：**“已具备来源定位（当前阅读器暂不支持直接跳转）”**；若有 `document_id` 可降级跳转至 `/library/:documentId` |
| `sourceDescribed === false` 且 `readerAddressable === false` | 渲染文案：**“来源定位不完整”**；禁用跳转按钮 |

---

### 2. 文本摘录 (Quoted) 与 运行态定位 (Resolved)

#### A. `quoted`（文本已摘录）
$$\text{quoted} \iff \text{quote } \neq \text{ null } \land \text{quote.trim().length } > 0$$
- **UI 规则：** 仅当 `quoted === true` 时渲染“原文摘录”框。`quoted === false` 时不渲染摘录框，但若 `readerAddressable === true`，跳转按钮规则不受影响。

#### B. `resolved`（DOM 定位成功）
$$\text{resolved} \iff \text{Reader 页面实际加载成功 } \land \text{DOM 中找到 \#chunk-<chunk\_id>}$$
- **文案约束：**
  - `resolved === true` 时，Reader 顶部提示：**“已定位至原文”**；
  - `resolved === false`（如文献加载成功但目标 `chunk` 不存在）时，Reader 顶部提示：**“目标定位点不可用”**，且绝对**不能显示“已定位至原文”**；
  - **绝对禁止使用“核复”、“核验”、“证实”等任何带有学术保真暗示的词汇！**

#### C. AI 归纳文本统一表述
由于 API 缺乏 `kind` 字段区分文本类型，全站所有 `claim_text` 统一渲染文案：
> **“系统生成的研究归纳（需核对原文）”**

---

### 3. 状态隔离与受控成功色规范

#### A. 跨 Run 数据隔离前置条件
所有 Result 视图数据的渲染，按三类对象分别校验：
1. **Evidence / Citation：** 仅由当前已确认 `targetRun` 的提取函数产出；
2. **Report：** 必须满足 `report.run_id === targetRunId` 且 `targetRun \in currentProjectRuns`；
3. **Citation Trace：** 必须满足 `trace_id \in currentRunCitationTraceIds`。

#### B. 受控的成功绿视觉禁令
- **禁用语境：** 仅限定在 **“Evidence / Citation / Claim 语境”**。表示研究数据与系统归纳时，绝不使用绿色的权威/核验样式。
- **正常解封：** 全局操作类反馈（如保存草稿成功、创建项目成功、表单提交成功等通知）正常使用系统成功绿与 Toast 反馈。

---

## 三、 客户端草稿状态机与防错契约 (`hfb_temp_pending_question`)

承认 `hfb_temp_pending_question` 为 Phase 0 唯一新增客户端状态，制定符合浏览器真实语义的三步顺次迁移与降级规范：

### 1. 超长与物理请求处理规范
- 放弃前端静默截断行为。
- **当后端返回超长限制错误时：** 界面展示服务端限制错误提示，**保留用户原始输入文本，不自动截断、不自动重试**。

### 2. 草稿迁移状态机

```text
[ 1. 首页草稿写入 ]
   └── 执行尝试: sessionStorage.setItem('hfb_temp_pending_question', text)
       └── 若捕获 QuotaExceededError / 存储被禁用:
           内存降级(仅供当前未刷新页面展示)，并明确警告提示: 
           "浏览器存储不可用，草稿未保存；请登录后重新输入。"

[ 2. 未登录回跳规则 ]
   └── 跳转至 /login?redirect=${encodeURIComponent('/research/new?from_draft=1')}

[ 3. 确定性三步顺序迁移 (无事务物理防错) ]
   Step A: sessionStorage.setItem(`hfb.research.${projectId}.pending-question`, draftText)
   Step B: 校验读取 -> sessionStorage.getItem(`hfb.research.${projectId}.pending-question`) === draftText
   Step C: 确认写入成功后，执行 sessionStorage.removeItem('hfb_temp_pending_question')
   (注: 若 Step A 或 Step B 失败，保留临时 Key，抛出可恢复提示: "草稿迁移失败，请手动确认输入")
```

---

## 四、 Result 视图隔离与后端授权的权责分离

明确区分 **后端安全授权** 与 **UI 呈现过滤**：

1. **后端授权边界 (Backend Authorization Guard)：**  
   跨项目/跨用户的非法 `run_id` 访问，由后端 API 校验 `session/run` 权限，物理抛出 `403 Forbidden` / `404 Not Found`。
2. **UI 视图渲染隔离 (Frontend Render Filter)：**  
   在权限合法的的前提下，前端仅渲染**明确属于当前 `projectId` 已授权 run 集合内的对象**（即 `targetRun \in currentProjectRuns`）。

---

## 五、 Phase 0 终极【文案-字段-交互精准映射大表】

```text
┌───────────────────────────────────────────────────────────┬─────────────────────────────────────────┐
│ 真实物理数据条件                                          │ 允许展现的 UI 文案与交互                 │
├───────────────────────────────────────────────────────────┼─────────────────────────────────────────┤
│ readerAddressable == true AND sourceDescribed == true     │ 显示标题；渲染“打开原文并定位”按钮      │
│ readerAddressable == true AND sourceDescribed == false    │ 显示“来源信息未提供；可打开文档定位”；按钮可用│
│ readerAddressable == false AND sourceDescribed == true    │ 显示“已具备来源定位（阅读器暂不支持跳转）”│
│ readerAddressable == false AND sourceDescribed == false   │ 显示“来源定位不完整”；禁用跳转按钮       │
│ Reader 加载成功且 DOM #chunk-<id> 找到                    │ 顶部提示“已定位至原文”（绝对不含“核验”）│
│ Reader 加载成功但 DOM #chunk-<id> 未找到                  │ 顶部提示“目标定位点不可用”；不显“已定位”│
│ quoted == true (quote.trim().length > 0)                  │ 渲染“原文摘录”框                        │
│ quoted == false                                           │ 不渲染摘录框；但跳转按钮规则不受影响    │
│ 任何 claim_text                                           │ 系统生成的研究归纳（需核对原文）         │
│ Evidence / Citation / Claim 语境                          │ ✖ 严禁出现“已核验/已证实”字样及成功绿   │
│ 全局操作通知 (如保存/创建)                                │ 正常使用系统成功绿与 Toast 反馈          │
└───────────────────────────────────────────────────────────┴─────────────────────────────────────────┘
```

---

## 六、 实施路线图与 Release E2E 物理断言矩阵

### 1. 阶段实施路线图

```text
Phase 0 — Specifications Frozen (当前已冻结)
  └── 本规格书 (v4.2) 达成 CONDITIONAL PASS，宣布 PHASE_0_FROZEN，进入 Phase 1

Phase 1 — Tokens & Primitive Gap Audit (样式与既有组件缺口审计)
  ├── 审计 styles/tokens/*.css 与 Design Tokens 适配度
  └── 确认 HfbButton / HfbBadge / HfbDrawer 等既有组件缺口（不新造 Primitive）

Phase 2 — Primary Loop Clickable Prototype (主链路原型)
  ├── 制作 [首页草稿 ➔ 项目选择/草稿迁移 ➔ Workflow Run ➔ Result ➔ Reader] 四页原型
  └── 在 1024px/768px/640px 屏宽与 200% 缩放规范下执行原型验收

Phase 3 — Minimal Domain Modules Extraction (按需抽取)
  ├── 仅当原型证明跨 2 处以上复用时抽取 Domain Components
  └── 严格绑定真实数据模型 (chunk_id, passage_id)

Phase 4 — Page Restyle & E2E Validation (工程落地与最终发布)
  ├── 对主链路命中的页面进行基于 Design Tokens 的最小 Restyle
  └── 全量跑通 Release E2E 物理测试矩阵，合入代码并发布
```

---

### 2. Phase 4 发布门禁 (Release E2E 物理断言矩阵)

在 Phase 4 编码完成后，Playwright 测试套件必须 **100% 全量跑通以下物理断言用例** 方可允许发布：

1. **[缺标题可跳 Reader 用例]** 当 `source_ref_title` 为空但 `document_id` + `chunk_id` 存在时，断言按钮可用，且能成功构造跳转；
2. **[无 quote 无摘录框用例]** 当 `quote` 为空时，断言不渲染摘录框，但跳转按钮不受影响；
3. **[无 anchor 无按钮用例]** 当 `chunk_id` 缺失时，断言正确显示状态，且跳转按钮禁用；
4. **[存储失败无迁移假像用例]** 当 `sessionStorage` 禁用时，断言不发生“已迁移”假象，诚实展示不可用提示；
5. **[无成功绿用例]** 断言 Evidence/Claim 区块内绝无“已核验”字样或成功绿样式；
6. **[非当前 Project 隔离用例]** 故意构造不属于当前 `projectId` 的 `runId`，断言 UI 拒绝将其渲染至 Result 视图；
7. **[浏览器请求物理唯一性用例]** 断言用户提交后，浏览器发送了**恰好一次** `POST /api/v4/research/workflow` 物理请求；
8. **[Reader 成功定位用例]** 跳转至 `/reader/:documentId#chunk-<id>` 后：
   - 断言 URL 精确匹配；
   - 断言 Reader 数据加载成功且 DOM 节点存在；
   - **在 `.reader-highlight` 动画淡出清除之前**，断言该 DOM 曾经被赋予过高亮 class；
   - 目标 DOM 渲染成功后，断言顶部提示语为 **“已定位至原文”**（绝对不含“核复/核验/证实”）；
9. **[Reader 定位失效用例]** 跳转至 `/reader/:documentId#chunk-<id>`，若目标 `chunk` 不存在：
   - 断言顶部提示为 **“目标定位点不可用”**；
   - 断言**绝不显示“已定位至原文”**。

---

## 七、 结论

本份规格书 (v4.2) 已通过 `CONDITIONAL PASS` 验收。它标志着 **Phase 0 规格彻底冻结（`PHASE_0_FROZEN`）**。

工程团队即刻解除阻断，正式进入 **Phase 1（existing tokens 与既有组件缺口审计）** 阶段！
