# 皇甫谧与《针灸甲乙经》专题文献采集库 — 现状审计报告

**文档编号:** context-18
**主题:** 皇甫谧专题文献采集入库 — 阶段 0 现状审计
**审计日期:** 2026-07-10
**状态:** 完成
**版本:** 1.0

---

## 一、当前已有能力

### 1.1 文献库 (Literature Management) — ✅ 具备基础

| 能力                    | 状态    | 说明                                                                  |
| ----------------------- | ------- | --------------------------------------------------------------------- |
| Book（古籍）CRUD        | ✅ 完整 | `books` 表，含书名、拼音、英译、作者、朝代、年代、分类、摘要、来源URL |
| Version（版本）CRUD     | ✅ 完整 | `versions` 表，含版本名、年代、馆藏地、索书号、编纂者、来源URL        |
| Chapter（章节）CRUD     | ✅ 完整 | `chapters` 表，自引用层级结构（篇→章→节）                             |
| Passage（段落）CRUD     | ✅ 完整 | `passages` 表，含正文、译文、注释、标签                               |
| Document（文献）CRUD    | ✅ 完整 | `documents` 表，含 PDF 二进制存储 (`raw_pdf_blob`)、全文文本、分页数  |
| Paper（论文）CRUD       | ✅ 完整 | `papers` 表，含 DOI、期刊、卷期页码、全文、论文类型                   |
| Person（人物）CRUD      | ✅ 完整 | `persons` 表，含字号、生卒年、籍贯、传记、代表作                      |
| Image（图片）CRUD       | ✅ 完整 | `images` 表，含 URL、标题、来源、许可证信息                           |
| Institution（机构）CRUD | ✅ 完整 | `institutions` 表，含类型（研究/大学/档案/机构）、地点                |

### 1.2 古籍版本库 — ✅ 深度具备

| 能力                   | 状态 | 说明                                                                                                                         |
| ---------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------- |
| 版本世系追踪           | ✅   | `VersionRelation` 模型，6 种关系类型（derived_from, revised_from, corrected_by, annotated_by, compared_with, referenced_by） |
| 版本差异对比           | ✅   | `VersionDiff` 模型，预计算差异 JSON + 摘要                                                                                   |
| 段落映射               | ✅   | `PassageMapping` 模型，4 种映射类型（equivalent, variant, missing, added）                                                   |
| 版本校勘（句/词/异文） | ✅   | `Sentence` → `Token` → `Variant` 三级模型，5 种异文类型                                                                      |
| TEI 标准持久化         | ✅   | `TextSentence` → `TextToken` → `TextualVariant`，符合 TEI P5 规范                                                            |
| TEI 校勘栏生成         | ✅   | `/api/v2/tei/apparatus` 端点，生成 XML 校勘栏                                                                                |
| 注疏系统               | ✅   | `Commentary` 模型，自引用层级，支持注/疏/笺/评                                                                               |
| 版本中心 API           | ✅   | `/api/v1/version_center.py`，世系树、关系、比较、差异                                                                        |

### 1.3 文件摄取模块 — ⚠️ 部分具备

| 能力              | 状态 | 说明                                          |
| ----------------- | ---- | --------------------------------------------- |
| PDF 文本提取      | ✅   | `pypdf` 库，`ingestion.py` 服务               |
| 纯文本摄取        | ✅   | `POST /api/v1/search/ingest` 端点             |
| 文本分块          | ✅   | `chunking.py`，基于段落边界的中文分块器       |
| 分块-段落血统回填 | ✅   | `backfill_passage.py` 脚本，幂等匹配          |
| 多部分文件上传    | ❌   | 无 multipart/form-data 上传端点               |
| 批量导入          | ❌   | 无 CSV/JSON 批量导入端点或脚本                |
| 图片文件上传      | ❌   | Image CRUD 为管理型（URL 引用），无二进制上传 |

### 1.4 RAG 文档库 — ✅ 具备基础

| 能力                    | 状态 | 说明                                                                                  |
| ----------------------- | ---- | ------------------------------------------------------------------------------------- |
| 文档分块存储            | ✅   | `document_chunks` 表，含 chunk_index、content、token_count                            |
| 关键词检索              | ✅   | `RetrievalService`，SQL ILIKE 多关键词分词 + 评分                                     |
| 上下文组装              | ✅   | `rag_service.py`，混合检索 + 引文丰富                                                 |
| 学术 RAG 问答           | ✅   | `academic_rag_service.py`，中文查询规划 → 语料检索 → 图谱多跳 → 证据验证 → 确定性回答 |
| 证据门控 AI 聊天        | ✅   | `POST /api/v1/ai/chat`，流式 + 证据验证                                               |
| 向量嵌入/语义搜索       | ❌   | pgvector 存在但未启用；embeddings 未集成                                              |
| 混合检索（关键词+向量） | ❌   | 预留但未实现                                                                          |

