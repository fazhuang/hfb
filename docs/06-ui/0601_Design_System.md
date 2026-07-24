---
title: Design System
document_id: HFB-UI-0601
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product Designer
effective_date: 2026-06-24
scope: User Interface & Design Language
priority: P0
related_documents:
  - HFB-ARC-0201 Technical Blueprint
  - HFB-DEV-0503 Frontend Development Standard
  - HFB-AI-0405 AI Academic Review Standard
  - HFB-PS-1702 Platform Information Architecture Specification
  - HFB-PS-1703 Platform Navigation Interaction Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Design System
## 平台设计系统

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的统一视觉语言（Design Language）。
>
> 本平台定位为**国家级数字人文学术研究平台**，设计目标不是互联网产品，而是兼具学术严谨性、文化表达力和现代交互体验的新一代数字人文平台。

---

# 第一章 设计理念

平台设计遵循：

> **典籍为魂 · 学术为本 · 科技为器**

设计关键词：

- Academic（学术）
- Humanistic（人文）
- Trustworthy（可信）
- Elegant（雅致）
- Modern（现代）
- Intelligent（智能）

避免：

- 商业营销风
- 娱乐社交风
- 炫酷科技风
- 国潮堆砌风

---

# 第二章 品牌视觉定位

整体风格：

> **数字典籍 × 东方美学 × AI 学术研究平台**

视觉气质：

- 安静
- 克制
- 留白
- 清晰
- 权威
- 可长期阅读

目标参考对象：

- 国家图书馆数字平台
- 故宫数字文物平台
- 国际数字人文研究平台

而不是普通后台管理系统。

---

# 第三章 色彩系统

本章色值以 `apps/frontend/src/styles/tokens/colors.css` 与 `semantic.css` 为唯一真源。
所有组件必须通过 `var(--color-*)` / `var(--color-*-*)` 引用，禁止组件内硬编码颜色。

## 核心色彩（Core Colors）

定义于 `styles/tokens/colors.css`：

| Token | 用途 | 值 |
|-------|------|-----|
| `--color-accent` | 主强调色/链接/AI | `#2b6cb0` |
| `--color-accent-hover` | 主强调色悬停 | `#1a4f8a` |
| `--color-accent-light` | 主强调色浅底 | `#ebf8ff` |
| `--color-text-primary` | 正文/主标题 | `#1a365d` |
| `--color-text-secondary` | 次要文字/说明 | `#4a5568` |
| `--color-text-muted` | 占位/禁用/辅助文字 | `#a0aec0` |
| `--color-border` | 边框/分割线 | `#e2e8f0` |
| `--color-hover` | 列表/行悬停底色 | `#edf2f7` |
| `--color-active` | 选中/激活底色 | `#ebf8ff` |
| `--color-navbar-bg` | 顶部导航背景 | `#ffffff` |
| `--color-footer-bg` | 底部背景 | `#f8fafc` |
| `--color-page-bg` | 页面背景 | `#f7fafc` |
| `--color-surface` | 卡片/面板/弹窗背景 | `#ffffff` |
| `--color-tag-bg` | 标签背景 | `#edf2f7` |

## 语义色彩（Semantic Colors）

定义于 `styles/tokens/semantic.css`：

| Token | 语义 | 值 |
|-------|------|-----|
| `--color-success` | 成功（图标/边框） | `#68d391` |
| `--color-success-text` | 成功文字 | `#276749` |
| `--color-success-bg` | 成功背景 | `#f0fff4` |
| `--color-success-icon-bg` | 成功图标背景 | `#c6f6d5` |
| `--color-warning` | 警告（图标/边框） | `#d69e2e` |
| `--color-warning-text` | 警告文字 | `#975a16` |
| `--color-warning-bg` | 警告背景 | `#fffff0` |
| `--color-error` | 错误（图标/边框） | `#fc8181` |
| `--color-error-text` | 错误文字 | `#c53030` |
| `--color-error-light-text` | 错误文字（alt） | `#9b2c2c` |
| `--color-error-bg` | 错误背景 | `#fff5f5` |
| `--color-error-icon-bg` | 错误图标背景 | `#fed7d7` |
| `--color-info` | 信息（图标/边框） | `#3182ce` |
| `--color-info-text` | 信息文字 | `#2c5282` |
| `--color-info-bg` | 信息背景 | `#ebf8ff` |

