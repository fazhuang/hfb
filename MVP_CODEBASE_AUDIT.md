# MVP Codebase Audit — 皇甫谧数字人文平台

**Generated:** 2026-06-25
**Audit Scope:** Phase 1 前置完整盘点
**Project Version:** 0.2.0 (Sprint 0.2 — Repository Foundation)
**Auditor:** Claude Code (Opus 4.8)

---

## 1. 当前前端结构

```
apps/frontend/
  src/
    api/client.ts              — Axios HTTP client, health/ready/version API wrappers
    assets/main.css            — CSS custom properties, light/dark theme tokens, reset
    components/
      common/
        PlaceholderPage.vue    — Placeholder for unimplemented pages
        StatusCard.vue         — Service status indicator card
      layout/
        AppNavbar.vue          — Top navigation bar with mobile menu toggle
        AppMain.vue            — <main> wrapper slot
        AppFooter.vue          — Footer with copyright & license
    composables/useTheme.ts    — light/dark/auto theme manager
    i18n/
      index.ts                 — vue-i18n setup, zh-CN + en, browser detection
      locales/zh-CN.ts         — Chinese UI strings
      locales/en.ts            — English UI strings
    layouts/
      DefaultLayout.vue        — Navbar + Main + Footer layout
    router/index.ts            — 4 routes: /, /search, /documents, /about
    stores/system.ts           — Pinia store for infra health status
    views/
      HomeView.vue             — System status dashboard (health checks)
      SearchView.vue           — Placeholder
      DocumentsView.vue        — Placeholder
      AboutView.vue            — Static about page with tech stack
    App.vue
    main.ts
    __tests__/system.test.ts   — 3 tests for systemStore
```

**Status:** Scaffolded Vue 3 + TypeScript app. Core layout (navbar + main + footer) present. Theme switching and i18n wired up. 4 page routes stub'd — only HomeView has real logic (health check display). Search, Documents, About are placeholders. **3 passing vitest tests.**

**Issues:**
- DefaultLayout.vue imports `AppNavbar`, `AppMain`, `AppFooter` from `./` but they reside in `components/layout/` — import path mismatch, will fail at runtime.
- No `/api/v1/` prefix used in API client — calls `/health`, `/ready`, `/version` directly (backend serves both root and `/api/v1` paths; v1 router is empty).
- No views implement any domain entity CRUD.

---

## 2. 当前后端结构

```
apps/backend/
  main.py                        — FastAPI app factory, CORS, lifespan, global exception handler
  app/
    api/
      health.py                  — GET /health
      ready.py                   — GET /ready (infra health checks)
      version.py                 — GET /version, GET /live, GET /config
      v1/__init__.py             — /api/v1 prefix router (empty, CRUD deferred)
    core/
      config.py                  — Pydantic Settings (env vars)
      logging.py                 — JSON + Console structured logging
      settings.py                — Re-export config singleton
    db/
      base.py                    — Base, BaseModel(Abstract), TimestampMixin, SoftDeleteMixin
      database.py                — Async engine, session factory, get_session dependency
      seed.py                    — 3 persons + 3 documents fixtures
      alembic.ini                — (duplicate of root alembic.ini)
    middleware/
      __init__.py                — Package marker
      logging.py                 — RequestLoggingMiddleware (duration, method, path, status)
    models/
      __init__.py                — Re-exports Document, Person
      document.py                — Document (文献): title, dynasty, year, category, abstract, content_text...
      person.py                  — Person (人物): name, courtesy_name, dynasty, birth/death_year, biography...
    repositories/
      __init__.py
      base.py                    — Generic async CRUD with soft-delete, pagination, LIKE search
      document.py                — DocumentRepository with search_query, get_by_dynasty
      person.py                  — PersonRepository with search_query, get_by_dynasty
    schemas/
      __init__.py
      common.py                  — PaginationParams, PaginatedResponse
      document.py                — DocumentCreate, DocumentBrief, DocumentResponse
      person.py                  — PersonCreate, PersonBrief, PersonResponse
    services/
      __init__.py
      base.py                    — Generic BaseService with validation hooks
      document_service.py        — Title-required validation + search
      person_service.py          — Name-required validation + search + dynasty filter
    startup/
      __init__.py
      check_infrastructure.py    — Concurrent health checks: PostgreSQL, Redis, ES, MinIO
    utils/
      __init__.py
      response.py                — Unified {success, timestamp, data, message} envelope
```

**Status:** Clean FastAPI scaffold with proper layered architecture (Controller → Service → Repository → DB). 2 domain models (Document, Person) fully wired with schemas, repos, services. Health/ready/version endpoints operational. Seed data available.

