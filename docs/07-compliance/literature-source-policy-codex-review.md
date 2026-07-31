# Codex Review: 文献采集来源白名单合规审计

**被审计文件:** `backend/app/config/source_whitelist.yaml`、`docs/07-compliance/literature-source-policy.md`  
**关联设计:** `docs/03-data/huangfu-mi-literature-data-model.md`  
**审计日期:** 2026-07-10  
**审计范围:** 来源分类、商业数据库限制、盗版站禁止、人工审核、非法下载逻辑、平台学术可信度要求

## 结论

**PASS, with runtime caveat**

来源白名单在政策层面满足本轮五项审计要求：商业数据库被列为 B 类且只允许元数据和外链；盗版站、无授权扫描本、绕过登录下载、破解数据库和镜像站被列为 D 类禁止源；C 类来源要求人工审核；当前实现层未发现针对 Sci-Hub、LibGen、CNKI、万方、维普、超星、Elsevier、Springer、JSTOR 等来源的硬编码非法下载逻辑；政策与平台的来源明确、Evidence/Citation、审核完成等学术可信度要求一致。

残余风险是运行时强制执行尚未证明：`source_whitelist.yaml` 当前未发现被后端采集服务直接读取或拦截执行路径使用。现阶段可以判定为“白名单政策合规”，但不能据此判定“所有未来采集请求已被运行时门禁强制约束”。

## 审计矩阵

| 审计项                         |               结论 | 证据                                                                                                                                                                                                                                                                                                                                          | 说明                                                                                                                                                        |
| ------------------------------ | -----------------: | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 是否把商业数据库列为“仅元数据” |               PASS | `source_whitelist.yaml` 将 B 类定义为“只允许采集元数据和外链”；CNKI、万方、维普、超星、中华经典古籍库、商业电子书平台、高校付费数据库均为 `metadata_allowed: true` 且 `fulltext_allowed: false`。`literature-source-policy.md` 第 2.2 节也声明商业数据库仅采集标题、作者、摘要、关键词、DOI/链接，禁止下载、缓存或索引全文。                  | 满足“商业数据库仅元数据”要求。                                                                                                                              |
| 是否明确禁止盗版站             |               PASS | `source_whitelist.yaml` D 类列出“盗版 PDF 站”“无授权扫描本”“绕过登录下载资源”“破解数据库”“镜像站”，均为 `metadata_allowed: false`、`fulltext_allowed: false`；备注明确 Sci-Hub、LibGen 禁止采集、索引或链接。`literature-source-policy.md` 第 2.4 节列出同类禁止源。                                                                          | 禁止范围覆盖盗版站、破解库、镜像站和绕过访问控制资源。                                                                                                      |
| 是否有人工审核机制             | PASS, policy-level | `source_whitelist.yaml` C 类来源将地方图书馆资源、个人博客整理资料、论坛资料、公众号文章、网盘资源标为 `requires_manual_review: true`。`literature-source-policy.md` 第 2.3 节规定提交申请、审核版权状态和可信度、通过后新增具体白名单条目、归档审核记录。                                                                                    | 人工审核机制在政策和配置层存在。当前未证明已有运行时工作流实现。                                                                                            |
| 是否没有硬编码非法下载逻辑     |               PASS | `rg` 检索 `apps`、`packages`、`tests`、`scripts`、`backend` 中的 `requests/httpx/aiohttp/urllib/download/fulltext/pdf/Sci-Hub/LibGen/cnki/wanfang/cqvip/chaoxing/elsevier/springer/jstor/paywall` 等关键词，未发现外部盗版或商业数据库全文下载器。现有 `IngestionService.ingest_pdf()` 只解析调用方提供的 PDF 字节，不包含外部 URL 下载逻辑。 | 未发现硬编码非法下载路径。注意 `Document.raw_pdf_blob` 和 `ingest_pdf(store_raw_pdf=True)` 能保存用户上传 PDF，后续若接入外部采集必须先接白名单和版权门控。 |
| 是否符合平台学术可信度要求     | PASS, policy-level | `1710_Production_Readiness_Specification.md` 要求数据来源明确、Citation 完整、Evidence 完整、审核完成且不得存在未知来源数据；`0303_Metadata_Standard.md` 要求来源明确、版本清晰、Citation/Evidence 完整、审核完成；来源政策要求记录采集时间、来源 URL、许可依据、审核状态和审核人。                                                           | 政策方向符合平台学术可信度要求。上线前仍需证明运行时采集、入库、RAG/Graph 消费路径都执行这些字段和门禁。                                                    |

## 关键证据

### 1. 商业数据库已限定为 B 类仅元数据

