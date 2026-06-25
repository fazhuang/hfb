---
title: "Knowledge Package Index"
version: "1.1"
status: "Active"
owner: "Domain Expert + AI Lead"
last_updated: "2026-06-25"
domain: "knowledge"
related:
  - "docs/03-data/0302_Ontology_Specification.md"
  - "docs/08-domain/0809_Master_Knowledge_Graph_Model.md"
  - "docs/17-Platform-Specifications/1709_MVP_Implementation_Specification.md"
---

# 14 Knowledge — 领域知识包

皇甫谧数字人文平台的结构化领域知识。供 AI 模型理解人文领域概念。

---

> 层级：**Level 6 — 执行工具与上下文**
>
> **版本:** 1.1
> **状态:** Active
> **适用范围:** AI · 领域专家 · 数据团队
> **维护者:** Domain Expert + AI Lead

## 知识域

| 域 | 路径 | 说明 | 状态 |
|---|---|---|---|
| Person | [person/](person/) | 人物知识库 | Active |
| Book | [book/](book/) | 古籍知识库 | Active |
| Paper | [paper/](paper/) | 论文知识库 | Active |
| Image | [image/](image/) | 图像知识规范 | Active |
| OCR | [ocr/](ocr/) | OCR 处理规范 | Active |
| Metadata | [metadata/](metadata/) | 元数据标准 | Active |
| Ontology | [ontology/](ontology/) | 领域本体 | Active |

## AI 使用

AI 读取 Knowledge Package 的顺序：

```
1. ontology/ → 理解实体和关系
2. person/ → 理解人物知识
3. book/ → 理解古籍知识
4. paper/ → 理解论文知识
5. metadata/ → 理解数据标注规范
6. image/ → 理解图像处理规范
7. ocr/ → 理解文字识别规范
```

## 关联目录

| 目录 | 关系 | 说明 |
|---|---|---|
| [docs/03-data/](../03-data/) | 数据规范基础 | 知识建模遵循 Ontology、Entity、Relation |
| [docs/08-domain/](../08-domain/) | 领域知识模型 | Person/Book/Version 等知识模型 |
| [docs/17-Platform-Specifications/](../17-Platform-Specifications/) | MVP 数据边界 | 知识包以 HFB-PS-1709 数据范围为边界 |

---

> **创建日期:** 2026-06-24
> **最后更新:** 2026-06-25
