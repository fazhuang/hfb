---
title: Sprint 0 — Engineering Initialization Plan
document_id: HFB-ENG-SPRINT-00
version: 1.0.0
status: Draft
owner: Lead Engineering Team
based_on: HFB-ARC-0203 System Architecture v1.2.0
effective_date: 2026-06-30
scope: Foundation building — no feature development
---

# Sprint 0 — Engineering Initialization Plan

> 本文档将已批准的系统架构（HFB-ARC-0203 v1.2.0）转化为可执行工程计划。
> 不修改架构、不扩展范围、不新增模块。

---

## 1. Repository Structure

### 1.1 Current State (pre-Sprint-0)

```
hfb/
├── apps/
│   ├── backend/            # FastAPI monolith
│   │   ├── app/
│   │   │   ├── api/        # v1/ 路由层 (ai, auth, dashboard, entities,
│   │   │   │               #   graph, research, search, users, version_center)
│   │   │   ├── core/       # config, logging, security
│   │   │   ├── db/         # base model, database, migrations
│   │   │   ├── middleware/ # auth, cors
│   │   │   ├── models/     # SQLAlchemy ORM (12 files)
│   │   │   ├── repositories/
│   │   │   ├── schemas/    # Pydantic DTO (ai_response, graph, search, ...)
│   │   │   ├── services/   # Business logic (14 files)
│   │   │   ├── startup/    # Infrastructure checks
│   │   │   └── utils/
│   │   └── main.py
│   └── frontend/           # Vue 3 + Vite
│       ├── src/
│       └── public/
├── packages/               # Shared monorepo packages
│   ├── config/
│   ├── types/
│   ├── ui/
│   └── utils/
├── docker/                 # Dockerfiles + nginx conf
│   ├── compose/
│   ├── dev/
│   └── prod/
├── tests/
│   ├── unit/               # 21 test files
│   ├── integration/
│   ├── e2e/
│   └── fixtures/
├── scripts/                # backup, dev, lint, test, ...
├── docs/                   # Governance, specs, ADR, architecture
├── tools/                  # hgt utility
├── deploy/
├── infra/                  # Empty (.gitkeep only)
├── .github/workflows/      # CI: build, docs, lint, security, test
├── docker-compose.prod.yml # Production compose (recently aligned)
├── docker-compose.dev.yml  # Development compose
└── pyproject.toml
```

### 1.2 Target State (post-Sprint-0)

```
hfb/
├── apps/
│   ├── backend/
│   │   ├── app/
│   │   │   ├── api/
│   │   │   │   └── v1/              # ✅ Existing, re-audit
│   │   │   │       ├── ai.py        # ✅ Current
│   │   │   │       ├── entities.py  # ✅ Current
│   │   │   │       ├── graph.py     # ✅ Current
│   │   │   │       ├── search.py    # ✅ Current
│   │   │   │       └── ...
│   │   │   ├── ports/               # 🆕 Abstract interfaces (Port/Adapter)
│   │   │   │   ├── __init__.py
│   │   │   │   ├── knowledge_repository.py
│   │   │   │   ├── ai_service.py
│   │   │   │   └── search_repository.py
│   │   │   ├── adapters/            # 🆕 Adapter implementations
│   │   │   │   ├── __init__.py
│   │   │   │   ├── pg_knowledge.py
│   │   │   │   ├── llm_gateway.py
│   │   │   │   └── pg_search.py
│   │   │   ├── core/
│   │   │   │   ├── config.py        # 🔧 Add: audit section, model registry
│   │   │   │   ├── logging.py       # 🔧 Add: request_id propagation
│   │   │   │   ├── error_handlers.py# 🆕 Unified exception → API response
│   │   │   │   └── security.py      # ✅ Existing
│   │   │   ├── db/
│   │   │   │   ├── audit_mixin.py   # 🆕 Created_by/at + Updated_by/at mixin
│   │   │   │   └── migrations/
│   │   │   │       └── versions/    # 🔧 Add: metadata, audit_log tables
│   │   │   ├── models/              # ✅ Existing, re-audit status fields
│   │   │   ├── middleware/
│   │   │   │   ├── auth.py          # ✅ Existing
│   │   │   │   ├── request_id.py    # 🆕 X-Request-ID injection
│   │   │   │   └── audit_logger.py  # 🆕 Request access logging
│   │   │   ├── schemas/             # ✅ Existing
│   │   │   ├── services/            # ✅ Existing, re-audit boundaries
│   │   │   └── startup/             # ✅ Existing (health checks)
│   │   └── main.py                  # 🔧 Register new middleware, routers
│   └── frontend/                    # No Sprint-0 changes
├── services/                        # 🆕 Future service stubs (empty)
│   └── .gitkeep
├── knowledge_graph/                 # 🆕 Future service stubs (empty)
│   └── .gitkeep
├── rag/                             # 🆕 Future service stubs (empty)
│   └── .gitkeep
├── ai_pipeline/                     # 🆕 Future service stubs (empty)
│   └── .gitkeep
├── tests/                           # ✅ Existing
│   └── unit/
│       ├── test_audit.py            # 🆕
│       ├── test_error_handlers.py   # 🆕
│       └── test_config.py           # 🔧 Expand
├── docs/
│   └── superpowers/
│       └── plans/
│           └── 2026-06-30-sprint-0-engineering-init.md  # 🆕 This document
├── docker-compose.prod.yml          # ✅ Aligned
├── pyproject.toml                   # 🔧 Add: uuid6, structlog deps
└── .env.example                     # 🔧 Add: all new env vars
```

