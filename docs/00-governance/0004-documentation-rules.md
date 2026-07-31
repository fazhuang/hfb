---
title: Documentation Rules
document_id: HFB-GOV-0004
version: 1.0.0
status: Approved
owner: Documentation Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-24
scope: All Project Documentation
priority: P0
related_documents:
  - HFB-GOV-0002 Project Constitution
  - HFB-GOV-0003 Governance
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
  - HFB-DOC-INDEX Documentation Index
---

# Documentation Rules

## 项目文档强制规范

> 所有项目文档的强制规范。本文档是 Constitution 的可执行附件。
>
> 所有开发人员、AI Agent、文档工程师必须遵守本规范。

---

## 目录

- [1. YAML 元数据](#1-yaml-元数据)
- [2. 格式](#2-格式)
- [3. 编号](#3-编号)
- [4. 标题](#4-标题)
- [5. 版本](#5-版本)
- [6. 目录](#6-目录)
- [7. 引用](#7-引用)
- [8. 命名](#8-命名)
- [9. 语言](#9-语言)
- [10. 文档层级与最高依据](#10-文档层级与最高依据)

---

## 1. YAML 元数据

所有非 README 的 Markdown 文件必须以 YAML frontmatter 开头：

```yaml
---
title: <文档标题>
document_id: HFB-<DOMAIN>-<NNNN>
version: <MAJOR.MINOR.PATCH>
status: Draft | Review | Accepted | Implemented | Retired
owner: <角色/姓名>
reviewer: <角色/姓名>
effective_date: YYYY-MM-DD
scope: <适用范围>
priority: P0 | P1 | P2 | P3 | P4
related_documents:
  - <DOC_ID_1> <Document Title>
  - <DOC_ID_2> <Document Title>
tags:
  - <tag1>
  - <tag2>
---
```

**强制字段**：title、document_id、version、status、effective_date

**document_id 命名规则**：

| 前缀      | 域                      | 示例              |
| --------- | ----------------------- | ----------------- |
| HFB-GOV-  | Governance              | HFB-GOV-0001      |
| HFB-PS-   | Platform Specifications | HFB-PS-1709       |
| HFB-RF-   | Research Framework      | HFB-RF-1601       |
| HFB-ARC-  | Architecture            | HFB-ARC-0201      |
| HFB-DAT-  | Data                    | HFB-DAT-0301      |
| HFB-AI-   | AI                      | HFB-AI-0401       |
| HFB-DEV-  | Development             | HFB-DEV-0501      |
| HFB-UI-   | UI                      | HFB-UI-0601       |
| HFB-SEC-  | Security                | HFB-SEC-0701      |
| HFB-DOM-  | Domain                  | HFB-DOM-0801      |
| HFB-PRM-  | Prompt                  | HFB-PRM-0001      |
| HFB-DGM-  | Diagram                 | HFB-DGM-0001      |
| HFB-ADR-  | ADR                     | HFB-ADR-0001      |
| HFB-TPL-  | Template                | HFB-TPL-0001      |
| HFB-DOC-  | Meta Documentation      | HFB-DOC-INDEX     |
| HFB-ARCH- | Archived                | HFB-ARCH-GOV-0001 |

**README.md 豁免** — 目录索引文件（README.md）不强制要求 YAML header。

---

## 2. 格式

- **Markdown** — 所有文档使用 Markdown（`.md`），禁用 `.docx`、`.txt`、`.pdf` 源文件
- **UTF-8** — 编码统一 UTF-8，无 BOM
- **换行** — 正文不硬折行，每段一行；表格、列表可多行展开
- **缩进** — 纯空格，2 空格为一级，禁用 Tab

---

## 3. 编号

- **文件名编号** — 所有文件以 4 位数字编号开头：`0001-project-charter.md`
- **分段编号** — 章节日从 `1.` 开始，不使用 `0.` 前缀
- **同类递增** — 同级目录下编号连续递增，不跳号
- **废弃标注** — 不再使用的文件不删除，移至 `_archive/` 并在顶部标注归档信息

---

## 4. 标题

- **格式** — 标题下方一行 `---` 分割线
- **中文副标题** — 关键规范文档可在英文标题下方以 `## 中文标题` 补充
- **层级** — 最多 4 级标题（`#` ~ `####`），超过 4 级拆文档
- **禁用** — 禁止标题编号自动化（不用 `1.1.1` 式标题），用语义标题

---

## 5. 版本

- **语义版本** — `vMAJOR.MINOR.PATCH`
  - MAJOR — 结构重写或结论推翻
  - MINOR — 新增章节或重大内容补充
  - PATCH — 修正笔误、格式、小改动
- **初始版本** — 所有文档从 `v0.1.0` 起步；首次发布时升为 `v1.0.0`
- **版本日志** — 文档末尾 **Changelog** 章节，格式：

```markdown
## Changelog

| 版本   | 日期       | 变更 |
| ------ | ---------- | ---- |
| v0.1.0 | YYYY-MM-DD | 初稿 |
```

---

## 6. 目录

- **每个目录有 README.md** — 包含该目录下所有文件的索引表
- **每个文档有目录（TOC）** — 紧随 YAML header 之后，用 Markdown 列表列出所有 `##` 标题：

```markdown
## 目录

- [1. 章节一](#1-章节一)
- [2. 章节二](#2-章节二)
  - [2.1 子节](#21-子节)
```

- **超过 6 个标题** 的文档必须有 TOC；少于此数可选

---

## 7. 引用

- **绝对路径** — 项目内引用一律使用仓库根相对路径或当前文件相对路径
- **推荐 document_id 引用** — 跨域引用时使用 `[HFB-PS-1709](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md)` 格式
- **锚点** — 跨文件锚点引用格式：`[概览](../02-architecture/overview.md#4-部署拓扑)`
- **禁止** — 禁止使用 `(参见上文)`、`(见下节)` 等模糊引用；禁止使用裸 URL 引用内部文档
- **外部链接** — 外部 URL 用完整链接，末尾标注访问日期：`[React 文档](https://react.dev)（访问于 2026-06-24）`

---

## 8. 命名

- **文件命名** — `NNNN-slug.md`
  - `NNNN` — 4 位数字，全局唯一编号
  - `slug` — 小写、英文、连字符分隔
  - 示例：`0001-project-charter.md`、`1709_MVP_Implementation_Specification.md`
- **目录命名** — `NN-domain/`（如 `00-governance/`、`17-Platform-Specifications/`）

---

## 9. 语言

- **主体语言** — 中文
- **技术术语** — 保留英文原文，首次出现加中文注释：`Container（容器）`
- **代码/命令/配置** — 保持原样，不翻译
- **专有名词** — 统一大小写：`React`、`TypeScript`、`PostgreSQL`、`GitHub`

---

## 10. 文档层级与最高依据

本项目文档按以下层级组织，编号靠前者优先级更高：

| 层级        | 目录                                                          | 作用                                     |
| ----------- | ------------------------------------------------------------- | ---------------------------------------- |
| **Level 0** | `00-governance/`                                              | 项目治理 — 章程、宪章、治理制度、AI 协议 |
| **Level 1** | `17-Platform-Specifications/`                                 | 产品规格 — 产品实现最高依据              |
| **Level 2** | `16-research-framework/`                                      | 研究框架 — 学术方向最高依据              |
| **Level 3** | `02-architecture/`                                            | 技术架构                                 |
| **Level 4** | `03-data/` `04-ai/` `05-development/` `06-ui/` `07-security/` | 领域规范                                 |
| **Level 5** | `08-domain/` `11-adr/`                                        | 领域模型与决策记录                       |
| **Level 6** | `09-prompts/` `10-diagrams/` `12-context/`                    | 执行工具与上下文                         |
| **Level 7** | `templates/` `_archive/`                                      | 模板与存档                               |

### 冲突裁决

- Level 0 > Level 1 > ... > Level 7
- `17-Platform-Specifications/` 为产品实现最高依据 — 任何产品功能冲突以此为准
- `16-research-framework/` 为学术方向最高依据 — 任何研究方向冲突以此为准
- `00-governance/00` (Constitution) 为全项目最高治理文件

---

## Changelog

| 版本   | 日期       | 变更                                                                                                       |
| ------ | ---------- | ---------------------------------------------------------------------------------------------------------- |
| v1.0.0 | 2026-06-25 | 正式发布 — 新增YAML元数据规范(§1)、文档层级与最高依据(§10)；补充document_id命名规则；明确17/16系列的优先级 |
| v0.1.0 | 2026-06-24 | 初稿                                                                                                       |
