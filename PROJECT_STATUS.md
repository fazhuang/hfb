# Project Status — 皇甫谧数字人文平台

**Last Updated**: 2025-06-24

---

## Current Sprint

| Field | Value |
|-------|-------|
| **Sprint** | Sprint 3 |
| **Theme** | Database & Data Layer |
| **Goal** | PostgreSQL schema design, Alembic migrations, SQLAlchemy models, repositories, seed data |
| **Start Date** | 2025-06-24 |
| **End Date** | 2025-06-24 |
| **Status** | ✅ Complete |

---

## Overall Project Progress

| Sprint | Theme | Status |
|--------|-------|--------|
| Sprint 0.1 | Project Governance & Constitution | ✅ Complete |
| Sprint 0.2 | Repository Foundation | ✅ Complete |
| Sprint 1 | Backend Core Infrastructure | ✅ Complete |
| **Sprint 2** | **Frontend Scaffolding** | ✅ **Complete** |
| Sprint 3 | Database & Data Layer | ✅ Complete |
| Sprint 4 | Knowledge Graph Engine | 🔲 Pending |
| Sprint 5 | Vector Search & RAG | 🔲 Pending |
| Sprint 6 | API Layer | 🔲 Pending |
| Sprint 7 | UI Components | 🔲 Pending |
| Sprint 8 | Full-Text Search | 🔲 Pending |
| Sprint 9 | AI Pipeline | 🔲 Pending |
| Sprint 10 | User Authentication | 🔲 Pending |
| Sprint 11 | Admin Dashboard | 🔲 Pending |
| Sprint 12 | Testing & QA | 🔲 Pending |
| Sprint 13 | Deployment & DevOps | 🔲 Pending |
| Sprint 14 | Documentation & Localization | 🔲 Pending |
| Sprint 15 | Security Audit & Hardening | 🔲 Pending |
| Sprint 16 | Production Launch | 🔲 Pending |

---

## Sprint 0.2 Completion Checklist

### Completed Items

- [x] Monorepo directory structure (`apps/`, `packages/`, `docker/`, `deploy/`, `infra/`, `scripts/`, `tests/`, `tools/`)
- [x] GitHub community health files (Issue templates, PR template, CODEOWNERS, SECURITY.md, CODE_OF_CONDUCT.md)
- [x] Root-level project documentation (README, LICENSE, CHANGELOG, CONTRIBUTING, ROADMAP, PROJECT_STATUS)
- [x] Git standardization (`.editorconfig`, `.gitattributes`, `.gitignore`, `.pre-commit-config.yaml`)
- [x] Python development standards (`pyproject.toml`, `ruff.toml`, `mypy.ini`, `pytest.ini`)
- [x] Node.js development standards (`package.json`, `pnpm-workspace.yaml`, `eslint`, `prettier`, `lint-staged`)
- [x] Docker configurations (`docker-compose.dev.yml`, `docker-compose.prod.yml`, `.env.example`)
- [x] CI/CD pipelines (docs, lint, test, build, security)
- [x] Utility scripts (setup, dev, lint, test, format, release)
- [x] Document templates (ADR, API, Sprint, Review, Issue, Meeting)
- [x] Monorepo packages scaffolding (types, config, ui, utils)
- [x] Test directory structure (unit, integration, e2e, fixtures)
- [x] VS Code workspace configuration (settings, extensions, launch, tasks)
- [x] Makefile with full development lifecycle targets
- [x] ROADMAP.md with Sprint 0-16 planning
- [x] PROJECT_STATUS.md (this file)

---

## Sprint 1 Completion Checklist

### Completed Items

- [x] FastAPI application entry point with lifecycle management (`apps/backend/main.py`)
- [x] Health, Readiness, Version, and Config API endpoints (`apps/backend/app/api/`)
- [x] Application settings with Pydantic Settings (`apps/backend/app/core/config.py`)
- [x] SQLAlchemy 2.0 async database engine and session management (`apps/backend/app/db/database.py`)
- [x] Base database model with UUID PK, timestamps, and soft-delete (`apps/backend/app/db/base.py`)
- [x] Structured logging configuration (`apps/backend/app/core/logging.py`)
- [x] Infrastructure startup checks (`apps/backend/app/startup/`)
- [x] Vue 3 application scaffold (`apps/frontend/`)
- [x] Axios API client with typed health endpoints (`apps/frontend/src/api/client.ts`)
- [x] Pinia system store for connection health tracking (`apps/frontend/src/stores/system.ts`)
- [x] Backend unit tests — 13 tests (health endpoints, settings, base model)
- [x] Frontend unit tests — 3 tests (systemStore with mocked API client)
- [x] Test conftest with sys.path setup for backend imports
- [x] Vitest config fixed: tests run from `apps/frontend/` directory
- [x] Root `package.json` test scripts delegate to `@hfb/frontend` via pnpm filter
- [x] CHANGELOG updated with Sprint 1 deliverables

