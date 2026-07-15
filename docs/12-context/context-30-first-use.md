# Context 30 — 首次使用引导设计文档

**日期**: 2026-07-16
**范围**: `apps/frontend/src/**` 全量页面与交互
**目标**: 建立首次使用引导体系：欢迎、下一步、空页面、操作提示

---

## 一、用户状态定义

系统当前无 `isNewUser` 标志。首次使用引导需基于以下四种状态设计：

| 状态 | 识别条件 | 核心目标 |
|------|---------|---------|
| **匿名访客** | 无 token，未登录 | 传达平台价值，引导注册 |
| **新注册用户** | 已登录，无研究课题，首次访问 Dashboard | 引导创建第一个研究课题 |
| **有账户无课题** | 已登录，无活跃研究课题 | 展示可用工具，鼓励开始研究 |
| **有课题用户** | 已登录，有活跃研究课题 | 直接进入研究，提供高效操作提示 |

---

## 二、欢迎（Welcome）

### 2.1 首页欢迎区（当前状态）

**文件**: `apps/frontend/src/views/HomeView.vue`

当前首页为纯系统状态页：标题 + 副标题 + 系统健康卡片 + 研究入口 CTA。

**现状问题**:
- 无平台介绍——匿名访客看到满屏技术状态卡片（后端、数据库、Redis 等），无法理解这个平台「做什么」。
- "系统就绪" 徽章对非技术人员无意义。
- 唯一有价值的元素是蓝紫色渐变 CTA 按钮，但未登录时显示「开始新的研究」，点击后跳转登录页——信息层级倒置。

**建议改造**:

新增 **WelcomeHero** 区块（在系统状态卡片之前），根据用户状态显示不同内容：

**匿名访客**:
```
┌──────────────────────────────────────────────┐
│  📜 皇甫谧数字人文平台                          │
│  古籍版本比较 · 知识图谱 · AI 辅助研究             │
│                                              │
│  [开始探索]  [了解更多]                         │
└──────────────────────────────────────────────┘
```
- 「开始探索」→ 跳转 `/register`
- 「了解更多」→ 跳转 `/about`

**新注册用户**（首次登录）:
```
┌──────────────────────────────────────────────┐
│  👋 欢迎，[显示名称]                            │
│  开始你的第一次研究——只需创建一个课题即可使用全部工具  │
│                                              │
│  [创建研究课题]                                │
└──────────────────────────────────────────────┘
```

### 2.2 关于页面（AboutView.vue）

**文件**: `apps/frontend/src/views/AboutView.vue`

当前 About 页包含技术栈描述和项目信息。应在欢迎流程中作为「了解更多」的落点。

**建议**: 为 About 页增加「如何开始」区块，列出三步入门路径。

### 2.3 登录/注册页

**文件**: `apps/frontend/src/views/LoginView.vue`, `RegisterView.vue`

当前为简洁表单，无平台介绍。副标题仅一行：「欢迎回到皇甫谧数字人文平台」。

**建议**: 在表单侧边（桌面端）或表单上方（移动端）增加 **价值主张卡片**：
- 「为什么注册？」—— 三行要点
- 已有功能：版本比较、知识图谱、AI 辅助研究

---

## 三、下一步（Next Steps）

### 3.1 核心路径

用户在平台的标准研究路径：

```
注册 → 登录 → 创建研究课题 → 使用研究工具 → 导出成果
                    ↑              │
                    └──────────────┘
                  （循环：一个课题可多次研究）
```

### 3.2 研究课题是核心入口

**文件**: `apps/frontend/src/views/ResearchNewView.vue`（创建课题）

研究课题（Research Topic）是整个平台的骨架概念：
- 所有研究工具（版本比较、V4 工作流、工作台、AI 助手）围绕课题组织
- 笔记、资料、报告、会话均归属于课题
- 一个用户可有多个课题，但同时只有一个「活跃课题」

**建议引导流程**（新用户登录后）:

**步骤 1** — Dashboard 页顶部展示引导条：
```
✨ 欢迎来到皇甫谧数字人文平台！让我们开始吧 →
  [1. 创建研究课题] → [2. 探索研究工具] → [3. 记录研究笔记]
```

**步骤 2** — 用户创建课题后，ResearchHomeView 显示工具选择面板（已存在 `researchEntry.toolsTitle` 及六个工具卡片），每个卡片附带简短中文说明。

**步骤 3** — 用户首次进入任一工具空态时，显示上下文操作提示（见第四节）。

### 3.3 导航栏研究入口

**文件**: `apps/frontend/src/components/layout/AppNavbar.vue`

导航栏已实现动态研究入口：
- 已登录 + 无课题 → 显示「开始研究」(🔬)，路由 `/research/new`
- 已登录 + 有课题 → 显示「当前研究」(🔬)，路由 `/research/home`

**建议**: 首次登录后，在导航栏「开始研究」旁增加短暂脉动动画（3 次循环后消失），引导注意力。

### 3.4 Dashboard 统计卡片

**文件**: `apps/frontend/src/views/DashboardView.vue`

