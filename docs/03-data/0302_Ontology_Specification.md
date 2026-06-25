---
title: Ontology Specification
document_id: HFB-DAT-0302
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Knowledge Layer
priority: P0
related_documents:
  - HFB-DAT-0301 Data Standard Specification
  - HFB-ARC-0201 Technical Blueprint
  - HFB-AI-0402 RAG Specification
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-GOV-0005 AI Execution Protocol
---

# Ontology Specification
## 本体规范

> 本文档定义《皇甫谧数字人文与中医经典智能研究平台》的统一知识本体（Ontology）。
>
> 所有数据库模型、知识图谱、GraphRAG、RAG、AI 检索、语义分析、学术标注及可视化关系均必须遵循本规范。

---

# 第一章 编制目标

建立平台统一知识语义体系，实现：

- 学术对象统一建模；
- 数据库与知识图谱一致；
- AI 理解统一；
- 多版本古籍统一关联；
- 学术引用统一表达；
- 后续可扩展至整个中医经典体系。

---

# 第二章 Ontology 总体结构

平台采用五层知识模型。

```
Knowledge Domain
        │
Concept Layer
        │
Entity Layer
        │
Relation Layer
        │
Evidence Layer
```

说明：

**Knowledge Domain**

定义研究领域。

例如：

- 皇甫谧研究
- 《针灸甲乙经》
- 古代医学
- 学术传播

---

**Concept Layer**

定义概念。

例如：

人物

著作

章节

论文

版本

机构

地点

朝代

---

**Entity Layer**

定义具体对象。

例如：

皇甫谧

《针灸甲乙经》

《三都赋》

人民卫生出版社点校本

---

**Relation Layer**

描述对象之间关系。

例如：

作者

引用

校勘

传承

属于

影响

研究

评价

---

**Evidence Layer**

所有关系必须具有证据来源。

例如：

古籍原文

论文

图片

碑刻

地方志

数据库

AI 不允许生成无证据关系。

---

# 第三章 一级实体（Core Entity）

一级实体固定如下：

| Entity | 说明 |
|---------|------|
| Person | 人物 |
| Book | 古籍 |
| Version | 版本 |
| Chapter | 章节 |
| Passage | 段落 |
| Paper | 学术论文 |
| Image | 图片 |
| Institution | 机构 |
| Place | 地点 |
| Event | 历史事件 |
| Dynasty | 朝代 |
| Document | 综合资源 |

未经批准不得新增一级实体。

---

# 第四章 Person 本体

用于描述人物。

包括：

- 皇甫谧
- 历代医家
- 注释者
- 校勘者
- 现代研究学者
- 传播者

属性：

```
id

name

aliases

gender

birth

death

dynasty

biography

occupation

source

citation
```

---

# 第五章 Book 本体

描述古籍。

属性：

```
id

title

alternative_title

author

category

dynasty

description

language

source
```

一本古籍可以拥有多个 Version。

---

# 第六章 Version 本体

Version 必须独立存在。

例如：

宋刻本

元刻本

明刻本

清刻本

人民卫生出版社版

数字校勘版

版本之间允许：

```
继承

修订

影印

翻刻

校勘
```

---

# 第七章 Chapter 本体

章节属于：

Book Version。

支持：

树结构。

例如：

```
卷

↓

篇

↓

章节
```

---

# 第八章 Passage 本体

Passage 是：

平台最小知识单元。

AI 默认：

以 Passage 为检索粒度。

不得：

整本书 Embedding。

每个 Passage 必须记录：

- 所属版本；
- 起止位置；
- 原文；
- 标点版本；
- 校勘说明；
- 注释。

---

# 第九章 Paper 本体

表示现代研究成果。

支持：

期刊

学位论文

会议论文

专著章节

研究报告

属性：

DOI

ISSN

引用次数

关键词

基金项目

作者机构

---

# 第十章 Image 本体

包括：

古籍扫描

人物照片

碑刻

拓片

地图

图片必须记录：

来源

版权

拍摄时间

采集人

关联对象

---

# 第十一章 Institution 本体

例如：

高校

科研机构

出版社

博物馆

图书馆

学会

---

# 第十二章 Place 本体

采用统一地理编码。

包括：

古地名

现代行政区

历史地点

支持：

GIS 扩展。

---

# 第十三章 Event 本体

表示历史事件。

例如：

著作完成

版本出版

学术会议

人物活动

事件必须：

关联：

时间

地点

参与人物

证据来源。

---

# 第十四章 Relation 定义

统一关系如下：

| Relation | 含义 |
|----------|------|
| authored_by | 作者 |
| edited_by | 校勘 |
| translated_by | 翻译 |
| belongs_to | 属于 |
| cites | 引用 |
| comments_on | 注释 |
| references | 提及 |
| inherits | 继承 |
| studies | 研究 |
| located_in | 位于 |
| occurred_in | 发生于 |
| related_to | 相关 |
| influences | 影响 |
| derived_from | 来源于 |

任何新增关系：

必须：

更新本规范。

---

# 第十五章 Evidence（证据）

每一个 Relation 必须至少拥有一个 Evidence。

Evidence 来源：

古籍

论文

地方志

数据库

图片

碑刻

档案

AI 输出

（仅作为辅助，不可成为最终证据）

不存在：

无来源关系。

---

# 第十六章 Ontology 与数据库映射

Ontology

↓

Entity

↓

Database Table

↓

Repository

↓

Service

↓

API

↓

RAG

↓

GraphRAG

↓

Visualization

保持一一对应。

不得：

数据库与 Ontology 不一致。

---

# 第十七章 Ontology 与 AI

AI：

只能读取：

Ontology。

不得：

自行创造：

Entity。

Relation。

Concept。

AI 新发现：

必须：

进入：

Candidate Ontology。

人工审核。

通过后：

进入正式 Ontology。

---

# 第十八章 扩展机制

未来允许增加：

Animal

Plant

Medicine

Formula

Disease

Symptom

Acupoint

Meridian

PersonGroup

等实体。

但：

不得进入 MVP。

MVP 阶段实体边界参见 [HFB-PS-1709 MVP](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)。

新增必须：

建立 ADR。

更新：

Ontology。

Data Standard。

数据库。

API。

Context。

Prompt。

---

# 第十九章 Ontology 生命周期

提出

↓

评审

↓

实验

↓

批准

↓

实施

↓

版本发布

↓

长期维护

所有版本永久保存。

---

# 第二十章 成功标准

平台所有：

数据库

API

Graph

RAG

AI

可视化

必须基于统一 Ontology。

Ontology 是整个系统唯一知识语义标准。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 新增MVP边界交叉引用(第十八章)；更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台统一知识本体规范。 |