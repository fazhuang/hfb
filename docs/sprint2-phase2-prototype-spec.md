# Phase 2 Prototype — 主链路可点击原型规范

**日期:** 2026-08-11
**基线:** HEAD `6bb825f0f1a13b62c3e2ae60b2ef26a75a3bc281` + 未提交的 `input.css`、`select.css` 变更
**范围:** 4 页交互流原型 + readerAddressable 跳转 + 响应式断点验证

---

## 1. 架构概览

```
Page 1 (首页, 匿名)     → Page 2 (登录/项目确定) → Page 3 (Workflow) → Page 4 (Result → Reader)
hfb_temp_pending_question → 3-Step Migration     → POST /api/v4/     → /reader/:id#chunk-<id>
                            + Login + projectId     research/workflow
```

**新增文件：**
| 文件 | 用途 |
|------|------|
| `src/composables/usePrototypeDraft.ts` | 临时/规范 Key 状态机、三步迁移、readerAddressable 检测 |
| `src/pages/prototype/Phase2PrototypePage.vue` | 可点击原型测试线束（4 页全部交互在一视图中） |
| `docs/sprint2-phase2-prototype-spec.md` | 本规范文档 |

**修改文件：**
| 文件 | 变更 |
|------|------|
| `src/views/HomeView.vue` | Page 1 匿名草稿输入区（hfb_temp_pending_question） |
| `src/components/research/result/SourceReferenceCard.vue` | readerAddressable 跳转：chunk_id → /reader/:id#chunk-<id>，否则 → /library/:id |
| `src/router/index.ts` | 新增 `/prototype` 路由 |

---

## 2. 存储 Key 契约

### 临时 Key（匿名）
- **Key:** `hfb_temp_pending_question`
- **作用域:** 整个 sessionStorage（不限 projectId）
- **写入者:** 首页匿名用户（Page 1）
- **读取者:** 迁移步骤 1
- **生命周期:** 迁移步骤 3 后销毁，或会话终止

### 规范 Key（已认证）
- **Key:** `hfb.research.<projectId>.pending-question`
- **作用域:** 单 projectId（UUID v4 格式校验）
- **写入者:** 迁移步骤 2
- **读取者:** `useResearchWorkflow.initPendingQuestion()`（已有）
- **生命周期:** workflow submit 后由 composable 清除

### 迁移状态机
```
idle → writing → reading → destroying → done / failed
```

**三步确定性顺序迁移（物理校验）：**
1. 写入 `hfb.research.<projectId>.pending-question`
2. 读取校验：`sessionStorage.getItem(canonicalKey)` 必须完全匹配写入内容
3. 销毁 `hfb_temp_pending_question` 并校验销毁结果：`getItem(TEMP_KEY)` 必须为 `null`

每一步必须在下一步开始前物理校验通过。任一步失败（包括销毁校验失败）立即置 `migrationState = 'failed'` 并 return false。**只有三步物理校验全部通过，才允许设为 done。**

---

## 3. 4 页交互流

### Page 1 — 首页草稿输入（匿名）

**位置:** `HomeView.vue`，引导卡片下方
**行为:**
- 未登录用户可见 2000 字 textarea + "保存草稿" 按钮
- 保存写入 `hfb_temp_pending_question`
- `sessionStorage` 不可用时显示："未保存，登录后重新输入。浏览器存储不可用。"
- 已登录用户：textarea 禁用，提示"已登录用户请通过项目工作流输入问题"
- 登录成功后自动重定向至 Research Project List

**交互:** 用户输入 → 保存草稿 → 右侧登录卡片登录 → 重定向至 `/research`

### Page 2 — 项目确定与草稿迁移

**位置:** Phase2PrototypePage.vue（原型线束），`#proto-page2` 区块
**入口点:** 用户登录并从 Project List 选择 projectId 后
**行为:**
- 输入 projectId，点击"执行迁移 (3-Step)"
- 显示三步骤进度：读取临时草稿 / 写入项目草稿 / 销毁临时草稿
- 每步显示状态图标 (`⬜` → `⏳` → `✅` / `❌`) 及详情文本
- 迁移完成后显示 Canonical Key 及其内容
- "读取项目草稿"/"清除项目草稿" 按钮用于手动诊断

**交互:** 选择项目 → 触发迁移 → 确认 Canonical Key → 导航至 Workflow

### Page 3 — 范围确认与 Workflow 提交

**位置:** Phase2PrototypePage.vue，`#proto-page3` 区块
**行为:**
- "从 Canonical Key 填充" 按钮读取并填充问题
- 问题 + projectId 确认后，点击"开始分析"
- 触发恰好一次 `POST /api/v4/research/workflow`（物理请求）
- submitCount 追踪请求计数（须恰好为 1）
- 成功后显示 runId，附带跳转至 Result Page 的链接

**交互:** 填充 Canonical Key → 确认问题 → POST workflow → 跳转至 Result