Dashboard 包含六个统计卡片（人物、古籍、版本、条文、论文、用户），新用户看到的全是 0。

**建议**: 当所有统计值均为 0 时，替换统计卡片区为引导文案：
```
📊 这里还没有数据
完成首次研究后，你的统计面板将显示平台内容概览。
[开始研究 →]
```

---

## 四、空页面（Empty Pages）

系统中的空状态可分为三类，每类需要不同的处理方式。

### 4.1 功能未实现页（占位页）

| 页面 | 路由 | 当前状态 |
|------|------|---------|
| DocumentsView | `/documents` | `PlaceholderPage`：「文献库 — 暂无数据」 |

**问题**: 「暂无数据」不准确——是功能未上线，不是用户没有数据。

**建议**: 区分两种占位语义，为 PlaceholderPage 增加 `type` prop：
- `type="coming-soon"` — 功能开发中：「此功能正在建设中，敬请期待」
- `type="empty"` — 数据为空：「暂无数据」

DocumentsView 应使用 `coming-soon`。

### 4.2 搜索无结果

**文件**: `apps/frontend/src/views/SearchView.vue`

当前搜索初始态：「在上方输入关键词开始搜索」
当前搜索无结果：「未找到相关结果」

**建议**: 无结果时增加操作建议：
- 「尝试更短或更通用的关键词」
- 「浏览[古籍库](/books)查看完整书目」
- 「浏览[人物](/persons)查看已知人物」

### 4.3 研究工具空态

**版本比较页** (`/research`) — 无检索结果时：
- 当前：「没有找到可比较的条文。」
- 建议追加：「试试换一个关键词，或从[古籍库](/books)浏览版本全文」

**研究工作台** (`/workspace`) — 无会话时：
- 当前：「暂无会话，点击 + 创建」
- 建议：增加会话用途说明（一行中文）

**统一研究主页** (`/research/workspace`) — 各标签页空态：
- 资料：「搜索文献资料...」→ 建议追加「或从[文献管理](/literature)导入」
- 版本：「搜索古籍版本...」→ 建议追加「或浏览[古籍版本库](/classical-versions)」
- 笔记：「暂无笔记」→ 建议追加「在研究过程中使用速记功能，笔记将自动汇聚于此」
- 报告：「暂无研究报告」→ 建议追加「完成 V4 研究工作流后将自动生成报告」

**知识图谱** (`/graph`) — 初始空态：
- 当前：「选择左侧实体开始图谱探索」
- 评价：已经较好，不需要修改

### 4.4 数据列表中无条目

**文件**: `apps/frontend/src/components/common/EntityListPage.vue`, `DataTable.vue`

这些通用组件使用 `t('common.noData')` 即「暂无数据」。

**建议**: 为列表页增加 `emptyHint` 可选 prop，允许父组件传入上下文提示。

例如 BookListView：「暂无古籍条目 — 系统尚未导入古籍数据」

---

## 五、操作提示（Operation Tips）

### 5.1 全局提示机制

**方案 A — 轻量 Tooltip 提示**（推荐）

在关键操作元素上增加悬浮提示（`title` 属性或自定义 tooltip），首次显示后写入 `localStorage` 标记，不再重复。

需要提示的关键元素：
| 元素 | 位置 | 提示内容 |
|------|------|---------|
| 研究入口 CTA | HomeView, Dashboard | 「研究课题是你使用所有工具的起点」 |
| 语言切换器 | AppNavbar 右侧 | 支持中/英文界面切换 |
| 主题切换器 | AppNavbar 右侧 | 三种模式：浅色、深色、跟随系统 |
| 创建课题按钮 | ResearchNewView | 「课题名称建议简洁明确，例如"针灸甲乙经版本考证"」 |
| 研究工具卡片 | ResearchHomeView | 每个卡片已有描述，无需额外提示 |

**方案 B — 引导遮罩（Tour Overlay）**

步骤式引导，适合新用户首次登录。不推荐此时实现——成本较高且与空态引导有重叠。可在引导体系验证后再考虑。

### 5.2 内联操作提示

以下位置适合直接在界面中加入一行提示文字（灰色小字，已有模式 `entry-desc`）：

| 位置 | 当前状态 | 建议 |
|------|---------|------|
| ResearchNewView 表单 | 有 subtitle | 已足够 |
| V4ResearchView 主题输入 | 有 placeholder | 已足够 |
| 版本比较检索框 | 有 placeholder | 已足够 |
| Workspace AI 助手 | 有 `assistantHint` | 已有「向 AI 研究助手提问，基于知识库获取答案」 |
| 图谱搜索 | 有 `emptyHint` | 已有「选择左侧实体开始图谱探索」 |

**结论**: 当前系统对已有功能的操作提示覆盖较好。主要缺口在「新用户不知道从哪里开始」——通过第 3.2 节的引导条解决。

### 5.3 桌面端与移动端

- 当前所有页面在 768px 以下有响应式断点。
- 导航栏在移动端无汉堡菜单——所有链接直接显示（可能溢出）。
- **提示**: 引导组件在移动端应使用底部弹出（Bottom Sheet）而非侧边模态。
- **提示**: 统计网格在移动端保持 3 列（`grid-template-columns: repeat(3, 1fr)`），小屏可读。

