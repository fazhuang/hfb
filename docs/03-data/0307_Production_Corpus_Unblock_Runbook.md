---
title: Production Corpus Unblock Runbook
document_id: HFB-DAT-0307
version: 0.1.0
status: READY_FOR_RESEARCH_LEAD
owner: Technical Lead
reviewer: Project Steering Committee
effective_date: 2026-08-18
scope: 生产语料解冻作战手册 — 治理动作 + 技术动作 + 验收标准
priority: P0
related_documents:
  - HFB-DAT-0306 Manual Research Source Admission Checklist
  - HFB-DAT-0301 Data Standard Specification
  - HFB-GOV-0002 Project Constitution
tags:
  - phase-3b
  - phase-3c
  - unblock-runbook
  - source-admission
---

# 生产语料解冻作战手册

---

> **状态:** READY_FOR_RESEARCH_LEAD — 技术侧已 100% 就绪；唯一阻塞是 Research Lead 空缺
> **版本:** v0.1.0
> **日期:** 2026-08-18
> **负责人:** Technical Lead
> **审核人:** Project Steering Committee
>
> 本文档是解冻作战手册，**不是准入清单本身**。准入清单在 [HFB-DAT-0306](0306_Manual_Research_Source_Admission_Checklist.md)，由 Research Lead 亲自填写。本手册不含、且不得补造任何示例来源、签署信息或导入脚本。

---

## 1. 一句话结论

**生产语料解冻被治理阻塞，不是技术阻塞。** 上传表单、后端摄入、门控开关、完整测试覆盖全部就绪。唯一缺失的是：一名到岗的 Research Lead 完成 [0306 准入清单](0306_Manual_Research_Source_Admission_Checklist.md) §3 的 13 行真实来源填写与 §4 签署。

解冻的唯一路径（不可跳步）：

```
任命 Research Lead → 填写 0306 §3 + §4 → Codex 验收绑定计划 → Steering 书面放行
   → 置 SOURCE_ADMISSION_OPEN=true → 3C 受控导入 → 3A-post → Codex 逐条真实链验收
```

---

## 2. 技术侧就绪清单（已完成，无需额外工程）

| 组件 | 位置 | 状态 |
| ----- | ---- | ---- |
| 上传端点 | `POST /api/v1/documents/upload` | ✅ 已实现 |
| fail-closed 门控 | `app/services/source_admission.py` + `app/core/config.py:94` | ✅ `SOURCE_ADMISSION_OPEN=False` 默认拒绝 |
| 前端上传表单 | `apps/frontend/src/components/library/ClassicalUploadForm.vue` | ✅ 真实表单，门控关闭时展示 409 |
| 摄入管线 | `IngestionService.ingest_pdf_with_pages` | ✅ PDF → 逐页 chunk + `page_image_hash` |
| 测试覆盖 | `tests/unit/test_v1_entities_api.py` | ✅ 门控关闭 409 / 打开 201 / 403 / 422 全分支 |

**解冻后唯一的技术动作**：在部署环境设置 `SOURCE_ADMISSION_OPEN=true` 并重启后端。前端无需改动。

---

## 3. 治理动作清单（按顺序，逐条勾选）

### 3.1 任命 Research Lead

- [ ] 由 Project Steering Committee 正式任命一名 Research Lead。
- [ ] 该人选须持有（或能合法取得）拟导入古籍版本、研究文献、馆藏资料的真实来源与授权。
- [ ] Research Lead 的真实姓名填入 [0306](0306_Manual_Research_Source_Admission_Checklist.md) 文档头部的 `owner` 字段，并将 `status` 从 `BLOCKED_REAL_SOURCE_AUTHORITY` 更新。

**硬性禁止**：不得以 AI、模拟数据、测试数据、示例数据代填或代签。

### 3.2 Research Lead 填写 §3（13 行）

Research Lead 逐行填写 [0306](0306_Manual_Research_Source_Admission_Checklist.md) §3 的三张表：

| 表 | 行 | 类型 |
| --- | --- | --- |
| §3.1 | CV-01 ~ CV-05 | 古籍版本 |
| §3.2 | DOC-01 ~ DOC-05 | 研究文献 |
| §3.3 | HOLD-01 ~ HOLD-03 | 馆藏资料 |

每行 9 列，其中 7 列由 Research Lead 填写（审核人/日期为签署）：

| 字段 | 要求 |
| ----- | ---- |
| 来源 URI / 馆藏标识 | 可解析 URL 或馆藏索书号（禁止留空） |
| 版权/授权依据 | 具体条款（公有领域 / CC 4.0 / 机构授权编号），禁止"待确认" |
| 版本标识 | 古籍：刊刻年代、藏板、序跋、行款；文献：出版社、版次、ISBN |
| 导入范围 | 精确到卷/篇/条，禁止"全库导入" |
| SourceRef→Evidence→Citation 绑定计划 | 逐条规划三层绑定，禁止填写尚未创建的数据库 ID |
| 风险说明 | 如实记录（避讳改字、版本异文、版权边界等），无风险须注明核查依据 |

### 3.3 Research Lead + 技术负责人签署 §4

- [ ] Research Lead 在 §4 签署（姓名 + ISO 8601 日期）。
- [ ] 技术负责人确认技术可行性并签署。

### 3.4 Codex 绑定计划验收

- [ ] 由非 Research Lead 的独立 Codex 流程，逐条核查 §3 绑定计划的一致性。
- [ ] 验收对象是「绑定计划」（外部来源标识、拟绑定范围、预期 Passage 定位规则、预期绑定数量），不是虚构数据或运行时链。

### 3.5 Steering Committee 书面放行

- [ ] 基于 Codex 验收报告，做出明确书面放行决定。

---

## 4. 放行后的技术动作（仅在前述全部完成后执行）

> ⚠️ 以下动作在 [0306](0306_Manual_Research_Source_Admission_Checklist.md) §6.1 全部条件满足 + Codex 验收 PASS + Steering 书面放行**之后**方可执行。在此之前属于 §6.2 冻结禁令范围。

1. 部署环境设置 `SOURCE_ADMISSION_OPEN=true`，重启后端。
2. 由技术负责人按已审核清单执行 3C 受控导入（严格限定清单范围）。
3. 运行 `scripts/data_admission_check.py` 做 3A-post 阈值验收。
4. Codex 以实际数据库记录逐条核实 `SourceRef.url → Evidence.source_ref_id → Evidence.source_passage_id → Citation.evidence_id` 同链绑定。

---

## 5. 现状与下一步

| 阶段 | 状态 | 阻塞点 |
| ----- | ---- | ------ |
| 3A-pre | ✅ PASS（PostgreSQL hfb） | — |
| 3B 填写+签署 | 🔒 BLOCKED | Research Lead 空缺 |
| Codex 验收 | ⏳ 未开始 | 依赖 3B |
| Steering 放行 | ⏳ 未开始 | 依赖 Codex |
| 3C 导入 | 🔒 FROZEN | 依赖放行 |
| 3A-post / Codex 链验收 | ⏳ 未开始 | 依赖 3C |

**唯一可推进的动作**：任命 Research Lead。其余环节在其到岗后按 §3 顺序执行。

---

## Changelog

| 版本 | 日期 | 变更 |
| ------ | ---- | ---- |
| v0.1.0 | 2026-08-18 | 初稿 — 固化技术就绪清单、治理动作清单、放行后技术动作；不含示例数据、不代填、不设计导入脚本（遵守 0306 §6.2 冻结禁令） |
