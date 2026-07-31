---
title: Platform Navigation & Interaction Specification
document_id: HFB-PS-1703
version: 1.0.0
status: Approved
owner: Product Committee
reviewer: Chief Product Architect
effective_date: 2026-06-24
scope: Platform Navigation and User Interaction
priority: P0
related_documents:
  - HFB-PS-1701 Version Center Product Specification
  - HFB-PS-1702 Platform Information Architecture Specification
  - HFB-UI-0601 Design System
  - HFB-UI-0603 Academic Interaction Standard
  - HFB-GOV-0001 Project Charter
  - HFB-PS-1709 MVP Implementation Specification
---

# Platform Navigation & Interaction Specification

## 平台导航与交互规范

> 本规格书定义《皇甫谧数字人文与中医经典智能研究平台》的统一导航体系（Navigation System）与统一交互体系（Interaction System）。
>
> 本规范适用于平台所有页面、组件、AI 工作区及未来新增模块，是平台 UI/UX 的最高约束规范。
>
> 任何模块不得自行设计导航逻辑、交互逻辑或页面结构。

---

# 第一章 设计目标

平台定位不是后台管理系统。

也不是传统数字图书馆。

平台定位：

> **面向数字人文科研全过程的智能研究平台。**

因此导航设计必须满足：

- 研究连续性
- 学术探索性
- AI 协同性
- 国际化
- 长时间科研工作的舒适性

平台优先支持连续研究，而不是页面跳转。

---

# 第二章 导航设计原则

平台统一遵循：

## Research First

导航服务于研究流程。

而不是功能分类。

---

## Object Driven

所有导航最终都应进入：

Knowledge Object。

而不是孤立页面。

---

## AI Always Available

AI 不属于独立页面。

AI 永远在线。

任何页面均可调用。

---

## Never Lose Context

用户切换页面时：

研究上下文不得丢失。

包括：

- 当前对象
- 当前Graph
- 当前AI对话
- 当前Evidence
- 当前Workspace

全部保持。

---

# 第三章 全局导航

统一顶部导航：

```text
首页

研究

知识

资源

AI工作台

分析

管理
```

导航保持固定。

不得根据模块增加一级菜单。

---

# 第四章 左侧导航

左侧为：

Context Navigation。

根据当前对象动态变化。

例如：

Version：

```text
概览

基本信息

版本关系

时间轴

校勘

引用

证据

Graph

AI分析
```

Person：

```text
概览

生平

著作

关系

传播

论文

Graph

AI分析
```

保持一致风格。

---

# 第五章 面包屑

所有页面：

必须显示：

```text
Home

>

Knowledge

>

Version

>

Song Edition
```

支持快速返回。

---

# 第六章 Workspace 导航

科研工作统一进入：

Workspace。

Workspace 固定布局：

```text
左

Knowledge Navigator

──────────────

中

Research Canvas

──────────────

右

AI Assistant

──────────────

下

Evidence Timeline
```

任何模块不得修改。

---

# 第七章 页面布局

统一布局：

```text
Header

↓

Breadcrumb

↓

Toolbar

↓

Content

↓

AI Panel

↓

Status Bar
```

所有页面保持一致。

---

# 第八章 页面交互

统一交互：

单击：

打开详情。

双击：

进入研究。

右键：

对象菜单。

Hover：

对象预览。

拖拽：

Graph。

所有对象保持一致。

---

# 第九章 Object Interaction

所有 Knowledge Object：

支持：

- 收藏
- 分享
- 引用
- Graph
- AI分析
- 添加笔记
- 添加标签
- 查看证据

无需进入详情。

---

# 第十章 AI Interaction

AI 默认提供：

```text
Explain

Compare

Summarize

Translate

Analyze

Generate Citation

Find Evidence

Research Suggestion
```

右侧固定存在。

不允许弹窗AI。

---

# 第十一章 Graph Interaction

Graph：

统一支持：

缩放

拖动

聚焦

过滤

路径分析

邻居分析

AI解释

Graph 体验统一。

---

# 第十二章 Search Interaction

统一搜索：

输入：

即时建议。

Enter：

全局搜索。

结果：

统一对象卡片。

支持：

Graph

AI

Preview

无需跳转。

---

# 第十三章 Research Interaction

研究过程：

```text
Search

↓

Object

↓

Evidence

↓

AI

↓

Notes

↓

Export
```

形成连续科研流。

平台禁止：

大量页面跳转。

---

# 第十四章 Notification

通知统一：

右上角。

分类：

- System
- Research
- AI
- Tasks

避免干扰研究。

---

# 第十五章 Keyboard

支持：

```text
/

搜索

G

Graph

A

AI

N

Note

E

Evidence

Ctrl+K

Command Palette
```

科研效率优先。

---

# 第十六章 Mobile

移动端：

保持：

Research First。

支持：

- 阅读
- Graph
- AI

复杂编辑建议桌面完成。

---

# 第十七章 Accessibility

支持：

- 键盘导航
- Screen Reader
- 高对比模式
- 字号缩放
- 色弱支持

符合国际规范。

---

# 第十八章 国际化

导航全部支持：

- 中文
- English

后续：

- 日本语
- 한국어

无需重新设计。

---

# 第十九章 验收标准

导航必须满足：

- 五秒找到对象
- 三步进入研究
- AI 全局可用
- Graph 全局一致
- Workspace 无状态丢失
- Search 全局统一

全部通过。

---

# 第二十章 后续模块约束

任何新增模块：

不得：

重新设计导航。

不得：

新增一级菜单。

不得：

改变 Workspace。

必须：

遵循：

1702

1703

统一规范。

---

# 修订记录

| Version | Date       | Description                                                               |
| ------- | ---------- | ------------------------------------------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，定义平台统一导航与交互规范，作为所有模块 UI/UX 开发的最高约束。 |