### 1.3 New Module Definitions

| Path               | Responsibility                                                                     | Module Boundary                                  | Dependency Rules                                                |
| ------------------ | ---------------------------------------------------------------------------------- | ------------------------------------------------ | --------------------------------------------------------------- |
| `app/ports/`       | Abstract interfaces (Protocol/ABC) for L3→L4 and L3→L5 communication               | Pure Python, no framework imports, no DB imports | Imported by services and adapters. Never imports from adapters. |
| `app/adapters/`    | Concrete implementations of ports — LLM Gateway, PG Knowledge repo, PG Search repo | May import httpx, SQLAlchemy, elasticsearch      | Implements ports. Never imported by domain services directly.   |
| `services/`        | Future independent service stubs (Post-MVP)                                        | Empty now, `.gitkeep` only                       | No import from apps/                                            |
| `knowledge_graph/` | Future Neo4j sync worker stubs (Post-MVP)                                          | Empty now                                        | Post-MVP only                                                   |
| `rag/`             | Future RAG engine stubs (Post-MVP)                                                 | Empty now                                        | Post-MVP only                                                   |
| `ai_pipeline/`     | Future AI pipeline stubs (Post-MVP)                                                | Empty now                                        | Post-MVP only                                                   |

---

## 2. Backend Initialization Blueprint

### 2.1 Config System Audit

Current `apps/backend/app/core/config.py` uses Pydantic `BaseSettings`. Required additions:

```
[config.py]
├── [project]       ✅ PROJECT_NAME, VERSION, ENVIRONMENT, DEBUG, LOG_LEVEL
├── [backend]       ✅ HOST, PORT, WORKERS, SECRET_KEY, CORS_ORIGINS
├── [postgres]      ✅ HOST, PORT, DB, USER, PASSWORD
├── [redis]         ✅ HOST, PORT, DB, PASSWORD
├── [minio]         ✅ HOST, PORT, ROOT_USER, ROOT_PASSWORD, BUCKET
├── [elasticsearch] ✅ HOST, PORT
├── [jwt]           ✅ SECRET_KEY, ALGORITHM, EXPIRE_MINUTES
├── [neo4j]         ✅ Commented out (Post-MVP)
├── [ai/llm]        ✅ PROVIDER, API_KEY, MODEL, EMBEDDING_MODEL,
│                       BASE_URL, MAX_TOKENS, TEMPERATURE, RATE_LIMIT
├── [audit]         🆕 AUDIT_RETENTION_DAYS, AUDIT_ENABLED
├── [backup]        ✅ BACKUP_DIR, BACKUP_RETENTION_DAYS (env)
└── [properties]    ✅ database_url, redis_url, minio_url,
                        elasticsearch_url, cors_origins_list
```