## 禁用状态（Disabled State）

定义于 `styles/tokens/components.css`：

| Token | 用途 | Light 值 | Dark 值 |
|-------|------|----------|---------|
| `--color-disabled-bg` | 禁用背景 | `#e2e8f0` | `#2d3748` |
| `--color-disabled-text` | 禁用文字 | `#a0aec0` | `#718096` |

## 暗色模式

`html.dark` 下同名 Token 覆盖为暗色对应值，详见各 Token 文件。组件无需感知模式切换——仅引用 Token 即可。

---

# 第四章 字体规范

所有字族定义于 `styles/tokens/typography.css`：

| Token | 用途 | 值 |
|-------|------|-----|
| `--font-sans` | UI 正文 | `-apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', 'Helvetica Neue', sans-serif` |
| `--font-mono` | 代码 | `'SF Mono', 'Fira Code', 'Fira Mono', 'Roboto Mono', monospace` |

| 字号 Token | 值 |
|------------|-----|
| `--text-xs` | `12px` |
| `--text-sm` | `13px` |
| `--text-base` | `14px` |
| `--text-lg` | `16px` |
| `--text-xl` | `20px` |
| `--text-2xl` | `22px` |
| `--text-3xl` | `24px` |

| 字重 Token | 值 |
|------------|-----|
| `--font-normal` | `400` |
| `--font-medium` | `500` |
| `--font-semibold` | `600` |
| `--font-bold` | `700` |

| 行高 Token | 值 |
|------------|-----|
| `--leading-tight` | `1.3` |
| `--leading-normal` | `1.5` |

禁止组件硬编码 `font-family`、`font-size`、`font-weight`、`line-height` 值；必须引用上述 Token。

---

# 第五章 栅格系统

统一：

12 Grid。

最大内容宽度：

```text
1440px
```

正文：

```text
960px
```

古籍阅读：

```text
1000px
```

保证长时间阅读舒适。

---

# 第六章 间距系统

定义于 `styles/tokens/spacing.css`，基于 4px 基网格：

| Token | 数值 |
|--------|------|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-7` | 28px |
| `--space-8` | 32px |
| `--space-10` | 40px |
| `--space-15` | 60px |

禁止硬编码 `margin`、`padding`、`gap` 中的非 Token 间距值。

---

# 第七章 圆角规范

定义于 `styles/tokens/radius.css`：

| Token | 数值 |
|--------|------|
| `--radius-sm` | 4px |
| `--radius-md` | 6px |
| `--radius-lg` | 8px |
| `--radius-xl` | 10px |
| `--radius-2xl` | 12px |

禁止胶囊化按钮（`border-radius: 9999px` 仅限 Badge pill 变体与内部指示器）。

---

# 第八章 阴影规范

定义于 `styles/tokens/shadow.css`：

| Token | 数值 | 用途 |
|--------|------|------|
| `--shadow-sm` | `0 2px 8px rgba(0,0,0,0.06)` | 轻微悬浮 |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.08)` | 卡片/下拉菜单 |
| `--shadow-lg` | `0 8px 30px rgba(0,0,0,0.15)` | 弹窗/抽屉 |
| `--shadow-toast` | `0 4px 12px rgba(0,0,0,0.15)` | Toast 通知 |

保持纸张质感，避免重阴影。

---

# 第九章 图标体系

统一：

Material Symbols + 自定义学术图标。

新增图标必须保持：

- 线性风格
- 统一笔画
- 可缩放

禁止混用多个图标库。

---

# 第十章 组件体系

组件分四级：