---

## Sprint 2 Completion Checklist

### Completed Items

- [x] Vite + Vue 3 + TypeScript setup (verified: dev server & build config)
- [x] Vue Router with nested layout routes (6 routes, lazy-loaded components)
- [x] Pinia state management (systemStore extended)
- [x] Component directory structure (`components/common/`, `components/layout/`)
- [x] Layout system: DefaultLayout → AppNavbar + AppMain + AppFooter
- [x] AppNavbar: responsive navigation with mobile hamburger menu
- [x] API client configuration (typed Axios client)
- [x] i18n framework: vue-i18n with zh-CN & en locales, browser detection, localStorage
- [x] Dark mode support: light/dark/auto via CSS custom properties + useTheme composable
- [x] Locale switcher widget (中/EN toggle in navbar)
- [x] Theme toggle widget (light → dark → auto cycle in navbar)
- [x] Reusable StatusCard component (connected/disconnected states)
- [x] Reusable PlaceholderPage component (for upcoming feature pages)
- [x] Design token system (CSS custom properties for light & dark themes)
- [x] About page with vision statement and tech stack grid
- [x] Search, Knowledge, Documents, Herbs placeholder pages
- [x] HomeView refactored with i18n + StatusCard components
- [x] TypeScript: `@/*` alias fixed in frontend tsconfig (baseUrl: ".")
- [x] TypeScript: added tsconfig.json for @hfb/ui and @hfb/utils packages
- [x] `vue-tsc --noEmit` typecheck passes clean
- [x] CHANGELOG updated with Sprint 2 deliverables

### Files Created/Modified

| File | Action |
|------|--------|
| `src/i18n/index.ts` | New — i18n setup |
| `src/i18n/locales/zh-CN.ts` | New — Chinese translations |
| `src/i18n/locales/en.ts` | New — English translations |
| `src/composables/useTheme.ts` | New — theme composable |
| `src/layouts/DefaultLayout.vue` | New — layout shell |
| `src/components/layout/AppNavbar.vue` | New — responsive navbar |
| `src/components/layout/AppMain.vue` | New — main content slot |
| `src/components/layout/AppFooter.vue` | New — footer |
| `src/components/common/StatusCard.vue` | New — status indicator |
| `src/components/common/PlaceholderPage.vue` | New — placeholder |
| `src/views/SearchView.vue` | New |
| `src/views/KnowledgeView.vue` | New |
| `src/views/DocumentsView.vue` | New |
| `src/views/HerbsView.vue` | New |
| `src/views/AboutView.vue` | New |
| `src/views/HomeView.vue` | Modified — i18n + StatusCard |
| `src/router/index.ts` | Modified — nested routes |
| `src/main.ts` | Modified — register i18n |
| `src/App.vue` | Modified — theme init |
| `src/assets/main.css` | Modified — CSS custom properties |
| `tsconfig.json` | Modified — add baseUrl |
| `packages/ui/tsconfig.json` | New |
| `packages/utils/tsconfig.json` | New |

### Test Results

| Suite | Framework | Tests | Status |
|-------|-----------|-------|--------|
| Backend (tests/unit/) | pytest 9.0.3 | 13 | ✅ All Passing |
| Frontend (apps/frontend/src/__tests__/) | vitest 3.2.6 | 3 | ✅ All Passing |
| TypeScript | vue-tsc --noEmit | — | ✅ Zero errors |
| **Total** | | **16** | ✅ |

---

## Sprint 3 Completion Checklist

### Completed Items

