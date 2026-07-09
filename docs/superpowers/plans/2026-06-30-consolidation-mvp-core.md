---
title: System Consolidation — MVP Core Definition & Sprint 1 Realignment
document_id: HFB-ENG-CONSOLIDATION-01
version: 1.0.0
status: Draft
owner: Engineering Control Architect
based_on: HFB-ARC-0203 System Architecture v1.2.0
effective_date: 2026-06-30
scope: Reduce to Minimum Viable Production Core
---

# System Consolidation — MVP Core Definition & Sprint 1 Realignment

> **原则：减少代码、减少抽象、减少文件。只保留能跑的 MVP。**

---

## 1. Complexity Reduction Report

### 1.1 Over-Engineered Modules — IDENTIFIED & CUT

| Module | Found In | Problem | Action |
|--------|----------|---------|--------|
| **Port/Adapter abstraction layer** | Sprint-0 plan §2.5–2.8 | 3 abstract interfaces + 3 adapter files for a codebase that already follows Service→Repository→Model layering with zero leakage | **CUT.** Don't create ports/. Don't create adapters/. Existing layer discipline is enforced by code review, not by ABC. |
| **Structured JSON logging** | Sprint-0 plan §0.3.5 | Premature for MVP — adds structlog dependency, config complexity, and 3 new files for a problem that doesn't exist yet | **CUT.** Keep existing `app/core/logging.py`. Add `X-Request-ID` header propagation only (one middleware file). |
| **Request access log middleware** | Sprint-0 plan §0.3.7 | Separate audit stream for HTTP access logs — 90-day retention, separate table design | **DEFER to Sprint 3.** Audit log is needed only for Published data lifecycle; HTTP access logging is an ops concern, not MVP. |
| **BusinessAuditLog table** | Sprint-0 plan §3.1.8 | Full immutable audit log with before/after JSON snapshots, prompt_version, model_version | **DEFER to Sprint 2.** ReviewService needs it but ReviewService doesn't exist yet. Build it WITH ReviewService, not before. |
| **Metadata table + 1:1 constraint** | Sprint-0 plan §3.1.6 | Separate metadata table every entity must 1:1 reference — a constraint with no consumer | **DEFER to Sprint 2.** No feature reads metadata. No user sees metadata. The constraint is a Production Gate, not a Sprint-0 deliverable. |
| **Review queue table migration** | Sprint-0 plan §3.1.9 | Table for ReviewService that doesn't exist | **DEFER to Sprint 2.** Build with ReviewService. |
| **Future service stubs (services/, knowledge_graph/, rag/, ai_pipeline/)** | Sprint-0 plan §1.2 | Empty directories with .gitkeep for Post-MVP services | **CUT.** Don't create directories for code that doesn't exist. Post-MVP can scaffold itself. |
| **uuid6 dependency** | Sprint-0 plan §7.0.1 | UUID v7 library | **DEFER.** Current code uses string UUIDs via BaseModel. UUID v7 generation is needed only when we create entities programmatically from ingestion, not before. |

### 1.2 Premature Enterprise Abstractions — IDENTIFIED & CUT

| Abstration | Problem | Action |
|-----------|---------|--------|
| **8-way exception → HTTP mapping** | Sprint-0 plan §2.6: ValidationError→422, PermissionError→403, EntityNotFound→404, ConflictError→409, RateLimitError→429, AIProviderError→502, DatabaseError→503, Exception→500 | Existing code already handles errors. Don't build a taxonomy for errors that haven't occurred. **KEEP only:** the existing FastAPI exception handlers. Add ONE custom handler for `EntityNotFoundError` (used in services). |
| **AUDIT_RETENTION_DAYS config** | Config for audit log retention when audit log table doesn't exist | **CUT.** Add when audit log is created. |
| **Config file audit section** | New config namespace | **CUT.** No consumer exists. |

### 1.3 Post-MVP Leakage Into MVP — IDENTIFIED & CLEANED

