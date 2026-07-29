# Data Standard Specification — HFB Data Admission

## Purpose

本文档定义 HFB 数据准入预检（admission check）的统计口径、阈值和模型要求。准入脚本 `scripts/data_admission_check.py` 根据本规范对目标数据库执行只读审计。

**关键约束**：准入脚本仅做统计和阈值判定，不导入、不 seed、不生成、不变更任何数据。实际数据导入操作在 3C 授权后单独执行。

## 3A 双阶段定义

本规范定义的准入检查 `data_admission_check.py` 在两个不同阶段运行，语义不同，不可互相替代：

### 3A-pre — 导入前只读基线/模型可表达性检查

- **运行时机**：3B 资料清单签署之前，作为准入流水线的第一道门禁。
- **检查内容**：目标数据库是否存在、Schema 是否支持所有必要的模型绑定（`SourceRef → Evidence → Citation` 链是否可表达）、是否存在 `BLOCKED_SCHEMA_GAP`。
- **阈值要求**：3A-pre **不要求**数据阈值 PASS。即使 `approved_classical_versions`、`approved_rag_documents` 等阈值为零，只要模型可表达、无 Schema Gap，3A-pre 即判定为可继续。
- **与 3C 的关系**：3A-pre 的 PASS 是进入 3B 的必要条件，但不是 3C 的充分条件。3A-pre 不检查数据质量、版权或授权状态。
- **退出码语义**：
  - `0` (PASS) 或 `1` (FAIL_THRESHOLD) → 模型可表达，可进入 3B。
  - `2` (BLOCKED_SCHEMA_GAP) → 模型不可表达，阻塞所有后续阶段。

### 3A-post — 导入后结果验收

- **运行时机**：3C 受控导入完成后，Codex 逐条真实链验收之前。
- **检查内容**：对目标数据库运行完整的 `data_admission_check.py`，所有阈值（§Thresholds）和 Evidence 链覆盖门槛（§Evidence 链覆盖门槛）必须同时满足。
- **阈值要求**：3A-post **必须**阈值 PASS。任一阈值不满足即 FAIL，停止后续放行。
- **退出码语义**：
  - `0` (PASS) → 阈值全部满足，可进入 Codex 逐条真实链验收。
  - `1` (FAIL_THRESHOLD) → 阈值不满足，阻塞后续放行。
  - `2` (BLOCKED_SCHEMA_GAP) → 模型缺口，阻塞后续放行。
- **不可替代**：3A-pre 的 PASS 不能替代 3A-post 的阈值验收；3A-post 的结果也不能回溯证明 3B 签署的有效性。

## Core Objects (可准入核心对象)

准入预检覆盖以下五类核心对象：

| 对象 | 对应表 | 准入条件 |
|---|---|---|
| ClassicalVersion | `classical_versions` | `review_status = 'approved'` 且 `source_url` 非空 |
| Document | `documents` | `review_status = 'approved'` 且 `source_url` 非空 且 `rag_enabled = true` |
| Passage (已验证) | `passages` | 必须存在 `Citation → Evidence → SourceRef` 绑定链，且 `Evidence.source_passage_id` 与该 Passage 一致、`Evidence.source_ref_id` 非空、`SourceRef.url` 非空 |
| Passage (可对齐) | `passages` | `content_text` 非空 |
| Person | `persons` | **仅统计数量**；当前模型无 `review_status` 及 Citation/Evidence 绑定，不计入任何审核/Citation/Evidence 要求 |

### 已知模型缺口：Person

`Person` 模型当前仅有 `biography_source` 字段，缺少：

- `review_status` — 无法按审核状态过滤
- 与 `Citation` / `Evidence` 的关联 — 无法建立 Person ← Evidence 的学术证据链

因此 Person 在本卡仅按总行数统计。若未来模型扩充上述字段，准入条件应同步更新。

## Thresholds (通过阈值)

所有阈值必须同时满足才判定 PASS：

