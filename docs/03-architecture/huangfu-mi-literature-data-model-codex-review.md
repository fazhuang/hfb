# Codex Re-Review: 皇甫谧专题文献库数据模型设计再次验收

**被审计文件:** `docs/03-data/huangfu-mi-literature-data-model.md`  
**审计日期:** 2026-07-10  
**审计对象:** Claude 修订后的数据模型设计草案 v1.1  

## 结论

**PASS**

上一轮阻塞项已被设计层面修复：未知/受限版权全文入库路径被数据库约束、服务约束和上传 schema 同时封住；古籍版本设计已并回现有 `Version` 主轴；`EvidenceCitation` 已通过 `evidence_id`、`passage_id`、`version_id` 与现有证据链和版本/段落模型建立强桥接；采集审计已补齐 `IngestionItem` 明细表。

## 复验结果

| 验收项 | 结论 | 证据 |
|---|---:|---|
| 是否支持元数据与全文分离 | PASS | `LiteratureRecord` 保持 metadata-only 入口，不包含全文或文件字段；`FullTextDocument` 独立保存 `file_path`、`text_content`、`text_hash`、OCR 状态和访问字段。 |
| 是否支持版权状态标记 | PASS | `LiteratureRecord.copyright_status`、`FullTextDocument.copyright_status`、`license_type`、`authorization_basis`、`access_level`、`VersionBibliography.copyright_decision*` 和 `SourcePlatform.is_allowed_for_fulltext` 均已明确。 |
| 是否支持古籍版本管理 | PASS | 原 `ClassicalTextVersion` 已改为 `VersionBibliography`，并明确“不是独立版本主表”；`version_id` 为 `NOT NULL + UNIQUE`，强制 1:1 依附现有 `Version`。版本谱系继续使用 `VersionRelation`，段落对照继续使用 `PassageMapping`。 |
| 是否支持引文证据追溯 | PASS | `EvidenceCitation` 增加 `evidence_id -> evidences.id` UNIQUE FK，且增加 `passage_id -> passages.id`、`version_id -> versions.id`。状态流限定为 `extracted → draft → reviewed → promoted_to_evidence / rejected`，reviewed 前不得进入 RAG / Graph / AcademicRelation / Citation 证据链。 |
| 是否支持采集任务审计 | PASS | `IngestionJob` 作为批次级记录，新增 `IngestionItem` 做 item-level 审计，覆盖 `target_url`、`target_identifier`、`harvest_type`、`status`、`result_entity_type/id`、`skipped_reason`、`error_detail`、`copyright_decision`、`copyright_decision_basis`、`reviewed_by/at`。 |
| 是否避免把不明版权全文直接入库 | PASS | `FullTextDocument` 增加 `ck_full_text_documents_text_content_copyright_gate` 和 `ck_full_text_documents_file_path_copyright_gate`：`text_content` / `file_path` 非空时必须 `copyright_status IN ('public_domain','licensed')` 且 `authorization_basis IS NOT NULL`。上传 schema 要求 `copyright_status` 必须为 `public_domain` 或 `licensed`，未知版权走 metadata-only。 |
| 是否符合当前项目已有架构 | PASS | 设计继续使用现有 `BaseModel`、SQLAlchemy 2.0、Repository/Service/API 分层、RBAC、MinIO、`api_response()`，并保留 `Version` / `Evidence` / `Citation` / `Passage` 为主干模型。 |

## 已关闭阻塞项

### P0-1 未知版权全文入库

已关闭。修订稿在 `FullTextDocument.__table_args__` 中加入：

- `ck_full_text_documents_text_content_copyright_gate`
- `ck_full_text_documents_file_path_copyright_gate`
- `ck_full_text_documents_exactly_one_source`

同时在 API 上传伪代码和 `FullTextUploadRequest` 中要求全文上传必须满足 `copyright_status in ('public_domain', 'licensed')`、`authorization_basis` 非空、来源平台允许全文采集。`access_level` 被明确声明为访问控制，不是入库许可。

### P0-2 平行版本主表

已关闭。`ClassicalTextVersion` 不再作为独立版本主表出现；替换为 `VersionBibliography`，并通过 `version_id` 强制依附现有 `Version`。文档明确禁止第二套版本谱系和第二套古籍版本主路径。

### P0-3 引文证据弱桥接

已关闭。`EvidenceCitation` 已增加 `evidence_id` 外键，并定义 promotion 流程：审核通过后创建现有 `Evidence`，再回写 `EvidenceCitation.evidence_id`，之后才进入 RAG / Graph / AcademicRelation / Citation 证据链。

### P1-1 采集审计粒度不足

已关闭。新增 `IngestionItem`，并明确 `metadata_harvest` 成功不自动触发 `fulltext_download`；全文下载必须单独检查来源平台全文许可、版权状态和授权依据。

## 残余风险

1. 这是设计文档验收 PASS，不等于实现验收 PASS。后续实现时必须把 CHECK 约束、服务层校验、schema 校验和单元测试全部落地。
2. `authorization_basis IS NOT NULL` 不能防止空字符串，后续实现需用 Pydantic `min_length=1` 和服务层 `.strip()` 校验。
3. `context_before` / `context_after` 的版权限制依赖服务层校验，迁移层无法跨表检查来源版权状态，后续实现必须有测试覆盖。
4. `reviewed_at` / `copyright_reviewed_at` 在草案中仍用字符串表达，后续实现建议统一为 `DateTime(timezone=True)`。

## 最终门禁

**PASS**

允许进入下一阶段实现设计，但仅限按本设计的安全边界实施。实现阶段不得放松以下约束：

- 未知、受限、孤儿作品状态不得保存全文或全文文件。
- 古籍版本主数据只能是现有 `Version`。
- `EvidenceCitation` 只有 promotion 后才能进入现有证据链。
- `metadata_harvest` 与 `fulltext_download` 必须是分离的采集明细状态。
