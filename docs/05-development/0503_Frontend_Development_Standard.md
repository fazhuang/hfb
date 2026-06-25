---
title: Frontend Development Standard
document_id: HFB-DEV-0503
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Frontend Development
priority: P0
related_documents:
  - HFB-DEV-0501 Development Specification
  - HFB-DEV-0502 Backend Development Standard
  - HFB-ARC-0201 Technical Blueprint
  - HFB-UI-0601 Design System
  - HFB-PS-1702 Platform Information Architecture Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Frontend Development Standard
## 前端开发规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》前端开发的统一标准。
>
> 所有 Web 页面、后台管理系统、数字人文展示系统、AI 交互界面及可视化模块均必须遵循本规范。

---

# 第一章 建设目标

平台前端必须实现：

- 学术化（Academic）
- 专业化（Professional）
- 易用性（Usability）
- 一致性（Consistency）
- 响应式（Responsive）
- 可访问（Accessibility）
- 高性能（Performance）

平台不是企业官网。

平台定位：

> **数字人文研究平台。**

---

# 第二章 技术栈

统一采用：

| 模块 | 技术 |
|------|------|
| Framework | Vue 3 |
| Language | TypeScript |
| Build | Vite |
| Router | Vue Router |
| State | Pinia |
| HTTP | Axios |
| UI | 自研 Design System |

未经 ADR 不得更换。

---

# 第三章 项目目录

```text
src/

assets/

components/

composables/

layouts/

pages/

router/

services/

stores/

styles/

types/

utils/

views/
```

任何模块不得跨职责。

---

# 第四章 页面架构

统一采用：

```text
Layout

↓

Page

↓

Section

↓

Component

↓

Composable

↓

Service
```

页面不得直接请求 API。

---

# 第五章 Component 规范

组件分类：

```text
Base

Business

Academic

Visualization
```

Base Component：

禁止依赖业务。

Business Component：

不得跨模块调用。

---

# 第六章 页面规范

每个页面：

必须：

包含：

- Header
- Breadcrumb
- Content
- Footer（后台可选）

不得：

一个页面承担多个业务。

---

# 第七章 状态管理

统一：

Pinia。

Store：

负责：

- 用户状态
- 权限
- 配置
- 缓存

禁止：

Store 保存页面临时状态。

---

# 第八章 API 调用

统一：

Service。

流程：

```text
Page

↓

Service

↓

API

↓

Backend
```

禁止：

页面：

直接调用：

Axios。

---

# 第九章 路由规范

统一：

```text
/

↓

module

↓

page
```

例如：

```text
/person

/book

/version

/paper

/admin
```

禁止：

深层级嵌套。

---

# 第十章 TypeScript

所有对象：

必须：

声明：

Interface。

禁止：

大量：

any。

严格模式：

开启。

---

# 第十一章 样式规范

统一：

CSS Variables。

Design Token。

禁止：

Magic Number。

禁止：

行内 Style。

---

# 第十二章 响应式规范

支持：

Desktop

Tablet

Mobile

最低支持：

1280px

推荐：

1440px+

后台优先桌面端。

---

# 第十三章 国际化

统一：

i18n。

必须支持：

- 中文
- English

后续：

可扩展。

禁止：

中文写死。

---

# 第十四章 学术展示规范

古籍页面：

必须支持：

- 原文
- 校勘
- 注释
- 引文
- 版本切换

论文页面：

支持：

- DOI
- 引用
- 作者
- 摘要

人物页面：

支持：

- 时间轴
- 关系图
- 著作
- 图片

---

# 第十五章 数据可视化

统一：

Visualization Component。

支持：

- 时间轴
- 人物关系
- 文献传播
- 地图
- 版本谱系

禁止：

图表直接访问 API。

---

# 第十六章 AI 交互规范

AI 页面：

统一布局：

```text
Question

↓

Citation

↓

Evidence

↓

Answer

↓

References
```

禁止：

仅显示回答。

---

# 第十七章 可访问性

遵循：

WCAG 2.1 AA。

要求：

- 键盘可操作
- 图片 Alt
- ARIA
- 高对比度

---

# 第十八章 性能规范

目标：

| 指标 | 标准 |
|------|------|
| 首屏加载 | ≤2 秒 |
| 路由切换 | ≤300ms |
| Lighthouse | ≥90 |
| CLS | ≤0.1 |
| LCP | ≤2.5s |

---

# 第十九章 测试规范

统一：

Vitest。

Playwright（E2E）。

覆盖：

- Component
- Page
- Store
- Service

覆盖率：

≥80%。

---

# 第二十章 前端开发红线

禁止：

- 页面直接请求 API
- Component 写业务逻辑
- Store 写 HTTP 请求
- 行内样式
- any 泛滥
- 中文硬编码
- 无响应式设计
- 无测试提交

违反任一项不得合并。

---

# 第二十一章 修订规则

修改本规范必须：

1. 建立 ADR；
2. 更新 Design System；
3. 更新 Development Specification；
4. 更新 Context Package；
5. 项目负责人批准。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台前端开发统一规范。 |