**Issues:**
- `elasticsearch_url` referenced in `check_infrastructure.py:72` but NOT defined in `core/config.py` Settings class — runtime error if `/ready` is hit.
- `config.py` uses `from typing import Any` — unused import.
- `db/base.py` imports `UUID` from uuid — unused.
- `models/document.py:45` uses `"Person"` forward reference that Ruff flags (works at runtime due to string annotation).
- Entities fully scaffolded but no CRUD API endpoints wired (v1 router is intentionally empty per Sprint scoping).
- `db/alembic.ini` is a duplicate of root `alembic.ini`.
- `app/api/` has no `__init__.py` — relies on namespace package (works in Python 3.12 with proper path setup, as confirmed by 51 passing pytest tests).

---

## 3. 当前数据库/模型结构

| Model | Table | Columns | Status |
|-------|-------|---------|--------|
| **BaseModel** (abstract) | — | id (UUID string), created_at, updated_at, deleted_at, is_deleted | Complete |
| **Document** (文献) | documents | 17 columns incl. title, dynasty, year, category, abstract, content_text, author_id FK→persons | Complete, no API routes |
| **Person** (人物) | persons | 16 columns incl. name, courtesy_name, dynasty, birth/death_year, biography, expertise | Complete, no API routes |

**MVP Requirements Not Yet Modeled:**
- **Book** (书籍) — required per MVP scope Chapter 5
- **Version** (版本) — required per 1701 Version Center spec
- **Passage** (段落) — required per 1705 AI Research Workspace
- **Paper** (论文) — referenced in domain docs
- **Chapter** (章节) — referenced in tech blueprint 9.1
- **User** (用户) — required for RBAC
- **Role** (角色) — required for RBAC
- **Workspace** / **ResearchSession** — required per 1705
- **Evidence / Citation** — required per MVP Chapter 10
- **Image** (影像) — referenced in blueprint 9.1

**Deferred Models (correctly absent):**
- Herb, Prescription, Disease, Symptom, Meridian, Formula, Acupoint — all correctly excluded from MVP per tech blueprint 9.2.

---

## 4. 当前 API 状态

| Endpoint | Method | Status | Notes |
|----------|--------|--------|-------|
| `/health` | GET | ✅ Working | Returns `{"status": "healthy"}` |
| `/ready` | GET | ⚠️ Bug | References undefined `settings.elasticsearch_url` |
| `/version` | GET | ✅ Working | Returns version + environment |
| `/live` | GET | ✅ Working | Minimal liveness probe |
| `/config` | GET | ✅ Working | Public config (hosts/ports) |
| `/api/v1/*` | — | ❌ Empty | Router defined but no routes |
| CRUD for Document | — | ❌ Missing | Only repository/service layer exists |
| CRUD for Person | — | ❌ Missing | Only repository/service layer exists |
| Auth / Login | — | ❌ Missing | No auth system |
| Search | — | ❌ Missing | No search API |
| Graph | — | ❌ Missing | No graph API |

**Unified Response Format:** All implemented endpoints use the standard envelope:
```json
{"success": true, "timestamp": "...", "data": {...}, "message": "ok"}
```

---

## 5. 当前测试状态

### Python (pytest)
- **51 tests, all passing** in `tests/unit/`
- Coverage: test_health (5), test_base_model (3), test_models (7), test_repositories (12), test_schemas (7), test_seed (5), test_services (4), test_settings (5)
- Configuration: conftest.py (sys.path), conftest_db.py (in-memory SQLite fixtures)
- No integration tests (directory exists but empty)
- No E2E tests (directory exists but empty)
- Coverage target: ≥70% (`--cov-fail-under=70`)

### Frontend (vitest)
- **3 tests, all passing** in `src/__tests__/system.test.ts`
- Tests Pinia systemStore with mocked API client

### Total: 54 passing tests, 0 failing

**Gaps:**
- No integration tests (database migration, API integration, auth flows)
- No E2E tests
- No AI tests
- No graph tests
- No search tests

---

## 6. 当前 AI 能力状态

**Current: AI Phase 1 — 接口预留 (per tech blueprint Chapter 10)**

- No AI service implemented
- No LLM integration
- No RAG pipeline
- No embedding service
- No vector search
- `pyproject.toml` lists AI dependencies as optional: `langchain>=0.3.0`, `llama-index>=0.12.0`, `openai>=1.58.0`
- `.env.example` has OPENAI_API_KEY, ANTHROPIC_API_KEY placeholders
- AI packages not installed (optional extras not selected)

