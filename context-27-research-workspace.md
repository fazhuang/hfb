# Context 27 — 统一研究主页 (Research Workspace)

## 目标

在现有研究入口流程中新增「统一研究主页」(`/research/workspace`)，将分散的研究能力聚合为单一五标签页视图。

## 设计原则

- **零新数据库** — 无需新建表或迁移
- **零新 AI** — 复用现有 `/api/v1/ai/chat`、`/api/v1/search`、`/api/v1/workspace/*`、`/api/v4/research/*`、`/api/v1/documents`、`/api/classical-versions`
- **聚合而非替换** — 每个标签页链接到完整功能页（资料 → `/literature`，版本 → `/classical-versions`，报告 → `/v4/research`）
- **保持原有路由** — `/workspace`、`/v4/research`、`/research` 均保持不变

## 新增文件

### `apps/frontend/src/views/ResearchWorkspaceView.vue`

五标签页视图：

| 标签页       | 图标 | 数据源                                                          | 功能                                                               |
| ------------ | ---- | --------------------------------------------------------------- | ------------------------------------------------------------------ |
| **资料**     | 📄   | `GET /api/v1/documents`                                         | 分页文献列表，含搜索、朝代/分类标签，点击跳转 `/literature/:id`    |
| **版本**     | 🏛️   | `GET /api/classical-versions`                                   | 分页古籍版本列表，含搜索、馆藏机构标签，点击跳转 `/versions/:id`   |
| **笔记**     | 📝   | `GET /api/v1/workspace/sessions/:id/notes`                      | 跨会话笔记网格，含快速记录输入框、会话筛选器，支持删除             |
| **报告**     | 📊   | `GET /api/v4/research/session/:id/runs`                         | 研究报告运行记录列表，含步骤状态徽章、报告片段预览、"查看详情"链接 |
| **研究助手** | 🤖   | `POST /api/v1/ai/chat`（SSE 流） + `GET /api/v1/search`（证据） | 双面板：聊天及会话管理 + 证据面板。支持建议提示词、会话创建/切换   |

### 路由

- `research/workspace` → `research-workspace` → `ResearchWorkspaceView.vue`（需要认证）

### i18n

- 新增 `researchEntry.researchWorkspace` 及 `researchEntry.toolResearchWorkspaceDesc`
- 新增完整 `researchWorkspace` 命名空间（zh-CN + en），含 `title`、`subtitle`、`materials`、`versions`、`notes`、`reports`、`assistant` 等共 20 个键值

## 修改的文件

| 文件                                                | 改动内容                                                         |
| --------------------------------------------------- | ---------------------------------------------------------------- |
| `apps/frontend/src/router/index.ts`                 | 新增 `research/workspace` 路由（第 100 行之后）                  |
| `apps/frontend/src/i18n/locales/zh-CN.ts`           | 扩展 `researchEntry` + 新增 `researchWorkspace` 命名空间         |
| `apps/frontend/src/i18n/locales/en.ts`              | 扩展 `researchEntry` + 新增 `researchWorkspace` 命名空间（英文） |
| `apps/frontend/src/components/layout/AppNavbar.vue` | 导航"工作台"链接至 `/research/workspace`（原 `/workspace`）      |
| `apps/frontend/src/views/ResearchHomeView.vue`      | 研究工具网格新增"统一研究主页"卡片（突出样式）                   |

## 架构说明

```
用户流程：
  /research/new（创建课题）→ /research/home（工具启动器）
    ├── 版本研究 (/research)
    ├── V4 研究 (/v4/research)
    ├── 工作台 (/workspace) ← 旧版三面板 AI 工作台
    ├── 统一研究主页 (/research/workspace) ← **新增** 聚合视图
    └── ...
```

此视图为研究操作的**主页入口** — 用户可在此浏览资料与版本、回顾笔记、查阅报告、与 AI 对话，无需在多个页面间频繁切换。

## 构建验证

- `vue-tsc --noEmit` ✓ 通过
- `vite build` ✓ 通过（16.92 kB，5.38 kB gzip）
- 无新增依赖、无迁移、无后端变更

## 定义完成

当以下各项全部满足时，本 context 视为完成：

1. `ResearchWorkspaceView.vue` 存在且可通过 `/research/workspace` 访问（需认证）
2. 五个标签页（资料、版本、笔记、报告、研究助手）均可切换，各自从实时 API 加载数据
3. 导航栏上的"工作台"链接指向 `/research/workspace`
4. 研究主页工具网格包含"统一研究主页"卡片
5. i18n 中英文均完整覆盖所有新增键值
6. 零新建数据库、零新建 AI 端点
