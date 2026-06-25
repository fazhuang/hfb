---
title: Version Knowledge Model
document_id: HFB-DOM-0803
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Classical Text Version Knowledge Model
priority: P0
related_documents:
  - HFB-DOM-0802 Book Knowledge Model
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-AI-0402 RAG Specification
  - HFB-UI-0603 Academic Interaction Standard
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-RF-1604 Versionology Research Framework
---

# Version Knowledge Model
## 古籍版本知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的古籍版本知识模型。
>
> **Version 是本平台最重要的数据模型之一，也是平台区别于传统古籍数据库和普通 RAG 系统的核心能力。**
>
> 平台所有版本研究、版本比较、版本传播、版本校勘、AI 引用均基于本模型。

---

# 第一章 建设目标

建立统一版本知识体系，实现：

- 古籍版本数字化
- 版本谱系表达
- 版本演化分析
- 校勘依据管理
- AI 精准引用
- GraphRAG 多版本推理

---

# 第二章 Version 定义

Version：

表示同一部古籍在不同历史时期形成的具有独立学术价值的文本版本。

例如：

《针灸甲乙经》：

- 北宋刻本
- 南宋刻本
- 元刻本
- 明刻本
- 清刻本
- 日本刊本
- 现代点校本
- 数字整理本

Version 不是 Book。

Version 属于 Book。

---

# 第三章 Version 层级

统一层级：

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

平台所有引用均定位至：

**Passage。**

---

# 第四章 Version 唯一标识

统一：

UUID v7。

同时维护：

```text
version_code
```

例如：

```text
VER-000001
```

Version Code 永久不变。

---

# 第五章 基础字段

统一字段：

| 字段 | 说明 |
|------|------|
| id | UUID |
| version_code | 版本编码 |
| book_id | 所属 Book |
| version_name | 版本名称 |
| dynasty | 朝代 |
| publication_year | 年代 |
| editor | 整理者 |
| publisher | 出版机构 |
| language | 文本语言 |
| description | 简介 |
| metadata_id | Metadata |

---

# 第六章 版本分类

统一分类：

```text
Original

Printed

Annotated

Critical Edition

Modern Edition

Digital Edition
```

一个版本可具有多个属性。

---

# 第七章 版本来源

必须记录：

- 收藏机构
- 馆藏号
- 出版社
- ISBN（现代）
- DOI（数字资源）
- 扫描来源
- OCR 来源

来源缺失不得发布。

---

# 第八章 版本谱系

平台建立 Version Tree。

例如：

```text
《针灸甲乙经》

        │

──────────────

北宋刻本

        │

明刻本

        │

清刻本

        │

现代点校本
```

谱系不仅记录时间先后，还记录：

- 承袭关系
- 校勘关系
- 整理关系
- 引用关系

---

# 第九章 版本关系模型

统一 Relation Type：

- Derived From（承袭）
- Revised From（修订）
- Corrected By（校勘）
- Annotated By（注释）
- Compared With（比较）
- Referenced By（引用）

每一条关系均必须提供：

Evidence。

---

# 第十章 版本比较模型

Version Compare：

支持：

- 字级比较
- 词级比较
- 句级比较
- 条文比较
- 篇章比较
- 全书比较

比较结果永久保存。

---

# 第十一章 校勘记录

建立 Criticism Record。

记录：

- 校勘位置
- 原文
- 校改内容
- 校勘依据
- 校勘者
- 校勘日期
- 参考文献

所有校勘均可追溯。

---

# 第十二章 Passage 映射

不同版本：

Passage 必须建立映射关系。

例如：

```text
Version A

第12条

↓

Version B

第15条
```

允许：

一对一

一对多

多对一

映射。

---

# 第十三章 版本差异模型

差异类型：

| 类型 | 示例 |
|------|------|
| 缺失 | 条文缺失 |
| 新增 | 后世增补 |
| 改写 | 用词变化 |
| 顺序调整 | 卷次变化 |
| 注释变化 | 新增校注 |

差异必须结构化存储。

---

# 第十四章 AI 引用模型

AI 回答引用 Version 时：

必须包含：

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

Evidence
```

禁止引用：

仅书名。

---

# 第十五章 Version Timeline

自动生成：

Version Timeline。

展示：

- 出现时间
- 流传过程
- 整理历史
- 数字化历史

支持时间轴分析。

---

# 第十六章 Graph 建模

Version 节点允许关联：

- Book
- Version
- Person
- Institution
- Place
- Event
- Paper

形成版本传播网络。

---

# 第十七章 检索模型

支持：

- 版本名称
- 朝代
- 整理者
- 出版社
- 馆藏机构
- 差异内容
- Passage 内容

支持跨版本联合检索。

---

# 第十八章 《针灸甲乙经》专项模型

平台重点建设：

## Version Registry

建立：

全部已知版本目录。

---

## Version Genealogy

建立：

完整版本谱系。

---

## Passage Mapping

建立：

全文条文对应关系。

---

## Difference Database

建立：

版本差异数据库。

---

## Critical Apparatus

建立：

校勘数据库。

---

## AI Citation

实现：

AI 精确引用到：

具体版本、

具体卷、

具体篇、

具体条文。

---

# 第十九章 数据质量

目标：

| 指标 | 标准 |
|------|------|
| Version 唯一率 | 100% |
| Metadata 完整率 | 100% |
| Passage Mapping 完成率 | ≥95% |
| Version Tree 完整率 | ≥95% |
| AI 精确引用率 | ≥98% |

---

# 第二十章 Version 红线

禁止：

- Book 与 Version 混淆
- 无谱系版本
- 无 Metadata
- 无来源版本
- Passage 无映射
- AI 引用版本错误
- 覆盖历史版本

违反任一项不得进入正式知识库。

---

# 第二十一章 修订规则

修改 Version 模型必须同步更新：

- Book Knowledge Model
- Passage Knowledge Model
- Knowledge Graph Model
- RAG Specification
- Academic Citation Model

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.0.0 | 2026-06-24 | 首版发布，作为平台古籍版本知识模型统一规范。 |