### Page 4 — Result → Reader 跳转

**位置:** Phase2PrototypePage.vue，`#proto-page4` 区块
**行为:**
- 显示模拟证据数据表，包含 trace_id、document_id、chunk_id
- readerAddressable 检测：`!!document_id && !!chunk_id`
- 符合条件的条目：绿色圆点 Badge "是" + 可点击的 `/reader/:documentId#chunk-<chunk_id>` 链接
- 不符合条件的条目：中性灰色 Badge "否" + "—"
- 手动验证区域：输入 document_id + chunk_id 测试跳转

**SourceReferenceCard 更新（生产跳转逻辑）：**
```typescript
// 旧逻辑：/library/:docId?passage=:passageId（仅在 source_ref_title 存在时渲染）
// 新逻辑：
//   source_ref_title 存在 → 显示完整元数据
//   source_ref_title 缺失 → 显示"来源信息未提供；可打开文档定位"，跳转按钮始终可用
//   内部路由不受 source_ref_title 条件约束：
if (document_id && chunk_id) → /reader/:documentId#chunk-<chunk_id>
else if (document_id) → /library/:documentId
else → 不生成内部路由
```
**关键修复：** 模板最外层 `v-if="evidence.source_ref_title"` 已移除，内部路由块无条件渲染。`hasInternalRoute` 仅依赖 `document_id` 存在性。

**交互:** 查看证据列表 → 点击 readerAddressable 条目 → 跳转至 /reader/:id#chunk-<id>

---

## 4. 响应式与排版自适应

### 三级断点

| 断点 | 宽度 | 模式 |
|-----------|-------|------|
| 移动端 | < 1024px | 覆盖式 Drawer（全宽） |
| 平板 | 1024px–1439px | 悬浮 Overlay Drawer（40 字黄金行宽） |
| 桌面端 | ≥ 1440px | Docked 模式（侧边面板常驻） |

**验证方式：** Phase2PrototypePage 底部断点指示条，实时显示当前视口宽度及激活的断点区域。

### 200% 缩放验证

运行 `document.body.style.zoom = '200%'`，验证：
- 无水平溢出（页面宽度适配）
- 文字不裁剪
- 交互元素不重叠
- 固定定位导航栏不在页面作用域内（200% 缩放检测独立规则）

---

## 5. 物理断言清单（来自执行计划）

1. **[缺标题可跳 Reader 断言]** `source_ref_title` 为空但 `document_id` + `chunk_id` 存在时，按键可用，且精确构造 `/reader/:documentId#chunk-<chunk_id>` 路由
2. **[无 quote 无摘录框断言]** `quote` 为空时，不渲染摘录框，但跳转按钮不受影响
3. **[无 anchor 无按钮断言]** `chunk_id` 缺失时，正确显示状态，且跳转按钮禁用
4. **[存储失败无迁移假像断言]** `sessionStorage` 禁用时，断言展示"草稿未保存"提示，且不发生假迁移
5. **[无成功绿断言]** Evidence/Claim 区块内绝无"已核验"字样或成功绿样式
6. **[非当前 Project 隔离断言]** 使用异构数据库 run 数据，断言 UI 拒绝渲染非当前 `projectId` 的 Report 对象
7. **[物理请求唯一性断言]** 断言提交后，浏览器发送了**恰好一次** `POST /api/v4/research/workflow` 物理请求
8. **[Reader 成功定位断言]** 跳转至 `/reader/:documentId#chunk-<id>` 后，在 `.reader-highlight` 动画淡出前断言 DOM 被赋予高亮 class，且顶部提示"已定位至原文"
9. **[Reader 定位失效断言]** 若目标 `chunk` 不存在，断言顶部提示"目标定位点不可用"，且绝不显示"已定位至原文"

**注:** 断言 5-9 由 Phase 4 Playwright E2E 套件验证。Phase 2 原型仅验证 1-4 在原型线束中的行为。

---

## 6. 类型检查与 Lint

```
npx vue-tsc --noEmit   → 零新错（仅预存：PersonRoleBadge, SystemHealthView 等）
npx eslint             → 零新错
```

---

## 7. 实现笔记

- `usePrototypeDraft` 单独作为 composable 存在——不修改 `useResearchWorkflow` 的内部结构。迁移后两者通过 Canonical Key 解耦。
- 原型页面（`/prototype`）不需要认证——将所有 4 页整合到一个视图中以便加速迭代。
- `SourceReferenceCard` 中的 readerAddressable 跳转逻辑以 chunk_id 为中心。内部路由现在优先使用 `/reader/:id#chunk-<id>`，而非旧的 `/library/:id?passage=:pid` 模式。
- `HomeView` 草稿输入区动态切换：未登录时启用（写入临时 Key），已登录时禁用（重定向至项目工作流）。

---

*Phase 2 原型实现。由 Claude 构建。Codex 审计待定。*
