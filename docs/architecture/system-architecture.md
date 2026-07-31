---
title: System Architecture — Full Blueprint
document_id: HFB-ARC-0203
version: 1.2.0
status: Review
owner: Project Steering Committee
reviewer: Chief Product & Technical Architect
effective_date: 2026-06-30
scope: Full Platform Architecture (MVP + Phase 2 + Phase 3)
priority: P0
related_documents:
  - HFB-ARC-0201 Technical Blueprint
  - HFB-DAT-0301 Data Standard Specification
  - HFB-DAT-0302 Ontology Specification
  - HFB-DAT-0304 Entity Specification
  - HFB-DAT-0305 Relation Specification
  - HFB-DOM-0809 Master Knowledge Graph Model
  - HFB-AI-0401 AI Engineering Standard
  - HFB-PS-1709 MVP Implementation Specification
  - HFB-PS-1710 Production Readiness Specification
  - ADR-0004 Neo4j
  - ADR-0005 Elasticsearch
  - ADR-0006 GraphRAG
  - ADR-0007 Milvus
---

# System Architecture — Full Blueprint

## 皇甫谧数字人文平台 · 生产级系统架构

> **规范层级声明：**
>
> - [HFB-ARC-0201 Technical Blueprint](../02-architecture/0201_Technical_Blueprint.md) 决定技术架构和阶段边界
> - [HFB-DAT-0304 Entity Specification](../03-data/0304_Entity_Specification.md) 决定 Entity 定义和分类
> - [HFB-DAT-0305 Relation Specification](../03-data/0305_Relation_Specification.md) 决定 Relation 定义和分类
> - [ADR-0004 Neo4j](../11-adr/ADR-0004-Neo4j.md)、[ADR-0006 GraphRAG](../11-adr/ADR-0006-GraphRAG.md) 决定 Post-MVP 技术方向
> - **本文档是上述规范的整合视图，不是冲突时的唯一依据。** 冲突以各专项规范为准。
>
> 各阶段实施边界以 [HFB-PS-1709 MVP Implementation Specification](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) 和本文档第九章为准。

---

## 目录