### 1.5 OCR 模块 — ❌ 完全缺失

| 能力               | 状态 | 说明                                                          |
| ------------------ | ---- | ------------------------------------------------------------- |
| OCR 引擎           | ❌   | 无 tesseract、pytesseract、tesserocr、easyocr、paddleocr 依赖 |
| OCR API 端点       | ❌   | 无                                                            |
| 扫描件转文本管道   | ❌   | 无                                                            |
| 图像预处理         | ❌   | 无                                                            |
| OCR 结果校对工作流 | ❌   | 无                                                            |

`docs/14-knowledge/ocr/README.md` 存在但为空壳。

### 1.6 知识图谱模块 — ✅ 深度具备

| 能力         | 状态 | 说明                                                                       |
| ------------ | ---- | -------------------------------------------------------------------------- |
| 跨实体关系   | ✅   | `EntityRelation` 模型，12 种实体类型、11 种关系类型                        |
| 证据绑定     | ✅   | 关系必须绑定 `evidence_document_id`、`evidence_quote`、`evidence_citation` |
| 验证工作流   | ✅   | evidence_status (unverified→verified→rejected) + verified_by FK            |
| 学术知识图谱 | ✅   | `AcademicEntity` + `AcademicRelation` + `RelationConfidence`               |
| 针灸本体     | ✅   | ACUPOINT, MERIDIAN, DISEASE, PERSON, TECHNIQUE 实体类型                    |
| 多跳查询     | ✅   | BFS 最短路径 + evidence-chains 端点                                        |
| 概念图谱     | ✅   | `build_concept_graph()`，Jaccard 相似度                                    |
| 图谱可视化   | ✅   | `/api/v4/visualization/graph` 端点                                         |
| 本体框架     | ✅   | `packages/tcm_ontology/`，EntityType 注册 + Schema                         |
| 内存图谱     | ✅   | `packages/tcm_kg/`，Node/Edge/GraphStore/GraphQuery/KGBuilder              |

### 1.7 搜索模块 — ✅ 具备

| 能力          | 状态 | 说明                              |
| ------------- | ---- | --------------------------------- |
| 统一全文搜索  | ✅   | PostgreSQL ILIKE，跨 7 种实体类型 |
| 自动补全      | ✅   | `GET /api/v1/search/suggest`      |
| 分面结果      | ✅   | 按实体类型分组                    |
| 相关性评分    | ✅   | 多字段加权评分                    |
| Elasticsearch | ⚠️   | 配置中声明但搜索实际走 PostgreSQL |
| 高级筛选      | ❌   | 无朝代/年代/分类/许可证筛选       |

### 1.8 数据导入脚本 — ⚠️ 最少具备

| 能力           | 状态 | 说明                                        |
| -------------- | ---- | ------------------------------------------- |
| 数据库种子     | ✅   | `seed.py`、`seed_graph.py`、`seed_rbac.py`  |
| 段落血统回填   | ✅   | `backfill_passage.py`                       |
| 验收演示       | ✅   | `demo_tcm_acceptance.py`（HTTP API 调用链） |
| 文献批量导入   | ❌   | 无                                          |
| 元数据批量导入 | ❌   | 无                                          |
| 外部数据源采集 | ❌   | 无（无 requests/httpx 爬虫代码）            |
| ETL 流水线     | ❌   | 无 Airflow/Prefect/Dagster                  |

### 1.9 权限控制模块 — ✅ 完善

| 能力                | 状态 | 说明                                                                                                                        |
| ------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------- |
| RBAC 用户-角色-权限 | ✅   | `User` ↔ `Role` ↔ `Permission` 多对多                                                                                       |
| JWT 认证            | ✅   | access + refresh token 对                                                                                                   |
| 权限粒度            | ✅   | 资源级（book/version/passage/evidence 等 15 种）+ 操作级（create/read/update/delete/export/publish/review/approve/reindex） |
| 中间件              | ✅   | `require_permission()`、`require_any_permission()`                                                                          |
| 软删除              | ✅   | `SoftDeleteMixin`，全部实体支持                                                                                             |

