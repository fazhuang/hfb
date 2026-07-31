---
title: AI Research Workspace Specification
document_id: HFB-PS-1705
version: 1.0.0
status: Approved
owner: Product Committee
reviewer: Chief Product Architect
effective_date: 2026-06-24
scope: AI Research Workspace
priority: P0
related_documents:
  - HFB-PS-1702 Platform Information Architecture Specification
  - HFB-PS-1703 Platform Navigation & Interaction Specification
  - HFB-PS-1704 Platform Permission & Workspace Specification
  - HFB-RF-1606 AI-Assisted Academic Research Framework
  - HFB-RF-1611 Knowledge Discovery Research Framework
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# AI Research Workspace Specification

## AI 科研工作台产品规格书

> 本规格书定义《皇甫谧数字人文与中医经典智能研究平台》AI Research Workspace（AI 科研工作台）的产品设计、功能边界、交互模式、AI 协作机制及验收标准。
>
> AI Research Workspace 是平台最核心的科研生产环境，也是研究者开展数字人文研究、AI 协同分析、知识发现及科研成果沉淀的统一工作空间。
>
> 平台所有 AI 能力均通过 AI Research Workspace 提供，而不是分散到各个独立页面。

---

# 第一章 产品定位

AI Research Workspace 是平台的核心产品。

不是：

AI Chat。

不是：

大模型聊天窗口。

而是：

> **AI 驱动的数字人文科研操作系统（AI-powered Research Operating System）**

Workspace 服务整个科研生命周期。

---

# 第二章 产品目标

Workspace 支持：

- 阅读文献
- 查看版本
- 比较版本
- 构建知识图谱
- 收集证据
- AI 推理
- 撰写研究笔记
- 输出科研成果

所有科研活动均可连续完成。

---

# 第三章 Workspace 总体布局

统一采用四栏布局：

```text
┌──────────────────────────────────────────────────────────┐
│ Toolbar                                                  │
├────────┬──────────────────────┬──────────────┬───────────┤
│        │                      │              │           │
│        │                      │              │           │
│Knowledge│   Research Canvas   │ AI Assistant │ Evidence  │
│Navigator│                      │              │  Panel    │
│        │                      │              │           │
│        │                      │              │           │
├────────┴──────────────────────┴──────────────┴───────────┤
│ Research Timeline / Tasks / Activity Log                 │
└──────────────────────────────────────────────────────────┘
```

所有模块统一采用此布局。

---

# 第四章 Knowledge Navigator

左侧导航统一展示：

- 当前研究对象
- 文献目录
- Passage
- Version
- 人物
- 学派
- 地域
- 知识图谱

支持：

- 拖拽
- 收藏
- 多选
- 快速定位

---

# 第五章 Research Canvas

Research Canvas 为科研主区域。

支持：

- 阅读文献
- 图片浏览
- IIIF（预留）
- Passage 对照
- 多版本阅读
- 批注
- 高亮
- 标签
- 引文插入

Research Canvas 是所有研究工作的中心。

---

# 第六章 AI Assistant

AI Assistant 常驻右侧。

统一提供：

- 学术问答
- 文献总结
- 多版本比较
- 自动引文
- 学术翻译
- 概念解释
- 研究建议
- Graph 分析

AI 必须基于平台知识库回答。

所有回答自动附带：

- 引文
- Passage
- Version
- Evidence

---

# 第七章 Evidence Panel

统一管理：

- 引文
- Passage
- 图片
- 校勘记录
- Graph
- 学术论文
- AI 推理记录

支持：

拖拽到 Canvas。

形成研究材料。

---

# 第八章 AI 工作模式

Workspace 支持四种模式：

## Explore

探索模式。

发现资料。

---

## Research

研究模式。

深入分析。

---

## Writing

写作模式。

生成研究笔记。

整理引文。

形成论文草稿。

---

## Review

审核模式。

检查：

- 引文
- AI
- 证据
- Graph

---

# 第九章 Research Session

平台建立：

Research Session。

每次科研：

自动保存：

- 当前对象
- 当前 Graph
- 当前 AI
- 当前页面
- 当前笔记
- 当前证据

任何时候：

继续研究。

---

# 第十章 Notes System

支持：

研究笔记。

包括：

- Markdown
- 富文本
- Graph 引用
- Evidence 引用
- AI 插入
- 图片
- Footnote

自动保存。

---

# 第十一章 AI Context

AI 默认获得：

当前：

Workspace Context。

包括：

- 当前 Version
- 当前 Passage
- 当前 Graph
- 当前 Note
- 当前 Citation
- 当前 Evidence

AI 不需要重新理解上下文。

---

# 第十二章 Graph Workspace

Graph 可独立展开。

支持：

- Graph 编辑
- 路径分析
- Neighbor
- Community
- Timeline

Graph 与 AI 联动。

---

# 第十三章 Research Timeline

自动记录：

```text
Search

↓

Open

↓

Read

↓

AI

↓

Note

↓

Citation

↓

Export
```

形成完整科研轨迹。

---

# 第十四章 Export

支持导出：

- Word
- PDF
- Markdown
- BibTeX
- RIS
- CSL JSON
- PNG（Graph）

导出自动附带引用。

---

# 第十五章 Collaboration

多人协同：

支持：

- 评论
- 批注
- AI 讨论
- Task
- 实时同步
- Review

形成科研协作空间。

---

# 第十六章 AI 能力边界

AI：

允许：

- 阅读
- 检索
- 总结
- 对比
- 翻译
- 推理建议

禁止：

- 发布成果
- 修改正式数据
- 删除资料
- 自动确认结论

所有 AI 输出必须标记：

> AI Generated

---

# 第十七章 性能要求

Workspace：

要求：

- 秒级打开
- 自动保存
- AI 流式回答
- Graph 流畅
- 百万对象支持
- 多窗口

科研不中断。

---

# 第十八章 安全要求

包括：

- Workspace 隔离
- AI 日志
- 操作日志
- 权限控制
- 数据恢复
- 自动备份

保障科研数据安全。

---

# 第十九章 验收标准

Workspace 必须完成：

- 四栏布局
- AI 常驻
- Graph 联动
- Evidence Panel
- Notes
- Session
- Export
- 多人协同
- 自动保存

全部通过。

---

# 第二十章 后续扩展

未来支持：

- 多 Agent 协同
- AI 科研规划
- AI 自动综述
- AI 自动校勘
- AI 自动论文辅助
- AI 实验记录
- MCP 工具调用
- 外部知识库接入

Workspace 保持持续演进。

---

# 修订记录

| Version | Date       | Description                                                                      |
| ------- | ---------- | -------------------------------------------------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，定义 AI 科研工作台产品规格，作为平台 AI 能力的统一入口与科研生产环境。 |
