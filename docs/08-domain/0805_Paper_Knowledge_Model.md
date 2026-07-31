---
title: Paper Knowledge Model
document_id: HFB-DOM-0805
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Academic Paper Knowledge Model
priority: P0
related_documents:
  - HFB-DOM-0801 Person Knowledge Model
  - HFB-DOM-0802 Book Knowledge Model
  - HFB-DOM-0804 Passage Knowledge Model
  - HFB-AI-0403 GraphRAG Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-PS-1709 MVP Implementation Specification
---

# Paper Knowledge Model

## 学术论文知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的学术论文知识模型。
>
> **Paper 不仅是文献资源，更是现代学术研究成果的知识载体。**
>
> 本平台不仅管理论文，还将论文中的观点、证据、人物、古籍、版本、地域和研究方向结构化，构建皇甫谧研究的现代学术知识网络。

---

# 第一章 建设目标

建立统一论文知识模型，实现：

- 论文标准化管理
- 学术观点结构化
- 引文关系可追踪
- 地域研究分析
- 学术演化分析
- AI 学术推理

---

# 第二章 Paper 定义

Paper：

表示具有正式学术发表属性的研究成果。

包括：

- 期刊论文
- 学位论文
- 会议论文
- 专著章节
- 学术报告
- 科研项目成果
- 数字人文研究成果

Paper 属于一级知识实体。

---

# 第三章 唯一标识

统一：

UUID v7。

同时维护：

```text
paper_code
```

例如：

```text
PAPER-000001
```

永久保持唯一。

---

# 第四章 基础字段

统一字段：

| 字段             | 说明     |
| ---------------- | -------- |
| id               | UUID     |
| paper_code       | 论文编号 |
| title            | 标题     |
| subtitle         | 副标题   |
| abstract         | 摘要     |
| keywords         | 关键词   |
| language         | 语言     |
| publication_year | 发表年份 |
| metadata_id      | Metadata |

---

# 第五章 作者模型

作者统一关联：

Person。

支持：

- 第一作者
- 通讯作者
- 多作者
- 作者排序
- 作者贡献（CRediT，可扩展）

不得保存为普通字符串。

---

# 第六章 机构模型

关联：

Institution。

记录：

- 单位
- 学院
- 实验室
- 研究中心

支持机构层级管理。

---

# 第七章 期刊模型

统一记录：

- 期刊名称
- ISSN
- 卷
- 期
- 页码
- DOI
- 出版机构

支持中英文期刊。

---

# 第八章 研究主题

平台建立标准主题体系：

例如：

- 皇甫谧研究
- 《针灸甲乙经》研究
- 针灸史
- 医学史
- 文献学
- 校勘学
- 数字人文
- 知识图谱
- AI 中医研究

支持多主题关联。

---

# 第九章 学术观点

每篇论文可建立：

```text
Paper

↓

Claim（学术观点）

↓

Evidence（证据）

↓

Citation（引文）
```

实现观点级知识管理。

---

# 第十章 引文模型

记录：

- 引用古籍
- 引用版本
- 引用人物
- 引用论文
- 引用章节
- 引用 Passage

支持双向引用。

---

# 第十一章 地域研究模型

重点建设：

Region Research。

记录：

- 地区
- 学派
- 代表人物
- 代表机构
- 研究成果
- 时间分布

支持地域研究统计。

---

# 第十二章 学术流派

建立：

Academic School。

例如：

- 甘肃研究
- 陕西研究
- 日本研究
- 韩国研究
- 欧洲研究

支持跨地区比较。

---

# 第十三章 时间演化

建立：

Research Timeline。

展示：

- 年度论文数量
- 热点变化
- 学术主题演变
- 研究机构变化

支持趋势分析。

---

# 第十四章 知识关联

Paper 可关联：

- Book
- Version
- Passage
- Person
- Institution
- Place
- Event

所有关系均建立 Graph。

---

# 第十五章 AI 表示

AI 返回论文时必须包含：

```text
论文信息

↓

核心观点

↓

引用对象

↓

研究方法

↓

研究贡献

↓

参考文献

↓

可信度
```

不得只返回摘要。

---

# 第十六章 学术影响力

记录：

- 被引次数
- 下载次数
- 收藏次数
- Graph 影响力
- 平台引用次数

支持综合影响力评价。

---

# 第十七章 全文索引

支持：

- 标题
- 摘要
- 全文
- 关键词
- 图表
- 引文

支持语义检索。

---

# 第十八章 《皇甫谧》专项建设

建立：

## 皇甫谧论文数据库

收录：

国内外公开研究成果。

---

## 《针灸甲乙经》论文数据库

建立专题论文库。

---

## 地域研究数据库

重点分析：

- 甘肃
- 陕西
- 河南
- 日本
- 韩国
- 欧洲

研究成果分布。

---

## 学术观点数据库

抽取：

- 观点
- 证据
- 分歧
- 共识

形成观点知识图谱。

---

## AI 学术综述

支持：

自动生成：

- 研究现状
- 热点分析
- 学术争议
- 未来方向

所有结论必须引用来源。

---

# 第十九章 数据质量

目标：

| 指标                 | 标准 |
| -------------------- | ---- |
| Metadata 完整率      | 100% |
| DOI 覆盖率（适用时） | ≥95% |
| 作者关联率           | 100% |
| Book 引用关联率      | ≥95% |
| AI 引文准确率        | ≥99% |

---

# 第二十章 Paper 红线

禁止：

- 作者字符串存储
- 无来源论文
- 无 Metadata
- 无引用关系
- AI 编造论文
- 删除历史版本

违反任一项不得进入正式知识库。

---

# 第二十一章 修订规则

修改 Paper 模型必须同步更新：

- Academic Citation Model
- Knowledge Graph Model
- GraphRAG Specification
- Person Knowledge Model
- Book Knowledge Model

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date       | Description                                  |
| ------- | ---------- | -------------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台学术论文知识模型统一规范。 |