---

## 二、缺失能力

### 2.1 文献采集入库流程 — 🔴 关键缺失

| 缺失项                                                                          | 影响                     | 严重度 |
| ------------------------------------------------------------------------------- | ------------------------ | ------ |
| **文献发现层**：无外部数据源连接器（图书馆 OPAC、学术数据库 API、开放获取仓储） | 所有数据需手工录入       | 🔴 高  |
| **元数据采集管道**：无 Dublin Core / MARC / MODS 解析器                         | 无法批量导入标准书目记录 | 🔴 高  |
| **去重引擎**：无题名/作者/DOI 相似度匹配                                        | 重复录入风险             | 🟡 中  |
| **采集任务管理**：无 `IngestionJob` / `ImportTask` 模型                         | 无法追踪批次导入状态     | 🟡 中  |
| **来源溯源**：现有 `source_url` 字段过于简单                                    | 无法满足"来源可追溯"要求 | 🔴 高  |

### 2.2 版本目录库 — 🟡 部分缺失

| 缺失项                                                      | 影响                         | 严重度 |
| ----------------------------------------------------------- | ---------------------------- | ------ |
| **版本目录标准字段**：缺 ISBN、出版者、版次、丛书名         | 书目信息不完整               | 🟡 中  |
| **馆藏信息**：现 `repository` + `shelf_mark` 各一个文本字段 | 无法表示多馆藏地、复本       | 🟡 中  |
| **版本层级关系**：现仅 Version → Book 两层                  | 缺丛书、子目、合刻等复杂关系 | 🟢 低  |
| **目录导出**：无 BibTeX / RIS / MARC 导出                   | 学术互操作性不足             | 🟢 低  |

### 2.3 合规全文库 — 🔴 关键缺失

| 缺失项                                                                                      | 影响                               | 严重度 |
| ------------------------------------------------------------------------------------------- | ---------------------------------- | ------ |
| **版权状态字段**：Document/Book 模型无 `copyright_status`、`license`、`access_restrictions` | 无法区分公版/版权保护/授权使用     | 🔴 高  |
| **全文访问控制**：无文档级 ACL                                                              | 受版权保护的全文与公版全文同权访问 | 🔴 高  |
| **许可证元数据**：Image 有 `license_info` 字段，但 Book/Version/Document/Paper/Passage 均无 | 许可证信息碎片化                   | 🔴 高  |
| **OCR 文本层**：扫描版 PDF 无法提取文字                                                     | 大量古籍扫描本不可用               | 🟡 中  |
| **全文格式转换**：仅支持 PDF（通过 pypdf）和纯文本                                          | 无 DOCX/HTML/EPUB 支持             | 🟢 低  |

### 2.4 引文证据库 — 🟢 基本具备

现有 `SourceRef` → `Evidence` → `Citation` 三级模型 + `EvidenceLevel` 枚举（LEVEL_1 出土文献 → LEVEL_4 现代学术论著）已较为完善。主要缺失：

| 缺失项                      | 影响                           | 严重度 |
| --------------------------- | ------------------------------ | ------ |
| **证据与 Passage 自动关联** | 需手动挂载 `source_passage_id` | 🟢 低  |
| **证据冲突检测**            | 已存在 `conflict_detector.py`  | ✅     |
| **引文格式自动生成**        | 无 Chicago/GB/T 7714 格式化    | 🟢 低  |

### 2.5 采集工作流与质量保障 — 🟡 关键缺失

| 缺失项                 | 影响                                       | 严重度 |
| ---------------------- | ------------------------------------------ | ------ |
| **采集任务状态机**     | 无 draft→reviewing→approved→published 流程 | 🟡 中  |
| **质量核验工作流**     | 无人工审核/专家校验/同行评议流程           | 🟡 中  |
| **版本锁定与审计日志** | 软删除存在，但无不可变审计日志             | 🟡 中  |
| **数据质量报告**       | 无完整性/一致性/重复度检查报告             | 🟢 低  |

### 2.6 外部数据采集 — 🔴 关键缺失

| 缺失项           | 影响                                                  | 严重度 |
| ---------------- | ----------------------------------------------------- | ------ |
| Web 采集框架     | 无 HTTP 客户端/爬虫基础设施                           | 🔴 高  |
| API 集成         | 无 CrossRef / OpenAlex / WorldCat / CNKI API 客户端   | 🔴 高  |
| 速率限制与合规   | 无 robots.txt 解析、速率控制                          | 🔴 高  |
| 开放数据源适配器 | 无 ctext.org / 国学大师 / 中国哲学书电子化计划 等接口 | 🟡 中  |

