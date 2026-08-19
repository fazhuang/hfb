---
title: Research Lead Appointment Resolution Template
document_id: HFB-GOV-0006
version: 0.1.0
status: Template
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-08-18
scope: Research Lead 任命决议模板
priority: P0
related_documents:
  - HFB-DAT-0306 Manual Research Source Admission Checklist
  - HFB-DAT-0307 Production Corpus Unblock Runbook
  - HFB-DAT-0308 Research Lead Source Filling Guide
tags:
  - governance
  - resolution-template
  - research-lead
---

# Research Lead 任命决议（模板）

---

> **使用说明**：本文件是 Project Steering Committee 任命 Research Lead 的**决议模板**。方括号 `[ ]` 内为待填内容。填写完成、全体相关方签署后，本决议即生效，并作为 [0306 准入清单](0306_Manual_Research_Source_Admission_Checklist.md) 解除 `BLOCKED_REAL_SOURCE_AUTHORITY` 状态的组织依据。

---

## 决议编号

`HFB-RES-[YYYY]-[NNN]`

## 决议日期

`[YYYY-MM-DD]`

## 决议主体

Project Steering Committee（项目指导委员会）

---

## 一、背景

1. 项目数据准入流水线（见 [HFB-DAT-0306](0306_Manual_Research_Source_Admission_Checklist.md) §6.0）当前处于 **3B 阻塞**状态：`SOURCE_ADMISSION_OPEN=False`，古籍全文上传冻结。
2. 阻塞根因是 **Research Lead 职位空缺**，导致准入清单 §3 全部 13 行空白、§4 零签署。
3. 技术侧已 100% 就绪（见 [HFB-DAT-0307](0307_Production_Corpus_Unblock_Runbook.md) §2），解冻仅需治理动作。

## 二、决议

Project Steering Committee 现决议：

**任命 `[姓名]` 为本项目 Research Lead（研究负责人），自 `[生效日期 YYYY-MM-DD]` 起履职。**

## 三、职责范围

Research Lead 的职责包括但不限于：

1. **来源准入**：逐条填写并签署 [0306 准入清单](0306_Manual_Research_Source_Admission_Checklist.md) §3（古籍版本 5 行、研究文献 5 行、馆藏资料 3 行）与 §4。
2. **来源核实**：对每项来源的真实性、可追溯性、授权合法性承担审核责任。
3. **风险记录**：如实填写 §5 风险汇总。
4. **填写规范**：遵循 [0308 填写指引](0308_Research_Lead_Source_Filling_Guide.md) 的逐字段要求，严禁使用模拟/测试/示例数据或 AI 代填。

## 四、授权边界（重要）

Research Lead 的职权受以下约束：

1. **不自行放行 3C**：完成 0306 §3/§4 后，3C 仍须经独立 Codex 绑定计划验收 PASS + Steering Committee 书面放行（见 0306 §6.3）。
2. **不绕过硬停止条款**：在 0306 §6.1 全部条件满足前，禁止设计或执行任何数据导入操作。
3. **不授权未登记来源**：仅可登记本人持有真实授权依据的来源；不得以 Research Lead 身份为他人代填未经核实的来源。

## 五、生效条件

本决议自以下全部签署完成之日起生效：

1. Project Steering Committee 授权代表签署。
2. 被任命人签署接受声明。

## 六、签署

| 角色 | 姓名 | 签署日期 | 备注 |
| ---- | ---- | -------- | ---- |
| Steering Committee 授权代表 | | | |
| 被任命人（Research Lead） | | | 接受任命 |

---

## 被任命人接受声明（抄录于签署时）

> 本人 `[姓名]` 接受 Research Lead 任命，知悉并同意履行本决议第三条所列职责，遵守第四条授权边界，并对准入清单中所填来源的真实性、可追溯性与授权合法性承担审核责任。

---

## Changelog

| 版本 | 日期 | 变更 |
| ------ | ---- | ---- |
| v0.1.0 | 2026-08-18 | 初稿 — 任命决议模板（背景、决议、职责、授权边界、生效条件、签署） |