**Status:** Correctly deferred per MVP phase planning. The tech blueprint explicitly states:
> Phase 1: AI 接口预留 | MVP | 当前
> Phase 2: RAG | Post-MVP | 排队
> Phase 3: GraphRAG | Post-MVP | 排队
> Phase 4: Research Agent | Post-MVP | 排队

---

## 7. 当前 docs 与代码差距

| Document Scope | What Code Has | Gap |
|---------------|---------------|-----|
| 1704 Permission & Workspace | Nothing | Complete gap — 0% |
| 1701 Version Center | Nothing | Complete gap — 0% |
| Passage model (0804) | Nothing | Complete gap — 0% |
| Book model (0802) | Nothing | Complete gap — 0% |
| Paper model (0805) | Nothing | Complete gap — 0% |
| Knowledge Graph (0809) | Nothing | Complete gap — 0% |
| 1706 Unified Search | Nothing | Complete gap — 0% |
| 1705 AI Research Workspace | Nothing | Complete gap — 0% |
| User / RBAC | Nothing | Complete gap — 0% |
| Document model (0801-like) | ✅ Implemented | Partial — has Document (generic 文献), need Book/Version/Passage subtypes |
| Person model (0801) | ✅ Implemented | Good match |
| 1708 Platform Integration | ⚠️ Partial | Layered architecture correct; missing capability centers (Search, Graph, AI, Evidence, Citation services) |
| HFB-ARC-0201 Blueprint | ✅ Aligned | Monorepo, FastAPI, Vue3, layered architecture all match |
| 0506 Testing Standard | ⚠️ Partial | Unit tests exist; no integration/E2E/API/permission/AI/graph/search tests |
| 0504 API Design Standard | ⚠️ Partial | Envelope correct; no versioned entity CRUD APIs exist |
| 0502 Backend Standard | ✅ Good | Controller→Service→Repository→DB followed |

---

## 8. 已实现功能

1. **Monorepo structure** — apps/backend, apps/frontend, packages/{types,config,ui,utils}, docker/, tests/, tools/, docs/
2. **FastAPI backend scaffold** — app factory, CORS, health/ready/version/live/config endpoints
3. **Structured logging** — JSON (production) + Console (development) with request logging middleware
4. **Database layer** — SQLAlchemy 2.0 async with PostgreSQL target, BaseModel with UUID PK + timestamps + soft-delete
5. **Repository pattern** — Generic BaseRepository with CRUD, pagination, LIKE search
6. **Service layer** — Generic BaseService with validation hooks
7. **Pydantic schemas** — DocumentCreate/Response/Brief, PersonCreate/Response/Brief, pagination
8. **Seed data** — 3 persons (皇甫谧, 张仲景, 李时珍) + 3 documents (针灸甲乙经, 伤寒杂病论, 本草纲目)
9. **Infrastructure health checks** — Concurrent check of PostgreSQL, Redis, Elasticsearch, MinIO
10. **Vue 3 frontend scaffold** — Router, Pinia store, i18n (zh-CN/en), theme (light/dark/auto)
11. **Frontend system dashboard** — Live health check display with StatusCard components
12. **Docker Compose dev** — Backend, Frontend, PostgreSQL (pgvector), Redis, Elasticsearch, MinIO
13. **Docker Compose prod** — (exists, not verified)
14. **GitHub Actions CI** — 5 workflows: docs, lint, test, build, security
15. **HGT (HFB Governance Toolkit)** — `python3 -m tools.hgt docs validate` ✅ passes
16. **TypeScript shared types** — @hfb/types package with Document, Person, ApiResponse, utility types
17. **Development scripts** — setup.sh, dev.sh, lint.sh, test.sh, format.sh, release.sh + Makefile (14 targets)
18. **Python testing** — 51 pytest unit tests, all passing
19. **Frontend testing** — 3 vitest tests, all passing
20. **TypeScript typecheck** — All packages pass `tsc --noEmit` / `vue-tsc --noEmit`

---

## 9. 缺失功能 (MVP 范围内)