| Leakage | Location in Sprint-0 Plan | Fix |
|---------|--------------------------|-----|
| **Evidence + relation_evidence + citation tables** described as Sprint-0 migrations | §3.1.7 | These are Sprint-2 (used by ReviewService). Current MVP has NO ReviewService and NO Evidence enforcement. **MOVE to Sprint 2.** |
| **6-pipeline AI skeleton** described as detailed design | §4.1–4.6 | OCR/NER/Relation/Graph/RAG/Research-Assistant all Post-MVP. Writing detailed process flows for Post-MVP work is architecture creep. **CUT all pipeline descriptions.** Keep only the 2-sentence summary: "Current MVP = ILIKE + LLM. Post-MVP = Text RAG + GraphRAG." |
| **Node registry extension to 12 types** | §5.2 | GraphService currently handles 4 types. Expanding the doc-only registry before code needs it is aspirational. **KEEP current state as-is.** Expand when actual graph queries require it. |
| **Edge name standardization** | §5.3 | Renaming graph.py short names to HFB-DAT-0305 standard names is a code change with no user impact. **DEFER to Sprint 1.** Do it when adding new relation types. |
| **Graph update strategy (Post-MVP section)** | §5.5 | Detailed outbox pattern, sync worker design — all Post-MVP. **KEEP 1 paragraph.** Delete the detailed process flow. |

### 1.4 Duplicated Responsibilities

| Duplication | Found In | Action |
|-------------|----------|--------|
| **Sprint 0 deliverable list + Execution Checklist** | §6 Sprint 0 table + §7 Phase checkboxes | Same content in two formats. **Keep §7 checkboxes only.** Delete §6 Sprint 0 deliverable table. |
| **Production Gap Tracker** in Appendix | Duplicates HFB-ARC-0203 Appendix A risk register + Production Gap tracking | **DELETE.** Architecture doc already tracks this. Don't duplicate. |

---

## 2. MVP Core System Definition (FINAL)

### 2.1 What Is MVP

```
MVP = what currently RUNS + what must be ADDED to meet the 5 acceptance criteria

CURRENTLY RUNS (do not rebuild, do not redesign):
  ✅ PostgreSQL schema (books, versions, chapters, passages, persons,
     papers, images, documents, entity_relations, users, roles, permissions,
     research_sessions, research_notes)
  ✅ REST API (14 route groups, unified JSON envelope)
  ✅ AI Chat endpoint (SSE streaming, evidence-gated, StructuredResponseBuilder)
  ✅ GraphService BFS/DFS (4 entity types, 8 relation types)
  ✅ SearchService (PostgreSQL ILIKE)
  ✅ Auth (User/Role/Permission + require_permission guard)
  ✅ Research workflow (find passage → compare → record note → export)
  ✅ Readiness endpoint (HTTP 503 on dependency failure)
  ✅ Docker compose (MVP services: PG + Redis + MinIO + ES + Backend + Frontend)

MUST ADD (Sprint 1):
  📋 Institution, Place, Event, Dynasty models (4 new files)
  📋 4 new API route groups (institutions, places, events, dynasties)
  📋 ES integration into SearchService (current ES is deployed but unused in query path)
  📋 Status lifecycle enforcement (Draft→Review→Published state machine in app layer)
  📋 EntityNotFoundError + unified handler (one new exception class + registration)
  📋 X-Request-ID middleware (one file)
```

### 2.2 What Is NOT MVP

```
POST-MVP (do not build, do not design, do not scaffold):
  ✗ Neo4j (ADR-0004)
  ✗ GraphRAG (ADR-0006)
  ✗ Milvus (ADR-0007)
  ✗ Text RAG / pgvector vector retrieval
  ✗ Citation RAG
  ✗ Acupoint, Meridian, Disease, Symptom, Herb, Formula, Treatment entities
  ✗ OCR pipeline
  ✗ NER pipeline
  ✗ Relation extraction pipeline
  ✗ Graph builder pipeline
  ✗ Literature review / evidence chain / topic suggestion / version comparison assistants
  ✗ Learning center
  ✗ Full digital exhibition

DEFERRED TO SPRINT 2 (next sprint, not now):
  ⏳ Evidence + Citation tables
  ⏳ Relation evidence binding (published relation ≥ 1 evidence)
  ⏳ ReviewService (Draft→Review→Published flow)
  ⏳ Expert Workbench UI
  ⏳ BusinessAuditLog
  ⏳ Metadata table

DEFERRED TO SPRINT 3 (pre-release):
  ⏳ Full-text search polish (ES query tuning, highlighting)
  ⏳ Citation auto-generation from Passage metadata
  ⏳ Huangfu Mi static timeline page
  ⏳ Production readiness (perf test, security audit, backup hardening)
```