---

## 三、数据模型差距

### 3.1 现有模型 vs 专题采集需求

| 需求字段          | 现有模型                            | 差距                                                                                                       |
| ----------------- | ----------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| **版权状态**      | ❌ 全模型缺失                       | 需在所有文本实体增加 `copyright_status`（public_domain / in_copyright / orphan_work / licensed / unknown） |
| **许可证**        | ⚠️ 仅 Image 有 `license_info`       | 需统一为 `license` 字段（CC0 / CC-BY / CC-BY-NC / custom）                                                 |
| **访问限制**      | ❌ 全模型缺失                       | 需 `access_level`（open / registered / restricted / embargoed）                                            |
| **来源出处**      | ⚠️ 仅简单的 `source_url`            | 需结构化 `source_institution`、`source_collection`、`source_accession_date`、`source_contact`              |
| **采集批次**      | ❌ 无对应模型                       | 需 `IngestionBatch` / `IngestionTask` 模型                                                                 |
| **馆藏复本**      | ⚠️ 单一 `repository` + `shelf_mark` | 需 `Holding` 关联表（institution_id + shelf_mark + copy_number + condition）                               |
| **丛书/子目关系** | ❌ Book 无自引用                    | 需 `parent_book_id` 支持丛书→子目层级                                                                      |
| **数字化状态**    | ❌ 无                               | 需 `digitization_status`（digitized / partially_digitized / not_digitized）                                |
| **原文语言**      | ⚠️ Book/Document 有 `language` 字段 | 已有，足够                                                                                                 |
| **完整书目信息**  | ⚠️ 缺 ISBN/出版者/版次              | 需在 Version 增加 `isbn`、`publisher`、`edition_number`                                                    |
| **文件格式**      | ❌ 无                               | 需在 Document 增加 `file_format`（pdf/jpg/tiff/txt）和 `file_size`                                         |
| **采集方法**      | ❌ 无                               | 需 `acquisition_method`（manual_entry / api_import / web_crawl / ocr / user_upload）                       |

### 3.2 需要新建的模型

```
IngestionBatch          — 采集批次（项目、操作人、时间、状态、来源）
IngestionTask           — 批次内的单个采集任务（目标、状态、结果、错误日志）
Holding                 — 馆藏信息（机构、索书号、复本号、品相）
CopyrightAssertion      — 版权声明（实体类型+ID、状态、依据、确认人、确认时间）
ProvenanceRecord        — 来源溯源记录（实体类型+ID、来源机构、采集时间、采集方式、原始URL）
```

### 3.3 需要扩展的现有模型

**Book:**

- `copyright_status` VARCHAR(50)
- `license` VARCHAR(100)
- `access_level` VARCHAR(20) DEFAULT 'open'
- `parent_book_id` FK → books.id (丛书关系)
- `digitization_status` VARCHAR(30)

**Version:**

- `isbn` VARCHAR(20)
- `publisher` VARCHAR(300)
- `edition_number` VARCHAR(50)
- `copyright_status` VARCHAR(50)
- `license` VARCHAR(100)

**Document:**

- `copyright_status` VARCHAR(50)
- `license` VARCHAR(100)
- `access_level` VARCHAR(20) DEFAULT 'open'
- `file_format` VARCHAR(20)
- `file_size` BIGINT
- `acquisition_method` VARCHAR(30)
- `source_institution` VARCHAR(300)
- `source_collection` VARCHAR(300)
- `source_accession_date` DATE

**Passage:**

- `source_document_id` FK → documents.id
- `copyright_status` VARCHAR(50) (继承自父文档，冗余以便检索)

---

## 四、安全与版权风险

### 4.1 🔴 高风险

| 风险                     | 描述                                                                                                                                                           | 缓解措施                                                               |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------- |
| **全文无访问控制**       | `Document.raw_pdf_blob` 和 `Document.content_text` 无 ACL 保护。任何认证用户可通过 API 获取任意文档全文。受版权保护的论文全文可能被非法分发。                  | 增加 `access_level` 字段 + 中间件检查；受保护全文仅返回摘要            |
| **版权状态不可知**       | 系统无法区分公版古籍（如宋本《针灸甲乙经》）和版权保护文献（如 2023 年期刊论文）。可能将版权内容当作公版内容分发。                                             | 所有文本实体必须标注 `copyright_status`；默认设为 `unknown` 并限制访问 |
| **缺乏数据治理红线执行** | `docs/07-security/0703_Privacy_Standard.md` 定义了 19 条数据治理红线（禁止无来源数据入库、禁止删除元数据、禁止 AI 使用未授权数据等），但代码中无自动执行机制。 | 在服务和 API 层增加校验逻辑                                            |
| **PDF 二进制无病毒扫描** | `raw_pdf_blob` 直接存入数据库，无安全扫描                                                                                                                      | 上传管道中集成 ClamAV 或类似工具                                       |