### 2.2 API Gateway Structure

```
/api/v1/
├── /auth           # POST login, POST register, GET me — ✅ Existing
├── /entities       # CRUD generic entities — ✅ Existing
├── /ai             # POST chat, summarize, translate, compare — ✅ Existing
├── /search         # POST search — ✅ Existing
├── /graph          # GET neighbors, paths, subgraph — ✅ Existing
├── /workspace      # CRUD sessions, notes — ✅ Existing
├── /version-center # Version comparison — ✅ Existing
├── /dashboard      # Admin dashboard — ✅ Existing
├── /users          # User management — ✅ Existing
├── /health         # GET health — ✅ Existing
├── /ready          # GET readiness — ✅ Existing (recently aligned)
├── /version        # GET version info — ✅ Existing
├── /live           # GET liveness — ✅ Existing
└── /config         # GET public config — ✅ Existing
```

**Sprint-0 audit tasks:**

- Verify all routes return unified `{success, timestamp, data, message}` envelope
- Verify all routes have appropriate `require_permission` guards
- Verify error responses go through unified exception handlers (not individual try/except in controllers)

### 2.3 Auth & RBAC Skeleton

Current state: `User`, `Role`, `Permission` models exist. `require_permission(resource, action)` decorator works for AI and Workspace routes.

**Sprint-0 additions:**

- No new RBAC features. Re-audit existing guards.
- Add `X-Request-ID` middleware for trace propagation.
- Add request access log middleware (method, path, status, user_id, duration_ms).

### 2.4 Logging System

Current: `app/core/logging.py` — basic logger.

**Sprint-0 upgrades:**

1. Structured JSON logging (logfmt or JSON lines)
2. Every log line includes: `request_id`, `user_id`, `timestamp`, `level`, `message`
3. `request_id` propagation: inbound HTTP header → context variable → outbound (to PG/ES/AI)
4. Log levels: DEBUG (dev), INFO (prod default), WARNING, ERROR, CRITICAL

### 2.5 Audit System

Two distinct audit streams (per HFB-ARC-0203 §8.4):

| Stream             | Purpose                                                           | Retention | Immutable |
| ------------------ | ----------------------------------------------------------------- | --------- | --------- |
| Request Access Log | HTTP access log (method, path, status, user_id, duration)         | 90 days   | No        |
| Business Audit Log | Entity/Relation lifecycle changes (CREATE, REVIEW, PUBLISH, etc.) | ≥ 5 years | Yes       |

**Sprint-0 implementation:**

1. `AuditMixin` base class: `created_by`, `created_at`, `updated_by`, `updated_at` — add to all models lacking it
2. `BusinessAuditLog` model and migration
3. Request access logging middleware (separate from business audit)

### 2.6 Unified Error Handling

**Sprint-0 implementation:**

```python
# app/core/error_handlers.py — register on FastAPI app

# Exception → HTTP Status mapping:
#   ValidationError      → 422
#   PermissionError      → 403
#   EntityNotFoundError  → 404
#   ConflictError        → 409 (optimistic lock)
#   RateLimitError       → 429
#   AIProviderError      → 502
#   DatabaseError        → 503
#   Exception            → 500 (catch-all)

# All responses use the unified envelope:
#   {"success": false, "timestamp": "...", "data": null, "message": "..."}
```

---

## 3. Database Initialization Strategy

### 3.1 Schema Bootstrap Order

