---
title: UI Component Standard
document_id: HFB-UI-0602
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product Designer
effective_date: 2026-06-24
scope: UI Component Library
priority: P0
related_documents:
  - HFB-UI-0601 Design System
  - HFB-DEV-0503 Frontend Development Standard
  - HFB-DEV-0504 API Design Standard
  - HFB-PS-1702 Platform Information Architecture Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# UI Component Standard

## UI 组件规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》所有 UI 组件的设计、开发、命名、组合及维护标准。
>
> 所有页面必须由标准组件构建，不允许自由拼接页面样式。

---

# 第一章 建设目标

建立统一组件体系，实现：

- 风格统一
- 代码复用
- 快速开发
- 易维护
- 易测试
- 易扩展

平台所有页面均应由组件组合生成。

---

# 第二章 组件分层

组件统一划分四层：

```text
Foundation

↓

Basic Component

↓

Business Component

↓

Academic Component
```

---

## Foundation

设计基础：

- Color Token
- Typography
- Spacing
- Radius
- Shadow
- Icon

仅提供设计能力。

---

## Basic Component

基础组件：

- Button
- Input
- Select
- Checkbox
- Radio
- Switch
- Badge
- Tag
- Avatar
- Tooltip
- Dialog

不得包含业务逻辑。

---

## Business Component

业务组件：

- SearchBar
- FilterPanel
- DataTable
- TreeView
- FileUploader
- Pagination
- Breadcrumb
- SideNavigation

服务多个业务模块。

---

## Academic Component

平台专属组件：

- AncientBookViewer
- VersionComparePanel
- CitationCard
- EvidenceCard
- OCRCorrectionPanel
- PersonTimeline
- KnowledgeGraphViewer
- AcademicMap
- AIAnswerPanel
- PassageViewer

不得用于平台外项目。

---

# 第三章 命名规范

统一：

PascalCase

例如：

```text
BookCard.vue

PersonTimeline.vue

KnowledgeGraphViewer.vue
```

禁止：

```text
book.vue

test.vue

component.vue
```

---

# 第四章 目录规范

```text
components/

base/

business/

academic/

charts/

layout/
```

组件不得跨目录放置。

---

# 第五章 Props 规范

所有 Props：

必须：

- 类型明确
- 默认值明确
- 文档说明完整

禁止：

大量 Optional Props。

---

### 5.1 ariaLabel（可访问名称）

适用范围：HfbButton 及其他交互式基础组件。

**必须提供 `ariaLabel` 的场景：**

- 仅图标按钮（无 default slot 可见文本）——aria-label 是唯一的可访问名称来源
- 无可见文本的交互控件（如纯图标开关、图标操作按钮）

**可省略 `ariaLabel` 的场景：**

- default slot 已包含可见文本（`<HfbButton>提交</HfbButton>`）
- 通过 `aria-labelledby` 引用外部标签

**规则：** 每个交互式 `<button>` 必须拥有可访问名称（来自 innerText、aria-label 或 aria-labelledby），否则 Screen Reader 将读作"未标记按钮"。

---

# 第六章 Events 规范

统一：

```text
onSelect

onChange

onExpand

onCompare
```

禁止：

自定义命名混乱。

---

# 第七章 Slots 规范

统一：

- default
- header
- footer
- actions
- empty

不得随意新增 Slot。

---

# 第八章 状态规范

统一状态：

```text
Loading

Empty

Success

Error
```

每个组件必须处理四种状态。

---

# 第九章 表格组件

统一：

AcademicTable

支持：

- 排序
- 分页
- 筛选
- 导出
- 固定列
- 多选

禁止直接使用原生 Table。

---

# 第十章 表单组件

统一支持：

- 自动校验
- 错误提示
- 必填标识
- 国际化
- 禁用状态

统一使用 Schema 校验。

---

# 第十一章 古籍阅读组件

AncientBookViewer 必须支持：

- 原文阅读
- 注释显示
- 行号定位
- 多版本切换
- 引文复制
- 全文检索
- OCR 对照

属于平台核心组件。

---

# 第十二章 版本比较组件

VersionComparePanel：

支持：

- 左右对照
- 差异高亮
- 行级同步滚动
- 差异统计
- 引文定位

禁止普通 Diff 替代。

---

# 第十三章 人物组件

PersonProfile：

包括：

- 基本信息
- 生平时间轴
- 著作
- 学术关系
- 地图
- 图片

统一布局。

---

# 第十四章 AI 回答组件

AIAnswerPanel：

必须显示：

```text
回答

↓

引用

↓

证据

↓

可信度

↓

模型信息
```

不得仅展示自然语言回答。

---

# 第十五章 图谱组件

KnowledgeGraphViewer：

支持：

- 节点展开
- 边过滤
- 路径高亮
- 多跳关系
- Evidence 查看

Graph 节点颜色统一。

---

# 第十六章 可视化组件

统一：

Charts Library。

包括：

- Timeline
- Tree
- Network
- Sankey
- Geo Map

禁止多个图表库混用。

---

# 第十七章 可测试性

所有组件必须：

- 支持 Unit Test
- 支持 Snapshot
- 支持 Storybook（规划）

组件覆盖率：

≥90%。

---

# 第十八章 可访问性

组件必须：

- 支持键盘操作
- 支持 Screen Reader
- 支持 Focus
- 支持 ARIA

---

# 第十九章 性能规范

组件：

- 按需加载
- Lazy Load
- Virtual List（长列表）

禁止：

大型组件一次全部渲染。

---

# 第二十章 UI 红线

禁止：

- 页面复制组件
- 重复实现 Button
- 重复实现 Table
- 内联样式
- 魔法数字
- 未注册组件
- 无测试组件

违反任一项不得合并。

---

# 第二十一章 修订规则

新增组件必须同步更新：

- Design System
- Component Library
- Figma
- Storybook（规划）
- Frontend Development Standard

---

# 修订记录

| Version | Date       | Description                          |
| ------- | ---------- | ------------------------------------ |
| 1.1.0   | 2026-06-25 | 更新related_documents                |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台 UI 组件统一规范。 |
