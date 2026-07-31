# Codex Review: context-18 Claude 现状报告验收

**被审计文件:** `docs/12-context/context-18-huangfu-mi-literature-ingestion-audit.md`  
**审计日期:** 2026-07-10  
**审计对象:** Claude 生成的“皇甫谧专题文献采集入库”现状审计报告

## 结论

**PASS**

Claude 报告基本满足本轮验收要求：有真实代码读取痕迹，识别了版权与全文访问风险，区分了元数据采集与公版/受限全文采集，明确列出商业数据库受限全文不可采集，并给出了可执行的模块差距与阶段路线。当前工作区未发现 Claude 越权修改代码。

## 验收项

| 验收项                               | 结论 | 证据                                                                                                                                                                                                                                                        |
| ------------------------------------ | ---: | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 是否真实读取项目代码，而不是凭空推断 | PASS | 报告列出的 `Document.raw_pdf_blob`、`Document.content_text`、`Paper.full_text`、`Image.license_info`、`/api/v1/search/ingest`、`IngestionService`、`RetrievalService`、`VersionRelation`、TEI/校勘模型等均能在当前代码中对应到真实文件与字段。              |
| 是否识别版权风险                     | PASS | 报告第四章列出“全文无访问控制”“版权状态不可知”“缺乏数据治理红线执行”“许可证元数据碎片化”等风险，并把版权字段、访问级别、许可证、来源溯源列为阶段 0 高优先级。                                                                                               |
| 是否区分“元数据采集”和“全文采集”     | PASS | 报告在外部数据源规划中区分 `CrossRef / OpenAlex — 现代学术论文元数据`、`国学大师 — 书目元数据`、`ctext.org / 维基文库 — 公版古籍全文`，并明确“学术论文元数据（摘要 + DOI，不含全文）”。                                                                     |
| 是否明确商业数据库不可批量抓取全文   | PASS | 报告在红线中写明禁止“采集商业数据库受限全文（如 CNKI 付费全文、中华书局授权电子版）”。建议后续把措辞进一步加硬为“不得批量抓取、下载、缓存或入库商业数据库全文；仅允许按授权 API 获取元数据/摘要/DOI”。                                                      |
| 是否给出可执行的模块差距             | PASS | 报告给出模型、采集、OCR、权限、文件存储、外部数据源、审核工作流等差距，并落到 `IngestionBatch`、`IngestionTask`、`Holding`、`CopyrightAssertion`、`ProvenanceRecord`、`copyright_status`、`license`、`access_level`、`acquisition_method` 等具体模块/字段。 |
| 是否没有越权修改代码                 | PASS | `git status --short --untracked-files=all` 只显示两个未跟踪文档：本报告源文件和 `docs/academic_implementation_manual.md`；`git diff --name-only` 为空，未发现已跟踪代码变更。                                                                               |

## 代码证据抽样

- `apps/backend/app/models/document.py`：`documents` 表包含 `content_text`、`source_url`、`raw_pdf_blob`、`page_count`，无 `copyright_status`、`license`、`access_level`。
- `apps/backend/app/models/paper.py`：`papers` 表包含 DOI、期刊、摘要、关键词、`full_text`，无版权/授权/访问级别字段。
- `apps/backend/app/models/image.py`：仅图片模型有 `license_info`，支持 Claude 对“许可证元数据碎片化”的判断。
- `apps/backend/app/api/v1/entities.py`：通用 CRUD 工厂确实注册了 book/version/chapter/passage/paper/image/person/document。
- `apps/backend/app/services/ingestion.py`：确实存在 PDF 文本提取和纯文本摄取，但没有外部数据源采集、批量元数据导入、版权状态校验或文档级 ACL。
- `apps/backend/app/api/v1/day2_search.py`：`POST /api/v1/search/ingest` 只接收纯文本请求；未发现 multipart 文件上传端点。
- `docs/07-security/0703_Privacy_Standard.md`：项目治理标准要求来源、采集方式、版权状态、License、使用限制，并禁止来源不明、未授权、移除版权信息等行为。

## 非阻塞问题

1. 报告附录的文件计数有轻微漂移：当前抽样统计为 models 22 个含 `__init__.py`、v1/v2/v4 API Python 文件 24 个、services 24 个、迁移文件 17 个、tests 下 Python 文件 50 个；报告写 22/22/26/15/49。该问题不影响主体判断，但后续应避免把计数当作验收证据。
2. 报告称 `raw_pdf_blob` 和 `content_text` 可经 API 获取任意文档全文。当前 `DocumentResponse` 返回 `content_text`，但未返回 `raw_pdf_blob`；`raw_pdf_blob` 风险更准确应描述为“数据库层无版权/ACL 控制，摄取服务可保存原始 PDF，当前 API schema 未直接返回 blob”。
3. 工作区另有未跟踪文档 `docs/academic_implementation_manual.md`。它不是代码改动，不构成本轮“越权修改代码”失败项；但若阶段 0 只允许现状审计报告，该文档属于范围外产物，建议后续由用户决定是否保留。

## 最终门禁

**PASS**

允许把 `context-18-huangfu-mi-literature-ingestion-audit.md` 作为阶段 0 现状审计的输入基线继续使用；进入执行阶段前，应补强商业数据库全文红线措辞，并把附录计数改为可复现命令输出或删除计数。
