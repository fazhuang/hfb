# Context 30 — 首次使用引导设计文档

**日期**: 2026-07-16
**范围**: `apps/frontend/src/**` 全量页面与交互
**目标**: 建立首次使用引导体系：欢迎、下一步、空页面、操作提示
**实施**: P0-P3 全部完成（commit 序列：`5a6e953` → `5d6566e` → `124f025` → `0b5b2b3`）。

---

## 一、用户状态定义

系统当前无 `isNewUser` 标志。首次使用引导需基于以下四种状态设计：

| 状态             | 识别条件                               | 核心目标                       |
| ---------------- | -------------------------------------- | ------------------------------ |
| **匿名访客**     | 无 token，未登录                       | 传达平台价值，引导注册         |
| **新注册用户**   | 已登录，无研究课题，首次访问 Dashboard | 引导创建第一个研究课题         |
| **有账户无课题** | 已登录，无活跃研究课题                 | 展示可用工具，鼓励开始研究     |
| **有课题用户**   | 已登录，有活跃研究课题                 | 直接进入研究，提供高效操作提示 |

---

## 二、欢迎（Welcome）

### 2.1 首页欢迎区 ✅ 已实施

**文件**: `apps/frontend/src/views/HomeView.vue`

**实施方案**:

新增 **WelcomeHero** 区块（在系统状态卡片之前），根据用户状态显示不同内容：

**匿名访客**: 显示「皇甫谧数字人文平台 — 古籍版本比较 · 知识图谱 · AI 辅助研究」，按钮：「开始探索」（→ `/register`）+「了解更多」（→ `/about`）。

**已登录用户**: 显示「欢迎，[显示名称] — 开始你的第一次研究」，按钮根据有无活跃课题切换：无课题→「创建研究课题」（→ `/research/new`），有课题→「返回当前研究」（→ `/research/home`）。

原 `status-header`（系统标题 + 副标题）改为小号分区标签，避免与 WelcomeHero 重复。旧研究入口 CTA 按钮保留在系统状态卡片区域上方。

### 2.2 关于页面（AboutView.vue）

**文件**: `apps/frontend/src/views/AboutView.vue`

当前 About 页包含技术栈描述和项目信息。已在欢迎流程中作为「了解更多」的落点（WelcomeHero 匿名访客按钮指向 `/about`）。

### 2.3 登录/注册页 ✅ 已实施（P3）

**文件**: `apps/frontend/src/views/LoginView.vue`, `RegisterView.vue`

**实施方案**: 表单右侧（桌面端）或表单上方（移动端）增加价值主张卡片：「为什么注册？」+ 三条功能要点（版本比较 / 知识图谱 / AI 辅助研究）。

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

### 3.3 导航栏研究入口 ✅ 已实施（P2）

**文件**: `apps/frontend/src/components/layout/AppNavbar.vue`

**实施方案**: 已登录 + 无课题用户的「开始研究」导航链接首次加载时显示脉动缩放动画 + 光环扩散效果（5 次循环约 5 秒后自动消失）。点击链接触发 `showResearchPulse = false` 提前停止动画。

### 3.4 Dashboard 统计卡片 ✅ 已实施

**文件**: `apps/frontend/src/views/DashboardView.vue`

**实施方案**: 当所有统计值均为 0 且用户无活跃研究课题时，在统计网格下方插播引导区：

```
📊 这里还没有数据
完成首次研究后，你的统计面板将显示平台内容概览。
[开始探索 →]
```

统计卡片本身仍显示（值为 0）供参考，引导区为追加区块。

---

## 四、空页面（Empty Pages）

系统中的空状态可分为三类，每类需要不同的处理方式。

### 4.1 功能未实现页（占位页） ✅ 已实施

| 页面          | 路由         | 实施                                                          |
| ------------- | ------------ | ------------------------------------------------------------- |
| DocumentsView | `/documents` | 改为 `type="coming-soon"`，描述「此功能正在建设中，敬请期待」 |