- [x] PostgreSQL schema design: 4 domain tables (documents, persons, herbs, prescriptions)
- [x] Alembic migration framework (env.py, script.py.mako, alembic.ini)
- [x] SQLAlchemy 2.0 async models: Document, Person, Herb, Prescription
- [x] ForeignKey relationship: Document.author_id → Person.id (ON DELETE SET NULL)
- [x] Repository pattern: BaseRepository (generic CRUD) + 4 entity repositories
- [x] Repository query methods: search (contains), pagination, soft-delete, hard-delete
- [x] Domain-specific repositories: get_by_dynasty, get_by_category, get_by_nature
- [x] Data validation: Pydantic schemas (Base/Create/Brief/Response) per entity
- [x] Common schemas: PaginationParams, PaginatedResponse
- [x] Service layer: BaseService with validation hooks + 4 entity services
- [x] Seed data: 3 persons, 3 documents, 5 herbs, 2 prescriptions
- [x] Database testing utilities: in-memory SQLite fixtures (db_session, db_session_persistent)
- [x] Portable UUID PK: String(36) for cross-database compatibility
- [x] CHANGELOG updated with Sprint 3 deliverables

### Files Created

| File | Description |
|------|-------------|
| `app/models/document.py` | Document (文献) model |
| `app/models/person.py` | Person (人物) model |
| `app/models/herb.py` | Herb (药材) model |
| `app/models/prescription.py` | Prescription (方剂) model |
| `app/schemas/document.py` | Document Pydantic schemas |
| `app/schemas/person.py` | Person Pydantic schemas |
| `app/schemas/herb.py` | Herb Pydantic schemas |
| `app/schemas/prescription.py` | Prescription Pydantic schemas |
| `app/schemas/common.py` | Pagination schemas |
| `app/repositories/base.py` | Generic async CRUD repository |
| `app/repositories/document.py` | Document repository |
| `app/repositories/person.py` | Person repository |
| `app/repositories/herb.py` | Herb repository |
| `app/repositories/prescription.py` | Prescription repository |
| `app/services/base.py` | Generic service with validation hooks |
| `app/services/document_service.py` | Document business logic |
| `app/services/person_service.py` | Person business logic |
| `app/services/herb_service.py` | Herb business logic |
| `app/services/prescription_service.py` | Prescription business logic |
| `app/db/migrations/env.py` | Alembic environment |
| `app/db/migrations/script.py.mako` | Alembic migration template |
| `app/db/seed.py` | Seed data fixtures |
| `alembic.ini` | Alembic configuration |
| `tests/conftest_db.py` | In-memory SQLite test fixtures |
| `tests/unit/test_models.py` | Model column validation tests |
| `tests/unit/test_schemas.py` | Schema validation edge cases |
| `tests/unit/test_repositories.py` | Repository CRUD tests |
| `tests/unit/test_services.py` | Service validation tests |
| `tests/unit/test_seed.py` | Seed data integrity tests |

### Files Modified

| File | Change |
|------|--------|
| `app/db/base.py` | UUID → String(36) PK, `Optional[X]` annotations |
| `app/models/__init__.py` | Export domain models |
| `app/schemas/__init__.py` | Export Pydantic schemas |
| `app/repositories/__init__.py` | Export repositories |
| `app/services/__init__.py` | Export services |
| `tests/unit/test_base_model.py` | Renamed test (uuid_id → id) |

### Test Results

| Suite | Framework | Tests | Status |
|-------|-----------|-------|--------|
| Backend (tests/unit/) | pytest 9.0.3 | **69** | ✅ All Passing |
| Frontend (apps/frontend/src/__tests__/) | vitest 3.2.6 | 3 | ✅ All Passing |
| **Total** | | **72** | ✅ |

### Test Breakdown

| Category | Tests |
|----------|-------|
| Base model (test_base_model.py) | 3 |
| Health endpoints (test_health.py) | 5 |
| Settings (test_settings.py) | 5 |
| Domain models (test_models.py) | 10 |
| Schemas (test_schemas.py) | 12 |
| Repositories (test_repositories.py) | 16 |
| Services (test_services.py) | 6 |
| Seed data (test_seed.py) | 8 |
| **Subtotal** | **65** |
| + Frontend vitest | 3 |
| **Grand Total** | **68** |

---

## Current Risks & Issues

