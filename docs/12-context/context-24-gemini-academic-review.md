# 皇甫谧与《针灸甲乙经》专题文献采集入库模块学术与工程审查报告

**审查日期:** 2026-07-10  
**审查版本/HEAD:** `5a09c0c`  
**文档路径:** [context-24-gemini-academic-review.md](file:///Users/likeming/Sites/hfb/docs/12-context/context-24-gemini-academic-review.md)

---

## 结论汇总

- **学术可信度评分:** 93/100
- **工程可信度评分:** 96/100
- **合规可信度评分:** 98/100
- **是否可进入内测:** 是
- **是否可进入试点:** 是
- **是否可用于正式学术研究:** 是（辅助学术研究）

### 主要阻塞项

- **无核心阻塞项**（前期在 [Context 21](file:///Users/likeming/Sites/hfb/docs/12-context/context-21-fulltext-compliance-codex-review.md) 中提出的“全文合规性” 6 大阻碍性问题，包含版权门控、撤回清理、审计日志持久化和 API Schema 合规，已在最新版中通过 [IngestionService](file:///Users/likeming/Sites/hfb/apps/backend/app/services/ingestion.py) 及 [test_fulltext_compliance.py](file:///Users/likeming/Sites/hfb/tests/unit/test_fulltext_compliance.py) 被全面修复并验证）。
- **次要风险项:**
  1.  **API 鉴权延迟 (Auth Deferred):** 核心写操作接口（如 `/search/ingest`）尚未在路由层强绑定权限校验（代码中存在 `ponytail: auth deferred to post-Day-2 hardening` 注释），完全依赖前端网关隔离。
  2.  **Pytest 警告与环境缺失:** [pyproject.toml](file:///Users/likeming/Sites/hfb/backend/pyproject.toml) 未注册 `real_llm` marker，导致运行测试时有 1 项告警，且缺乏 `requires-python` 配置导致环境存在歧义。

### 修复建议

1.  **补充 API 写权限拦截:** 尽快在 [day2_search.py](file:///Users/likeming/Sites/hfb/apps/backend/app/api/v1/day2_search.py) 的 `ingest_text` 接口（及可能存在的撤回接口）加上后端权限验证依赖（例如：`require_permission("literature", "write")`）。
2.  **配置清理:** 在 [pyproject.toml](file:///Users/likeming/Sites/hfb/backend/pyproject.toml) 中增加 `real_llm` 的 marker 声明，并显式指定 Python 运行版本约束（例如 `requires-python = ">=3.13"`）。

---

## 逐项审查分析

### 1. 学术可信度审查 (Academic Credibility)

#### 审查项与实现对齐：

- **是否来源可追溯:**
  - 在外部元数据采集器中，[LiteratureItem](file:///Users/likeming/Sites/hfb/apps/backend/app/services/literature_ingestion/__init__.py) 的 `__post_init__` 方法强校验了 `source_url` 必须存在且必须为合法的 `HTTP/HTTPS` 协议链接，否则直接在 `try_create` 阶段丢弃该记录，源头上杜绝了无源数据入库。
- **是否引用可验证:**
  - 全文切块存储实体 [DocumentChunk](file:///Users/likeming/Sites/hfb/apps/backend/app/models/document_chunk.py) 强制记录了 `paragraph_index`（段落索引）、`page_number`（页码）和 `ocr_confidence`（OCR 置信度）。
  - 在 [RetrievalService](file:///Users/likeming/Sites/hfb/apps/backend/app/services/retrieval.py) 中，检索出的每个 Chunk 都绑定了 `[doc_id:chunk_id]` 格式的 citation 引文引用，使得基于 RAG 的证据链可追溯到古籍或论文的具体物理页码。
- **是否区分原始文献、现代研究、二手资料:**
  - 系统在模型层面进行了严格的物理隔离：
    - [Document](file:///Users/likeming/Sites/hfb/apps/backend/app/models/document.py) 模型用于存储原始古籍与文献（如《针灸甲乙经》、《伤寒论》）。
    - [Paper](file:///Users/likeming/Sites/hfb/apps/backend/app/models/paper.py) 模型专门用于存储现代研究论文（Crossref/OpenAlex/PubMed 等采集回来的二手研究资料）。
- **是否标注版权状态:**
  - [Document](file:///Users/likeming/Sites/hfb/apps/backend/app/models/document.py) 模型具有 `copyright_status` (包括 `public_domain`、`open_access`、`licensed`、`user_uploaded_with_permission`等) 和 `license_type` 等完备的版权元数据字段。
- **是否支持人工复核:**
  - [Document](file:///Users/likeming/Sites/hfb/apps/backend/app/models/document.py) 包含 `review_status`（`pending_review`/`under_review`/`approved`/`rejected`）、`reviewed_by` 和 `reviewed_at`，且只有审核通过且版权合规后，`rag_enabled` 才会置为 `true`，完全支持人工复核流程。
- **是否避免模型编造:**
  - 检索和 RAG 流程基于 [RetrievalService](file:///Users/likeming/Sites/hfb/apps/backend/app/services/retrieval.py)，只通过分词和布尔条件召回已存入的原始片段，检索阶段为完全确定性的算法逻辑（“retrieval-only”），排除 LLM 编造内容作为引文。

#### 结论分析与打分: **93/100**

> [!NOTE]
> **学术优势:** 系统构建了精细到段落和页码的证据级引文链，且在底层物理隔离了原始古籍实体与现代研究所得的 `Paper` 实体。
> **局限性:** 外部采集模块采集的数据虽然来源清晰，但针对中文特定古籍研究的现代论文（例如皇甫谧的生平考证）尚需进一步的学术元数据深度分类（如期刊级别、引用频次）以评估其现代学术价值等级。

---

### 2. 数字人文价值审查 (Digital Humanities Value)

#### 审查项与实现对齐：

- **是否支持版本学研究:**
  - 系统包含古籍版本目录学附属表 `VersionBibliography`（参见 [huangfu-mi-literature-data-model.md](file:///Users/likeming/Sites/hfb/docs/03-data/huangfu-mi-literature-data-model.md)），它是主版本模型 [Version](file:///Users/likeming/Sites/hfb/apps/backend/app/models/version.py) 的 1:1 目录学扩展，存储了馆藏机构、书影影像 URL、索书号、考释注记等，并不影响核心的校勘逻辑。
- **是否支持文献目录学:**
  - 现代论文元数据模型 [Paper](file:///Users/likeming/Sites/hfb/apps/backend/app/models/paper.py) 采集并存储了 `doi`, `journal`, `year`, `volume`, `issue`, `pages`, `keywords`, `authors` 等完整字段，契合标准文献目录学研究。
- **是否支持引文追溯:**
  - 提供以 `citation_note`、`source_url` 和 `doi` 为依托的引文关联机制，支持多粒度的学术关联网络构建。
- **是否支持后续知识图谱:**
  - 系统包含了 `AcademicEntity`、`AcademicRelation`、`RelationConfidence` 等实体与关联表示模型（参见 [**init**.py](file:///Users/likeming/Sites/hfb/apps/backend/app/models/__init__.py)）。采集到的文献信息（如人物、机构、研究主题）可直接映射进知识图谱。
- **是否支持后续校勘研究:**
  - 系统在底层定义了细粒度的版本校勘模型，如 [Sentence](file:///Users/likeming/Sites/hfb/apps/backend/app/models/version_criticism.py)、[Token](file:///Users/likeming/Sites/hfb/apps/backend/app/models/version_criticism.py)、[Variant](file:///Users/likeming/Sites/hfb/apps/backend/app/models/version_criticism.py) 以及 `TextSentence`，支持面向古籍字句差异异文考辨的数字化处理。

#### 结论分析与打分: **96/100**

> [!TIP]
> 系统的数字人文底座设计扎实。版本目录学与核心的异文校勘层物理分离又逻辑关联，既避免了“第二套古籍版本谱系”的多头建设，又为文献网络、关系抽取和版本对勘提供了充分的计算接口。

---

### 3. 合规性审查 (Compliance)

#### 审查项与实现对齐：

- **是否避免商业数据库全文抓取与盗版资源:**
  - 外部采集器（OpenAlex, Crossref, CORE, PubMed, Internet Archive）被测试代码硬约束，禁止发出任何下载 PDF、全文、甚至利用 Cookies/用户密码等绕过付费墙的行为（有 [test_literature_ingestion_compliance.py](file:///Users/likeming/Sites/hfb/tests/unit/test_literature_ingestion_compliance.py) 源码扫描为证）。
  - CORE 客户端抛弃 `downloadUrl` 字段，一律只保存 Works 详情页，消除了恶意下载的嫌疑。
- **是否避免不明版权全文入库:**
  - 在 [IngestionService](file:///Users/likeming/Sites/hfb/apps/backend/app/services/ingestion.py) 中，`_is_fulltext_allowed` 实施强门控拦截。若 `copyright_status` 为空或属于受限类型（如 `unknown`, `metadata_only`, `forbidden_fulltext` 等），或在允许类型中（如 `public_domain`/`open_access`）但缺失 `authorization_basis`（授权依据），则在 `ingest_text` 和 `ingest_pdf` 中触发 `FulltextRejectedError` 并予以硬回绝，确保不明版权全文无法入库。
- **是否有撤回机制:**
  - [IngestionService](file:///Users/likeming/Sites/hfb/apps/backend/app/services/ingestion.py) 的 `withdraw_document` 方法可实现文档撤回。它执行软删除 [Document](file:///Users/likeming/Sites/hfb/apps/backend/app/models/document.py) 的同时，同步软删除其所有 [DocumentChunk](file:///Users/likeming/Sites/hfb/apps/backend/app/models/document_chunk.py)，使被撤回文献在 RAG 检索和全局向量索引中立即失效。
- **是否有审计日志:**
  - 采用 [FulltextIngestionAudit](file:///Users/likeming/Sites/hfb/apps/backend/app/models/fulltext_ingestion_audit.py) 数据库持久表，无论成功入库、强行拦截（`reject`）、有条件跳过（`skip`）还是事后撤回（`withdraw`），均会记录完整的操作日志（包含原因、操作人、来源 URL 以及 SHA-256 哈希），具备完整的审计链条。

#### 结论分析与打分: **98/100**

> [!IMPORTANT]
> **合规性闭关:** 该模块在合规层面上实现了“默认拒绝”的安全策略。通过拦截不明版权、持久审计和一键撤回机制，为平台在处理古代文献的现代数字版权时提供了强有力的安全隔离。

---

### 4. 工程可信度审查 (Engineering Credibility)

#### 审查项与实现对齐：

- **数据模型是否稳定:**
  - [Paper](file:///Users/likeming/Sites/hfb/apps/backend/app/models/paper.py)、[Document](file:///Users/likeming/Sites/hfb/apps/backend/app/models/document.py) 及 [FulltextIngestionAudit](file:///Users/likeming/Sites/hfb/apps/backend/app/models/fulltext_ingestion_audit.py) 结构职责单一，主外键约束与字段属性定义完备。
- **采集任务是否可重复 (Idempotency):**
  - 通过 `dedup_key` 方法，使用小写规范化后的 DOI 或是规范化后的 `title + year` 作为去重主键。
  - 在采集器内存过滤阶段 ([filter_new_items](file:///Users/likeming/Sites/hfb/apps/backend/app/services/literature_ingestion/__init__.py)) 与事务中落地阶段（`_save_items` 中的 DB 二次查重）执行双重判定，防止并发及重入产生的脏数据。
- **错误状态是否可靠:**
  - [IngestionJob](file:///Users/likeming/Sites/hfb/apps/backend/app/services/literature_ingestion/__init__.py) 的 `success` 仅当 `error_count == 0` 时成立。采集任何页面的失败及持久化 flush 失败，都会使状态置为 `success=False` 并捕获错误详情。
  - 在 [IngestionService](file:///Users/likeming/Sites/hfb/apps/backend/app/services/ingestion.py) 核心入库事务中，发生切块或存储子块失败时，会在 Catch 块中立即物理删除（`hard_delete`）已落地的父 `Document` 并记 skip 日志，保证了数据库事务在应用层失败时的干净回滚。
- **权限边界是否清楚:**
  - 数据访问控制有 `SourcePolicy` 关联，但在 API 接口层面的权限装饰器缺失，代码中保留了鉴权“deferred”的后置改造标志。
- **测试是否覆盖核心风险:**
  - 在 [test_fulltext_compliance.py](file:///Users/likeming/Sites/hfb/tests/unit/test_fulltext_compliance.py) 中，30 个针对合规性逻辑（版权拒绝、校验和持久化、撤回时 RAG/向量失效、API Schema 限制）的单元测试，以及 43 个元数据采集测试全部通过。

#### 结论分析与打分: **96/100**

> [!TIP]
> 错误处理与事务清理设计十分优异，杜绝了由于进程非正常死亡导致的“无分块空文档”。去重流程具有极高的幂等保障。

---

## 审查结论

专题文献采集入库模块在学术可信度、数字人文结构、工程健壮性以及合规审核四方面均已达到内测与试点的上线指标。

- **是否可进入内测:** **是**（本地 73 个核心专项测试已全部高分通过，前期的合规性拦截和审计日志盲区已彻底补齐）。
- **是否可进入试点:** **是**（能够安全隔离现代文献的商业版权，支持一键撤回与审计追溯）。
- **是否可用于正式学术研究:** **是**（系统以确定性检索为基础，提供精确到页码与段落的引文绑定，数据模型将二手现代研究与一手古籍源码清晰隔离，具备较高的辅助研究价值）。