PlaceholderPage 新增可选 `type` prop（`'empty'` | `'coming-soon'`）区分两种占位语义，当前仅 DocumentsView 使用 `coming-soon`。

### 4.2 搜索无结果 ✅ 已实施（P1）

**文件**: `apps/frontend/src/views/SearchView.vue`

**实施方案**: 无结果时追加操作建议：

- 「尝试更短或更通用的关键词」
- 「浏览古籍库查看完整书目」（router-link → `/books`）
- 「浏览人物列表」（router-link → `/persons`）

### 4.3 研究工具空态 ✅ 部分已实施（P1）

**版本比较页** (`/research`) — 无检索结果时：

- ✅ 已追加：「试试换一个关键词，或从古籍库浏览版本全文」

**研究工作台** (`/workspace`) — 无会话时：

- ✅ 已追加：「点击 + 创建研究会话，在画布中组织你的研究资料」

**统一研究主页** (`/research/workspace`) — 各标签页空态：

- ✅ 资料：「或从文献管理导入」
- ✅ 版本：「或浏览古籍版本库」
- ✅ 笔记：「在研究过程中使用速记功能，笔记将自动汇聚于此」
- ✅ 报告：「完成研究工作流后将自动生成报告」

**知识图谱** (`/graph`) — 初始空态：

- 已有「选择左侧实体开始图谱探索」，不修改。

### 4.4 数据列表中无条目

**文件**: `apps/frontend/src/components/common/EntityListPage.vue`, `DataTable.vue`

这些通用组件使用 `t('common.noData')` 即「暂无数据」。

**建议**: 为列表页增加 `emptyHint` 可选 prop，允许父组件传入上下文提示。

例如 BookListView：「暂无古籍条目 — 系统尚未导入古籍数据」

---

## 五、操作提示（Operation Tips）

### 5.1 全局提示机制 ✅ 已实施（P2）

**实施方案**: 使用 `title` 属性实现轻量 tooltip（浏览器原生行为）：

| 元素                     | 位置           | 提示内容                             |
| ------------------------ | -------------- | ------------------------------------ |
| 研究入口 CTA（脉动链接） | AppNavbar      | 「点击这里开始你的第一次研究」       |
| 语言切换器               | AppNavbar 右侧 | 「切换界面语言：中文 / English」     |
| 主题切换器               | AppNavbar 右侧 | 「切换主题：浅色 / 深色 / 跟随系统」 |

Tooltip 通过 `title` 属性实现，始终悬浮可见（无 localStorage 首次标记），属于零成本轻量方案。

### 5.2 内联操作提示

以下位置适合直接在界面中加入一行提示文字（灰色小字，已有模式 `entry-desc`）：

| 位置                    | 当前状态           | 建议                                           |
| ----------------------- | ------------------ | ---------------------------------------------- |
| ResearchNewView 表单    | 有 subtitle        | 已足够                                         |
| V4ResearchView 主题输入 | 有 placeholder     | 已足够                                         |
| 版本比较检索框          | 有 placeholder     | 已足够                                         |
| Workspace AI 助手       | 有 `assistantHint` | 已有「向 AI 研究助手提问，基于知识库获取答案」 |
| 图谱搜索                | 有 `emptyHint`     | 已有「选择左侧实体开始图谱探索」               |

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

| 优先级 | 改动                             | 状态    | 影响范围                                                   |
| ------ | -------------------------------- | ------- | ---------------------------------------------------------- |
| P0     | HomeView 增加 WelcomeHero 区块   | ✅ 完成 | HomeView.vue                                               |
| P0     | Dashboard 零统计引导文案         | ✅ 完成 | DashboardView.vue                                          |
| P0     | DocumentsView 改为「功能开发中」 | ✅ 完成 | DocumentsView.vue + PlaceholderPage.vue                    |
| P1     | 搜索无结果增加操作建议           | ✅ 完成 | SearchView.vue                                             |
| P1     | 研究工具空态增加上下文提示       | ✅ 完成 | ResearchWorkflowView, WorkspaceView, ResearchWorkspaceView |
| P1     | 新用户 Dashboard 步骤引导条      | ✅ 完成 | DashboardView.vue                                          |
| P2     | 导航栏「开始研究」脉动动画       | ✅ 完成 | AppNavbar.vue                                              |
| P2     | 关键元素 tooltip                 | ✅ 完成 | AppNavbar.vue (title 属性)                                 |
| P3     | 登录/注册页价值主张卡片          | ✅ 完成 | LoginView.vue, RegisterView.vue                            |

