---
title: Passage Knowledge Model
document_id: HFB-DOM-0804
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Passage Knowledge Model
priority: P0
related_documents:
  - HFB-DOM-0802 Book Knowledge Model
  - HFB-DOM-0803 Version Knowledge Model
  - HFB-DAT-0302 Ontology Specification
  - HFB-AI-0402 RAG Specification
  - HFB-AI-0403 GraphRAG Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Passage Knowledge Model

## 条文知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的条文（Passage）知识模型。
>
> **Passage 是平台最小知识单元（Atomic Knowledge Unit）。**
>
> 平台所有 AI 检索、知识图谱推理、版本比较、学术引用、校勘分析、术语识别、知识发现均以 Passage 为核心对象。

---

# 第一章 建设目标

建立统一的 Passage 知识模型，实现：

- 古籍全文结构化
- 多版本精准映射
- AI 精准检索
- GraphRAG 推理
- 自动引文定位
- 学术知识抽取

平台不以"章节"作为最小单位，而以 **Passage（条文）** 为最小知识粒度。

---

# 第二章 Passage 定义

Passage：

表示具有独立学术意义、能够单独引用、单独比较、单独建立知识关系的文本片段。

例如《针灸甲乙经》中的：

- 一条经文
- 一条针法
- 一条病证描述
- 一条腧穴说明
- 一条诊疗原则

均视为一个 Passage。

---

# 第三章 层级关系

统一结构：

```text
Book
   ↓
Version
   ↓
Volume（卷）
   ↓
Chapter（篇）
   ↓
Section（节，可选）
   ↓
Passage（条文）
```

AI 与知识图谱默认定位至 Passage。

---

# 第四章 唯一标识

统一：

UUID v7

同时维护：

```text
passage_code
```

例如：

```text
PAS-000000001
```

Passage Code 永久保持不变。

---

# 第五章 基础字段

统一字段：

| 字段            | 说明               |
| --------------- | ------------------ |
| id              | UUID               |
| passage_code    | 条文编码           |
| version_id      | 所属版本           |
| volume_no       | 卷号               |
| chapter_no      | 篇号               |
| section_no      | 节号               |
| sequence_no     | 顺序号             |
| title           | 条文标题（可为空） |
| original_text   | 原文               |
| normalized_text | 标准化文本         |
| metadata_id     | 元数据             |

---

# 第六章 标准化文本

平台维护两套文本：

## Original Text

忠实保留原貌：

- 原字
- 原标点（若有）
- 异体字

不得修改。

---

## Normalized Text

用于：

- AI 检索
- 全文搜索
- NLP
- GraphRAG

保留标准化记录。

---

# 第七章 Passage 分类

统一分类：

```text
Theory（理论）

Acupoint（腧穴）

Disease（病证）

Treatment（治法）

Needling（针法）

Moxibustion（灸法）

Pulse（脉诊）

Prohibition（禁忌）

Case（医案）

Annotation（注释）
```

一个 Passage 可拥有多个类别。

---

# 第八章 Passage Annotation

支持：

- 现代注释
- 古注
- 校勘
- 翻译
- 教学说明

Annotation：

独立实体。

不得修改原文。

---

# 第九章 Passage Mapping

建立：

跨版本映射。

例如：

```text
宋本 Passage 152

↓

明本 Passage 147

↓

现代整理本 Passage 151
```

支持：

- 一对一
- 一对多
- 多对一

---

# 第十章 Passage Difference

记录：

- 增补
- 缺失
- 异文
- 顺序调整
- 校勘意见

所有差异必须可追溯。

---

# 第十一章 Passage Entity

自动抽取实体：

- 人物
- 地名
- 经穴
- 病证
- 药物
- 方剂
- 经络
- 器官
- 朝代
- 古籍

所有实体均关联 Knowledge Graph。

---

# 第十二章 Passage Relation

自动建立关系：

```text
Passage

↓

Entity

↓

Relation

↓

Evidence
```

所有关系必须具备来源。

---

# 第十三章 AI 检索模型

AI 默认检索：

Passage。

返回：

```text
Passage

↓

Version

↓

Book

↓

Evidence

↓

Citation

↓

Confidence
```

禁止直接返回模型生成内容。

---

# 第十四章 学术引用模型

任何引用必须定位：

```text
Book

↓

Version

↓

Volume

↓

Chapter

↓

Passage

↓

Sentence（可选）
```

支持生成：

- GB/T 7714
- APA
- MLA
- Chicago
- BibTeX

---

# 第十五章 Passage Graph

Graph 中：

Passage 可连接：

- Person
- Book
- Version
- Acupoint
- Disease
- Herb
- Prescription
- Paper
- Place
- Event

Passage 是知识图谱的重要枢纽节点。

---

# 第十六章 Passage Embedding

每个 Passage 建立：

- Semantic Embedding
- Keyword Index
- Graph Index
- Citation Index

Embedding 可重建，不作为唯一数据源。

---

# 第十七章 AI 推理

AI 必须支持：

- Passage 推理
- 多 Passage 联合推理
- 多版本 Passage 推理
- 跨古籍 Passage 推理

推理结果必须展示引用链。

---

# 第十八章 《针灸甲乙经》专项建设

平台重点建设：

## 全书 Passage 化

全文拆分至条文级。

---

## Passage 对齐

建立所有版本条文映射。

---

## Passage 校勘

建立条文差异数据库。

---

## Passage 标注

完成：

- 经穴
- 病证
- 治法
- 针法
- 医学术语

实体标注。

---

## Passage AI

实现：

AI 回答精确引用：

> 《针灸甲乙经》××版本 · 第×卷 · 第×篇 · 第×条

---

# 第十九章 数据质量

目标：

| 指标                   | 标准 |
| ---------------------- | ---- |
| Passage 编码覆盖率     | 100% |
| Passage Mapping 完成率 | ≥95% |
| Entity 标注率          | ≥95% |
| AI 精确定位率          | ≥98% |
| Citation 准确率        | ≥99% |

---

# 第二十章 Passage 红线

禁止：

- Passage 无唯一编码
- Passage 无 Metadata
- Passage 无版本关联
- AI 引用未定位 Passage
- 覆盖 Original Text
- 删除校勘记录

违反任一项不得进入正式知识库。

---

# 第二十一章 修订规则

修改 Passage 模型必须同步更新：

- Version Knowledge Model
- Knowledge Graph Model
- RAG Specification
- GraphRAG Specification
- Academic Citation Model

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date       | Description                              |
| ------- | ---------- | ---------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台条文知识模型统一规范。 |
