---
title: Person Knowledge Model
document_id: HFB-DOM-0801
version: 1.1.0
status: Approved
owner: Academic Committee
reviewer: Chief Knowledge Architect
effective_date: 2026-06-24
scope: Person Domain Model
priority: P0
related_documents:
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-UI-0603 Academic Interaction Standard
  - HFB-AI-0402 RAG Specification
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-RF-1602 Huangfu Mi Studies Framework
---

# Person Knowledge Model

## 人物知识模型

> 本规范定义《皇甫谧数字人文与中医经典智能研究平台》的人物知识建模标准。
>
> Person 是平台最核心的知识实体之一，也是知识图谱、RAG、GraphRAG、数字人文研究及 AI 推理的重要基础。

---

# 第一章 建设目标

建立统一的人物知识模型，实现：

- 人物信息标准化
- 多来源融合
- 学术关系表达
- 时空关联分析
- AI 可推理
- 知识图谱可扩展

平台所有人物均必须遵循本规范。

---

# 第二章 Person 定义

Person：

表示具有明确身份并能够建立学术关系的人物。

包括：

- 皇甫谧
- 医家
- 学者
- 注释者
- 校勘者
- 编者
- 作者
- 导师
- 研究者

Person 不是姓名，而是知识实体。

---

# 第三章 Person 生命周期

统一生命周期：

```text
Collect

↓

Verify

↓

Normalize

↓

Publish

↓

Maintain

↓

Archive
```

所有修改均保留历史版本。

---

# 第四章 Person 唯一标识

统一采用：

UUID v7。

同时维护：

```text
person_code
```

例如：

```text
PERSON-00000001
```

不得使用姓名作为唯一标识。

---

# 第五章 核心字段

Person 至少包含：

| 字段        | 说明                 |
| ----------- | -------------------- |
| id          | UUID                 |
| person_code | 人物编码             |
| name        | 标准姓名             |
| aliases     | 别名、字、号、谥号等 |
| gender      | 性别                 |
| birth_year  | 生年                 |
| death_year  | 卒年                 |
| dynasty     | 朝代                 |
| ethnicity   | 民族（适用时）       |
| occupation  | 身份/职业            |
| biography   | 生平简介             |
| metadata_id | 元数据关联           |

---

# 第六章 扩展字段

支持：

- 籍贯
- 活动地区
- 师承
- 学派
- 官职
- 爵位
- 医学流派
- 社会身份
- 研究方向（现代人物）

采用可扩展属性模型。

---

# 第七章 人物分类

统一分类：

```text
Ancient Person

Modern Scholar

Institution Member

Historical Figure

Medical Practitioner

Research Contributor
```

一个人物可属于多个分类。

---

# 第八章 时间属性

支持：

- 生卒年
- 活跃年代
- 朝代
- 年号
- 历史时期

支持：

不确定时间表达：

例如：

```text
约215年

三国时期

西晋初年
```

---

# 第九章 地理属性

支持关联：

- 出生地
- 活动地
- 任职地
- 著述地
- 墓葬地（适用时）

统一关联：

Place Entity。

禁止文本硬编码。

---

# 第十章 著作关系

Person 可关联：

- Book
- Paper
- Annotation
- Commentary
- Translation

关系必须标明角色：

```text
Author

Editor

Commentator

Translator

Compiler
```

---

# 第十一章 人物关系

支持：

- 师承
- 同门
- 合作者
- 家族
- 学术影响
- 引用关系
- 被研究关系

关系必须关联：

Evidence。

---

# 第十二章 学术影响

记录：

- 代表著作
- 学术贡献
- 医学贡献
- 后世评价
- 现代研究情况

支持：

引用来源。

---

# 第十三章 图片资源

支持关联：

- 肖像
- 石刻
- 雕像
- 手稿
- 文献照片

所有图片必须关联：

Metadata。

---

# 第十四章 时间轴

自动生成：

Person Timeline。

包括：

- 出生
- 求学
- 著述
- 任职
- 学术事件
- 卒年

时间轴数据来源可追溯。

---

# 第十五章 AI 表示

AI 检索 Person 时：

必须返回：

```text
人物

↓

基本信息

↓

代表著作

↓

学术关系

↓

引用来源

↓

可信度
```

不得返回未经验证信息。

---

# 第十六章 Graph 建模

Person 节点允许连接：

- Person
- Book
- Version
- Paper
- Place
- Institution
- Event

所有边必须：

具备 Relation Type。

---

# 第十七章 Metadata

每个 Person 必须关联：

- 来源
- 编辑记录
- 创建者
- 审核状态
- License
- 更新时间

Metadata 缺失不得发布。

---

# 第十八章 数据质量

目标：

| 指标            | 标准 |
| --------------- | ---- |
| Metadata 完整率 | 100% |
| 人物唯一性      | 100% |
| 来源完整率      | 100% |
| Graph 可连接率  | 100% |
| AI 可解释率     | 100% |

---

# 第十九章 Person 红线

禁止：

- 重复人物
- 无来源人物
- 无 Metadata
- 姓名作为主键
- AI 编造人物
- 未建立关系直接发布

违反任一项不得进入正式知识库。

---

# 第二十章 修订规则

修改 Person 模型必须同步更新：

- Ontology Specification
- Entity Specification
- Relation Specification
- Knowledge Graph Model
- RAG Specification

未经学术委员会批准不得修改。

---

# 修订记录

| Version | Date       | Description                              |
| ------- | ---------- | ---------------------------------------- |
| 1.0.0   | 2026-06-24 | 首版发布，作为平台人物知识模型统一规范。 |
