---
title: RAG Specification
document_id: HFB-AI-0402
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: AI Retrieval Layer
priority: P0
related_documents:
  - HFB-AI-0401 AI Engineering Standard
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0303 Metadata Standard
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-PS-1705 AI Research Workspace Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# RAG Specification

## 检索增强生成（RAG）规范

> 本规范定义平台 Retrieval-Augmented Generation（RAG）架构，是所有 AI 学术问答、文献检索、智能分析、多版本对比等功能的统一技术标准。
>
> **RAG 是平台第一代 AI 检索架构，也是后续 GraphRAG 的基础。**

---

# 第一章 建设目标

平台 RAG 的目标不是简单"向量检索"。

而是建设：

> **数字人文领域可信知识检索系统（Trustworthy Academic Retrieval System）**

必须满足：

- 引文可信
- 检索可解释
- 数据可追溯
- 支持多版本古籍
- 支持数字人文研究

---

# 第二章 RAG 总体架构

平台采用六阶段 RAG Pipeline。

```text
User Question
      │
      ▼
Query Understanding
      │
      ▼
Retriever
      │
      ▼
Reranker
      │
      ▼
Context Builder
      │
      ▼
LLM + Citation
```

---

# 第三章 Query Understanding

负责：

- 查询规范化
- 同义词扩展
- 古今异名统一
- 人物别名解析
- 朝代名称统一
- 古籍简称展开

例如：

```
甲乙经

↓

《针灸甲乙经》
```

```
皇甫士安

↓

皇甫谧
```

所有 Query Rewrite 必须可记录。

---

# 第四章 Retrieval（检索）

RAG 检索采用混合检索。

包括：

- 全文检索（BM25）
- 向量检索
- Metadata Filter
- Ontology Filter

检索对象包括：

- Passage
- Paper
- Image
- Book
- Chapter
- Document

---

# 第五章 Chunk 规范

平台统一采用 Passage 作为默认 Chunk。

禁止：

整本古籍 Embedding。

Chunk 必须满足：

- 语义完整
- 可独立引用
- 保留上下文定位

建议长度：

```
300～800 Token
```

每个 Chunk 必须关联：

- Book
- Version
- Chapter
- Metadata
- Entity

---

# 第六章 Embedding 规范

Embedding 对象：

- Passage
- Paper Abstract
- Caption
- Annotation

禁止：

OCR 原始全文直接 Embedding。

Embedding 必须记录：

- Model
- Version
- Vector Dimension
- Created Time

---

# 第七章 Metadata Filtering

RAG 必须支持 Metadata 检索。

例如：

按：

- 朝代
- 作者
- 古籍
- 版本
- 地区
- 年份
- 来源

进行过滤。

不得仅依赖向量相似度。

---

# 第八章 Reranker

所有检索结果必须经过 Reranker。

排序依据：

- 语义相关性
- Evidence 完整性
- Metadata 匹配
- 学术可信度

禁止直接返回 Retriever 结果。

---

# 第九章 Context Builder

Context Builder 负责：

- 去重
- 合并
- 排序
- 引文编号
- Token 控制

最终 Context 必须：

- 保留出处
- 保留版本
- 保留章节
- 保留引用编号

---

# 第十章 Citation Engine

平台所有回答必须引用来源。

引用最少包含：

- 古籍名称
- 版本
- 卷
- 篇
- 段落
- 页码（如有）
- DOI（论文）

示例：

> 《针灸甲乙经》·人民卫生出版社点校本·卷三·第十二节

禁止：

"据资料显示"

"根据文献"

等模糊表达。

---

# 第十一章 多版本支持

RAG 必须支持：

同一 Passage：

多个版本。

例如：

```
宋刻本

↓

明刻本

↓

人民卫生出版社版

↓

现代校勘版
```

用户可指定：

- 单版本
- 多版本
- 自动比较

---

# 第十二章 学术问答模式

平台支持：

## 1. 文献检索

返回：

文献 + 引文。

---

## 2. 人物研究

返回：

人物关系。

时间轴。

著作。

引用。

---

## 3. 古籍比对

返回：

版本差异。

校勘说明。

引用。

---

## 4. 学术综述

自动整理：

论文。

引用。

研究观点。

争议。

---

# 第十三章 AI 输出规范

所有 RAG 输出必须包含：

```json
{
  "answer": "...",
  "citations": [],
  "evidence": [],
  "confidence": 0.98,
  "retrieval_count": 12,
  "model": "...",
  "prompt_version": "..."
}
```

禁止仅输出自然语言。

---

# 第十四章 性能指标

| 指标              | 标准  |
| ----------------- | ----- |
| 首次检索          | ≤1 秒 |
| RAG 响应          | ≤3 秒 |
| Top10 Recall      | ≥95%  |
| Citation Accuracy | ≥99%  |
| Metadata 完整率   | 100%  |

---

# 第十五章 Roadmap

Sprint 1~5：

完成数据规范。

Sprint 6：

Embedding。

Sprint 7：

OCR。

Sprint 8：

RAG 第一版。

Sprint 9：

知识图谱。

Sprint 10：

GraphRAG。

---

# 第十六章 RAG 红线

禁止：

- 无引用回答
- 无 Metadata 检索
- 全书 Embedding
- OCR 原文直接检索
- 未审核数据进入 RAG
- AI 自生成引用

违反任一项不得上线。

---

# 第十七章 修订规则

新增：

Retriever

Chunk Strategy

Embedding

Citation

Reranker

必须同步更新：

- AI Engineering Standard
- Technical Blueprint
- Context Package
- ADR

---

# 修订记录

| Version | Date       | Description                       |
| ------- | ---------- | --------------------------------- |
| 1.1.0   | 2026-06-25 | 更新related_documents             |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台 RAG 技术规范。 |
