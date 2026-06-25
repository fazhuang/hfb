---
title: Data Standard Specification
document_id: HFB-DAT-0301
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Entire Project
priority: P0
related_documents:
  - HFB-GOV-0002 Project Constitution
  - HFB-GOV-0005 AI Execution Protocol
  - HFB-ARC-0201 Technical Blueprint
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
  - HFB-DAT-0302 Ontology Specification
---

# Data Standard Specification
## 数据标准规范

> 本文档定义本项目所有数据资源的统一标准，是数据库设计、知识组织、AI 检索和数字人文研究的唯一数据依据。
>
> 所有数据模型、数据库表、知识图谱、本体模型、API 及 AI 检索必须遵守本规范。

---

# 第一章 编制目的

建立统一的数据治理体系，实现：

- 数据标准统一；
- 数据来源可追溯；
- 数据版本可管理；
- 数据关系可扩展；
- AI 可理解；
- 学术可引用。

---

# 第二章 数据治理原则

所有数据必须遵循以下六项原则：

## 2.1 唯一性（Uniqueness）

每个实体必须拥有唯一标识（UUID）。

不得出现：

- 重复实体；
- 重复版本；
- 重复文献记录。

---

## 2.2 可追溯（Traceability）

任何数据必须记录：

- 来源
- 创建者
- 创建时间
- 修改时间
- 修改原因
- 数据版本

不得存在来源未知的数据。

---

## 2.3 可版本化（Versioning）

所有重要对象必须支持版本管理。

例如：

- 古籍版本
- OCR 修订版本
- AI 标注版本
- 学者校勘版本

---

## 2.4 可引用（Citation）

所有数据必须能够生成标准引用。

例如：

- 古籍引用
- 图片引用
- 学术论文引用
- AI 输出引用

---

## 2.5 可扩展（Extensible）

新增字段不得影响已有数据。

采用：

向前兼容（Forward Compatible）。

---

## 2.6 AI 可读（AI Readable）

所有数据必须：

- 结构化；
- 可序列化；
- 支持 JSON；
- 支持向量化；
- 支持知识图谱。

---

# 第三章 数据域划分

平台数据划分为九个领域。

| 数据域 | 说明 |
|---------|------|
| Person | 人物 |
| Book | 古籍 |
| Version | 文献版本 |
| Chapter | 篇章 |
| Passage | 段落 |
| Paper | 学术论文 |
| Image | 图片资源 |
| Document | 综合文献 |
| User | 用户（权限模块） |

所有新增数据必须归属某一数据域。

---

# 第四章 核心实体标准

## Person

代表人物。

例如：

- 皇甫谧
- 历代注释者
- 现代研究学者

必须字段：

- id
- name
- aliases
- birth
- death
- dynasty
- biography
- source_id

---

## Book

代表古籍。

例如：

- 《针灸甲乙经》
- 《三都赋》

必须字段：

- id
- title
- author
- dynasty
- category
- description

---

## Version

用于描述不同版本。

例如：

- 宋刻本
- 明刻本
- 清刻本
- 点校本
- 数字校勘版

必须支持：

版本之间关联。

---

## Chapter

对应古籍章节。

必须保持：

树状结构。

---

## Passage

最小研究单元。

AI 检索默认以 Passage 为粒度。

不得直接以整本书作为最小检索单位。

---

## Paper

代表现代研究成果。

包括：

- 论文
- 学位论文
- 研究报告
- 专著章节

---

## Image

代表图片资源。

包括：

- 古籍影印
- 人物照片
- 碑刻
- 地图
- 插图

必须记录版权信息。

---

## Document

统一资源抽象。

允许：

Book

Paper

Image

OCR

PDF

全部纳入统一资源管理。

---

# 第五章 元数据规范

所有资源必须拥有：

- UUID
- 标题
- 作者
- 来源
- 创建时间
- 更新时间
- 版本号
- 语言
- 地区
- 标签
- 关键词
- 权限级别

不得缺失。

---

# 第六章 命名规范

统一：

英文命名。

数据库：

snake_case

API：

kebab-case

JSON：

camelCase

Markdown：

Title_Case.md

---

# 第七章 数据关系规范

允许关系：

- Author Of
- Version Of
- Citation
- Annotation
- Translation
- Commentary
- Inheritance
- Reference
- Belongs To

禁止建立未定义关系。

新增关系必须更新《Ontology Specification》。

---

# 第八章 数据生命周期

所有数据必须经历：

采集

↓

校验

↓

标准化

↓

入库

↓

审核

↓

发布

↓

更新

↓

归档

↓

长期保存

任何阶段均需记录日志。

---

# 第九章 数据质量标准

数据质量要求：

完整性 ≥ 95%

准确性 ≥ 99%

一致性 ≥ 98%

引用完整率 = 100%

来源记录率 = 100%

---

# 第十章 数据安全

所有数据必须支持：

- 权限控制
- 操作日志
- 数据备份
- 历史版本恢复
- 审计记录

---

# 第十一章 AI 数据规范

AI 只能读取：

已审核数据。

AI 输出：

不得写回原始数据。

AI 标注：

必须保存为独立版本。

人工审核通过后方可成为正式数据。

---

# 第十二章 数据标准变更

新增：

实体

字段

关系

元数据

命名规范

均必须：

1. 更新本规范；
2. 更新 Ontology；
3. 更新数据库迁移；
4. 更新 API 文档；
5. 更新 AI 检索配置。

未经批准不得实施。

---

# 第十三章 MVP 约束

本文档明确：**MVP 阶段数据范围以 [HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) 为边界。**

## 13.1 MVP 数据域

MVP 阶段仅建设以下数据域：

- Person、Book、Version、Chapter、Passage、Paper、Image、Document、User

## 13.2 禁止进入 MVP 的实体

- Herb、Prescription、Disease、Symptom、Meridian、Formula、Acupoint
- Animal、Plant、Medicine

以上实体仅在未来扩展阶段讨论。

## 13.3 数据上线标准

所有进入生产环境的数据必须满足 [HFB-PS-1710 Production Readiness](../17-Platform-Specifications/1710_Production_Readiness_Specification.md) 第四章数据要求：

- 来源明确
- 版本清晰
- Citation 完整
- Evidence 完整
- 审核完成

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 新增第十三章(MVP约束)；更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布。作为项目唯一数据标准规范。 |