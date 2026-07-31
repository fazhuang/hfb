# Templates

Claude 直接复制使用。新建文档时，复制对应模板 → 填入内容 → 编号 → 保存到目标目录。

---

> **状态:** Draft
> **版本:** v0.1.0
> **日期:** 2026-06-24
> **作者:** —
> **负责人:** —

## 目录

- [1. 核心流程模板](#1-核心流程模板)
- [2. 技术模板](#2-技术模板)
- [3. 管理模板](#3-管理模板)
- [4. 质量模板](#4-质量模板)

## 1. 核心流程模板

| #    | 模板                      | 用途               | 保存到                                         |
| ---- | ------------------------- | ------------------ | ---------------------------------------------- |
| 0001 | [Sprint](sprint-note.md)  | Sprint 计划 / 结果 | `08-sprints/sprint-notes/`                     |
| 0002 | [Retro](retrospective.md) | Sprint 回顾        | `08-sprints/retrospectives/`                   |
| 0003 | [ADR](adr.md)             | 架构决策记录       | `00-governance/adr/` 或 `02-architecture/adr/` |
| 0004 | [RFC](rfc.md)             | 变更请求           | `02-architecture/rfc/`                         |

## 2. 技术模板

| #    | 模板                           | 用途         | 保存到                |
| ---- | ------------------------------ | ------------ | --------------------- |
| 0005 | [API](api.md)                  | API 端点文档 | `05-development/api/` |
| 0006 | [ER](er.md)                    | 实体关系文档 | `03-data/er/`         |
| 0007 | [Component](component-spec.md) | UI 组件规格  | `06-ui/components/`   |

## 3. 管理模板

| #    | 模板                                           | 用途        | 保存到                       |
| ---- | ---------------------------------------------- | ----------- | ---------------------------- |
| 0008 | [Feature Brief](feature-brief.md)              | 功能简介    | `01-product/feature-briefs/` |
| 0009 | [Model Card](model-card.md)                    | AI 模型文档 | `04-ai/model-cards/`         |
| 0010 | [Incident Post-Mortem](incident-postmortem.md) | 事故回顾    | `07-security/incidents/`     |

## 4. 质量模板

| #    | 模板                      | 用途           | 保存到               |
| ---- | ------------------------- | -------------- | -------------------- |
| 0011 | [Review](review.md)       | 结构化审查报告 | 按需，附在审查对象旁 |
| 0012 | [Checklist](checklist.md) | 可勾选检查清单 | 按需，附在流程文档旁 |

## 用法

```
cp docs/templates/sprint-note.md docs/08-sprints/sprint-notes/0001-sprint-1.md
# 编辑 0001-sprint-1.md → 填入内容 → 改状态 → 保存
```

## Changelog

| 版本   | 日期       | 变更                                 |
| ------ | ---------- | ------------------------------------ |
| v0.1.0 | 2026-06-24 | 统一 12 份模板，四分类，全部格式对齐 |
