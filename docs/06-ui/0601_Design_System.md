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

## 主色（Primary）

```text
玄墨黑
#1F2937
```

用于：

- 导航
- 标题
- Logo

---

## 学术蓝（Academic Blue）

```text
#1E40AF
```

用于：

- 链接
- AI
- 图谱
- 数据分析

---

## 朱砂红（Vermilion）

```text
#B91C1C
```

用于：

- 校勘
- 批注
- 重要提示

---

## 宣纸白（Paper）

```text
#FAF8F2
```

页面背景。

---

## 墨灰

```text
#6B7280
```

正文说明。

---

## 成功绿

```text
#15803D
```

审核通过。

---

## 警示橙

```text
#D97706
```

待审核。

---

# 第四章 字体规范

中文：

```text
思源宋体
```

用于：

古籍。

---

中文 UI：

```text
思源黑体
```

---

英文：

```text
Inter
```

---

代码：

```text
JetBrains Mono
```

禁止：

系统默认字体混用。

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

统一采用 8pt Grid：

| Token | 数值 |
|--------|------|
| XS | 4px |
| SM | 8px |
| MD | 16px |
| LG | 24px |
| XL | 32px |
| XXL | 48px |
| XXXL | 64px |

禁止使用任意间距值。

---

# 第七章 圆角规范

统一：

| 类型 | 数值 |
|------|------|
| Small | 4px |
| Medium | 8px |
| Large | 12px |
| Dialog | 16px |

禁止胶囊化按钮。

---

# 第八章 阴影规范

统一三级：

Level 1

轻微悬浮。

Level 2

卡片。

Level 3

弹窗。

避免重阴影。

保持纸张质感。

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

原则：

少而精。

动画时长：

150~250ms。

禁止：

炫酷特效。

不得影响阅读。

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

所有颜色、字体、间距必须配置为：

```text
Design Tokens
```

禁止：

组件硬编码颜色。

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