### 4.2 🟡 中风险

| 风险                 | 描述                                                                  | 缓解措施                             |
| -------------------- | --------------------------------------------------------------------- | ------------------------------------ |
| **来源追溯不完整**   | `source_url` 为简单文本字段，不足以满足"来源可追溯"要求               | 增加 `ProvenanceRecord` 模型         |
| **采集方法无审计**   | 无记录说明数据是通过 API、手动录入还是爬虫获取                        | 增加 `acquisition_method` 字段       |
| **图片许可证碎片化** | 仅 Image 有 `license_info`，其他实体无许可证字段                      | 统一许可证元数据方案                 |
| **MinIO 文件存储**   | 配置声明了 MinIO，但无文件上传端点使用它；PDF 以 blob 存于 PostgreSQL | 大文件应使用 MinIO，数据库仅存元数据 |

### 4.3 🟢 低风险

| 风险               | 描述                                         | 缓解措施                           |
| ------------------ | -------------------------------------------- | ---------------------------------- |
| **软删除可恢复**   | 软删除数据理论上可恢复，可能违反数据删除请求 | 增加硬删除 + 保留策略              |
| **无数据加密**     | 全文以明文存储                               | 如存储受版权保护全文，需应用层加密 |
| **API 无速率限制** | 无请求频率控制                               | 增加速率限制中间件                 |

### 4.4 ⛔ 红线（不可触碰）

根据项目数据治理标准，以下行为绝对禁止：

1. 采集商业数据库受限全文（如 CNKI 付费全文、中华书局授权电子版）
2. 将未经核验的内容直接喂给 RAG
3. 伪造论文、伪造版本、伪造出处
4. 删除或篡改原始元数据中的版权信息
5. 无来源数据入库
6. 未标注 AI 生成内容即作为原创学术成果

---

## 五、推荐实施路线

### 阶段 0：安全基础加固（1-2 天）— ⬅ 当前阶段

```
优先级: 🔴 最高
依赖: 无
```

- [ ] 扩展数据模型：为 Book、Version、Document、Passage、Paper 增加 `copyright_status`、`license`、`access_level` 字段
- [ ] 创建迁移脚本
- [ ] 扩展 Document 模型：增加 `file_format`、`file_size`、`acquisition_method`、`source_institution`、`source_collection`、`source_accession_date`
- [ ] 创建 `ProvenanceRecord` 模型
- [ ] 为现有种子数据标注版权状态

### 阶段 1：采集基础管道（3-5 天）

```
优先级: 🔴 高
依赖: 阶段 0
```

- [ ] 创建 `IngestionBatch` / `IngestionTask` 模型 + 迁移
- [ ] 创建采集任务状态机（pending → fetching → parsing → reviewing → approved → published → rejected）
- [ ] 构建批量元数据导入端点（CSV/JSON → Book/Version/Passage）
- [ ] 实现去重引擎（基于题名+作者+年代的相似度匹配）
- [ ] 构建文件上传端点（multipart/form-data → MinIO）
- [ ] 构建 `Holding` 模型 + 迁移

### 阶段 2：皇甫谧专题数据采集（5-8 天）

```
优先级: 🔴 高
依赖: 阶段 1
```

- [ ] 设计皇甫谧专题元数据方案（人物、著作、版本、相关论文、相关人物）
- [ ] 构建外部数据源适配器：
  - 中国哲学书电子化计划 (ctext.org) — 公版古籍全文
  - 国学大师 — 书目元数据
  - CrossRef / OpenAlex — 现代学术论文元数据
  - 维基文库 — 公版古籍全文
- [ ] 实现合规采集管道（robots.txt 检查、速率限制、用户代理声明）
- [ ] 批量导入《针灸甲乙经》已知版本目录：
  - 宋刻本（残卷）- 中国国家图书馆
  - 明嘉靖刻本 - 上海图书馆
  - 四库全书本（文渊阁、文津阁）
  - 日本静嘉堂文库藏本
  - 现代校注本（如 2005 年人民卫生出版社黄龙祥校注本）
