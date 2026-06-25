---
title: Master Knowledge Graph Model
document_id: HFB-DOM-0809
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Platform Master Knowledge Graph
priority: P0
related_documents:
  - HFB-DOM-0801 Person Knowledge Model
  - HFB-DOM-0802 Book Knowledge Model
  - HFB-DOM-0803 Version Knowledge Model
  - HFB-DOM-0804 Passage Knowledge Model
  - HFB-DOM-0805 Paper Knowledge Model
  - HFB-DOM-0806 Chronology Knowledge Model
  - HFB-DOM-0807 Geography Knowledge Model
  - HFB-DOM-0808 Academic Citation & Claim Knowledge Model
  - HFB-AI-0403 GraphRAG Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Master Knowledge Graph Model
## 平台总知识图谱模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的总体知识图谱模型（Master Knowledge Graph）。
>
> **Knowledge Graph 是整个平台的知识操作系统（Knowledge Operating System）。**
>
> 所有数据、AI、RAG、GraphRAG、Agent、数字人文分析均建立在统一知识图谱之上。

---

# 第一章 总体目标

平台知识图谱承担六项职责：

- 知识组织（Knowledge Organization）
- 知识关联（Knowledge Linking）
- 知识推理（Knowledge Reasoning）
- 知识发现（Knowledge Discovery）
- 学术分析（Academic Analytics）
- AI 支撑（AI Foundation）

---

# 第二章 图谱总体架构

统一采用：

```text
Data Layer
      │
Knowledge Layer
      │
Semantic Layer
      │
Reasoning Layer
      │
Application Layer
```

Graph 是平台唯一知识中心。

---

# 第三章 一级实体（Core Entity）

一级实体统一定义：

```text
Person

Book

Version

Passage

Paper

Institution

Place

Chronology

Event

Claim

Evidence

Acupoint

Disease

Prescription

Herb

Image

Dataset

Project
```

未来允许扩展。

---

# 第四章 二级实体

二级实体包括：

- Dynasty
- ReignTitle
- Annotation
- OCR
- Metadata
- Publisher
- Journal
- AcademicSchool
- Region
- Topic

均可独立演化。

---

# 第五章 核心关系（Relation）

统一关系分类：

## 学术关系

- AuthorOf
- EditorOf
- TranslatorOf
- Annotates
- Cites
- Supports
- Refutes

---

## 文献关系

- HasVersion
- HasVolume
- HasChapter
- HasPassage

---

## 人物关系

- TeacherOf
- StudentOf
- ColleagueOf
- Influenced
- Cooperated

---

## 地域关系

- BornIn
- WorkedIn
- PublishedIn
- PreservedIn
- SpreadTo

---

## 时间关系

- HappenedAt
- CreatedAt
- PublishedAt
- ActiveDuring

---

## AI关系

- RetrievedBy
- GeneratedFrom
- ReasonedBy

---

# 第六章 Evidence First

所有边必须满足：

```text
Relation

↓

Evidence

↓

Citation

↓

Metadata
```

任何关系不得凭空建立。

---

# 第七章 多层知识网络

平台建立四层图谱：

## 文献图谱

Book

↓

Version

↓

Passage

---

## 人物图谱

Person

↓

Institution

↓

Paper

---

## 学术图谱

Claim

↓

Evidence

↓

Citation

---

## 时空图谱

Chronology

↓

Place

↓

Event

四层共同组成总图谱。

---

# 第八章 GraphRAG

GraphRAG 检索流程：

```text
Question

↓

Entity Linking

↓

Subgraph Retrieval

↓

Evidence Ranking

↓

Reasoning

↓

Citation

↓

Answer
```

Graph 永远先于 LLM。

---

# 第九章 多跳推理

支持：

二跳

三跳

四跳

五跳

例如：

> 皇甫谧

↓

《针灸甲乙经》

↓

某版本

↓

某条文

↓

现代论文

↓

最新观点

形成完整知识链。

---

# 第十章 皇甫谧数字画像

建立：

Digital Huangfu Mi。

包括：

- 生平
- 著作
- 学术关系
- 医学思想
- 地域传播
- 国际影响

动态图谱。

---

# 第十一章 《针灸甲乙经》知识网络

建立：

Book Graph。

包括：

- 全版本
- 全条文
- 全校勘
- 全注释
- 全论文
- 全引用

形成平台最核心知识网络。

---

# 第十二章 学术传播网络

建立：

Academic Influence Graph。

展示：

- 学派传播
- 地域传播
- 国际传播
- 引文传播

支持动态图分析。

---

# 第十三章 地域传承分析

建立：

Regional Knowledge Graph。

自动分析：

- 哪些地区研究最深入
- 哪些地区形成流派
- 哪些地区贡献最大

支持 AI 自动生成分析报告。

---

# 第十四章 AI 推理网络

AI 推理必须遵循：

```text
Question

↓

Graph

↓

Evidence

↓

Reasoning

↓

Citation

↓

Answer
```

LLM 不允许直接生成结论。

---

# 第十五章 自动知识发现

平台支持自动发现：

- 新人物关系
- 新版本关系
- 新传播路径
- 新研究热点
- 新争议观点

所有发现进入待审核状态。

---

# 第十六章 学术分析引擎

平台建立：

Academic Analytics Engine。

自动分析：

- 学术热点
- 学派演化
- 版本传播
- 地域特色
- 国际影响

---

# 第十七章 AI Agent

所有 Agent 均建立在 Graph 上：

包括：

- 学术助手
- 校勘助手
- 版本比较助手
- 文献综述助手
- 地域研究助手

---

# 第十八章 数据质量

目标：

| 指标 | 标准 |
|------|------|
| Entity 完整率 | 100% |
| Relation 可追溯率 | 100% |
| Evidence 覆盖率 | ≥98% |
| AI 引用准确率 | ≥99% |
| Graph 推理成功率 | ≥95% |

---

# 第十九章 Graph 红线

禁止：

- 无来源关系
- AI 编造节点
- AI 编造关系
- Graph 与 Metadata 不一致
- 删除 Evidence
- 删除 Citation

违反任一项不得上线。

---

# 第二十章 平台最终能力

平台最终形成十大核心能力：

1. 皇甫谧数字画像
2. 《针灸甲乙经》数字孪生
3. 全版本知识图谱
4. 地域传播分析
5. 学术观点图谱
6. 自动知识发现
7. AI 学术问答
8. AI 自动综述
9. AI 学术推理
10. 数字人文智能研究平台

---

# 第二十一章 V2 演进规划（Graph 2.0）

Graph 2.0 增加：

- Knowledge Evolution Engine（知识演化引擎）
- Academic Controversy Engine（学术争议引擎）
- Regional Heritage Engine（地域传承引擎）
- Digital Humanities Analytics Engine（数字人文分析引擎）
- Knowledge Recommendation Engine（知识推荐引擎）

Graph 将由知识存储升级为知识计算平台。

---

# 第二十二章 修订规则

修改总知识图谱模型必须同步更新：

- 全部 Domain Model
- GraphRAG Specification
- AI Agent Specification
- RAG Specification
- Data Standard
- Ontology Specification

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台总知识图谱模型。 |