- [第一章 架构总览](#第一章-架构总览)
- [第二章 领域模型](#第二章-领域模型)
- [第三章 模块架构](#第三章-模块架构)
- [第四章 数据库模型](#第四章-数据库模型)
- [第五章 知识图谱模型](#第五章-知识图谱模型)
- [第六章 RAG 流程](#第六章-rag-流程)
- [第七章 AI 服务架构](#第七章-ai-服务架构)
- [第八章 安全与专家审核](#第八章-安全与专家审核)
- [第九章 MVP 切分与演进路线](#第九章-mvp-切分与演进路线)
- [第十章 部署与运维](#第十章-部署与运维)
- [第十一章 架构红线](#第十一章-架构红线)

---

# 第一章 架构总览

## 1.1 技术路线 (目标态)

```
古籍/论文/医案/图片
       ↓
OCR / 文本清洗 / 版本校勘
       ↓
结构化标注
       ↓
实体识别：人物、书名、腧穴、病证、经络、治法、方药  ← Post-MVP
       ↓
关系抽取：引用、传承、病证-腧穴、腧穴-经络、治法-病证  ← Post-MVP
       ↓
知识图谱 (PostgreSQL Source of Truth + Neo4j Read Replica)  ← Neo4j Post-MVP
       ↓
RAG 检索增强 (Text RAG + GraphRAG + Citation RAG)          ← Post-MVP
       ↓
AI科研助手 / 数字人文展示 / 教学问答
```

**当前实际状态（2026-06-30）：** 实体识别、关系抽取、Neo4j、GraphRAG、Citation RAG、Text RAG（pgvector 向量检索）均未实现。当前仓库仅包含 MVP 基础领域模型（Person/Book/Version/Chapter/Passage/Paper/Document/Image + User/Role/Permission）和基于 ILIKE 关键字检索的研究工作流。详见 [第九章 MVP 切分](#第九章-mvp-切分与演进路线)。

## 1.2 六层架构 (目标态)

```
┌─────────────────────────────────────────────────────────┐
│                L1 Presentation                           │
│  Portal │ Admin │ AI Assistant │ Visualization │ Mobile  │
└────────────────────────┬────────────────────────────────┘
                         │         ↑ Port: REST API (JSON)
┌────────────────────────┴────────────────────────────────┐
│                L2 Application                            │
│  REST API Gateway │ Auth │ Workflow │ Export │ Webhook   │
└────────┬───────┬───────┬───────┬───────┬────────────────┘
         │       │       │       │       │
         │  Port: Service interface (domain-level contracts)
         │       │       │       │       │
┌────────┴───────┴───────┴───────┴───────┴────────────────┐
│                L3 Domain                                 │
│  VersionService │ PassageService │ PersonService         │
│  BookService    │ PaperService   │ ReviewService         │
│  ResearchWorkflowService │ ExportService                 │
│                                                          │
│  ⚠ Domain 通过 Port 接口访问 L4/L5，不得直接依赖:        │
│     Neo4j, Elasticsearch, 具体 LLM Provider, OCR engine  │
└────────┬───────┬───────┬───────┬───────┬────────────────┘
         │       │       │       │       │
         │  Port: KnowledgeRepository (abstract)
         │  Port: AIService (abstract)
         │  Port: SearchRepository (abstract)
         │       │       │       │       │
┌────────┴───────┴───────┴───────┴───────┴────────────────┐
│                L4 AI (Post-MVP target)                   │
│  LLM Gateway │ RAG Engine │ GraphRAG │ Citation Engine   │
│  EntityExtractor │ RelationExtractor │ Summarizer        │
│                                                          │
│  Adapts: Anthropic, OpenAI, DeepSeek, Gemini via Gateway │
│  Adapts: pgvector, Neo4j, ES via retrieval adapters      │
└────────┬───────┬───────┬───────┬───────┬────────────────┘
         │       │       │       │       │
         │  Port: VectorStore (abstract)
         │  Port: GraphStore (abstract)
         │  Port: FullTextSearch (abstract)
         │       │       │       │       │
┌────────┴───────┴───────┴───────┴───────┴────────────────┐
│                L5 Knowledge                              │
│  PostgreSQL │ Neo4j (Post-MVP) │ Elasticsearch │ pgvector│
│  MinIO (MVP) │ Redis (MVP)     │                         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────┴────────────────────────────────┐
│                L6 Infrastructure                         │
│  Docker Compose │ CI/CD │ Health │ Backup/Restore       │
│  Logging │ Metrics │ Secrets │ TLS                     │
└─────────────────────────────────────────────────────────┘
```

**架构原则：**

- 上层依赖下层，下层不感知上层
- 每层通过明确定义的接口（Port）通信
- L3 Domain 通过 Port/Adapter 隔离外部技术依赖；不得直接 import Neo4j driver、Elasticsearch client 或 LLM SDK
- 禁止跨层直接访问（Controller → Database）
- **当前实现状态：** L4 AI 层仅提供基础 LLM Gateway（单模型 `AI_MODEL`，httpx 调用，60s timeout，`guard_ai_read` 鉴权）；L5 仅 PostgreSQL + Elasticsearch（无 Neo4j、无 pgvector 扩展启用、Redis/MinIO 已部署）；L6 仅单机 docker-compose.prod.yml（Neo4j 受 post-mvp profile 控制不默认启动）

## 1.3 项目定位

**皇甫谧中医古籍智能研究与数字传承平台**

不做临床诊疗建议。只做学术研究辅助。平台价值在于：把皇甫谧及《针灸甲乙经》的学术知识体系做成可计算、可检索、可追溯、可展示、可辅助研究的数字学术基础设施。

---

# 第二章 领域模型

## 2.1 实体分类体系

遵循 [HFB-DAT-0304 Entity Specification](../03-data/0304_Entity_Specification.md) 的四级分类。以下 "Current" = 代码已有模型，"Planned" = MVP 目标但代码未完成，"Post-MVP" = 超出 MVP 范围。

### 一级实体 (Core Entity, 12 类) — 平台核心研究对象

与 [HFB-DAT-0304 Entity Specification](../03-data/0304_Entity_Specification.md) §3 完全一致。

| #   | 实体            | 状态    | 代码证据                                            |
| --- | --------------- | ------- | --------------------------------------------------- |
| 1   | **Person**      | Current | `apps/backend/app/models/person.py` — `persons`     |
| 2   | **Book**        | Current | `apps/backend/app/models/book.py` — `books`         |
| 3   | **Version**     | Current | `apps/backend/app/models/version.py` — `versions`   |
| 4   | **Chapter**     | Current | `apps/backend/app/models/chapter.py` — `chapters`   |
| 5   | **Passage**     | Current | `apps/backend/app/models/passage.py` — `passages`   |
| 6   | **Paper**       | Current | `apps/backend/app/models/paper.py` — `papers`       |
| 7   | **Image**       | Current | `apps/backend/app/models/image.py` — `images`       |
| 8   | **Institution** | Planned | 无模型文件                                          |
| 9   | **Place**       | Planned | 无模型文件                                          |
| 10  | **Event**       | Planned | 无模型文件                                          |
| 11  | **Dynasty**     | Planned | 无模型文件                                          |
| 12  | **Document**    | Current | `apps/backend/app/models/document.py` — `documents` |

### 二级实体 (Supporting Entity, 7 类) — 辅助研究对象

| 实体         | 状态    |
| ------------ | ------- |
| Publisher    | Planned |
| Collection   | Planned |
| Journal      | Planned |
| Conference   | Planned |
| Project      | Planned |
| Organization | Planned |
| Archive      | Planned |

### 三级实体 (System Entity, 6 类) — 系统运行实体

| 实体       | 状态    | 代码证据                                          |
| ---------- | ------- | ------------------------------------------------- |
| User       | Current | `apps/backend/app/models/user.py` — `users`       |
| Role       | Current | `apps/backend/app/models/user.py` — `roles`       |
| Permission | Current | `apps/backend/app/models/user.py` — `permissions` |
| Attachment | Planned | —                                                 |
| Task       | Planned | —                                                 |
| AuditLog   | Planned | —                                                 |

### 四级实体 (Future Entity, 7 类) — **严禁进入 MVP**

| #   | 实体          | 状态     | HFB-DAT-0304 依据        |
| --- | ------------- | -------- | ------------------------ |
| F1  | **Acupoint**  | Post-MVP | HFB-DAT-0304 §3 四级实体 |
| F2  | **Meridian**  | Post-MVP | HFB-DAT-0304 §3 四级实体 |
| F3  | **Disease**   | Post-MVP | HFB-DAT-0304 §3 四级实体 |
| F4  | **Symptom**   | Post-MVP | HFB-DAT-0304 §3 四级实体 |
| F5  | **Herb**      | Post-MVP | HFB-DAT-0304 §3 四级实体 |
| F6  | **Formula**   | Post-MVP | HFB-DAT-0304 §3 四级实体 |
| F7  | **Treatment** | Post-MVP | HFB-DAT-0304 §3 四级实体 |

**注意：** 任何 HFB-DAT-0304 未列出的实体类型不得纳入本架构。所有四级实体均为 Post-MVP，严禁进入 MVP。

### Bounded Context 划分

| Bounded Context | 拥有的聚合根                    | 公开接口                       | 禁止直接访问                       |
| --------------- | ------------------------------- | ------------------------------ | ---------------------------------- |
| **Versioning**  | Book, Version, Chapter, Passage | VersionService, PassageService | Person 表, Paper 表                |
| **Personnel**   | Person, Institution             | PersonService                  | Book 表, Version 表                |
| **Research**    | Paper, Document, Image          | PaperService, DocumentService  | Passage 直接写                     |
| **Graph**       | EntityRelation（仅 published）  | GraphService                   | 绕过 ReviewService 直接 Publish    |
| **Review**      | Review 队列, AuditLog           | ReviewService                  | 被审核实体的直接写                 |
| **AI**          | LLM 调用, Embedding 请求        | AIGateway Port                 | 跨过 Gateway 直接调 Provider API   |
| **Auth**        | User, Role, Permission          | AuthService                    | 任何 Domain Service 直接查 User 表 |

### Anti-corruption Layer (ACL) 适用边界

| 外部系统                                        | ACL 位置                    | 职责                                              |
| ----------------------------------------------- | --------------------------- | ------------------------------------------------- |
| LLM Provider (Anthropic/OpenAI/DeepSeek/Gemini) | L4 AI Gateway               | 统一请求格式、模型路由、成本追踪、响应校验        |
| OCR Engine (PaddleOCR/Tesseract)                | L4 OCR Adapter              | 标准化输出为 Passage 格式，隔离引擎差异           |
| Neo4j                                           | L5 Graph Adapter (Post-MVP) | PG→Neo4j 同步，Cypher→Domain 对象映射，不可用降级 |
| Elasticsearch                                   | L5 Search Adapter           | PG→ES 索引同步，查询 DSL→Domain Query 映射        |
| External DOI/Paper APIs                         | L4 Paper Adapter            | CrossRef/Semantic Scholar → 内部 Paper Schema     |

## 2.2 核心关系

遵循 [HFB-DAT-0305 Relation Specification](../03-data/0305_Relation_Specification.md) 第四章分类体系。完整批准列表如下。

### 创作关系 (Creation — HFB-DAT-0305 §4.1)

| 关系            | 方向                | 代码状态                               |
| --------------- | ------------------- | -------------------------------------- |
| `authored_by`   | Person→Book         | Planned (graph.py 使用简写 `authored`) |
| `edited_by`     | Person→Book/Version | Planned                                |
| `translated_by` | Person→Book         | Planned                                |
| `compiled_by`   | Person→Book         | Planned                                |
| `annotated_by`  | Person→Book/Passage | Planned                                |

### 结构关系 (Structure — HFB-DAT-0305 §4.2)

| 关系          | 方向                          | 代码状态 |
| ------------- | ----------------------------- | -------- |
| `belongs_to`  | Chapter→Book                  | Planned  |
| `contains`    | Book→Chapter, Chapter→Passage | Planned  |
| `consists_of` | Book→Chapter                  | Planned  |

### 学术关系 (Academic — HFB-DAT-0305 §4.3)

| 关系          | 方向                        | 代码状态                        |
| ------------- | --------------------------- | ------------------------------- |
| `cites`       | Passage→Passage, Paper→Book | Planned                         |
| `comments_on` | Person→Book/Passage         | Planned                         |
| `references`  | Entity→Entity               | Current (graph.py `referenced`) |
| `studies`     | Paper→Person/Book           | Current (graph.py `studied`)    |
| `critiques`   | Paper→Book/Paper            | Planned                         |

### 历史关系 (Historical — HFB-DAT-0305 §4.4)

| 关系             | 方向                  | 代码状态 |
| ---------------- | --------------------- | -------- |
| `occurred_in`    | Event→Dynasty/Place   | Post-MVP |
| `lived_in`       | Person→Place          | Post-MVP |
| `published_in`   | Version→Place/Dynasty | Post-MVP |
| `inherited_from` | Version→Version       | Planned  |

### 地理关系 (Spatial — HFB-DAT-0305 §4.5)

| 关系              | 方向                           | 代码状态 |
| ----------------- | ------------------------------ | -------- |
| `located_in`      | Person/Institution/Event→Place | Post-MVP |
| `originated_from` | Entity→Place                   | Post-MVP |
| `discovered_at`   | Entity→Place                   | Post-MVP |

### 语义关系 (Semantic — HFB-DAT-0305 §4.6)

| 关系            | 方向                     | 代码状态           |
| --------------- | ------------------------ | ------------------ |
| `related_to`    | Entity→Entity            | Current (graph.py) |
| `equivalent_to` | Entity→Entity            | Planned            |
| `influences`    | Person→Person, Book→Book | Post-MVP           |
| `derived_from`  | Entity→Entity            | Post-MVP           |

**代码命名对照：** graph.py 使用简写形式 (`authored`, `studied`, `referenced`)。本文档以 HFB-DAT-0305 批准名称为准。未来代码应迁移至标准名称。

**当前代码支持的 Relation 类型 (graph.py:26-35):** `authored`, `compiled`, `commented_on`, `cited_in`, `studied`, `compared`, `referenced`, `related_to` — 共 8 种。

## 2.3 实体规范约束

- **UUID v7** 唯一标识 — **由应用层生成，不得依赖数据库 `gen_random_uuid()`（PostgreSQL 生成的是 UUID v4）**
- 统一生命周期（Entity）：Draft → Review → Published → Archived → Deprecated
- 统一生命周期（Relation）：Draft → Verified → Published → Deprecated → Archived
- 所有 Entity 天然对应 Graph Node（Node ID = Entity UUID）
- 复杂关系统一进入 Relation 表，禁止在 Entity 表中保存外键关系
- 每个 Entity 必须关联 1:1 Metadata（[HFB-DAT-0304 §10](../03-data/0304_Entity_Specification.md)），禁止孤立 Entity

---

# 第三章 模块架构

## 3.1 模块总图与依赖方向

```
                          ┌──────────────────────┐
                          │    L1 Presentation    │
                          │  Portal │ Admin │ Viz │
                          └──────────┬───────────┘
                                     │ reads via API
                          ┌──────────┴───────────┐
                          │   L2 Application      │
                          │  API Gateway │ Auth   │
                          └──────────┬───────────┘
                                     │ calls
         ┌───────────────────────────┼───────────────────────┐
         ▼                           ▼                       ▼
┌─────────────────┐   ┌──────────────────────┐   ┌──────────────────┐
│  古籍库 (1)      │   │   人物库 (2)          │   │   文献库 (4)      │
│  Bounded:        │   │  Bounded: Personnel  │   │  Bounded: Research│
│  Versioning      │   │                      │   │                  │
│  Owns: Book,     │   │  Owns: Person,       │   │  Owns: Paper,     │
│  Version,        │   │  Institution(planned) │   │  Document, Image  │
│  Chapter,Passage │   │                      │   │                  │
└────────┬─────────┘   └──────────┬───────────┘   └────────┬─────────┘
         │                        │                        │
         │  EntityRelation        │  EntityRelation        │  EntityRelation
         │  (published only)      │  (published only)      │  (published only)
         │                        │                        │
         └────────────────────────┼────────────────────────┘
                                  │
                                  ▼
                    ┌──────────────────────────┐
                    │  知识图谱 (3)              │
                    │  Bounded: Graph           │
                    │  Owns: EntityRelation     │
                    │  (published rows)         │
                    │  + auto-derived FK edges  │
                    │  ⚠ Reads ONLY published   │
                    │  entities from upstream   │
                    └──────────┬───────────────┘
                               │ reads published graph
                               │
         ┌─────────────────────┼──────────────────────┐
         ▼                     ▼                      ▼
┌──────────────────┐ ┌──────────────┐ ┌──────────────────────┐
│ 数字展陈 (7)      │ │AI研究助手(5) │ │  专家工作台 (8)       │
│ Bounded: Display │ │Bounded: AI   │ │  Bounded: Review      │
│ Owns: nothing    │ │Owns: AIResp  │ │  Owns: ReviewQueue,   │
│ Pure read only   │ │              │ │  AuditLog              │
│                  │ │              │ │  ⚠ 唯一发布网关        │
└──────────────────┘ └──────────────┘ └──────────────────────┘

                    ┌──────────────────┐
                    │  教学中心 (6)     │
                    │  Bounded: Learning│
                    │  Owns: Course,Quiz│
                    │  Post-MVP         │
                    └──────────────────┘
```

**关键依赖规则：**

- 古籍库(1)、人物库(2)、文献库(4) 是数据生产者。写入 Entity 和 Relation（status=draft）。
- 专家工作台(8) 是**唯一的发布网关**。所有 status 变更（draft→verified→published）必须经 ReviewService。
- 知识图谱(3) 只读取 Published 状态的 Entity/Relation，不直接写入 Entity 表。
- 数字展陈(7)、AI研究助手(5)、教学中心(6) 为纯消费者，只读取 Published 数据。
- **禁止跨 Context 直接写表**。

## 3.2 八大模块详解

### 模块 1：古籍库 (Book & Version Center)

| 维度                | 内容                                                                                                             |
| ------------------- | ---------------------------------------------------------------------------------------------------------------- |
| **Bounded Context** | Versioning                                                                                                       |
| **拥有的数据**      | Book, Version, Chapter, Passage (status=Draft/Review)                                                            |
| **可调用接口**      | VersionService.get_book(), VersionService.list_versions(), PassageService.get_passage(), CollationService.diff() |
| **禁止直接访问**    | Person 表, Paper 表, EntityRelation 表                                                                           |
| **依赖**            | PostgreSQL（本 Context 的表）                                                                                    |
| **风险**            | ① OCR 质量参差 → 人工校勘比例高；② 多版本对齐复杂 → 先人工标注锚点；③ 繁简转换+异体字 → 需中医专用词表           |
| **当前状态**        | Book/Version/Chapter/Passage 模型+API 已实现；CollationService 接口预留                                          |
| **MVP 目标**        | 《针灸甲乙经》单版本入库 + 章节树 + 段落原文                                                                     |
| **Post-MVP**        | 多版本对照、自动断句标点、OCR 流水线、全文译文                                                                   |

### 模块 2：人物库 (Person & Institution Center)

| 维度                | 内容                                                                               |
| ------------------- | ---------------------------------------------------------------------------------- |
| **Bounded Context** | Personnel                                                                          |
| **拥有的数据**      | Person, Institution (status=Draft/Review)                                          |
| **可调用接口**      | PersonService.get_person(), PersonService.search(), PersonService.list_relations() |
| **禁止直接访问**    | Book 表, Version 表, Passage 表                                                    |
| **依赖**            | PostgreSQL（Person 表）                                                            |
| **风险**            | ① 历史人物信息不完整 → 允许字段为空；② 同人异名 → 依赖 Ontology 消歧               |
| **当前状态**        | Person 模型+CRUD API 已实现；Institution 模型未创建；关系网络图依赖 GraphService   |
| **MVP 目标**        | 皇甫谧 + 前代核心人物（岐伯、黄帝、张仲景）+ 10 位现代关键研究者                   |
| **Post-MVP**        | 全部医家、传承链、学派分析                                                         |

### 模块 3：知识图谱 (Knowledge Graph Engine)

| 维度                | 内容                                                                                                                       |
| ------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| **Bounded Context** | Graph                                                                                                                      |
| **拥有的数据**      | EntityRelation（仅 published 行）+ 查询时计算的自推导 FK 边                                                                |
| **可调用接口**      | GraphService.get_neighbors(), GraphService.find_paths(), GraphService.get_subgraph()                                       |
| **禁止直接访问**    | 直接写 Entity/Relation 表的 status 字段                                                                                    |
| **依赖**            | PostgreSQL（读取 Entity + EntityRelation 表）                                                                              |
| **风险**            | ① MVP 用 PG 邻接表+BFS → 性能上限 ~50K Relation；② 图膨胀 → 严格 entity_type 约束                                          |
| **当前状态**        | GraphService 已实现 PG 邻接表 BFS/DFS 遍历；仅支持 4 种 entity_type `{person, book, version, passage}`，8 种 relation_type |
| **MVP 目标**        | 人物-著作-版本关系图（4 种实体 + 8 种关系）、1-2 hop 遍历                                                                  |
| **Post-MVP**        | Neo4j 全量图 + GraphRAG + 多跳推理                                                                                         |

### 模块 4：文献库 (Paper & Research Center)

| 维度                | 内容                                                                                                                                    |
| ------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| **Bounded Context** | Research                                                                                                                                |
| **拥有的数据**      | Paper, Document, Image                                                                                                                  |
| **可调用接口**      | PaperService.search(), PaperService.get_by_doi()                                                                                        |
| **禁止直接访问**    | Passage 直接写, EntityRelation 直接写                                                                                                   |
| **依赖**            | PostgreSQL, Elasticsearch                                                                                                               |
| **风险**            | ① 论文版权 → 全文通过 DOI 外链，本地仅存元数据+摘要；② 爬取合规 → 使用 CrossRef/Semantic Scholar API                                    |
| **当前状态**        | Paper/Document/Image 模型+ CRUD API 已实现；全文检索使用 SearchService (PostgreSQL ILIKE)，ES 已部署但尚未集成到 SearchService 查询路径 |
| **MVP 目标**        | 100 篇核心论文入库，基础检索+分类                                                                                                       |
| **Post-MVP**        | 自动爬取、研究主题聚类、引文网络分析                                                                                                    |

### 模块 5：AI 研究助手 (AI Research Workspace)

| 维度                | 内容                                                                                                                                                                                           |
| ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Bounded Context** | AI                                                                                                                                                                                             |
| **拥有的数据**      | AI 响应缓存（非知识库数据）                                                                                                                                                                    |
| **可调用接口**      | AIService.chat(), AIService.compare_versions(), AIService.generate_citation()                                                                                                                  |
| **禁止直接访问**    | 直接调 LLM Provider API（必须经 AI Gateway Port）；直接写 Entity/Relation 表                                                                                                                   |
| **依赖**            | AI Gateway (L4 Port), SearchService (MVP 关键字检索)                                                                                                                                           |
| **风险**            | ① LLM 幻觉 → Citation First 强制；② 临床问题 → 意图路由拦截医疗建议；③ Token 成本                                                                                                              |
| **当前状态**        | ai_router 已实现 `/api/v1/ai/chat` (SSE streaming) + `/summarize` + `/translate` + `/compare`；AIService 单模型 HTTP 调用 (httpx, 60s timeout)；API 执行 `guard_ai_read` 鉴权；无 RAG 向量检索 |
| **MVP 目标**        | 基于关键字检索 + LLM 的学术问答 + 自动引文                                                                                                                                                     |
| **Post-MVP**        | Text RAG + GraphRAG + 文献综述/证据链/选题/版本比较                                                                                                                                            |

### 模块 6：教学中心 (Learning Center)

| 状态 | Post-MVP，不建设 |
| ---- | ---------------- |

### 模块 7：数字展陈 (Digital Exhibition)

| 维度                | 内容                                                                          |
| ------------------- | ----------------------------------------------------------------------------- |
| **Bounded Context** | Display（纯消费者）                                                           |
| **风险**            | ① 古地名与 GPS 映射不准 → 手工维护映射表；② 大图渲染 → 后端子图裁剪 ≤200 节点 |
| **当前状态**        | 未实现                                                                        |
| **MVP 目标**        | 皇甫谧生平时间轴 + 著作列表（静态 HTML 呈现）                                 |
| **Post-MVP**        | 交互式知识网络、学术传播地图                                                  |

### 模块 8：专家工作台 (Expert Workbench)

| 维度                | 内容                                                                                         |
| ------------------- | -------------------------------------------------------------------------------------------- |
| **Bounded Context** | Review                                                                                       |
| **拥有的数据**      | ReviewQueue, AuditLog                                                                        |
| **可调用接口**      | ReviewService.submit(), ReviewService.approve(), ReviewService.reject()                      |
| **核心职责**        | **唯一发布网关**：所有 Entity/Relation 的 Draft→Review/Verified→Published 转换必须经过本模块 |
| **禁止**            | Draft 直接 Published（跳过标准流程）；审核人审核自己创建的记录                               |
| **依赖**            | PostgreSQL, RBAC                                                                             |
| **风险**            | ① 审核积压 → 按风险+影响+置信度综合排序；② 专家时间有限                                      |
| **当前状态**        | Entity/Relation 模型有 status 字段，但无 ReviewService 实现；无审核队列 UI                   |
| **MVP 目标**        | 基础状态流转 + 手动纠错                                                                      |
| **Post-MVP**        | 批量审核、校勘工作台、AI 回答评分、质量仪表盘                                                |

---

# 第四章 数据库模型

## 4.1 双存储架构

```
                   ┌──────────────────┐
                   │   PostgreSQL      │  ← Source of Truth (唯一权威写入源)
                   │ (Entity + Relation │
                   │  + Evidence 表)   │
                   └────────┬─────────┘
                            │
                   ┌────────┴─────────┐
                   │  PG Outbox Table  │  ← 事务内原子写入变更事件 (Post-MVP)
                   │  (graph_events)   │     entity_id, version, op, ts
                   └────────┬─────────┘
                            │
                   ┌────────┴─────────┐
                   │  Graph Sync Worker│  ← 消费 outbox 事件 (Post-MVP)
                   │ (Post-MVP only)  │     idempotent UPSERT to Neo4j
                   └────────┬─────────┘
                            │
                   ┌────────┴─────────┐
                   │      Neo4j        │  ← 读优化副本 (Post-MVP)
                   │  (Node + Edge)    │     Node ID = Entity UUID
                   └──────────────────┘
```

**生产契约 (Post-MVP)：**

- PG 事务内通过 `graph_events` outbox 表记录可靠变更事件
- Neo4j UPSERT 必须幂等
- 支持重试、死信、重放、全量重建、差异校验
- Neo4j 不可用时**不得阻塞** PG 权威写入
- 禁止将 LISTEN/NOTIFY 单独作为持久化事件保证
- **当前状态:** Neo4j 未部署（docker-compose.prod.yml 中已定义但 ADR 将其标为 Post-MVP），graph_events 表未创建，Graph Sync Worker 未实现

## 4.2 核心表设计

以下 DDL 为说明性示例，不可直接执行。代码中实际表名见注释。

### base_entity

```sql
-- UUID v7 由应用层生成 (Python: uuid6 或 uuid7 库)
-- 禁止使用 gen_random_uuid() — PG 生成的是 UUID v4
-- 实际表: 无统一 base_entity 表，各实体模型继承 BaseModel (app/db/base.py)
-- 实际用户表: users (apps/backend/app/models/user.py:46)
-- 实际 Metdata 表: 尚未创建
CREATE TABLE base_entity (
    id            UUID PRIMARY KEY,      -- 应用层 UUID v7
    entity_type   VARCHAR(32)  NOT NULL,
    title         VARCHAR(512) NOT NULL,
    description   TEXT,
    status        VARCHAR(16)  NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft','review','published','archived','deprecated')),
    created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
    created_by    UUID REFERENCES users(id),  -- 实际表名: users, 非 "user"
    updated_by    UUID REFERENCES users(id),
    version       INTEGER      NOT NULL DEFAULT 1,
    source_id     UUID,
    metadata_id   UUID NOT NULL REFERENCES metadata(id)  -- metadata 表尚未创建
);
```

### Entity 生命周期约束

```
Entity: Draft → Review → Published → Archived → Deprecated
           ↑                     ↓
           └─── 驳回 ────────────┘  (回到 Draft，不物理删除)

Relation: Draft → Verified → Published → Deprecated → Archived
           ↑                     ↓
           └─── 驳回 ────────────┘  (回到 Draft)

禁止: Draft → Published (跳过 Review/Verified)
禁止: Published → Draft (回退绕过 Archived)
禁止: 审核人审核自己创建的记录 (created_by IS DISTINCT FROM reviewed_by)
驳回: 设置 status='draft'，保留驳回原因。不 DELETE。
```

### relation

```sql
CREATE TABLE relation (
    id            UUID PRIMARY KEY,  -- 应用层 UUID v7
    relation_type VARCHAR(64)  NOT NULL
                  CHECK (relation_type IN (
                    'authored_by','edited_by','translated_by','compiled_by','annotated_by',
                    'belongs_to','contains','consists_of',
                    'cites','comments_on','references','studies','critiques',
                    'occurred_in','lived_in','published_in','inherited_from',
                    'located_in','originated_from','discovered_at',
                    'related_to','equivalent_to','influences','derived_from'
                  )),
    source_id     UUID NOT NULL REFERENCES base_entity(id),
    target_id     UUID NOT NULL REFERENCES base_entity(id),
    confidence    DECIMAL(3,2) NOT NULL DEFAULT 0.0
                  CHECK (confidence >= 0.0 AND confidence <= 1.0),
    status        VARCHAR(16) NOT NULL DEFAULT 'draft'
                  CHECK (status IN ('draft','verified','published','deprecated','archived')),
    created_by    UUID REFERENCES users(id),
    reviewed_by   UUID REFERENCES users(id),
    reviewed_at   TIMESTAMPTZ,   -- 审核通过时间
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    version       INTEGER NOT NULL DEFAULT 1,
    -- 乐观锁: UPDATE WHERE id=? AND version=? SET version=version+1
    -- 冲突时 409 Conflict
    CHECK (created_by IS DISTINCT FROM reviewed_by)
);

CREATE UNIQUE INDEX idx_relation_unique
    ON relation (source_id, target_id, relation_type)
    WHERE status NOT IN ('deprecated', 'archived');
```

### evidence + relation_evidence

```sql
CREATE TABLE evidence (
    id           UUID PRIMARY KEY,
    entity_id    UUID NOT NULL REFERENCES base_entity(id),  -- 外键存在
    source_type  VARCHAR(32) NOT NULL
                 CHECK (source_type IN ('ancient_text','paper','image','inscription','archive','database','manual_annotation')),
    source_id    UUID,
    excerpt      TEXT,
    url          TEXT,
    verified_by  UUID REFERENCES users(id),
    created_at   TIMESTAMPTZ DEFAULT now()
);

-- 多对多: 一个 Relation 可有多条 Evidence
CREATE TABLE relation_evidence (
    relation_id UUID NOT NULL REFERENCES relation(id) ON DELETE CASCADE,
    evidence_id UUID NOT NULL REFERENCES evidence(id) ON DELETE RESTRICT,
    PRIMARY KEY (relation_id, evidence_id)
);

-- 可执行约束: Published Relation 至少一条 Evidence
-- 通过应用层或 BEFORE INSERT/UPDATE 触发器:
-- IF NEW.status = 'published' AND
--    (SELECT count(*) FROM relation_evidence WHERE relation_id = NEW.id) = 0
-- THEN RAISE EXCEPTION 'published relation must have >= 1 evidence';
```

### citation

```sql
CREATE TABLE citation (
    id            UUID PRIMARY KEY,
    label         VARCHAR(256) NOT NULL,
    entity_type   VARCHAR(32),
    entity_id     UUID REFERENCES base_entity(id),  -- 外键存在
    evidence_id   UUID REFERENCES evidence(id),
    format        VARCHAR(16) DEFAULT 'chicago'
                  CHECK (format IN ('chicago','apa','gb7714')),
    full_text     TEXT NOT NULL,
    created_at    TIMESTAMPTZ DEFAULT now()
);
```

### graph_events (PG→Neo4j 同步 Outbox — Post-MVP)

```sql
CREATE TABLE graph_events (
    id          BIGSERIAL PRIMARY KEY,
    entity_id   UUID NOT NULL,
    entity_type VARCHAR(32) NOT NULL,
    op          VARCHAR(8) NOT NULL CHECK (op IN ('upsert','delete','archive')),
    version     INTEGER NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed   BOOLEAN NOT NULL DEFAULT FALSE,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_error  TEXT
);
CREATE INDEX idx_graph_events_pending ON graph_events (processed, occurred_at)
    WHERE processed = FALSE;
```

### Paper 版权策略

- `paper.full_text` 字段在 MVP 阶段**不填充完整论文全文**，仅存储作者/出版者授权的摘要或开放获取内容
- 对非开放获取论文，`full_text` 为 NULL，`abstract` 存储摘要，正文通过 DOI 链接跳转
- pgvector 仅对 `abstract` 建立索引，不索引未授权全文

### Metadata 关联

遵循 [HFB-DAT-0304 §10](../03-data/0304_Entity_Specification.md)：每个 Entity 必须 1:1 关联 Metadata。代码中的 `metadata` 表和 `base_entity.metadata_id` 字段均尚未创建 — 此为 Production Gap。

## 4.3 索引规范

| 表            | 索引 DDL                              | 类型    | 适用查询                           | 建立条件          | 性能指标      |
| ------------- | ------------------------------------- | ------- | ---------------------------------- | ----------------- | ------------- |
| `base_entity` | `(entity_type, status)`               | B-tree  | `WHERE entity_type=? AND status=?` | 始终              | < 1ms         |
| `base_entity` | `title GIN trgm`                      | GIN     | `WHERE title ILIKE '%kw%'`         | 中文搜索启用      | < 50ms @ 100K |
| `passage`     | `(chapter_id, start_pos)`             | B-tree  | 章节+位置定位                      | 始终              | < 1ms         |
| `passage`     | `embedding vector_cosine_ops IVFFlat` | IVFFlat | `ORDER BY embedding <=> $1`        | Post-MVP pgvector | < 20ms @ 100K |
| `paper`       | `doi UNIQUE WHERE doi IS NOT NULL`    | B-tree  | DOI 去重                           | 始终              | < 1ms         |
| `relation`    | `(source_id, relation_type)`          | B-tree  | 图出边遍历                         | 始终              | < 5ms @ 100K  |
| `relation`    | `(target_id, relation_type)`          | B-tree  | 图入边遍历                         | 始终              | < 5ms @ 100K  |
| `evidence`    | `(entity_id, source_type)`            | B-tree  | 证据追溯                           | 始终              | < 5ms         |

### 乐观锁与迁移

- `version` 字段: UPDATE 时 `WHERE id = :id AND version = :expected_version SET version = version + 1`
- 并发冲突: 409 Conflict 或自动重试（≤3次）
- 使用 Alembic 管理迁移；每次迁移含 forward + downgrade
- 数据回填独立于 DDL
- 兼容窗口: 向前至少 2 个迁移版本

---

# 第五章 知识图谱模型

## 5.1 双存储状态

- **MVP (Current):** 无 Neo4j。图查询通过 GraphService 在 PG 邻接表 (entity_relations + version_relations) 直接 BFS/DFS。
- **Post-MVP:** 引入 Neo4j 读副本。同步通过 `graph_events` outbox 表 + Graph Sync Worker。
- **部署现状:** docker-compose.prod.yml 已定义 Neo4j 服务，受 `profiles: [post-mvp]` 控制，默认 MVP 不启动。此配置符合 ADR-0004 Post-MVP 定位。

同步契约（Post-MVP）:

- Node ID = Entity UUID, Edge ID = Relation UUID
- 只同步 `status = 'published'` 且有 RBAC 可见权限的数据
- 增量同步 via `graph_events` outbox
- 删除: op='delete' → DETACH DELETE; 归档: op='archive' → 标记 `archived: true`
- 全量重建: truncate + re-insert all published
- 差异校验: 定期对比 PG vs Neo4j counts

## 5.2 可追溯路径

```
Graph Node (:Entity:Person {id: UUID, status: 'published'})
    │
    └─[:SUPPORTED_BY]→ (:Evidence {source_type, excerpt})
         │
         └─[:CITED_AS]→ (:Citation {label, full_text})
              │
              └→ PG users.created_by, reviewed_by, created_at, reviewed_at
```

## 5.3 Neo4j 节点标签 (Post-MVP 目标 — 与代码和 HFB-DAT-0304 一致)

```cypher
// 文献域 (Current models)
:Entity:Person       {id, name, aliases, birth, death, dynasty, pg_version}
:Entity:Book         {id, title, author, category, dynasty, pg_version}
:Entity:Version      {id, book_id, edition_type, year, pg_version}
:Entity:Chapter      {id, book_id, parent_id, title, order, pg_version}
:Entity:Passage      {id, chapter_id, original_text, pg_version}
:Entity:Document     {id, title, pg_version}

// 学术域 (Current models)
:Entity:Paper        {id, doi, title, year, keywords, pg_version}
:Entity:Image        {id, url, caption, source, license_info, pg_version}

// 学术域 (Planned)
:Entity:Institution  {id, name, type, pg_version}
:Entity:Place        {id, name, geo_code, pg_version}
:Entity:Event        {id, name, date_range, pg_version}
:Entity:Dynasty      {id, name, start_year, end_year, pg_version}

// 中医域 (Post-MVP only — HFB-DAT-0304 四级实体)
:Entity:Acupoint     {id, name, location, pg_version}
:Entity:Meridian     {id, name, category, flow_order, pg_version}
:Entity:Disease      {id, name, category, pg_version}
:Entity:Symptom      {id, name, category, pg_version}
:Entity:Herb         {id, name, category, pg_version}
:Entity:Formula      {id, name, pg_version}
:Entity:Treatment    {id, name, method, pg_version}

// 知识域
:Entity:Evidence     {id, source_type, excerpt, pg_version}
:Entity:Citation     {id, label, full_text, pg_version}
```

## 5.4 边类型 (Post-MVP 目标 — 与 HFB-DAT-0305 完全对齐)

```cypher
// ===== 创作 (HFB-DAT-0305 §4.1) =====
(:Person)-[:AUTHORED_BY]->(:Book)
(:Person)-[:EDITED_BY]->(:Book|Version)
(:Person)-[:TRANSLATED_BY]->(:Book)
(:Person)-[:COMPILED_BY]->(:Book)
(:Person)-[:ANNOTATED_BY]->(:Book|Passage)

// ===== 结构 (HFB-DAT-0305 §4.2) =====
(:Chapter)-[:BELONGS_TO]->(:Book)
(:Book)-[:CONTAINS]->(:Chapter)
(:Chapter)-[:CONTAINS]->(:Passage)
(:Book)-[:CONSISTS_OF]->(:Chapter)

// ===== 学术 (HFB-DAT-0305 §4.3) =====
(:Passage)-[:CITES]->(:Passage)
(:Paper)-[:CITES]->(:Book|Paper)
(:Person)-[:COMMENTS_ON]->(:Book|Passage)
(:Entity)-[:REFERENCES]->(:Entity)
(:Paper)-[:STUDIES]->(:Person|Book)
(:Paper)-[:CRITIQUES]->(:Book|Paper)

// ===== 历史 (HFB-DAT-0305 §4.4) =====
(:Event)-[:OCCURRED_IN]->(:Dynasty|Place)
(:Person)-[:LIVED_IN]->(:Place)
(:Version)-[:PUBLISHED_IN]->(:Place|Dynasty)
(:Version)-[:INHERITED_FROM]->(:Version)

// ===== 地理 (HFB-DAT-0305 §4.5) =====
(:Person|Institution|Event)-[:LOCATED_IN]->(:Place)
(:Entity)-[:ORIGINATED_FROM]->(:Place)
(:Entity)-[:DISCOVERED_AT]->(:Place)

// ===== 语义 (HFB-DAT-0305 §4.6) =====
(:Entity)-[:RELATED_TO]->(:Entity)
(:Entity)-[:EQUIVALENT_TO]->(:Entity)
(:Person|Book)-[:INFLUENCES]->(:Person|Book)
(:Entity)-[:DERIVED_FROM]->(:Entity)

// ===== 版本 (Domain 设计) =====
(:Book)-[:HAS_VERSION]->(:Version)

// ===== 中医 (Post-MVP only — 关系待实体获批后通过 HFB-DAT-0305 审批) =====
(:Acupoint)-[:BELONGS_TO]->(:Meridian)
(:Formula)-[:CONTAINS]->(:Herb)
```

**命名说明：** Cypher 边名使用 SCREAMING_SNAKE_CASE，与 relation_type 的 snake_case 一一对应。命名以 HFB-DAT-0305 批准名为准。graph.py 中使用的简写 (`authored`/`studied`/`referenced`) 将在代码迁移时更新为标准名称。

## 5.5 GraphRAG 检索流程 (Post-MVP 目标)

```
Question → Entity Linking → Subgraph Retrieval (Neo4j, max 3 hops, max 200 nodes)
         → Evidence Ranking → Reasoning (LLM) → Citation → Answer
```

**Graph 永远先于 LLM。**

---

# 第六章 RAG 流程

## 6.1 阶段拆分

| 能力                          | 阶段              | 当前代码状态                                                        |
| ----------------------------- | ----------------- | ------------------------------------------------------------------- |
| 关键字检索 (PostgreSQL ILIKE) | **MVP (Current)** | RAGService → SearchService (ILIKE across entities)                  |
| Elasticsearch 全文检索        | **MVP (Planned)** | ES 已部署 (docker-compose.prod.yml) 但 SearchService 未接入 ES 查询 |
| Text RAG (pgvector 向量)      | **Post-MVP**      | pgvector 扩展未启用                                                 |
| GraphRAG (Neo4j)              | **Post-MVP**      | Neo4j 未部署                                                        |
| Citation RAG (ES+PG)          | **Post-MVP**      | 未实现                                                              |
| Milvus                        | **Post-MVP**      | 未引入                                                              |

**MVP 的"RAG"实为：** 关键字检索 (PostgreSQL ILIKE) + LLM 生成 + 结构化响应。不包含向量语义检索。此边界与 [HFB-ARC-0201](../02-architecture/0201_Technical_Blueprint.md) 第十章和 [HFB-PS-1705](../17-Platform-Specifications/1705_AI_Research_Workspace_Specification.md) 一致。

## 6.2 Text RAG 架构 (Post-MVP 目标)

### 离线索引

- Chunk 策略: 段落级切分（以 Passage 为天然边界），max 512 tokens，overlap 64 tokens
- 父子锚点: chunk 记录 parent passage_id, version_id, chapter_id, char_range
- Embedding: BGE-M3 (1024d, 本地) 或 text-embedding-3-large (3072d, API 备选)；Cosine similarity，存储前 L2 归一化
- 重切分: Passage 原文修改时重新 Embed，增量更新索引版本

### 在线检索

```
Query → Query Rewrite (LLM) → Embedding → pgvector ANN (Top 20)
      → 过滤 status='published' + RBAC
      → BM25 融合 (ES Top 10 合并去重)
      → Reranker (BGE-Reranker-v2) Top 10
      → Context Builder (chunk + citation 绑定)
      → LLM 生成 → Hallucination Detection → Answer
```

### Reranker

- 输入: Query + Top 30 chunks → 输出: Top 10 with scores
- 降级: Reranker 不可用 → 回退为 cosine similarity 排序

## 6.3 Graph Retrieval 约束 (Post-MVP)

- Max hops: 3（可配置），循环检测，max nodes: 200
- RBAC 裁剪在 Neo4j 查询或应用后处理层执行

## 6.4 Citation 验证 (Post-MVP)

- Citation Existence: 解析回答中的 `[来源标记]` → 查 citation 表 → 不存在 → flag "citation_hallucination"
- Claim-Evidence Support: 提取断言 → 向量检索 evidence → 相似度 < 0.7 → flag "unsupported_claim"
- Abstention Gate: Evidence 不足 → 拒答或降级

### Confidence 组成

```
confidence = {
    "citation_verification": 0.0-1.0,  // 引用存在率
    "claim_support": 0.0-1.0,          // 断言-证据支持率
    "source_quality": 0.0-1.0,         // primary > secondary > tertiary
    "overall": "high|medium|low|candidate"  // ≥0.9, 0.7-0.89, 0.5-0.69, <0.5
}
// candidate 级别不返回给用户
```

## 6.5 离线评估指标

| 指标               | 目标   |
| ------------------ | ------ |
| Recall@20          | ≥ 0.90 |
| Citation Precision | ≥ 0.99 |
| Groundedness       | ≥ 0.95 |
| Abstention Rate    | ≥ 0.90 |

## 6.6 对象级权限

所有检索路径（Text RAG, GraphRAG, Citation RAG, ES）必须执行相同权限过滤：

- 仅返回 `status='published'` 的数据
- ACL 检查：用户须有该对象所在工作区的 read 权限
- Redis 缓存 per-user key

---

# 第七章 AI 服务架构

## 7.1 AI Gateway — 当前实现 vs 目标

| 功能        | 当前实现 (代码证据)                                                  | 目标状态 |
| ----------- | -------------------------------------------------------------------- | -------- |
| LLM 调用    | AIService: httpx → OpenAI/Anthropic via `AI_PROVIDER` + `AI_API_KEY` | Current  |
| 鉴权        | `guard_ai_read` (ai.py:101 — `require_permission("ai","read")`)      | Current  |
| 超时        | 60.0s (ai_service.py:179 — `httpx.AsyncClient(timeout=60.0)`)        | Current  |
| 速率限制    | RateLimiter 内存滑动窗口 (ai_service.py:25-40)                       | Current  |
| 模型路由    | 无 — 单模型 `AI_MODEL` 配置                                          | Planned  |
| 成本统计    | 无                                                                   | Planned  |
| 审计日志    | 无                                                                   | Planned  |
| 重试/熔断   | 无自定义重试（仅 httpx 默认连接层行为）                              | Planned  |
| Prompt 管理 | 无版本管理 (Prompt 在代码/Service 中构建)                            | Planned  |

## 7.2 总体拓扑 (目标)

```
                     AI Gateway
  POST /api/v1/ai/chat│限流│鉴权│成本│审计
  POST /api/v1/ai/summarize│translate│compare
         │
    ┌────┴────────────┐
    ▼                 ▼
 Model Router     Prompt Store
(Claude/GPT/      (Git版本管理
 DeepSeek/Gemini)  审批/发布/回滚)
    │                 │
    ▼                 ▼
       LLM Providers
  Anthropic│OpenAI│DeepSeek│Google
```

## 7.3 模型策略三层

| 层级      | 模型                            | 用途             | 部署     | 状态     |
| --------- | ------------------------------- | ---------------- | -------- | -------- |
| 通用 LLM  | Claude / GPT-4o / DeepSeek-V3   | 推理、生成、问答 | API      | Current  |
| Embedding | BGE-M3 / text-embedding-3-large | 向量化           | BGE 本地 | Post-MVP |
| Reranker  | BGE-Reranker-v2                 | 重排序           | 本地     | Post-MVP |
| NER       | bert-base-chinese fine-tuned    | 实体粗筛         | 本地     | Post-MVP |
| OCR       | PaddleOCR / Tesseract           | 古籍识别         | 本地     | Post-MVP |

## 7.4 AI 服务清单

| 服务              | 路由                                | 当前代码                                | 状态            |
| ----------------- | ----------------------------------- | --------------------------------------- | --------------- |
| Chat              | `POST /api/v1/ai/chat`              | ai.py:101 (SSE streaming + RAG context) | Current         |
| Summarize         | `POST /api/v1/ai/summarize`         | ai.py:184                               | Current         |
| Translate         | `POST /api/v1/ai/translate`         | ai.py:196                               | Current         |
| Compare           | `POST /api/v1/ai/compare`           | ai.py:208                               | Current         |
| Citation Generate | —                                   | ai_service.py StructuredResponseBuilder | Current (basic) |
| Entity Extract    | `POST /api/v1/ai/extract/entities`  | 未实现                                  | Post-MVP        |
| Relation Extract  | `POST /api/v1/ai/extract/relations` | 未实现                                  | Post-MVP        |
| Literature Review | `POST /api/v1/ai/review`            | 未实现                                  | Post-MVP        |
| Evidence Chain    | `POST /api/v1/ai/evidence-chain`    | 未实现                                  | Post-MVP        |

**异步 Production Gap:** 标记为"异步"的服务需要持久化任务队列。当前仓库无 Celery/ARQ/Dramatiq。

## 7.5 AI 输出规范

**当前 `StructuredAIResponse` Schema (ai_response.py):**

| 字段            | 当前状态 |
| --------------- | -------- |
| `answer`        | Current  |
| `evidence`      | Current  |
| `citations`     | Current  |
| `graph_context` | Current  |
| `ai_generated`  | Current  |

**目标 Schema (未实现):**

| 字段             | 状态                                           |
| ---------------- | ---------------------------------------------- |
| `model_version`  | Planned — 当前无模型版本追踪                   |
| `prompt_version` | Planned — Prompt 无版本管理                    |
| `generated_at`   | Planned — 生成时间仅从 HTTP response time 推断 |

当前 `StructuredResponseBuilder` 从 RAG chunk 投影 Citation 对象，不执行独立 Citation 查询。不存在独立的 Citation Generate API — 引文生成仅发生在 Chat 响应组装阶段。

---

# 第八章 安全与专家审核

## 8.1 RBAC 资源×动作矩阵 (目标)

| 资源               | 动作            | 角色          | 当前状态                                 |
| ------------------ | --------------- | ------------- | ---------------------------------------- |
| `entity:published` | read            | authenticated | Planned                                  |
| `entity:draft`     | read, write     | editor        | Planned                                  |
| `entity:review`    | approve, reject | reviewer      | Planned                                  |
| `entity:*`         | archive, delete | admin         | Planned                                  |
| `ai:chat`          | use (`ai.read`) | authenticated | **Current** (ai.py:40 — `guard_ai_read`) |
| `ai:summarize`     | use (`ai.read`) | authenticated | **Current**                              |
| `workspace:read`   | use             | authenticated | **Current** (ai.py:41)                   |
| `workspace:create` | use             | authenticated | **Current** (ai.py:42)                   |
| `export`           | execute         | editor        | Planned                                  |

**职责分离:**

- `editor` 创建 Entity/Relation (status=draft)，**不能**审核自己的记录
- `reviewer` 审核并推进到 Published，**不能**创建 Entity
- 同一人不得同时持有 editor + reviewer

## 8.2 对象级权限

权限粒度覆盖：

- **PostgreSQL**: Repository 层过滤 `status='published' OR created_by=current_user`
- **Elasticsearch**: 查询时附加 `status:published` filter
- **Neo4j (Post-MVP)**: Cypher 附加 `WHERE n.pg_status='published'`
- **AI Context**: 组装 Prompt 时仅注入有权限的 chunk/citation

## 8.3 专家校审闭环

```
AI 抽取 (status=draft, confidence=auto, created_by=system)
        │
        ▼
┌───────────────────┐
│ 审核队列排序       │  排序: 风险(40%) + 影响(30%) + 置信度(20%) + 时效(10%)
│ (Expert Workbench) │
└────────┬──────────┘
         │
    ┌────┴────┐
    ▼         ▼
 通过        驳回
    │         │
    ▼         ▼
[Entity: status='review' → 二次确认 → 'published']
[Relation: status='verified' → 'published']
              │
              └── status='draft' + 驳回原因 + reviewed_by + reviewed_at
                 (禁止 DELETE)
    │
    ├──→ 更新 PG + reviewed_by + reviewed_at
    ├──→ graph_events outbox (Post-MVP)
    ├──→ 可用于检索
    └──→ 用户反馈 → 重新进入队列
```

**关键区别：** Entity 使用 Draft→Review→Published（HFB-DAT-0304）；Relation 使用 Draft→Verified→Published（HFB-DAT-0305 §5）。

**审核约束：**

- 不得 Draft → Published（跳过中间状态）
- 审核人 ≠ 创建人 (`created_by IS DISTINCT FROM reviewed_by`)
- 驳回保留原记录，不 DELETE
- 审核操作写入 AuditLog（操作人、时间、前后值、驳回原因）

## 8.4 不可篡改业务审计

审计日志（与请求访问日志分离）：

| 字段               | 内容                                                                        |
| ------------------ | --------------------------------------------------------------------------- |
| `operation`        | CREATE / UPDATE / REVIEW / APPROVE / REJECT / PUBLISH / DEPRECATE / ARCHIVE |
| `actor_id`         | 操作人 UUID                                                                 |
| `target_type`      | entity / relation / evidence / citation                                     |
| `target_id`        | 目标 UUID                                                                   |
| `before_state`     | 变更前 JSON snapshot                                                        |
| `after_state`      | 变更后 JSON snapshot                                                        |
| `evidence_changes` | Evidence 关联变更                                                           |
| `prompt_version`   | AI 操作时的 Prompt 版本                                                     |
| `model_version`    | AI 操作时的 Model 版本                                                      |
| `occurred_at`      | server-generated timestamp                                                  |

业务审计日志不可修改或删除。保留期 ≥ 5 年。

---

# 第九章 MVP 切分与演进路线

## 9.1 规范依据

MVP 严格以 [HFB-ARC-0201 Technical Blueprint](../02-architecture/0201_Technical_Blueprint.md) 第十六章和 [HFB-PS-1709 MVP Implementation Specification](../17-Platform-Specifications/1709_MVP_Implementation_Specification.md) 为边界。

## 9.2 MVP 建设清单与验收条件

| #   | 能力                           | 可测验收条件                                         | 当前代码状态                                 |
| --- | ------------------------------ | ---------------------------------------------------- | -------------------------------------------- |
| 1   | **《针灸甲乙经》结构化入库**   | 章节树入库；Passage 含 original_text；可全文检索     | Book/Version/Chapter/Passage 模型+API 已实现 |
| 2   | **皇甫谧人物资料库**           | Person CRUD 完整；关联 ≥3 Book Record；生平时间轴    | Person 模型+API 已实现；时间轴未实现         |
| 3   | **人物-著作-版本知识图谱**     | 1-hop traversal 返回正确节点；Relation 可查 Evidence | GraphService BFS 已实现；Evidence 表未创建   |
| 4   | **学术问答（关键字检索+LLM）** | 回答含 Citation；Citation 对应真实 Passage           | ai_router `/chat` 已实现；Evidence gate 生效 |
| 5   | **皇甫谧学术思想专题页**       | 静态页面展示生平+著作列表；可点击至详情              | Frontend Portal 组件未实现                   |

## 9.3 MVP 不建设范围 (禁止建设)

- **Future Entity (7 类):** Acupoint, Meridian, Disease, Symptom, Herb, Formula, Treatment
- **TheoryConcept:** 不在 HFB-DAT-0304 批准列表中
- **Neo4j:** 禁止在 MVP 部署和实现 — ADR-0004 明确标为 Post-MVP
- **GraphRAG:** 禁止在 MVP 实现 — ADR-0006 标为 Post-MVP
- **Milvus:** 禁止在 MVP 引入 — ADR-0007 标为 Post-MVP
- **Text RAG (pgvector 向量检索):** 禁止在 MVP — pgvector 扩展未启用
- **异步任务队列:** 不得引入 Celery/ARQ 等
- **教学中心、数字展陈全量功能**

## 9.4 三阶段对照

| 层       | MVP (Current + Planned)                                                                                     | Phase 2                                                          | Phase 3            |
| -------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------ |
| **数据** | Person, Book, Version, Chapter, Passage, Paper, Image, Document + Place/Event/Institution/Dynasty (Planned) | + Acupoint, Meridian, Disease, Symptom, Herb, Formula, Treatment | 全文翻译, 自动 OCR |
| **存储** | PostgreSQL + Elasticsearch + Redis + MinIO                                                                  | + pgvector 向量检索 + Neo4j + GraphRAG                           | + Milvus           |
| **图谱** | PG 邻接表 (GraphService BFS)                                                                                | pgvector + Neo4j + GraphRAG                                      | 多跳推理           |
| **RAG**  | 关键字检索 (PostgreSQL ILIKE)                                                                               | Text RAG + GraphRAG + Citation RAG                               | Multi-hop          |
| **AI**   | LLM GW (单模型) + 引文                                                                                      | + 文献综述/证据链/选题                                           | Multi-Agent        |

## 9.5 Phase 2 触发条件

以下**全部**满足后，经 Project Steering Committee 批准方可启动：

1. **MVP 验收通过** — 所有 5 项 MVP 能力满足验收条件
2. **数据与权限正确** — 所有 Published Entity 有 Metadata；所有 Published Relation 有 ≥1 Evidence；RBAC 生效
3. **性能数据证明需要 Neo4j** — GraphService 2-hop query > 500ms 或 EntityRelation > 50K
4. **ADR 升级** — ADR-0004 (Neo4j) + ADR-0006 (GraphRAG) 从 Post-MVP 升级为 Active；Chief Architect 批准
5. **运维就绪** — Neo4j 部署/备份/恢复/监控方案就绪

---

# 第十章 部署与运维

> **当前 docker-compose.prod.yml 是单机部署资产。以下 "Current" 对应代码中存在的内容，"Production Gap" 为上线前必须补齐。**

## 10.1 当前部署拓扑

```
Docker Host (单机)
  ├── backend (Dockerfile.backend, :8000)
  ├── frontend (Dockerfile.frontend, :80)
  ├── postgres (pgvector/pg16, :5432)
  ├── redis (redis:7-alpine, :6379)         ← MVP
  ├── minio (minio/minio, :9000/:9001)      ← MVP
  ├── elasticsearch (8.17.0, :9200)
  └── neo4j (neo4j:5, :7687)               ← 已定义，profiles: [post-mvp]
```

## 10.2 阶段合规说明

部署资产当前状态：Redis 和 MinIO 已在生产 Compose 中定义（MVP 服务），Neo4j 已定义但受 `profiles: [post-mvp]` 控制。默认 `docker compose up` 不启动 Neo4j。`docker compose --profile post-mvp up` 包含所有服务。

## 10.3 健康检查与降级

| 端点          | 内容                                                          | 状态                    |
| ------------- | ------------------------------------------------------------- | ----------------------- |
| `GET /health` | 进程存活                                                      | Current (api/health.py) |
| `GET /ready`  | 依赖检查 (PG/Redis/ES/MinIO)，任一必需服务不健康返回 HTTP 503 | Current (api/ready.py)  |
| PG 不可用     | 返回 503                                                      | Current                 |
| ES 不可用     | 降级为 PG ILIKE                                               | Current                 |
| Neo4j 不可用  | 降级为 PG 邻接表                                              | Post-MVP                |

## 10.4 备份恢复

| 组件  | 方式                              | RPO    | RTO    | 状态                                                       |
| ----- | --------------------------------- | ------ | ------ | ---------------------------------------------------------- |
| PG    | pg_dump (手动, scripts/backup.sh) | 未达标 | 未达标 | Current (backup.sh — 手动执行，未验证恢复，无定时，无 WAL) |
| ES    | Snapshot to MinIO                 | < 1h   | < 2h   | Production Gap                                             |
| Neo4j | neo4j-admin dump                  | < 1h   | < 2h   | Post-MVP                                                   |

## 10.5 单点故障清单

| 组件                   | 影响           | 缓解                         | 状态                        |
| ---------------------- | -------------- | ---------------------------- | --------------------------- |
| PostgreSQL (单节点)    | 全站不可写     | WAL backup + 从库 (Post-MVP) | **Single Point**            |
| Elasticsearch (单节点) | 全文降级 ILIKE | ES Cluster (Post-MVP)        | **Degradable**              |
| Docker Host            | 全站不可用     | Swarm/K8s (Post-MVP)         | **Single Point**            |
| Neo4j (单节点)         | 图降级 PG      | Enterprise (Post-MVP)        | **Single Point** (Post-MVP) |

## 10.6 容量门槛

| 指标      | MVP 目标          | 测试             |
| --------- | ----------------- | ---------------- |
| 并发 API  | ≥ 50 req/s        | k6/Locust        |
| P95 延迟  | < 500ms (不含 AI) | k6/Locust        |
| PG 连接池 | 20, no exhaustion | pg_stat_activity |

---

# 第十一章 架构红线

## 11.1 红线与执行控制

| #   | 红线                            | 执行控制                                                    |
| --- | ------------------------------- | ----------------------------------------------------------- |
| 1   | 无来源关系进入知识图谱          | DB: relation_evidence FK + app 层 publish 前检查            |
| 2   | AI 编造节点/关系                | Runtime: AI 抽取 status=draft, 不自动 publish               |
| 3   | AI 直接修改正式知识库           | API: AI Service 无权调用 ReviewService.approve()            |
| 4   | AI 回答不附出处                 | Runtime: StructuredResponseBuilder evidence gate            |
| 5   | 无证据推理                      | Runtime: evidence context 为空时拒答 (ai.py:148)            |
| 6   | 删除 Evidence/Citation          | DB: ON DELETE RESTRICT                                      |
| 7   | 绕过 AI Gateway 调 Provider API | CI: import check — 业务模块不得 import openai/anthropic SDK |
| 8   | Prompt 硬编码                   | CI: 扫描裸 LLM prompt 字符串                                |
| 9   | 跨层直接访问                    | CI: import lint — api/ 不得 import models/                  |
| 10  | Controller 业务逻辑             | Code Review (责任人: Tech Lead)                             |
| 11  | 跳阶段开发                      | Release Gate (责任人: Chief Architect)                      |
| 12  | Draft 直接 Published            | DB: CHECK status + app 状态机                               |
| 13  | 审核人审自己                    | DB: CHECK (created_by IS DISTINCT FROM reviewed_by)         |
| 14  | 驳回物理删除                    | App: reject → UPDATE status='draft'，不 DELETE              |
| 15  | Future Entity 进入 MVP          | DB: 禁止创建四级实体表；CI: schema diff vs HFB-DAT-0304     |
| 16  | Neo4j/GraphRAG/Milvus 进入 MVP  | CI: requirements 依赖检查；Release Gate: 架构审计           |

## 11.2 无法自动执行的红线

| 红线                | 责任人             | 验收证据                     |
| ------------------- | ------------------ | ---------------------------- |
| Controller 业务逻辑 | Tech Lead          | Code Review records          |
| 跳阶段开发          | Chief Architect    | ADR status + Sprint Planning |
| Prompt 版本管理     | AI Lead            | Prompt Store Git history     |
| 版权合规            | Academic Committee | Per-source license review    |

---

# 附录 A：风险声明

以下风险尚存，且无工程证据证明已解决：

| #   | 风险                            | 严重   | 状态     |
| --- | ------------------------------- | ------ | -------- |
| R1  | PG↔Neo4j 数据漂移 (Post-MVP)    | High   | **Open** |
| R2  | Neo4j Community 单点 (Post-MVP) | Medium | **Open** |
| R3  | PostgreSQL 单点                 | High   | **Open** |
| R4  | ES 索引陈旧                     | Medium | **Open** |
| R5  | Graph/RAG/Citation 权限不一致   | High   | **Open** |
| R6  | 自研 GraphRAG 维护成本          | Medium | **Open** |
| R7  | 专家审核积压                    | High   | **Open** |
| R8  | LLM/OCR/NER 模型漂移            | Medium | **Open** |
| R9  | 论文全文版权                    | Medium | **Open** |
| R10 | Neo4j Community 单点 (Post-MVP) | Medium | **Open** |

---

# 附录 B：术语对齐

| 本文档        | CONTEXT.md                      |
| ------------- | ------------------------------- |
| AI 研究助手   | AI-assisted Scholarly Research  |
| 证据          | Evidence                        |
| 引文          | Citation                        |
| 校勘          | Version Comparison              |
| 审核 (Entity) | Review (Draft→Review→Published) |

---

## 修订记录

| Version | Date       | Description                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1.2.0   | 2026-06-30 | **Compose / Readiness / 文档事实同步:** (1) Compose MVP Backend 完整连接矩阵 (PG/Redis/MinIO/ES 显式变量 + `:?` 必填)；Backend depends_on 四项 service_healthy；Redis 密码容器环境变量 + REDISCLI_AUTH healthcheck；Neo4j post-mvp profile；(2) Readiness REQUIRED_SERVICES 扩充至四项；统一 required_healthy 驱动 HTTP 状态/success/ready/message；参数化测试覆盖每项失败+缺失+全部健康+脱敏；(3) 文档全局替换 MVP 存储为 PostgreSQL+ES+Redis+MinIO；Phase 2 引入 pgvector+Neo4j；更新部署拓扑、阶段合规说明、L5 当前状态、RAG 关键字描述、Phase 2 触发条件 |
| 1.1.0   | 2026-06-30 | **P0 标准对齐修订 (第二轮):** (1) 移除越权 0202 文件及索引变更；(2) 移除不合规 TheoryConcept；(3) 实体分类完全对齐 HFB-DAT-0304（7 类 Future Entity, 非 8 类）；(4) 关系清单补全 HFB-DAT-0305 缺失类型；(5) 修正 Current 声明；(6) 修正生命周期；(7) 修正 SQL 引用完整性；(8) 标注部署阶段冲突；(9) 区分 Current/Planned/Post-MVP/Production Gap                                                                                                                                                                                                             |
| 1.0.0   | 2026-06-30 | 首版发布                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