| Order | Table(s)                                                                     | Status      | Migration                                  |
| ----- | ---------------------------------------------------------------------------- | ----------- | ------------------------------------------ |
| 1     | `users`, `roles`, `permissions`, `user_roles`                                | ✅ Existing | `221e630d3f7b`                             |
| 2     | `persons`, `books`, `versions`, `chapters`, `passages`                       | ✅ Existing | Same                                       |
| 3     | `papers`, `images`, `documents`                                              | ✅ Existing | Same                                       |
| 4     | `entity_relations`, `version_relations`, `passage_mappings`, `version_diffs` | ✅ Existing | Same                                       |
| 5     | `research_sessions`, `research_notes`                                        | ✅ Existing | Same                                       |
| 6     | `metadata`                                                                   | 🆕          | New migration: `create_metadata_table`     |
| 7     | `evidence`, `relation_evidence`, `citation`                                  | 🆕          | New migration: `create_evidence_tables`    |
| 8     | `business_audit_log`                                                         | 🆕          | New migration: `create_audit_log_table`    |
| 9     | `review_queue`                                                               | 🆕          | New migration: `create_review_queue_table` |
| 10    | `graph_events`                                                               | 🆕 Post-MVP | Deferred per ADR-0004/0006                 |

### 3.2 Neo4j Initialization Strategy (Post-MVP)

- Not in Sprint-0.
- When triggered (Phase 2): deploy via docker-compose `--profile post-mvp`
- Initial load: bulk upsert from PG published entities via `graph_events` replay
- Schema: see HFB-ARC-0203 §5.3–5.4 for node labels and edge types

### 3.3 Migration Sequence

```
# Generate only after models are stable:
alembic revision --autogenerate -m "create_metadata_table"
alembic revision --autogenerate -m "create_evidence_tables"
alembic revision --autogenerate -m "create_audit_log_table"
alembic revision --autogenerate -m "create_review_queue_table"

# Apply:
alembic upgrade head
```

### 3.4 Seed Data Strategy

**EMPTY SAFE SEED ONLY** — no production data in migrations.

| Seed          | Content                                                       | When               |
| ------------- | ------------------------------------------------------------- | ------------------ |
| `roles`       | admin, editor, reviewer — fixed system roles                  | Migration seed     |
| `permissions` | ai.read, workspace.read, workspace.create — fixed permissions | Migration seed     |
| `users`       | Single admin user from env vars (ADMIN_EMAIL, ADMIN_PASSWORD) | Migration seed     |
| Domain data   | NO seed — loaded via admin API after deployment               | Never in migration |

---

## 4. AI Pipeline Skeleton Design

### 4.1 OCR Pipeline (Post-MVP)

```
Input: scanned_image (JPEG/PNG/TIFF, from MinIO)
   │
   ▼
Process:
   1. Pre-process (deskew, denoise, binarize)
   2. PaddleOCR → raw text + bounding boxes
   3. Post-process (line merge, column detection for classical layout)
   4. Store: Passage.original_text + metadata (confidence, char_positions)
   │
   ▼
Output: Passage {original_text, ocr_confidence, page_number, line_positions}
```

**MVP status:** NOT implemented. OCR pipeline skeleton only — no code.

### 4.2 NER Pipeline (Post-MVP)

```
Input: Passage.original_text (normalized classical Chinese)
   │
   ▼
Process:
   1. Text pre-processing (traditional→simplified, variant normalization)
   2. Local NER (bert-base-chinese fine-tuned on TCM corpus)
      → Candidate Entity list [{name, type, position, confidence}]
   3. LLM refinement (Claude/GPT)
      → Disambiguated Entity list [{name, type, attributes, evidence_excerpt}]
   4. Dedup check against existing Entities (exact name + type match)
   │
   ▼
Output: CandidateEntity[] (status=draft, confidence, source_passage_id)
```

**MVP status:** NOT implemented. Skeleton only.

### 4.3 Relation Extraction Pipeline (Post-MVP)

```
Input: Entity pairs within the same Passage + full Passage text
   │
   ▼
Process:
   1. Entity pair candidate generation (co-occurrence within window)
   2. LLM relation classification
      Prompt: "Given these entities [A, B] in context [passage],
               what relation from [approved list] exists, if any?
               Output: {relation_type, confidence, evidence_excerpt}"
   3. Dedup against existing Relations (same source+target+type)
   │
   ▼
Output: CandidateRelation[] (status=draft, confidence, evidence_excerpt)
```

**MVP status:** NOT implemented. Skeleton only.