```text
Foundation

↓

Basic Components

↓

Business Components

↓

Academic Components
```

Academic Components：

平台特色组件。

---

# 第十一章 学术组件

平台专属组件：

- AncientBookViewer
- VersionComparePanel
- CitationCard
- EvidenceCard
- PersonTimeline
- KnowledgeGraphViewer
- AcademicMap
- OCRCorrectionPanel

不得替换为普通组件。

---

# 第十二章 AI 组件

统一组件：

- AIChatPanel
- CitationPanel
- EvidencePanel
- RetrievalPanel
- PromptInfoCard
- ConfidenceBadge

AI 回答必须展示引用来源。

---

# 第十三章 页面布局

统一：

```text
Top Navigation

↓

Sidebar

↓

Content

↓

Information Panel
```

学术页面可增加：

Reference Panel。

---

# 第十四章 古籍阅读规范

阅读页面必须支持：

- 原文
- 校勘
- 注释
- 多版本切换
- 行号定位
- 引文复制
- 夜间模式

支持连续阅读。

---

# 第十五章 数据可视化

统一组件：

- 时间轴
- 家谱树
- 人物关系图
- 学术传播图
- 地理分布图
- 版本演化图

统一设计语言。

---

# 第十六章 暗色模式

支持：

Light

Dark

Academic Night

Academic Night：

采用深墨色背景。

减少阅读疲劳。

---

# 第十七章 动效规范

定义于 `styles/tokens/transition.css`：

| Token | 值 | 用途 |
|-------|-----|------|
| `--transition-fast` | `0.1s` | 微交互（hover/icon） |
| `--transition-base` | `0.15s` | 常用过渡 |
| `--transition-slow` | `0.2s` | 面板/抽屉展开 |

原则：少而精，动画时长 ≤250ms。禁止炫酷特效，不得影响阅读。

## Z-Index 层级

定义于 `styles/tokens/z-index.css`：

| Token | 值 | 用途 |
|-------|-----|------|
| `--z-dropdown` | `900` | 下拉菜单/选择器 |
| `--z-dialog` | `1000` | 对话框 |
| `--z-drawer` | `1100` | 抽屉 |
| `--z-toast` | `1200` | Toast 通知 |

---

# 第十八章 可访问性

符合：

WCAG 2.1 AA。

必须：

- 键盘操作
- 屏幕阅读器
- 图片 Alt
- 色弱兼容

---

# 第十九章 响应式规范

支持：

- Desktop（优先）
- Tablet
- Mobile（基础支持）

后台系统：

以桌面端为主。

---

# 第二十章 Design Token

唯一真源目录：`apps/frontend/src/styles/tokens/`。

Token 文件结构：

| 文件 | 内容 |
|------|------|
| `colors.css` | 核心色彩（accent, text, border, surface, bg） |
| `semantic.css` | 语义色彩（success, warning, error, info） |
| `components.css` | 组件级 Token（btn, input, focus-ring, disabled） |
| `typography.css` | 字族、字号、字重、行高 |
| `spacing.css` | 4px 基网格间距 |
| `radius.css` | 圆角 |
| `shadow.css` | 阴影 |
| `z-index.css` | Z 轴层级 |
| `transition.css` | 动画时长 |

入口文件 `apps/frontend/src/assets/main.css` 仅负责 `@import` Token 文件与全局 reset/keyframe。禁止在其他位置定义同类视觉常量。

所有组件必须引用 `var(--*)` Token，禁止硬编码颜色/间距/圆角/阴影/z-index/transition 值。

---

# 第二十一章 UI 红线

禁止：

- 商业营销风
- 渐变滥用
- 动画滥用
- 多字体混用
- 多色彩混用
- 无引用 AI 回答
- 不符合学术定位

违反任一项不得上线。

---

# 第二十二章 修订规则

修改 Design System 必须同步更新：

- Frontend Development Standard
- UI Component Standard
- Academic Interaction Standard
- Visualization Standard
- Figma Design Library

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台统一设计系统规范。 |