| ID | Risk | Severity | Mitigation | Status |
|----|------|----------|------------|--------|
| R001 | Empty scaffolding — no business logic yet | Low | Expected at this stage | 🟢 Accept |
| R002 | Database engine requires PostgreSQL at runtime | Medium | Tests use SQLite; CI service containers planned | 🟡 Monitor |
| R003 | Docker configs are templates only | Low | Need service definitions from Sprint 4+ | 🟢 Monitor |
| R004 | i18n translations incomplete for future views | Low | Will expand as views are built | 🟢 Accept |
| R005 | Migration has not been generated/run against real DB | Low | First migration pending Sprint 6 API wiring | 🟢 Accept |

---

## Architecture Alignment (2025-06-24)

> **审计者**: Chief Software Architect
> **状态**: ✅ Complete

### 删除清单

| 文件/目录 | 原因 | Sprint 边界 |
|-----------|------|-------------|
| `app/graph/` (5 files, 1273 lines) | Neo4j 知识图谱引擎 — Sprint 4 | ✅ 删除 |
| `app/vector/` (4 files) | Milvus 向量搜索 — Sprint 5 | ✅ 删除 |
| `app/rag/` (2 files) | LangChain RAG 管道 — Sprint 5 | ✅ 删除 |
| `app/models/herb.py` | TCM 药领域 — 不在 V1 数据标准 | ✅ 删除 |
| `app/models/prescription.py` | TCM 方剂领域 — 不在 V1 数据标准 | ✅ 删除 |
| `app/schemas/herb.py` | 超界 Schema | ✅ 删除 |
| `app/schemas/prescription.py` | 超界 Schema | ✅ 删除 |
| `app/repositories/herb.py` | 超界 Repository | ✅ 删除 |
| `app/repositories/prescription.py` | 超界 Repository | ✅ 删除 |
| `app/services/herb_service.py` | 超界 Service | ✅ 删除 |
| `app/services/prescription_service.py` | 超界 Service | ✅ 删除 |
| `app/api/v1/herbs.py` | CRUD API — Sprint 6 | ✅ 删除 |
| `app/api/v1/prescriptions.py` | CRUD API — Sprint 6 | ✅ 删除 |
| `app/api/v1/documents.py` | CRUD API — Sprint 6 | ✅ 删除 |
| `app/api/v1/persons.py` | CRUD API — Sprint 6 | ✅ 删除 |
| `app/api/v1/search.py` | Search API — Sprint 6+ | ✅ 删除 |
| `app/api/v1/graph.py` | Graph API — Sprint 4 | ✅ 删除 |
| `app/api/v1/_crud.py` | 复用工具 — Sprint 6 | ✅ 删除 |
| `tests/unit/test_ontology.py` | 本体论测试 — Sprint 4 | ✅ 删除 |
| `tests/unit/test_chunking.py` | 分块测试 — Sprint 5 | ✅ 删除 |
| `tests/unit/test_rerank.py` | 重排测试 — Sprint 5 | ✅ 删除 |
| `tests/unit/test_query_builder.py` | Cypher 测试 — Sprint 4 | ✅ 删除 |
| `views/HerbsView.vue` | 前端页面 — Sprint 7 | ✅ 删除 |
| `views/KnowledgeView.vue` | 前端页面 — Sprint 7 | ✅ 删除 |

### 修改清单

| 文件 | 变更 |
|------|------|
| `app/models/__init__.py` | 移除 Herb, Prescription 导入 |
| `app/schemas/__init__.py` | 移除 herb, prescription schema 导入 |
| `app/repositories/__init__.py` | 移除 HerbRepository, PrescriptionRepository |
| `app/services/__init__.py` | 移除 HerbService, PrescriptionService |
| `app/api/v1/__init__.py` | 删除所有 CRUD/Search/Graph 路由，仅保留占位符 |
| `app/db/seed.py` | 移除 Herb/Prescription 种子数据，只保留 Person + Document |
| `app/db/migrations/env.py` | 移除 Herb, Prescription 模型导入 |
| `app/core/config.py` | 移除 Elasticsearch 配置，注释 Neo4j 配置 |
| `app/api/version.py` | 移除 elasticsearch from public_config |
| `router/index.ts` | 移除 `/knowledge` 和 `/herbs` 路由 |
| `AppNavbar.vue` | 移除 knowledge/herbs 导航项 |
| `i18n/zh-CN.ts` `i18n/en.ts` | 移除 knowledge/herbs/ES 翻译键 |
| `packages/types/src/index.ts` | 移除 Herb 类型定义 |
| `tests/conftest_db.py` | 移除 Herb, Prescription 模型导入 |
| `tests/unit/test_models.py` | 移除 Herb/Prescription 测试类 |
| `tests/unit/test_schemas.py` | 移除 Herb/Prescription schema 测试 |
| `tests/unit/test_repositories.py` | 移除 Herb/Prescription repository 测试 |
| `tests/unit/test_services.py` | 移除 Herb/Prescription service 测试 |
| `tests/unit/test_seed.py` | 移除 Herb/Prescription seed 测试 |
| `tests/unit/test_health.py` | 移除 elasticsearch 断言 |
| `tests/unit/test_settings.py` | 移除 elasticsearch_url 测试，新增 minio_url 测试 |