- [ ] 创建皇甫谧人物记录 + 生平年表
- [ ] 采集皇甫谧相关学术论文元数据（摘要 + DOI，不含全文）

### 阶段 3：OCR 与数字化管道（5-8 天）

```
优先级: 🟡 中
依赖: 阶段 1
```

- [ ] 集成 tesseract OCR 引擎（pytesseract）+ 中文语言包
- [ ] 构建扫描件预处理管道（去噪、二值化、倾斜校正）
- [ ] 构建 OCR → Passage 管道（OCR 结果 → 段落分割 → 人工校对界面）
- [ ] OCR 结果置信度标注（低置信度区域标记供人工复核）
- [ ] 仅对公版古籍扫描件开放 OCR 功能

### 阶段 4：质量保障与审核（3-5 天）

```
优先级: 🟡 中
依赖: 阶段 1
```

- [ ] 构建人工审核工作流（OCR 结果校对、元数据核验、版本信息确认）
- [ ] 构建数据质量报告（完整性、一致性、重复度、版权标注覆盖率）
- [ ] 构建不可变审计日志
- [ ] 实现引文格式自动生成（GB/T 7714、Chicago）

### 阶段 5：全文合规访问（3-5 天）

```
优先级: 🟡 中
依赖: 阶段 0
```

- [ ] 实现文档级访问控制中间件（基于 `access_level`）
- [ ] 公版全文：开放访问
- [ ] 版权保护全文：仅返回摘要 + DOI 链接
- [ ] 授权全文：登录用户可读，不可下载
- [ ] 受限全文：仅元数据可见
- [ ] 实现全文水印（授权用户查看时嵌入用户标识）

---

## 六、系统就绪度评估

| 维度         | 评分 | 说明                                       |
| ------------ | ---- | ------------------------------------------ |
| 数据模型基础 | 8/10 | 核心实体模型完善，缺版权/来源/采集相关字段 |
| API 基础设施 | 7/10 | 73 个端点，CRUD 完备，缺文件上传和批量导入 |
| 古籍版本能力 | 9/10 | 版本世系、校勘、TEI 均已实现，深度领先     |
| 知识图谱     | 8/10 | 双图谱系统 + 证据绑定 + 置信度，学术级     |
| RAG 与检索   | 5/10 | 关键词检索可用，无向量语义搜索             |
| OCR          | 0/10 | 完全缺失                                   |
| 版权合规     | 2/10 | 仅有治理文档，无代码执行                   |
| 数据采集     | 1/10 | 无外部数据源连接、无批量导入、无 ETL       |
| 权限控制     | 8/10 | RBAC 完善，缺文档级 ACL                    |
| 文件处理     | 3/10 | PDF 文本提取可用，无上传端点、无多格式支持 |

**综合就绪度: 5.1/10**

**结论:** 系统在古籍版本学和知识图谱方面具有深厚基础，但作为"专题文献采集入库"平台，在对外数据采集、版权合规管理、批量导入管道、OCR 四个方面存在关键缺口。建议按上述路线分阶段补齐，优先完成阶段 0（安全基础）和阶段 1（采集基础管道）。

---

## 附录 A：审计范围与方法

- **代码库路径:** `/Users/likeming/Sites/hfb`
- **审计方法:** 全量代码审查（模型文件、API 路由、服务层、依赖配置、文档体系）
- **Git 状态:** 当前分支 `master`，最近提交 `a66810e`
- **已检查的关键文件:**
  - 所有 `app/models/*.py`（22 个模型文件）
  - 所有 `app/api/v1/*.py`、`app/api/v2/*.py`、`app/api/v4/*.py`（22 个路由文件）
  - 所有 `app/services/*.py`（26 个服务文件）
  - `pyproject.toml`、`docker-compose.dev.yml`、`docker-compose.prod.yml`
  - `docs/07-security/0703_Privacy_Standard.md`
  - `docs/12-context/` 全部子目录
  - 15 个 Alembic 迁移文件

## 附录 B：现有测试覆盖

- 49 个 Python 测试文件，涵盖实体 CRUD、图谱、学术 RAG、搜索、多跳推理、段落回填
- 最低覆盖阈值 70%
- 验收演示脚本 `scripts/demo_tcm_acceptance.py` 覆盖 5 个关键集成场景

---

_本报告仅供阶段 0（现状审计）参考，不包含任何代码变更或开发指令。_
