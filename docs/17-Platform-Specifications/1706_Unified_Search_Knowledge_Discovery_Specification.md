---
title: Unified Search & Knowledge Discovery Specification
document_id: HFB-PS-1706
version: 1.0.0
status: Approved
owner: Product Committee
reviewer: Chief Product Architect
effective_date: 2026-06-24
scope: Unified Search and Knowledge Discovery
priority: P0
related_documents:
  - HFB-PS-1702 Platform Information Architecture Specification
  - HFB-PS-1705 AI Research Workspace Specification
  - HFB-RF-1611 Knowledge Discovery Research Framework
  - HFB-RF-1610 Academic Evidence Research Framework
  - HFB-GOV-0001 Project Charter
  - HFB-PS-1709 MVP Implementation Specification
---

# Unified Search & Knowledge Discovery Specification

## 统一检索与知识发现规格书

> 本规格书定义《皇甫谧数字人文与中医经典智能研究平台》的统一检索中心（Unified Search Center）与知识发现中心（Knowledge Discovery Center）的产品设计。
>
> 本模块是平台所有数据、知识对象、知识图谱、AI 推理及科研工作的统一入口。
>
> 平台任何对象均不得设计独立搜索系统，统一通过 Unified Search 完成。

---

# 第一章 产品定位

Unified Search 不是传统全文检索。

也不是数据库查询。

平台定义：

> **Research Discovery Engine（科研发现引擎）**

用户输入一个问题。

平台不仅返回：

"有什么数据"

还要回答：

"数据之间有什么关系。"

"哪些值得进一步研究。"

因此：

Search = Search + Graph + AI + Evidence。

---

# 第二章 产品目标

统一搜索支持：

- 数据发现
- 知识发现
- 学术发现
- AI 推理
- Graph 检索
- 研究导航

最终帮助研究人员：

快速进入科研。

---

# 第三章 检索对象

统一检索：

```text
Version

Book

Passage

Person

Institution

Concept

Disease

Acupoint

Prescription

Evidence

Citation

Paper

Project

Image
```

未来新增对象：

自动进入统一检索。

---

# 第四章 检索模式

平台统一提供：

## Keyword Search

关键词。

---

## Semantic Search

语义搜索。

---

## Graph Search

图谱搜索。

---

## Evidence Search

证据搜索。

---

## AI Search

自然语言搜索。

---

## Advanced Search

高级组合检索。

---

# 第五章 AI Search

支持：

例如：

```text
皇甫谧有哪些弟子？

↓

哪些版本保存最完整？

↓

针灸甲乙经中所有治疗头痛的方法。

↓

日本保存有哪些版本？

↓

皇甫谧与张仲景有哪些联系？
```

无需关键词。

AI 自动转换：

Graph Query。

---

# 第六章 检索流程

统一流程：

```text
User Question

↓

Intent Analysis

↓

Entity Recognition

↓

Knowledge Graph

↓

Vector Search

↓

Evidence Ranking

↓

Citation Verification

↓

Answer Generation
```

全过程统一。

---

# 第七章 搜索结果

统一结果：

第一页：

AI Summary。

第二页：

Knowledge Objects。

第三页：

Evidence。

第四页：

Citation。

第五页：

Graph。

第六页：

Research Suggestions。

不是：

一堆列表。

---

# 第八章 Search Result Card

统一对象卡片：

包括：

- 标题
- 类型
- 简介
- 来源
- Version
- Graph
- AI
- 收藏

点击：

进入 Workspace。

---

# 第九章 Graph Discovery

Graph：

支持：

- Neighbor
- Shortest Path
- Community
- Timeline
- Influence

Graph 与 Search 同时展示。

---

# 第十章 Evidence Discovery

自动展示：

支持答案的：

- 原文
- Version
- Passage
- Citation
- 图片
- 校勘记录

Evidence 永远先于 AI。

---

# 第十一章 Research Suggestion

AI 自动推荐：

例如：

相关人物。

相关 Passage。

相关论文。

相关版本。

相关证据。

形成：

Next Research。

---

# 第十二章 Search History

自动保存：

- Query
- AI
- Graph
- Evidence
- Workspace

方便继续研究。

---

# 第十三章 Advanced Search

支持：

AND

OR

NOT

时间。

地域。

Version。

人物。

馆藏。

Language。

支持组合。

---

# 第十四章 Discovery Dashboard

展示：

今日热点。

新增资料。

新增版本。

新增论文。

Graph 更新。

AI 推荐研究方向。

平台科研入口。

---

# 第十五章 API

统一：

```text
/search

/search/graph

/search/evidence

/search/ai

/search/advanced

/search/suggestion
```

禁止模块：

自行实现搜索。

---

# 第十六章 AI 能力

AI：

默认：

- Search
- Compare
- Explain
- Summarize
- Translate
- Suggest

全部基于：

平台知识。

---

# 第十七章 性能要求

要求：

百万对象。

秒级返回。

Graph：

实时。

AI：

流式。

缓存。

全文。

向量。

统一。

---

# 第十八章 安全要求

包括：

权限过滤。

AI 权限。

Workspace 权限。

日志。

防 Prompt Injection。

防越权。

统一实现。

---

# 第十九章 验收标准

必须支持：

- Keyword
- Semantic
- Graph
- Evidence
- AI
- Suggestion
- History
- Workspace

全部通过。

---

# 第二十章 后续扩展

未来支持：

OpenAlex。

Crossref。

PubMed。

Wikidata。

国家图书馆。

IIIF。

MCP Search。

形成：

全球知识检索。

---

# 修订记录

| Version | Date       | Description                                                            |
| ------- | ---------- | ---------------------------------------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，定义统一检索与知识发现中心产品规格，为平台提供统一科研入口。 |