| # | Feature | Spec Reference | Priority |
|---|---------|---------------|----------|
| 1 | **User & RBAC** (用户与权限) | 1704; MVP Ch.3,12 | P0 — blocking |
| 2 | **JWT Authentication** | Blueprint Ch.12 | P0 — blocking |
| 3 | **Version Center** (版本中心) | 1701; MVP Ch.3 | P0 |
| 4 | **Book Center** (书籍中心) | 0802; MVP Ch.3 | P0 |
| 5 | **Passage Center** (段落中心) | 0804; MVP Ch.3 | P0 |
| 6 | **Person Center** — API routes | 0801; MVP Ch.3 | P0 (models exist, no API) |
| 7 | **Knowledge Graph** | 1707; 0809; MVP Ch.7 | P0 |
| 8 | **Unified Search** | 1706; MVP Ch.3 | P0 |
| 9 | **AI Research Workspace** | 1705; MVP Ch.3,6 | P0 |
| 10 | **Dashboard** | MVP Ch.8 | P0 |
| 11 | **Evidence System** | MVP Ch.10 | P0 |
| 12 | **Citation System** | MVP Ch.10 | P0 |
| 13 | **Workspace/Research Session** | 1705 Ch.9 | P0 |
| 14 | **API CRUD routes** for existing models | 0504 | P0 |
| 15 | **Integration tests** | 0506; MVP Ch.11 | P1 |
| 16 | **E2E tests** | 0506; MVP Ch.11 | P1 |
| 17 | **API tests** | 0506; MVP Ch.11 | P1 |
| 18 | **Permission tests** | MVP Ch.11 | P1 |
| 19 | **AI tests** | MVP Ch.11 | P1 |
| 20 | **Graph tests** | MVP Ch.11 | P1 |
| 21 | **Search tests** | MVP Ch.11 | P1 |
| 22 | **Security** (RBAC, JWT, input validation, XSS/CSRF/Prompt Injection) | MVP Ch.12 | P0 |
| 23 | **Evidence + Citation services** | 1708 Ch.3 | P0 |
| 24 | **Search Service** (unified) | 1708 Ch.9 | P0 |
| 25 | **Graph Service** | 1708 Ch.8 | P0 |
| 26 | **AI Service** | 1708 Ch.7 | P0 |

---

## 10. 阻塞 MVP 的问题

### 🔴 Critical (must fix before development can proceed)

1. **`elasticsearch_url` missing from Settings** — `/ready` endpoint will crash at runtime. Must add `ELASTICSEARCH_HOST`, `ELASTICSEARCH_PORT` fields and `elasticsearch_url` property to `core/config.py`.

2. **DefaultLayout import path mismatch** — `DefaultLayout.vue` imports `./AppNavbar.vue` etc., but those files are in `components/layout/`, not `layouts/`. Frontend will fail to render.

3. **ESLint can't parse `.vue` files** — 8 parsing errors across all .vue files. The eslint config defines a Vue processor but the parsing is broken. Likely root cause: `eslint.config.mjs` uses `await import()` for plugins but may be missing proper Vue SFC parser setup. This blocks lint CI.

### 🟡 High (should fix in Phase 1)

4. **44 Ruff lint errors** — Unused imports, boolean comparison style (E712), redefined fixtures. Many auto-fixable. Should clean before Phase 2.

5. **`app/api/` has no `__init__.py`** — Relies on Python 3.12+ implicit namespace packages. Works but fragile. Adding `__init__.py` is recommended.

6. **Duplicate `alembic.ini`** — Exists at both `apps/backend/alembic.ini` and `apps/backend/app/db/alembic.ini`. Consolidate.

7. **No `.env` file exists** — `.env.example` exists but `.env` is missing. Development can't start without manual copy. `setup.sh` creates it automatically though.

### 🟢 Info (design gaps, not bugs)

8. **No API routes for existing Document/Person models** — Models, repos, services, schemas all exist but v1 router is empty. This is intentional (Sprint scoping) but must be resolved before MVP can claim CRUD functionality.

9. **No auth/protection on any endpoints** — All endpoints are public. Must add before any production deployment.

10. **Packages mostly placeholder** — `packages/config/`, `packages/ui/`, `packages/utils/` contain only stubs. Only `packages/types/` has meaningful content.

---

## Summary Numbers

| Metric | Count |
|--------|-------|
| Backend .py files | 28 (excluding __pycache__) |
| Frontend .ts/.vue files | 18 source + 1 test |
| Python tests | 51 (all passing) |
| Frontend tests | 3 (all passing) |
| Domain models implemented | 2 (Document, Person) of ~10 MVP required |
| API endpoints live | 5 (health, ready, version, live, config) |
| API endpoints needed for MVP | ~40+ (estimated) |
| Ruff lint errors | 44 |
| ESLint errors | 12 |
| TypeScript errors | 0 |
| Critical blockers | 3 |
| High issues | 4 |
| Docs files tracked | 291 |
| HGT validate | ✅ Pass |