### 2.3 Core Entity Rule

**Only 8 entities have models today.** 4 more (Institution, Place, Event, Dynasty) are needed to complete the Core Entity set per HFB-DAT-0304.

```
MVP Entity Model = 12 Core Entities + User/Role/Permission
                  = EXACTLY what HFB-DAT-0304 §3 defines
                  = NO Future Entities
```

---

## 3. Simplified Architecture Diagram

```
┌──────────────────────────────────────────┐
│              L1 Vue 3 Frontend           │
│   Portal / Admin / AI Assistant          │
└──────────────────┬───────────────────────┘
                   │ HTTP REST (JSON)
┌──────────────────┴───────────────────────┐
│              L2 FastAPI                   │
│  14 route groups  │  Auth (JWT + RBAC)   │
│  Unified envelope │  X-Request-ID        │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────┴───────────────────────┐
│              L3 Domain Services           │
│  14 services    │  Service → Repository  │
│  State machine  │  → SQLAlchemy Model    │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────┴───────────────────────┐
│              L4 AI (MVP only)            │
│  AIService (httpx → LLM Provider)       │
│  RateLimiter  │  guard_ai_read          │
│  StructuredResponseBuilder               │
│  RAGService (ILIKE keyword search)       │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────┴───────────────────────┐
│              L5 Storage                   │
│  PostgreSQL (source of truth)            │
│  Elasticsearch (MVP: deployed,           │
│    Sprint 1: integrated into search)     │
│  Redis (cache)  │  MinIO (files)         │
└──────────────────┬───────────────────────┘
                   │
┌──────────────────┴───────────────────────┐
│              L6 Infrastructure            │
│  Docker Compose (6 MVP services)         │
│  CI/CD (GitHub Actions)                  │
│  Health + Readiness probes               │
└──────────────────────────────────────────┘

What we DON'T build yet:
  Neo4j    — Post-MVP (ADR-0004)
  pgvector — Post-MVP (ADR-0007 milestone)
  GraphRAG — Post-MVP (ADR-0006)
  Task queue — Post-MVP
  Port/Adapter interfaces — unnecessary; discipline enforced by review
```

---

## 4. Sprint 1 Revised Plan

### Duration: 5–7 engineering days

### Goal: Complete Core Entity coverage + ES search + status lifecycle

### Deliverables (8 tasks)

| # | Task | Files Affected | Effort | Verifies |
|---|------|---------------|--------|----------|
| 1.1 | **Institution model + migration + API** | `models/institution.py`, `schemas/entities.py` (extend), `api/v1/entities.py` (extend or new route) | 0.5d | CRUD via API |
| 1.2 | **Place model + migration + API** | `models/place.py`, `schemas/`, `api/v1/` | 0.5d | CRUD via API |
| 1.3 | **Event model + migration + API** | `models/event.py`, `schemas/`, `api/v1/` | 0.5d | CRUD via API |
| 1.4 | **Dynasty model + migration + API** | `models/dynasty.py`, `schemas/`, `api/v1/` | 0.5d | CRUD via API |
| 1.5 | **ES integration into SearchService** | `services/search_service.py` (add ES backend path) | 1.5d | Search returns ES results with highlighting |
| 1.6 | **Status lifecycle state machine** | `services/entities.py` (add state validation), `core/status_machine.py` (new) | 1d | Draft→Review→Published enforced; Draft→Published rejected |
| 1.7 | **EntityNotFoundError + handler** | `core/exceptions.py` (new), `core/error_handlers.py` (new), `main.py` (register) | 0.5d | 404 on missing entity, unified envelope |
| 1.8 | **X-Request-ID middleware** | `middleware/request_id.py` (new), `main.py` (register) | 0.5d | `X-Request-ID` in all responses |

**Total: ~5.5 engineering days**

### NOT in Sprint 1 (explicit exclusion)