### 4.4 Graph Builder Pipeline (Post-MVP)

```
Input: Published Entity[] + Published Relation[]
   │
   ▼
Process:
   1. Query PG for all status='published' entities and relations
   2. Transform to Neo4j UPSERT statements
   3. Write to graph_events outbox (op='upsert')
   4. Graph Sync Worker consumes events → Neo4j
   │
   ▼
Output: Neo4j nodes + edges updated
```

**MVP status:** NOT implemented. Skeleton only. PG graph stays via GraphService BFS.

### 4.5 RAG Pipeline (Post-MVP)

```
Input: user_question (natural language)
   │
   ▼
Process:
   1. Query Rewrite (LLM) → search-friendly query
   2. Intent Router → classify: fact_lookup / review / compare / teaching
   3. Text RAG branch:
      a. Embed query (BGE-M3)
      b. pgvector ANN search (Top 20)
      c. Filter by RBAC + status='published'
      d. BM25 fusion with ES results (Top 10)
      e. Reranker (BGE-Reranker-v2) → Top 10 chunks
   4. Graph RAG branch:
      a. Entity Linking (exact + fuzzy)
      b. Neo4j subgraph retrieval (max 3 hops, max 200 nodes)
      c. Evidence ranking
   5. Context Builder: merge Text + Graph results, bind citations
   6. LLM Generation (with system prompt enforcing citation-first)
   7. Hallucination Detection:
      a. Citation existence check
      b. Claim-evidence support check
      c. Abstention gate (insufficient evidence → refuse)
   │
   ▼
Output: StructuredAIResponse {answer, evidence[], citations[], graph_context[]}
```

**MVP status:** Steps 1-7 NOT implemented. Current "RAG" = PostgreSQL ILIKE keyword search + LLM. This is the Post-MVP target architecture.

### 4.6 Research Assistant Pipeline (Post-MVP)

Six assistants defined in HFB-ARC-0203 §3.2 Module 5:

| Assistant | Pipeline Input           | Pipeline Output                                                         | Status   |
| --------- | ------------------------ | ----------------------------------------------------------------------- | -------- |
| 文献综述  | research topic string    | topic classification, key papers, gaps, suggested titles                | Post-MVP |
| 证据链    | passage/entity reference | original text, related passages, citations, modern interpretations      | Post-MVP |
| 版本比较  | two version IDs          | text diff, chapter diff, term diff, collation suggestions               | Post-MVP |
| 论文选题  | research area            | suggested topics, innovation points, literature basis, methodology      | Post-MVP |
| 教学问答  | student question         | plain-language answer, flashcard, quiz question                         | Post-MVP |
| 学术审校  | paper/claim text         | citation accuracy report, evidence chain check, hallucination detection | Post-MVP |

**MVP status:** None of the six assistants are implemented as independent pipelines. Current AI chat is a single general-purpose Q&A endpoint.

---

## 5. Knowledge Graph Bootstrap Framework

### 5.1 MVP Graph (Current)

```
Technology: PostgreSQL adjacency list + Python BFS/DFS (GraphService)
Node registry: {person, book, version, passage} — 4 types
Edge registry:  {authored, compiled, commented_on, cited_in, studied, compared,
                 referenced, related_to} — 8 types
Queries:        BFS neighbors, 1-2 hop traversal, path finding
```

### 5.2 Node Registry Extension (Sprint-0: doc only, no code)

```
MVP entity types → graph nodes (1:1 mapping):
  Person      → Node(:Entity:Person)
  Book        → Node(:Entity:Book)
  Version     → Node(:Entity:Version)
  Chapter     → Node(:Entity:Chapter)     # Current model, not yet in graph.py
  Passage     → Node(:Entity:Passage)
  Paper       → Node(:Entity:Paper)       # Current model, not yet in graph.py
  Image       → Node(:Entity:Image)       # Current model, not yet in graph.py
  Document    → Node(:Entity:Document)    # Current model, not yet in graph.py
```

### 5.3 Edge Registry Extension (Sprint-0: doc only, no code)

Standardize existing graph.py relation names to HFB-DAT-0305 approved names:

```
graph.py short name    → HFB-DAT-0305 standard name
authored               → authored_by
compiled               → compiled_by
commented_on           → comments_on
cited_in               → cites
studied                → studies
compared               → (domain-specific, keep)
referenced             → references
related_to             → related_to
```

Alias existing short names in the service layer; new code uses standard names.

### 5.4 Evidence Linking System (Sprint-0: migration only)

```
Schema (see HFB-ARC-0203 §4.2):
  evidence (id, entity_id FK, source_type, source_id, excerpt, url, verified_by)
  relation_evidence (relation_id FK, evidence_id FK) — many-to-many
  citation (id, label, entity_type, entity_id FK, evidence_id FK, format, full_text)

Constraint:
  Published Relation must have >= 1 Evidence (app-layer or trigger enforced)
```

### 5.5 Graph Update Strategy

```
MVP (Current):
  Write Path:  Entity/Relation INSERT/UPDATE/DELETE → PostgreSQL
  Read Path:   GraphService BFS queries entity_relations + version_relations
  Sync:        N/A — single source, no Neo4j

Post-MVP:
  Write Path:  Entity/Relation INSERT/UPDATE/DELETE → PostgreSQL
               + INSERT INTO graph_events (outbox, same TX)
  Sync Path:   Graph Sync Worker polls graph_events → Neo4j UPSERT
  Read Path:   GraphService queries Neo4j (1-3 hop traversal)
  Fallback:    Neo4j unavailable → GraphService BFS on PG
```

---

## 6. MVP Sprint Breakdown

### Sprint 0 (THIS SPRINT — Engineering Initialization)

**Goals:**

- Harden the existing foundation before feature work continues
- Establish Port/Adapter boundaries
- Add audit infrastructure
- Normalize error handling
- Create evidence/citation/review schemas
- Align compose config with architecture

**Deliverables:**

| #    | Deliverable                                             | File(s)                                                                      | Verification                                                   |
| ---- | ------------------------------------------------------- | ---------------------------------------------------------------------------- | -------------------------------------------------------------- |
| 0.1  | Port interfaces defined                                 | `app/ports/knowledge_repository.py`, `ai_service.py`, `search_repository.py` | All 3 ports are abstract (ABC/Protocol), no concrete imports   |
| 0.2  | Adapter stubs                                           | `app/adapters/pg_knowledge.py`, `llm_gateway.py`, `pg_search.py`             | Implements ports, registers in DI                              |
| 0.3  | AuditMixin base class                                   | `app/db/audit_mixin.py`                                                      | `created_by`, `created_at`, `updated_by`, `updated_at` columns |
| 0.4  | Metadata table migration                                | `app/db/migrations/versions/`                                                | `alembic upgrade head` succeeds                                |
| 0.5  | Evidence + relation_evidence + citation table migration | Same                                                                         | FK integrity verified                                          |
| 0.6  | BusinessAuditLog table migration                        | Same                                                                         | Immutable log table created                                    |
| 0.7  | Unified error handlers                                  | `app/core/error_handlers.py`                                                 | All exception types → unified envelope                         |
| 0.8  | Request ID middleware                                   | `app/middleware/request_id.py`                                               | `X-Request-ID` in all responses                                |
| 0.9  | Request access log middleware                           | `app/middleware/audit_logger.py`                                             | Structured log per request                                     |
| 0.10 | Structured logging upgrade                              | `app/core/logging.py`                                                        | JSON output with request_id, user_id                           |
| 0.11 | Compose variable hardening                              | `docker-compose.prod.yml`                                                    | ✅ Already done in prior remediation                           |
| 0.12 | Readiness HTTP 503                                      | `app/api/ready.py`                                                           | ✅ Already done                                                |
| 0.13 | Config audit section                                    | `app/core/config.py`                                                         | `AUDIT_RETENTION_DAYS`, `AUDIT_ENABLED`                        |
| 0.14 | Future service stubs                                    | `services/`, `knowledge_graph/`, `rag/`, `ai_pipeline/`                      | `.gitkeep` only                                                |
| 0.15 | Updated .env.example                                    | `.env.example`                                                               | All new env vars documented                                    |