- `backend/app/config/source_whitelist.yaml:91-147`: B 类为“只允许采集元数据和外链”，CNKI、万方、维普、超星、商业电子书平台、高校付费数据库均 `fulltext_allowed: false`。
- `docs/07-compliance/literature-source-policy.md:34-43`: 商业数据库仅允许元数据，禁止下载、缓存或索引全文，明确全文受版权和订阅协议保护。
- `backend/app/config/source_whitelist.yaml:266-272`: B 类来源仅存储元数据和外链，不本地缓存全文。

### 2. 盗版和绕过访问控制来源已列为 D 类禁止源

- `backend/app/config/source_whitelist.yaml:193-233`: 盗版 PDF 站、无授权扫描本、绕过登录下载资源、破解数据库、镜像站均禁止采集。
- `docs/07-compliance/literature-source-policy.md:61-69`: D 类为绝对禁止，不得索引、链接或采集，示例包括 Sci-Hub、LibGen、无授权扫描件、绕过登录或付费墙资源、破解数据库、未授权镜像站。
- `backend/app/config/source_whitelist.yaml:247-257`: 合规声明禁止绕过登录、付费墙或访问控制，禁止访问付费数据库全文，禁止批量下载商业论文。

### 3. 人工审核规则已写入政策与配置

- `backend/app/config/source_whitelist.yaml:150-190`: C 类来源 `requires_manual_review: true`，覆盖地方图书馆、个人博客、论坛、公众号、网盘资源。
- `docs/07-compliance/literature-source-policy.md:45-59`: 审核流程包括提交采集申请、审核版权状态和许可条款、审核通过后新增具体条目、审核记录归档。
- `docs/07-compliance/literature-source-policy.md:100-105`: 审计字段包含 `review_status` 和 `reviewed_by`。

### 4. 当前代码未发现外部非法下载实现

- `apps/backend/app/services/ingestion.py:143-183`: `ingest_pdf()` 从传入的 `BinaryIO` 读取 PDF，提取文本并可保存原始字节，没有外部 URL 抓取、盗版域名或商业数据库下载逻辑。
- `apps/backend/app/services/ingestion.py:21-24`: 摄取元数据键有白名单，只允许 `dynasty`、`category`、`source_url`、`raw_pdf_blob` 写入 Document。
- `apps/backend/app/services/graph_service.py:68-83`: 学术证据 URI 有允许 host 集合，但它用于证据来源 URI 校验，不是全文下载器。
- `apps/backend/app/services/graph_service.py:320-370`: `source_uri` 要求 HTTPS、拒绝 userinfo、拒绝 IP/localhost、拒绝示例域名，并按允许 host 校验。

## 残余风险

1. **白名单未证明已接入运行时采集门禁。** 当前检索未发现 `source_whitelist.yaml` 被后端服务加载使用。若未来实现外部文献采集，必须在请求发起前读取该配置并强制执行 `metadata_allowed`、`fulltext_allowed`、`requires_manual_review`、D 类禁止和默认拒绝。
2. **现有通用 PDF 摄取可以保存上传全文。** 这不是非法下载逻辑，但它不是版权门控模型。若它被复用于外部文献采集，必须先检查来源分类、版权状态和授权依据。
3. **设计文档中的更强模型尚未落地为代码。** `docs/03-data/huangfu-mi-literature-data-model.md` 已设计 `SourcePlatform`、`LiteratureRecord`、`FullTextDocument`、`IngestionItem` 等门控，但当前审计未在 `apps/backend/app/models` 或 API 中发现这些模型的实现。

## 上线门禁建议

**当前白名单政策:** PASS  
**作为运行时强制门禁:** NOT YET PROVEN

在实现外部采集功能前，必须新增并验证以下门禁：

1. 加载 `source_whitelist.yaml`，默认拒绝未列入来源。
2. 对 B 类来源只允许元数据和外链，拒绝全文下载、缓存、索引和 `raw_pdf_blob` 保存。
3. 对 C 类来源在审核通过前按 B 类处理，并记录 `review_status`、`reviewed_by`、审核依据。
4. 对 D 类来源拒绝元数据、外链、全文和索引，不保留任何数据。
5. 对 `domain: "*"` 条目禁止直接放行，必须解析为具体 hostname 后再采集。
6. 出站 HTTP 必须执行 DNS/IP 防 SSRF 校验、禁止私网/回环/链路本地地址，并限制重定向。

## 最终判定

**PASS, with runtime caveat**

本轮“来源白名单政策”满足商业数据库仅元数据、禁止盗版站、人工审核、无硬编码非法下载逻辑、学术可信度对齐五项要求。后续不得把该 PASS 扩大解释为外部采集系统已经完成运行时合规拦截。