| 阈值 | 要求 | 语义 |
|---|---|---|
| `approved_classical_versions` | >= 2 | 已审核古籍版本（`review_status=approved`，`source_url` 非空） |
| `chapters` OR `alignable_passages` | chapters >= 3 或 alignable_passages >= 100 | 有足够的章节结构或可对齐经文数据 |
| `persons` | >= 10 | 历史人物记录数（仅计数，无 Citation/Evidence 门槛） |
| `literature_or_collections` | >= 20 | 至少 20 条有来源链接的文献（`documents` 中 `source_url` 非空） |
| `approved_rag_documents` | >= 20 | 已审核且 RAG 启用的文献（`review_status=approved`, `source_url` 非空, `rag_enabled=true`） |

### Evidence 链覆盖门槛

| 路径 | 条件 | evidence_bound_passages 要求 |
|---|---|---|
| 章节路径 | `chapters >= 3` | >= 1 |
| 经文路径 | `alignable_passages >= 100` | >= 100 |

`evidence_bound_passages` 定义为同一 Passage 上真实存在 `Citation → Evidence → SourceRef` 绑定链，且 `Evidence.source_passage_id = Passage.id`、`Evidence.source_ref_id` 非空、`SourceRef.url` 非空。对应 SQL 见下方 Passage (已验证) 语义。

章节路径与经文路径同时满足时，优先采用章节路径（要求更低）。两条路径都不满足时，Evidence 链门槛无意义（chapters_or_alignable_passages 已失败）。

## SQL Semantics

### ClassicalVersion - 已审核版本

```sql
SELECT COUNT(*) FROM classical_versions
WHERE review_status = 'approved'
  AND source_url IS NOT NULL
  AND source_url != '';
```

ORM 语义：`ClassicalVersion.review_status == "approved"` 且 `ClassicalVersion.source_url` 非空非 ''。

### Document - 已审核 + RAG 启用文献

```sql
SELECT COUNT(*) FROM documents
WHERE review_status = 'approved'
  AND source_url IS NOT NULL AND source_url != ''
  AND rag_enabled = 1;
```

ORM 语义：`Document.review_status == "approved"` 且 `Document.source_url` 非空非 '' 且 `Document.rag_enabled == True`。SQLite 中布尔值存储为 0/1。

### Passage (已验证) - Evidence 链绑定

```sql
SELECT COUNT(DISTINCT p.id) FROM passages p
JOIN evidences e ON e.source_passage_id = p.id
JOIN source_refs sr ON sr.id = e.source_ref_id
JOIN citations c ON c.evidence_id = e.id
WHERE sr.url IS NOT NULL AND sr.url != '';
```

ORM 语义：

- `Passage.id == Evidence.source_passage_id`
- `Evidence.source_ref_id` 非空（指向 `SourceRef`）
- `SourceRef.url` 非空非 ''
- `Citation.evidence_id == Evidence.id`（Citation → Evidence 绑定存在）

### Person - 仅计数

```sql
SELECT COUNT(*) FROM persons;
```

ORM 语义：`Person` 表全行计数。不施加审核/Citation/Evidence 过滤。

## Exit Codes

| 退出码 | 判定 | 含义 |
|---|---|---|
| 0 | PASS | 以下**全部**条件满足：（1）`approved_classical_versions >= 2`，（2）`chapters >= 3` 或 `alignable_passages >= 100`，（3）`persons >= 10`，（4）`literature_or_collections >= 20`，（5）`approved_rag_documents >= 20`，（6）满足对应路径的 Evidence 链覆盖门槛（章节路径 >=1 或经文路径 >=100），且（7）无 `BLOCKED_SCHEMA_GAP` |
| 1 | FAIL_THRESHOLD | 无 schema gap，但上述任一条件不满足 |
| 2 | BLOCKED_SCHEMA_GAP | 当前模型无法表达某条所需绑定（如 Person 缺 `review_status`） |

## Output Schema

脚本向 stdout 输出稳定 JSON，包含以下必填键：

```json
{
  "verdict": "PASS | FAIL_THRESHOLD | BLOCKED_SCHEMA_GAP",
  "counts": { ... },
  "thresholds": { ... },
  "gaps": [ ... ],
  "failures": [ ... ],
  "evidence_bound": { ... },
  "checked_at": "ISO 8601"
}
```

## Version

- v1.1 — 2026-07-30 — 新增 3A-pre / 3A-post 双阶段定义，区分导入前基线检查与导入后阈值验收。
- v1.0 — 2026-07-29 — 初始准入规范。仅预检，不导入。