**Risk:** Existing tests may break due to new middleware or config changes. Run full test suite after each deliverable.

**Acceptance Criteria:**

- All 197 existing tests pass
- New migrations apply cleanly
- `GET /ready` returns 200 (when all services healthy)
- Audit logs appear in structured format
- Port interfaces are importable and type-check clean

---

### Sprint 1 — Entity Foundation

**Goals:** Complete Core Entity coverage, normalize status lifecycle, integrate ES search.

**Deliverables:**

| #   | Deliverable                                                                     |
| --- | ------------------------------------------------------------------------------- |
| 1.1 | Institution model + API                                                         |
| 1.2 | Place model + API                                                               |
| 1.3 | Event model + API                                                               |
| 1.4 | Dynasty model + API                                                             |
| 1.5 | Status lifecycle enforcement (Draft→Review→Published) — app-layer state machine |
| 1.6 | Graph node type expansion (Chapter, Paper, Image, Document → graph.py)          |
| 1.7 | Elasticsearch integration in SearchService (replace/coexist with ILIKE)         |
| 1.8 | Metadata CRUD (create metadata table + API)                                     |

**Risk:** ES integration is first production use of ES in query path.

**Acceptance Criteria:**

- All 12 Core Entities have CRUD API
- Published entities visible in unified search
- ES returns relevant results with highlighting
- Status state machine rejects Draft→Published transition

---

### Sprint 2 — Evidence & Review

**Goals:** Evidence system, Citation system, Expert Review workflow.

**Deliverables:**

| #   | Deliverable                                                  |
| --- | ------------------------------------------------------------ |
| 2.1 | Evidence CRUD API                                            |
| 2.2 | Citation CRUD API                                            |
| 2.3 | Relation evidence binding (link evidence to relation)        |
| 2.4 | ReviewService (Draft→Review→Published flow)                  |
| 2.5 | Expert Workbench UI (basic: queue + approve/reject)          |
| 2.6 | BusinessAuditLog read API                                    |
| 2.7 | Alias graph.py relation names to HFB-DAT-0305 standard names |

**Risk:** Expert Workbench UI is first new frontend component since Sprint 0.

**Acceptance Criteria:**

- Published Relation forced to have ≥1 Evidence
- Review queue shows pending entities/relations
- Reviewer cannot approve their own submissions
- Audit log tracks all status changes

---

### Sprint 3 — MVP Completion

**Goals:** Full-text search, citation generation, static exhibition page, MVP acceptance.

**Deliverables:**

| #   | Deliverable                                                                |
| --- | -------------------------------------------------------------------------- |
| 3.1 | ES integrated into SearchService query path (if not completed in Sprint 1) |
| 3.2 | Citation auto-generation from Passage metadata                             |
| 3.3 | Huangfu Mi timeline page (static)                                          |
| 3.4 | Research workflow: find passage → compare → record note → export           |
| 3.5 | Production readiness checklist audit                                       |
| 3.6 | Security audit (OWASP, dependency scan)                                    |
| 3.7 | Performance baseline (k6 load test)                                        |

**Acceptance Criteria (MVP Gate):**

- All 5 MVP capabilities per HFB-ARC-0203 §9.2
- All published relations have ≥1 evidence
- All published entities have metadata
- AI answers include citation
- No Future Entity models in codebase
- Test coverage ≥ 90% backend, ≥ 80% frontend

---

## 7. Execution Checklist (Sprint 0 Step-by-Step)

### Phase 0: Pre-flight

- [ ] 0.0.1 Verify `uv run pytest` — all 197 tests pass on clean checkout
- [ ] 0.0.2 Verify `docker compose -f docker-compose.prod.yml config` parses
- [ ] 0.0.3 Verify `ruff check` and `mypy` pass
- [ ] 0.0.4 Create Sprint-0 branch from master

### Phase 1: Infra Hardening

