---
title: Book Knowledge Model
document_id: HFB-DOM-0802
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Classical Book Knowledge Model
priority: P0
related_documents:
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0304 Entity Specification
  - HFB-DOM-0801 Person Knowledge Model
  - HFB-AI-0402 RAG Specification
  - HFB-UI-0603 Academic Interaction Standard
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-RF-1603 Acupuncture A-B Classic Research Framework
---

# Book Knowledge Model

## 古籍知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的古籍知识建模标准。
>
> **Book 是平台的一级核心实体。**
>
> 本平台所有古籍均采用统一知识模型，其中《针灸甲乙经》作为一级重点对象，建立完整的数字化、知识化、智能化表达体系。

---

# 第一章 建设目标

建立统一古籍知识模型，实现：

- 古籍标准描述
- 多版本统一管理
- 知识结构表达
- 学术引用规范
- AI 可理解
- GraphRAG 可推理

Book 是整个知识体系的核心节点。

---

# 第二章 Book 定义

Book：

表示一部具有独立学术身份、能够形成完整知识体系的古籍。

例如：

- 《针灸甲乙经》
- 《黄帝内经》
- 《难经》
- 《伤寒论》
- 《脉经》

Book 不是某一个版本。

Book 是所有版本的父级实体。

---

# 第三章 Book 生命周期

统一：

```text
Collect

↓

Catalog

↓

Review

↓

Publish

↓

Maintain

↓

Archive
```

任何修改均保存版本历史。

---

# 第四章 唯一标识

统一：

UUID v7。

同时维护：

```text
book_code
```

例如：

```text
BOOK-00000001
```

不得使用书名作为唯一主键。

---

# 第五章 Book 基础字段

统一字段：

| 字段          | 说明       |
| ------------- | ---------- |
| id            | UUID       |
| book_code     | 古籍编码   |
| title         | 标准书名   |
| aliases       | 异名、别称 |
| english_title | 英文名称   |
| category      | 分类       |
| dynasty       | 成书时代   |
| language      | 语言       |
| description   | 内容简介   |
| metadata_id   | Metadata   |

---

# 第六章 作者关系

Book：

必须关联：

Person。

关系类型：

- Author
- Compiler
- Editor
- Annotator
- Translator

支持：

多作者。

不得直接写字符串作者。

---

# 第七章 古籍分类

统一分类：

```text
针灸

内经

经方

本草

诊法

医论

方书

养生

其他
```

一个 Book 可属于多个分类。

---

# 第八章 知识层级

Book 建立统一层级：

```text
Book

↓

Version

↓

Volume

↓

Chapter

↓

Section

↓

Passage
```

所有古籍统一遵循此结构。

---

# 第九章 《针灸甲乙经》专属模型

平台重点对象。

除标准字段外，还应支持：

- 原书结构
- 后世整理结构
- 卷次映射
- 篇章映射
- 多版本对应关系
- 校勘记录
- 经穴关联
- 病证关联
- 针刺方法关联

作为平台一级知识对象。

---

# 第十章 学术属性

记录：

- 学术价值
- 医学价值
- 历史地位
- 后世影响
- 现代研究现状

支持：

多个来源。

---

# 第十一章 文献来源

记录：

- 收藏机构
- 出版机构
- ISBN（现代整理本）
- 馆藏编号
- DOI（数字资源）
- 数据来源

所有来源必须可追溯。

---

# 第十二章 图片资源

Book 支持关联：

- 封面
- 扉页
- 目录
- 原刻本
- 扫描件
- 高清图片

图片必须关联 Metadata。

---

# 第十三章 OCR 资源

支持：

OCR 数据。

包括：

- OCR 原文
- 校勘结果
- OCR 版本号
- 人工校正记录

OCR 数据不得覆盖原始图像。

---

# 第十四章 AI 表示

AI 返回 Book 时：

必须包含：

```text
书籍信息

↓

作者

↓

版本数量

↓

知识结构

↓

代表章节

↓

引用来源

↓

可信度
```

不得仅返回简介。

---

# 第十五章 Book Graph

Book 节点允许关联：

- Person
- Version
- Paper
- Institution
- Event
- Place

所有关系必须来源于：

Relation。

---

# 第十六章 检索模型

Book 检索支持：

- 标题
- 别名
- 作者
- 朝代
- 分类
- 内容关键词
- 经穴
- 病证

支持自然语言检索。

---

# 第十七章 Metadata

每部古籍必须包含：

- 来源
- License
- 创建时间
- 更新时间
- 审核状态
- 编辑历史

Metadata 不完整不得发布。

---

# 第十八章 数据质量

目标：

| 指标            | 标准 |
| --------------- | ---- |
| Book 唯一性     | 100% |
| Metadata 完整率 | 100% |
| 作者关联率      | 100% |
| Version 建立率  | 100% |
| AI 可解释率     | 100% |

---

# 第十九章 Book 红线

禁止：

- Book 与 Version 混淆
- 无作者关系
- 无 Metadata
- 无来源古籍
- OCR 覆盖原图
- AI 编造古籍信息

违反任一项不得进入正式知识库。

---

# 第二十章 《针灸甲乙经》重点建设要求

作为平台核心资源，必须实现：

## 1. 全版本数字化

建立完整版本体系。

---

## 2. 全文结构化

细化至：

**Passage（条文）级。**

---

## 3. 全文知识标注

包括：

- 经穴
- 病证
- 针法
- 人物
- 地名
- 医学术语

---

## 4. 全版本校勘

建立：

版本差异数据库。

---

## 5. GraphRAG

所有章节均支持：

知识图谱推理。

---

## 6. AI 学术问答

AI 回答必须：

引用具体版本、

具体卷、

具体篇、

具体条文。

---

# 第二十一章 修订规则

修改 Book 模型必须同步更新：

- Version Knowledge Model
- Passage Knowledge Model
- Knowledge Graph Model
- RAG Specification
- Metadata Standard

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date       | Description                              |
| ------- | ---------- | ---------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台古籍知识模型统一规范。 |