---

## 八、与 i18n 的关系

已新增顶级 key `onboarding`，实际写入 `zh-CN.ts` 和 `en.ts` 的字段：

```typescript
onboarding: {
  welcomeTitle: '皇甫谧数字人文平台',           // 匿名访客欢迎标题
  welcomeAnonymous: '古籍版本比较 · 知识图谱 · AI 辅助研究',  // 匿名访客副标题
  welcomeNewUser: '欢迎，{name}',              // 已登录用户欢迎（支持插值）
  welcomeNewUserHint: '开始你的第一次研究——只需创建一个课题即可使用全部工具',
  startExplore: '开始探索',                     // CTA 主按钮
  learnMore: '了解更多',                        // CTA 次按钮
  createFirstTopic: '创建研究课题',              // 无课题用户的 CTA
  dashboardAllZero: '这里还没有数据',           // Dashboard 零统计标题
  dashboardAllZeroHint: '完成首次研究后，你的统计面板将显示平台内容概览',
  comingSoon: '此功能正在建设中，敬请期待',       // PlaceholderPage type="coming-soon"
  searchNoResultHint: '试试更短或更通用的关键词',  // 搜索无结果提示
  searchNoResultBrowseBooks: '浏览古籍库查看完整书目',   // 搜索无结果操作链接
  searchNoResultBrowsePersons: '浏览人物列表',          // 搜索无结果操作链接
}
```

已实际使用但未在 i18n 中定义 `onboarding` key 的字符串沿用现有 `common.*`、`researchEntry.*` 等（如 Dashboard 引导区的「开始探索 →」复用 `onboarding.startExplore`）。

---

## 附录：关键文件索引

| 文件                                                      | 用途                               |
| --------------------------------------------------------- | ---------------------------------- |
| `apps/frontend/src/views/HomeView.vue`                    | 首页，系统状态 + 研究入口 CTA      |
| `apps/frontend/src/views/DashboardView.vue`               | Dashboard，统计数据 + 研究入口卡片 |
| `apps/frontend/src/views/AboutView.vue`                   | 关于页面                           |
| `apps/frontend/src/views/LoginView.vue`                   | 登录表单                           |
| `apps/frontend/src/views/RegisterView.vue`                | 注册表单                           |
| `apps/frontend/src/views/ResearchNewView.vue`             | 创建研究课题表单                   |
| `apps/frontend/src/views/ResearchHomeView.vue`            | 研究主页，工具选择面板             |
| `apps/frontend/src/views/SearchView.vue`                  | 全局搜索                           |
| `apps/frontend/src/views/DocumentsView.vue`               | 文献库占位页                       |
| `apps/frontend/src/views/GraphExplorerView.vue`           | 知识图谱                           |
| `apps/frontend/src/components/common/PlaceholderPage.vue` | 通用占位页组件                     |
| `apps/frontend/src/components/common/EntityListPage.vue`  | 通用实体列表页                     |
| `apps/frontend/src/components/common/DataTable.vue`       | 通用数据表格                       |
| `apps/frontend/src/components/layout/AppNavbar.vue`       | 导航栏                             |
| `apps/frontend/src/stores/auth.ts`                        | 认证状态（无 isNewUser 标志）      |
| `apps/frontend/src/stores/research.ts`                    | 研究课题状态                       |
| `apps/frontend/src/i18n/locales/zh-CN.ts`                 | 中文语言包                         |
| `apps/frontend/src/i18n/locales/en.ts`                    | 英文语言包                         |