- [ ] 0.1.1 Add `uuid6` to pyproject.toml dependencies
- [ ] 0.1.2 Add `structlog` to pyproject.toml dependencies
- [ ] 0.1.3 Update `.env.example` with all Config variables
- [ ] 0.1.4 Create `services/.gitkeep`, `knowledge_graph/.gitkeep`, `rag/.gitkeep`, `ai_pipeline/.gitkeep`

### Phase 2: Port/Adapter Architecture

- [ ] 0.2.1 Create `app/ports/__init__.py`
- [ ] 0.2.2 Create `app/ports/knowledge_repository.py` — abstract interface for entity/relation storage
- [ ] 0.2.3 Create `app/ports/ai_service.py` — abstract interface for LLM calls
- [ ] 0.2.4 Create `app/ports/search_repository.py` — abstract interface for full-text search
- [ ] 0.2.5 Create `app/adapters/__init__.py`
- [ ] 0.2.6 Create `app/adapters/pg_knowledge.py` — implements KnowledgeRepository via SQLAlchemy
- [ ] 0.2.7 Create `app/adapters/llm_gateway.py` — implements AIService via httpx → LLM Providers
- [ ] 0.2.8 Create `app/adapters/pg_search.py` — implements SearchRepository via ILIKE (ES deferred)
- [ ] 0.2.9 Run full test suite — verify no regressions

### Phase 3: Audit + Observability

- [ ] 0.3.1 Create `app/db/audit_mixin.py` — `AuditMixin` with created_by/at, updated_by/at
- [ ] 0.3.2 Generate and apply `create_metadata_table` migration
- [ ] 0.3.3 Generate and apply `create_evidence_tables` migration (evidence, relation_evidence, citation)
- [ ] 0.3.4 Generate and apply `create_audit_log_table` migration
- [ ] 0.3.5 Upgrade `app/core/logging.py` — structured JSON output
- [ ] 0.3.6 Create `app/middleware/request_id.py` — X-Request-ID injection
- [ ] 0.3.7 Create `app/middleware/audit_logger.py` — request access logging

### Phase 4: Error Handling + Config

- [ ] 0.4.1 Create `app/core/error_handlers.py` — unified exception → API response
- [ ] 0.4.2 Register error handlers on FastAPI app in `main.py`
- [ ] 0.4.3 Add `AUDIT_RETENTION_DAYS` and `AUDIT_ENABLED` to config
- [ ] 0.4.4 Run full test suite — verify no regressions

### Phase 5: Verification

- [ ] 0.5.1 `uv run pytest` — all tests pass
- [ ] 0.5.2 `ruff check` — no new lint errors
- [ ] 0.5.3 `mypy apps/backend` — no new type errors
- [ ] 0.5.4 `alembic upgrade head` — all migrations apply cleanly
- [ ] 0.5.5 `docker compose -f docker-compose.prod.yml config` — parses
- [ ] 0.5.6 Manual smoke test: `GET /health`, `GET /ready`, `POST /api/v1/ai/chat`
- [ ] 0.5.7 Document Sprint-0 completion in `docs/superpowers/plans/`

---

## Appendix: Production Gap Tracker

Copied from HFB-ARC-0203. These are NOT Sprint-0 tasks; they track what's missing before production.

| #    | Gap                                     | Severity | Target Sprint                |
| ---- | --------------------------------------- | -------- | ---------------------------- |
| PG-1 | No `metadata` table                     | High     | Sprint 0 ✓                   |
| PG-2 | No `relation_evidence` table            | High     | Sprint 0 ✓                   |
| PG-3 | No `graph_events` outbox                | Medium   | Post-MVP                     |
| PG-4 | No task queue (Celery/ARQ)              | Medium   | Post-MVP                     |
| PG-5 | ES not in SearchService query path      | Medium   | Sprint 1                     |
| PG-6 | Backup RPO/RTO not met                  | High     | Sprint 3                     |
| PG-7 | No ReviewService implementation         | High     | Sprint 2                     |
| PG-8 | Redis/MinIO runtime health not verified | Medium   | Sprint 0 (verify in compose) |
| PG-9 | Neo4j not deployed                      | Post-MVP | Post-MVP                     |