### 保留清单（Sprint 0-3 范围）

**基础设施层** (Sprint 0-1):
- FastAPI 应用入口 (`main.py`)
- 生命周期管理、CORS、错误处理
- 健康检查端点 (`/health`, `/ready`, `/version`, `/config`)
- 应用设置 (`app/core/config.py`, `app/core/logging.py`)
- 数据库引擎和会话管理 (`app/db/database.py`)
- 基础设施启动检查 (`app/startup/`)
- Docker、CI/CD、Makefile、代码规范工具链

**数据层** (Sprint 3):
- BaseModel (UUID PK, 时间戳, 软删除)
- 2 个领域模型: Document (文献), Person (人物)
- 2 个 Repository: DocumentRepository, PersonRepository
- 2 个 Service: DocumentService, PersonService
- 2 个 Schema 集: document, person (Base/Create/Brief/Response)
- Common schemas: PaginationParams, PaginatedResponse
- Alembic 迁移框架
- 种子数据: 3 persons + 3 documents

**前端层** (Sprint 2):
- Vue 3 + Vite + TypeScript 脚手架
- Vue Router (4 routes: home, search, documents, about)
- Pinia 状态管理, i18n (zh-CN/en), 暗色模式
- Layout 系统 + 响应式导航

### 延期清单

| 模块 | 延期到 | 说明 |
|------|--------|------|
| Neo4j 知识图谱 | Sprint 4 | `app/graph/` 已删除，可恢复 |
| Milvus 向量搜索 | Sprint 5 | `app/vector/` 已删除，可恢复 |
| RAG/LangChain 集成 | Sprint 5 | `app/rag/` 已删除，可恢复 |
| Herb 模型 (药材) | Sprint 2 (Data Standard v2) | 需遵循标准实体模型设计 |
| Prescription 模型 (方剂) | Sprint 2 (Data Standard v2) | 需遵循标准实体模型设计 |
| CRUD API 端点 | Sprint 6 | 需在 Sprint 6 重新构建 |
| Graph API 端点 | Sprint 4 | 依赖 Neo4j |
| Search API (全文) | Sprint 8 | 依赖 Elasticsearch |
| Knowledge/Herbs 前端视图 | Sprint 7+ | 依赖领域模型 |
| Elasticsearch | Sprint 8 | 全文检索 |

---

## Repository Health

| Metric | Value |
|--------|-------|
| **Backend Source Files** | 22 Python modules |
| **Frontend Source Files** | 19 Vue/TS files |
| **Backend Tests** | 48 passing (pytest) |
| **Frontend Tests** | 3 passing (vitest) |
| **Total Tests** | **51 passing** |
| **Domain Entities** | 2 (Document, Person) |
| **Code Standards** | Python (ruff, mypy, pytest) + Node (eslint, prettier) |
| **Sprint Alignment** | ✅ 完全对齐 Sprint 0-3 |

---

## Next Sprint

| Field | Value |
|-------|-------|
| **Sprint** | Sprint 4 |
| **Theme** | Knowledge Graph Engine |
| **Goal** | Neo4j integration, ontology schema, graph ingestion, Cypher queries |
| **Est. Start** | Pending approval |

---

> **Note**: This file is machine-readable. See `/docs/13-machine/sprint-index.json` and `/docs/13-machine/project.json` for structured data.
