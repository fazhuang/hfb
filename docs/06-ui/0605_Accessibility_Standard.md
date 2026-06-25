---
title: Accessibility Standard
document_id: HFB-UI-0605
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product Designer
effective_date: 2026-06-24
scope: Accessibility & Inclusive Design
priority: P0
related_documents:
  - HFB-UI-0601 Design System
  - HFB-UI-0602 UI Component Standard
  - HFB-UI-0603 Academic Interaction Standard
  - HFB-UI-0604 Visualization Standard
  - HFB-DEV-0503 Frontend Development Standard
  - HFB-PS-1710 Production Readiness Specification
---

# Accessibility Standard
## 无障碍设计规范

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的无障碍（Accessibility）设计标准。
>
> 平台不仅服务于普通用户，还应服务于老年研究者、视力受限用户、行动不便用户以及依赖辅助设备进行学术研究的人群。
>
> **无障碍不是附加功能，而是平台的基础能力。**

---

# 第一章 建设目标

平台必须实现：

- 可感知（Perceivable）
- 可操作（Operable）
- 可理解（Understandable）
- 可兼容（Robust）

全面遵循：

> **WCAG 2.1 AA**

作为最低建设标准。

---

# 第二章 设计原则

平台遵循四项原则：

```text
Perceivable

↓

Operable

↓

Understandable

↓

Robust
```

任何页面均不得违反上述原则。

---

# 第三章 色彩规范

颜色不得作为唯一信息表达方式。

例如：

错误状态：

❌ 仅使用红色。

必须：

```
红色

+

图标

+

文字说明
```

保证色弱用户可识别。

---

# 第四章 对比度

最小标准：

| 内容 | 对比度 |
|------|--------|
| 正文 | ≥4.5:1 |
| 大标题 | ≥3:1 |
| 图标 | ≥3:1 |

不得降低阅读对比度。

---

# 第五章 字体规范

默认字号：

```text
16px
```

支持：

- 放大至 200%
- 浏览器缩放
- 系统字体放大

不得影响布局。

---

# 第六章 键盘操作

所有功能必须支持：

- Tab
- Shift + Tab
- Enter
- Space
- Esc
- Arrow Keys

禁止：

鼠标唯一操作路径。

---

# 第七章 焦点（Focus）

所有可交互元素：

必须：

具有清晰 Focus。

不得：

隐藏 Focus。

Focus 顺序：

必须符合阅读逻辑。

---

# 第八章 Screen Reader

所有页面必须支持：

- NVDA
- VoiceOver
- TalkBack（基础）

关键元素必须具有：

ARIA Label。

---

# 第九章 图片规范

所有图片必须：

提供：

Alt Text。

学术图片必须增加：

- 图片来源
- 馆藏机构
- 编号
- 描述

---

# 第十章 图表规范

所有图表：

必须：

提供：

- 数据摘要
- 图例
- 表格替代
- 导出数据

图表不得成为唯一信息来源。

---

# 第十一章 表单规范

所有输入框：

必须：

关联：

```text
Label

↓

Input

↓

Hint

↓

Error
```

错误提示必须可朗读。

---

# 第十二章 AI 页面

AI 回答：

必须支持：

- 键盘复制引用
- 引文跳转
- 证据导航
- 可朗读

AI 不得输出图片替代文字。

---

# 第十三章 古籍阅读

AncientBookViewer：

必须支持：

- 字号调整
- 行距调整
- 夜间模式
- 高对比模式
- 朗读模式（规划）

支持长时间阅读。

---

# 第十四章 多版本比较

Version Compare：

支持：

- 键盘切换
- 差异朗读（规划）
- 高亮颜色替代方案

颜色不得成为唯一差异标识。

---

# 第十五章 知识图谱

Knowledge Graph：

必须支持：

- 键盘节点导航
- 节点列表模式
- 搜索模式
- 表格模式

Graph 不得仅依赖拖拽操作。

---

# 第十六章 响应式

支持：

- Desktop
- Tablet
- Mobile

缩放后：

不得：

内容遮挡。

---

# 第十七章 多语言

支持：

- 简体中文
- English

后续：

支持：

繁体中文。

所有语言：

保持一致体验。

---

# 第十八章 性能要求

目标：

| 指标 | 标准 |
|------|------|
| Lighthouse Accessibility | ≥95 |
| WCAG AA | 100% |
| Keyboard Coverage | 100% |
| Screen Reader Support | 100% |

---

# 第十九章 自动检测

CI 自动检查：

- ARIA
- Color Contrast
- Alt Text
- Heading Structure
- Focus Order

未通过不得发布。

---

# 第二十章 用户测试

正式发布前必须完成：

- 键盘测试
- Screen Reader 测试
- 高对比模式测试
- 老年用户体验测试（建议）
- 学术阅读场景测试

形成测试报告。

---

# 第二十一章 无障碍红线

禁止：

- 图片无 Alt
- 无 Focus
- 键盘无法操作
- 颜色唯一表达信息
- AI 回答无法复制引用
- 图表无文字说明
- 表单无 Label

违反任一项不得上线。

---

# 第二十二章 修订规则

修改无障碍规范必须同步更新：

- Design System
- UI Component Standard
- Frontend Development Standard
- Academic Interaction Standard
- Figma Design Library

未经批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台无障碍设计统一规范。 |