### 5.4 主题与语言

- 主题切换：`localStorage` key 为 `theme`，可选 `light` / `dark` / `auto`
- 语言切换：`localStorage` key 为 `hfb-locale`，可选 `zh-CN` / `en`
- 新用户无存储值，默认跟随浏览器语言并回退到 `zh-CN`，主题默认跟随系统

**提示**: 可在注册成功后的欢迎页或首个 Dashboard 访问中提示用户可切换语言和主题——但属于低优先级。

---

## 六、不需要的内容

### 禁止新增「帮助中心」
- 不新建独立的帮助页面、帮助中心或 FAQ 系统
- 所有引导通过**内联提示**、**空态文案**、**tooltip** 和**引导条**实现

### 不修改的部分
- 管理后台（`/admin/*`）不在引导范围内——管理员需具备专业知识
- 现有 `researchEntry.toolsTitle` 及工具卡片已是有效的功能介绍，不需要改造

---

## 七、实施优先级

| 优先级 | 改动 | 影响范围 | 复杂度 |
|--------|------|---------|--------|
| P0 | HomeView 增加 WelcomeHero 区块 | HomeView.vue | 中 |
| P0 | Dashboard 零统计引导文案 | DashboardView.vue | 低 |
| P0 | DocumentsView 改为「功能开发中」 | DocumentsView.vue + PlaceholderPage.vue | 低 |
| P1 | 搜索无结果增加操作建议 | SearchView.vue | 低 |
| P1 | 研究工具空态增加上下文提示 | ResearchView, WorkspaceView, ResearchWorkspaceView | 低 |
| P1 | 新用户 Dashboard 引导条 | DashboardView.vue | 中 |
| P2 | 导航栏「开始研究」脉动动画 | AppNavbar.vue | 低 |
| P2 | 关键元素 tooltip | 多个组件 | 中 |
| P3 | 登录/注册页价值主张卡片 | LoginView.vue, RegisterView.vue | 中 |

---

## 八、与 i18n 的关系

所有新增引导文字需同步添加到 `zh-CN.ts` 和 `en.ts`。建议新增顶级 key `onboarding`：

```typescript
// zh-CN.ts
onboarding: {
  welcomeTitle: '欢迎来到皇甫谧数字人文平台',
  welcomeAnonymous: '古籍版本比较 · 知识图谱 · AI 辅助研究',
  welcomeNewUser: '欢迎，{name}',
  welcomeNewUserHint: '开始你的第一次研究——只需创建一个课题即可使用全部工具',
  startExplore: '开始探索',
  learnMore: '了解更多',
  createFirstTopic: '创建研究课题',
  dashboardAllZero: '这里还没有数据',
  dashboardAllZeroHint: '完成首次研究后，你的统计面板将显示平台内容概览',
  stepGuide: '{step}/{total} 创建研究课题',
  comingSoon: '此功能正在建设中，敬请期待',
  searchNoResultHint: '试试更短或更通用的关键词',
  searchNoResultBrowse: '浏览古籍库查看完整书目',
  materialsEmptyHint: '或从文献管理导入',
  versionsEmptyHint: '或浏览古籍版本库',
  notesEmptyHint: '在研究过程中使用速记功能，笔记将自动汇聚于此',
  reportsEmptyHint: '完成研究工作流后将自动生成报告',
}
```

---

## 附录：关键文件索引

| 文件 | 用途 |
|------|------|
| `apps/frontend/src/views/HomeView.vue` | 首页，系统状态 + 研究入口 CTA |
| `apps/frontend/src/views/DashboardView.vue` | Dashboard，统计数据 + 研究入口卡片 |
| `apps/frontend/src/views/AboutView.vue` | 关于页面 |
| `apps/frontend/src/views/LoginView.vue` | 登录表单 |
| `apps/frontend/src/views/RegisterView.vue` | 注册表单 |
| `apps/frontend/src/views/ResearchNewView.vue` | 创建研究课题表单 |
| `apps/frontend/src/views/ResearchHomeView.vue` | 研究主页，工具选择面板 |
| `apps/frontend/src/views/SearchView.vue` | 全局搜索 |
| `apps/frontend/src/views/DocumentsView.vue` | 文献库占位页 |
| `apps/frontend/src/views/GraphExplorerView.vue` | 知识图谱 |
| `apps/frontend/src/components/common/PlaceholderPage.vue` | 通用占位页组件 |
| `apps/frontend/src/components/common/EntityListPage.vue` | 通用实体列表页 |
| `apps/frontend/src/components/common/DataTable.vue` | 通用数据表格 |
| `apps/frontend/src/components/layout/AppNavbar.vue` | 导航栏 |
| `apps/frontend/src/stores/auth.ts` | 认证状态（无 isNewUser 标志） |
| `apps/frontend/src/stores/research.ts` | 研究课题状态 |
| `apps/frontend/src/i18n/locales/zh-CN.ts` | 中文语言包 |
| `apps/frontend/src/i18n/locales/en.ts` | 英文语言包 |
