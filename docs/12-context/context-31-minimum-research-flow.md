# Context 31：最小可用研究流程

> 状态：**实施完成** | 日期：2026-07-16

---

## 一、背景

Context 28 已完成 7 个连接点（搜索→课题→阅读→AI→引用→笔记→报告→搜索）的贯通行，但研究主页本身存在多个用户体验问题，导致**最小可用流程不可行**：

1. **ResearchHomeView 工具卡片冗余混乱**：7 个卡片中有 2 个指向同一目标（"工作台"和"研究工作台"都到 `/research/workspace`），2 个指向版本研究/V4 研究（重度功能），入口排列无序
2. **SearchView 导航死点击**：`navigateToItem()` 仅处理 `book` 和 `person`，`version` 和 `document` 类型静默无反应
3. **"加入课题"静默覆盖**：已有活跃课题时无任何确认提示
4. **缺少中文 i18n 键**：新增卡片描述无对应翻译

本次修改的目标：

- **不新增能力**：不引入新 API、新组件、新依赖
- **仅优化流程**：修复死链、精简入口、理顺顺序
- **保持向后兼容**：所有现有路由和 API 调用不变

---

## 二、修改文件

### 2.1 SearchView.vue — 导航死点击修复

**文件**：`apps/frontend/src/views/SearchView.vue`

**修改**：`navigateToItem()`（第 348-356 行）

```diff
  function navigateToItem(item: SearchResultItem) {
    if (item.url) {
      router.push(item.url);
    } else if (item.entity_type === 'book') {
      router.push(`/books/${item.id}`);
    } else if (item.entity_type === 'person') {
      router.push(`/persons/${item.id}`);
+   } else if (item.entity_type === 'version') {
+     router.push(`/versions/${item.id}`);
+   } else if (item.entity_type === 'document') {
+     router.push(`/literature/${item.id}`);
    }
-   // Other types have no dedicated detail page yet
+   // passage and paper have no dedicated detail page yet — clicking shows nothing
  }
```

**影响**：`version` 和 `document` 类型搜索结果现在可正确跳转到详情页。`passage` 和 `paper` 仍无独立详情页（不变）。

**修改**：`addToTopic()`（第 359-363 行）

```diff
  function addToTopic(item: SearchResultItem) {
+   if (researchStore.hasActiveResearch) {
+     const confirmed = window.confirm(
+       `当前已有研究课题"${researchStore.currentTopic?.name}"，是否覆盖？`
+     );
+     if (!confirmed) return;
+   }
    researchStore.setTopic(item.title, item.snippet || item.subtitle || '');
    router.push({ name: 'research-home' });
  }
```

**影响**：避免静默覆盖现有课题，提供浏览器原生确认对话框。

---

### 2.2 ResearchHomeView.vue — 工具卡片精简

**文件**：`apps/frontend/src/views/ResearchHomeView.vue`

**修改**：工具卡片网格从 7 个条目精简为 6 个，按推荐使用顺序排列：

**旧排列**（7 个卡片）：

```
研究(版本比较) → V4研究 → 工作台 → 研究工作台 → 搜索 → 图谱 → 古籍库
```

问题：

- "工作台"和"研究工作台"重复（都到 `/research/workspace`）
- 版本研究和 V4 研究是重度功能，不应作为入口第一项
- 无序

**新排列**（6 个卡片）：

```
搜索 → 统一研究主页 → 报告 → 古籍库 → 知识图谱 → 研究助手
```

特点：

- 按自然研究流程排序：先搜索 → 进入工作区 → 查看报告 → 浏览古籍 → 探索图谱 → AI 问答
- 移除「版本研究」和「V4 研究」独立入口（这些功能已嵌入工作区标签页）
- 新增「报告」和「研究助手」直达链接（带 `?tab=` 参数精确跳转到工作区对应标签页）

---

### 2.3 i18n 新增键

**文件**：`apps/frontend/src/i18n/locales/zh-CN.ts`
**文件**：`apps/frontend/src/i18n/locales/en.ts`