- Evidence tables (→ Sprint 2)
- Citation tables (→ Sprint 2)
- ReviewService (→ Sprint 2)
- BusinessAuditLog (→ Sprint 2)
- Metadata table (→ Sprint 2)
- Graph.py relation rename (→ Sprint 2)
- Port/Adapter interfaces (→ never; unnecessary)
- Structured logging (→ Sprint 3 or never)
- Audit log middleware (→ Sprint 3)
- Frontend changes beyond bugfixes (→ Sprint 3)
- Any AI pipeline beyond current ILIKE + LLM

### Acceptance Criteria

1. `GET /api/v1/institutions` returns paginated results
2. `GET /api/v1/places` returns paginated results
3. `GET /api/v1/events` returns paginated results
4. `GET /api/v1/dynasties` returns paginated results
5. `POST /api/v1/search?q=针灸` returns ES results with highlight snippets
6. `PATCH /api/v1/entities/{id} status=published` when status=draft returns 409
7. `GET /api/v1/entities/nonexistent-id` returns 404 with unified envelope
8. All responses include `X-Request-ID` header
9. All 197+ existing tests still pass
10. `ruff check` + `mypy` clean

---

## 5. Post-MVP Deferred List

| Item | Deferred To | Trigger |
|------|------------|---------|
| Neo4j deployment | Phase 2 | ADR-0004 upgraded to Active |
| GraphRAG | Phase 2 | Neo4j deployed + ADR-0006 Active |
| pgvector / Text RAG | Phase 2 | Embedding model selected + pgvector extension enabled |
| Milvus | Phase 3 | >100K vectors |
| OCR pipeline | Phase 2 | Multi-version corpus acquired |
| NER pipeline | Phase 2 | TCM fine-tuned model available |
| Relation extraction | Phase 2 | NER pipeline operational |
| Literature review assistant | Phase 2 | Text RAG + GraphRAG operational |
| Evidence chain assistant | Phase 2 | GraphRAG operational |
| Version comparison assistant | Phase 2 | Multi-version data loaded |
| Topic suggestion assistant | Phase 2 | Paper corpus >500 |
| Teaching assistant | Phase 3 | Learning center built |
| Academic audit assistant | Phase 3 | All assistants operational |
| Evidence + Citation tables | Sprint 2 | Sprint 1 complete |
| ReviewService | Sprint 2 | Evidence tables exist |
| Metadata table | Sprint 2 | ReviewService exists (metadata is for published entities) |
| BusinessAuditLog | Sprint 2 | ReviewService exists (audit tracks review actions) |
| Port/Adapter interfaces | Never | Existing Service→Repository→Model layering is adequate |
| Structured logging | Sprint 3 | Ops requirement emerges |
| Audit log middleware | Sprint 3 | BusinessAuditLog established |
| Learning center | Phase 2 | MVP delivered |
| Full digital exhibition | Phase 2 | MVP delivered |
| Institution/Place/Event/Dynasty API | Sprint 1 | THIS SPRINT |

---

## 6. Summary of Cuts

| Cut | From Sprint-0 Plan | Saving |
|-----|-------------------|--------|
| Port/Adapter layer (6 files) | §2.5–2.8 | ~300 lines, 6 files, 1 dependency |
| Structured logging upgrade | §0.3.5 | structlog dep, 1 file rewrite, config complexity |
| Request audit middleware | §0.3.7 | 1 file, 1 migration, 1 config section |
| BusinessAuditLog table | §3.1.8 | 1 migration, 1 model, 1 API |
| Metadata table | §3.1.6 | 1 migration, 1 model, 1 API, 1 constraint |
| Review queue table | §3.1.9 | 1 migration, 1 model |
| Evidence + Citation tables | §3.1.7 | 3 migrations, 3 models, 2 APIs |
| Future service stubs (4 dirs) | §1.2 | 4 directories |
| uuid6 dependency | §7.0.1 | 1 dependency |
| 6-pipeline AI design docs | §4.1–4.6 | ~200 lines of premature design |
| Edge name standardization | §5.3 | Code churn with zero user impact |
| Production Gap Tracker duplicate | Appendix | ~20 lines |
| Sprint 0 deliverable table (duplicate) | §6 | ~20 lines |

**Total removed from Sprint 0 plan: ~500 lines of planned code, 15+ files, 2 dependencies, 6+ migrations.**
