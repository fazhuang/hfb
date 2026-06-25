---
title: Metadata Standard
document_id: HFB-DAT-0303
version: 1.1.0
status: Approved
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: Entire Data Layer
priority: P0
related_documents:
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-ARC-0201 Technical Blueprint
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
---

# Metadata Standard
## 元数据标准规范

> 元数据（Metadata）是本平台最重要的数据资产之一。
>
> 平台中任何资源（人物、古籍、版本、章节、论文、图片、视频、OCR、AI 标注等）都必须拥有完整元数据。
>
> **没有元数据的数据，不允许进入正式资源库。**

---

# 第一章 制定目的

建立统一元数据体系，实现：

- 数据来源可追溯
- 学术引用可验证
- AI 检索可理解
- 多版本资源统一管理
- 长期数字保存
- 知识关联自动建立

---

# 第二章 元数据分类

平台元数据划分为八类：

| 类别 | 说明 |
|------|------|
| Core Metadata | 核心元数据 |
| Bibliographic Metadata | 文献元数据 |
| Provenance Metadata | 来源元数据 |
| Version Metadata | 版本元数据 |
| Rights Metadata | 权限元数据 |
| AI Metadata | AI处理元数据 |
| Relationship Metadata | 关系元数据 |
| Preservation Metadata | 长期保存元数据 |

---

# 第三章 核心元数据（Core Metadata）

所有资源必须包含以下字段：

| 字段 | 必填 | 说明 |
|------|------|------|
| id | √ | UUID |
| resource_type | √ | 资源类型 |
| title | √ | 标题 |
| language | √ | 语言 |
| abstract | √ | 摘要 |
| keywords | √ | 关键词 |
| description | √ | 描述 |
| status | √ | 生命周期状态 |

---

# 第四章 文献元数据（Bibliographic Metadata）

适用于：

- 古籍
- 论文
- 专著
- 图片
- PDF

字段：

| 字段 | 说明 |
|------|------|
| author | 作者 |
| editor | 编者 |
| translator | 译者 |
| publisher | 出版者 |
| publication_year | 出版时间 |
| edition | 版次 |
| isbn | ISBN |
| issn | ISSN |
| doi | DOI |
| citation | 标准引用 |

---

# 第五章 来源元数据（Provenance Metadata）

所有资源必须记录：

- 数据来源
- 采集方式
- 上传人员
- 上传时间
- 数据责任人
- 来源可信度
- 原始文件位置

禁止存在来源未知资源。

---

# 第六章 版本元数据（Version Metadata）

支持：

- 原始版
- OCR版
- 校勘版
- 标点版
- AI标注版
- 专家审核版
- 发布版

字段：

| 字段 | 说明 |
|------|------|
| version_no | 版本号 |
| parent_version | 父版本 |
| version_type | 类型 |
| created_by | 创建者 |
| created_at | 创建时间 |
| change_log | 修改说明 |

---

# 第七章 权限元数据（Rights Metadata）

记录：

- 版权所有者
- 授权方式
- 使用范围
- 是否公开
- 是否允许 AI 训练
- 下载权限
- 引用要求

---

# 第八章 AI 元数据（AI Metadata）

所有 AI 处理结果必须保存：

| 字段 | 说明 |
|------|------|
| ai_model | 模型名称 |
| ai_version | 模型版本 |
| prompt_version | Prompt版本 |
| processing_time | 处理时间 |
| confidence | 置信度 |
| reviewer | 审核人 |
| review_status | 审核状态 |

AI 输出不得覆盖原始数据。

---

# 第九章 关系元数据（Relationship Metadata）

用于建立知识关联。

记录：

- relation_type
- source_entity
- target_entity
- evidence
- confidence
- reviewer
- created_at

所有关系必须绑定证据。

---

# 第十章 保存元数据（Preservation Metadata）

记录：

- 文件格式
- 编码方式
- 文件大小
- Hash（SHA256）
- 存储位置
- 备份状态
- 校验状态

用于长期数字保存。

---

# 第十一章 生命周期

所有资源必须经过：

创建

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

任何状态变化均必须记录。

---

# 第十二章 元数据质量标准

要求：

| 指标 | 标准 |
|------|------|
| 完整率 | ≥98% |
| 来源记录率 | 100% |
| 引用完整率 | 100% |
| UUID覆盖率 | 100% |
| AI处理记录率 | 100% |

---

# 第十三章 元数据交换

统一支持：

- JSON
- JSON-LD（后续）
- CSV（导入导出）
- XML（兼容）
- RDF（知识图谱阶段）

---

# 第十四章 与系统映射关系

```
Metadata
      │
      ▼
Database
      │
      ▼
API
      │
      ▼
Search
      │
      ▼
RAG
      │
      ▼
GraphRAG
      │
      ▼
Visualization
```

任何模块不得绕过 Metadata。

---

# 第十五章 修订规则

新增任何元数据字段必须：

1. 更新 Metadata Standard；
2. 更新 Data Standard；
3. 更新 Ontology；
4. 更新数据库迁移；
5. 更新 API；
6. 更新 Context Package。

未经批准不得新增。

---

# 第十六章 MVP 与上线约束

## 16.1 MVP 元数据范围

MVP 阶段元数据范围以 [HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) 第五章数据范围为边界。

## 16.2 元数据上线标准

所有资源元数据必须满足 [HFB-PS-1710](../17-Platform-Specifications/1710_Production_Readiness_Specification.md) 第四章数据要求方可上线：

- 来源明确
- 版本清晰
- Citation 完整
- Evidence 完整
- 审核完成

---

# 修订记录

| Version | Date | Description |
|----------|------|-------------|
| 1.1.0 | 2026-06-25 | 新增第十六章(MVP与上线约束)；更新related_documents |
| 1.0.0 | 2026-06-24 | 首版发布，作为平台统一元数据规范。 |