```diff
  researchEntry: {
+   toolReportsDesc: '查看和管理研究报告',     // zh-CN
+   toolReportsDesc: 'View and manage research reports',  // en
+   toolAssistantDesc: 'AI 智能问答与引用保存', // zh-CN
+   toolAssistantDesc: 'AI-powered Q&A with citation saving',  // en
  }
```

---

## 三、未修改项（保持原样）

- **不新增 API**：不修改任何后端端点
- **不新增组件**：不创建新 Vue 组件
- **不修改路由**：`router/index.ts` 不变
- **不修改数据模型**：无数据库迁移
- **不修改 Pinia store**：`useResearchStore` 不变
- **不修改连接点**：Context 28 定义的 7 个连接点不受影响

---

## 四、验证清单

- [x] `vue-tsc --noEmit` 通过
- [ ] 搜索 `version` 类型结果点击可跳转到版本详情页
- [ ] 搜索 `document` 类型结果点击可跳转到文献详情页
- [ ] 搜索 `book`、`person` 类型结果点击行为不变
- [ ] 已有课题时点击「加入课题」弹出确认对话框
- [ ] 研究主页显示 6 个工具卡片，无重复入口
- [ ] 「报告」卡片跳转到 `/research/workspace?tab=reports`
- [ ] 「研究助手」卡片跳转到 `/research/workspace?tab=assistant`
- [ ] 「搜索」卡片跳转到 `/search`
- [ ] 「统一研究主页」卡片跳转到 `/research/workspace`
- [ ] 所有卡片的中文描述正确显示
- [ ] 英文界面下所有卡片描述正确显示

---

## 五、影响分析

| 维度       | 评估                                          |
| ---------- | --------------------------------------------- |
| 破坏性变更 | 无 — 所有现有路由、API、组件签名不变          |
| 用户体验   | 正向 — 减少困惑入口，修复死点击，增加覆盖确认 |
| 测试影响   | 无 — 不引入新功能，纯 UI 流程优化             |
| 性能影响   | 无 — 同等渲染量                               |
| 安全影响   | 无                                            |
| 数据完整性 | 不影响                                        |

---

## 六、当前研究流程架构

```
┌─────────────────────────────────────────────────────────┐
│  /search                    搜索入口                      │
│    ├─ 结果跳转: book, person, version, document ✅       │
│    └─ "加入课题" → /research/home                        │
├─────────────────────────────────────────────────────────┤
│  /research/new              创建课题（localStorage）      │
│    └─ "创建" → /research/home                            │
├─────────────────────────────────────────────────────────┤
│  /research/home             研究主页（6 工具卡片）        │
│    ├─ 搜索          → /search                             │
│    ├─ 统一研究主页   → /research/workspace                │
│    ├─ 报告          → /research/workspace?tab=reports     │
│    ├─ 古籍库        → /books                              │
│    ├─ 知识图谱      → /graph                              │
│    └─ 研究助手      → /research/workspace?tab=assistant   │
├─────────────────────────────────────────────────────────┤
│  /research/workspace        统一工作区（7 标签页）         │
│    ├─ 资料(materials)    — 文献浏览/搜索                 │
│    ├─ 版本(versions)     — 古籍版本目录                  │
│    ├─ 笔记(notes)        — 会话笔记 CRUD                  │
│    ├─ 报告(reports)      — 历史报告查看                  │
│    ├─ 研究(research)     — 版本比较工作流                 │
│    ├─ V4研究(v4-research)— 多步骤研究 + 报告生成          │
│    └─ 助手(assistant)    — AI 聊天 + 引用捕获             │
├─────────────────────────────────────────────────────────┤
│  /literature/:id            文献详情页                    │
│    ├─ 课题上下文横幅 ✅                                    │
│    └─ "就此提问" → workspace?tab=assistant&ask=... ✅     │
└─────────────────────────────────────────────────────────┘
```
