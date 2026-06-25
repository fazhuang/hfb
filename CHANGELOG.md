# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.10.0] - 2025-06-25

### Added — MVP Phases 6-10
- **Phase 6: Knowledge Graph** — EntityRelation model, GraphService (BFS path finding, neighborhood, subgraph), 7 graph API endpoints, GraphExplorerView + GraphCanvas.vue (vis-network force layout), FK-derived edges auto-computed
- **Phase 7: Unified Search** — SearchService (ILIKE cross-entity search with scoring, snippets), autocomplete, reindex, 3 search API endpoints, SearchView with faceted filters and pagination
- **Phase 8: AI Research Workspace** — AIService (streaming chat, summarize, translate, AI compare), RAGService (hybrid retrieval + context assembly), ResearchSession/ResearchNote models, 9 AI/workspace API endpoints, WorkspaceView three-panel layout
- **Phase 9: Dashboard** — DashboardService (entity counts, activity, dynasty/category distributions), 2 dashboard API endpoints, DashboardView with stats cards + bar charts
- **Phase 10: Testing & Production Readiness** — RBAC security audit, workspace IDOR fixes, double API prefix fix, Playwright E2E test scaffolding, full verification (197 tests, ruff/lint/typecheck green)

### Security
- Fixed double `/api/v1` prefix in child routers causing `/api/v1/api/v1/...` URLs
- Fixed workspace session/note IDOR — added user ownership checks on all workspace endpoints
- Added `graph`, `search`, `ai`, `dashboard` RBAC permissions to role seed
- Added RBAC endpoint coverage audit (73 endpoints, all properly guarded)

### Changed
- All child API routers no longer duplicate `prefix="/api/v1"` (parent router provides it)
- Workspace routes now verify session ownership via `get_current_user`

## [0.2.0] - 2025-06-24

### Added
- Complete monorepo directory structure (`apps/`, `packages/`, `docker/`, `deploy/`, `infra/`, `scripts/`, `tests/`, `tools/`)
- GitHub community health files (ISSUE_TEMPLATE, PR_TEMPLATE, CODEOWNERS, SECURITY.md, CODE_OF_CONDUCT.md)
- Root-level project documentation (README, LICENSE, CHANGELOG, CONTRIBUTING, ROADMAP, PROJECT_STATUS)
- Git standardization (.editorconfig, .gitattributes, .gitignore, .pre-commit-config.yaml)
- Python development standards (pyproject.toml, ruff.toml, mypy.ini, pytest.ini)
- Node.js development standards (package.json, pnpm-workspace.yaml, eslint, prettier, lint-staged)
- Docker configurations (docker-compose.dev.yml, docker-compose.prod.yml, .env.example)
- CI/CD pipelines (docs, lint, test, build, security)
- Utility scripts (setup, dev, lint, test, format, release)
- Document templates (ADR, API, Sprint, Review, Issue, Meeting)
- Monorepo packages scaffolding (types, config, ui, utils)
- Test directory structure (unit, integration, e2e, fixtures)
- VS Code workspace configuration (settings, extensions, launch, tasks)
- Makefile with full development lifecycle targets

### Changed
- Reorganized repository from flat structure to monorepo layout

## [0.7.0] - 2025-06-24

### Added — Sprint 6
- Full CRUD REST API for all 4 entities (documents, persons, herbs, prescriptions)
- Entity-specific full-text search endpoints: `/api/v1/search/documents` etc.
- Unified search endpoint: `/api/v1/search?q=...&entity=...`
- Graph API: node lookup, related nodes, neighborhood, shortest path, graph search, stats
- API versioning: `/api/v1/` prefix with shared CRUD helpers
- Paginated response helper with metadata (page, limit, total, total_pages)
- Main router updated to register v1 API router
- OpenAPI 3.1 auto-documentation via FastAPI + Pydantic response models

## [0.6.0] - 2025-06-24

### Added — Sprint 4 & 5
- **Knowledge Graph Engine (Sprint 4)**:
  - Neo4j connection management (async driver, session factory, health check)
  - Ontology schema: 9 node labels, 14 relationship types, property definitions
  - Type-safe Cypher query builder (node CRUD, relationships, traversal, search)
  - Graph ingestion pipeline (PostgreSQL → Neo4j full sync)
  - GraphRepository: high-level async API for node/relationship CRUD
  - Graph traversal: find_related, shortest_path, neighborhood
  - Entity resolution via fuzzy name matching
  - Co-occurrence relationship extraction
- **Vector Search & RAG (Sprint 5)**:
  - Milvus connection management (Lite mode for dev, server mode for prod)
  - Embedding pipeline: OpenAI text-embedding-3-small, batched generation
  - Text chunking: simple character-based + recursive sentence-boundary splitter
  - VectorStore: insert, search, batch search, hybrid search (dense + keyword)
  - VectorStoreManager: 3 collections (documents, herbs, prescriptions)
  - RAGChain: retrieve → re-rank → generate with source citations
  - Chinese-medicine-specific RAG prompt template
  - Re-ranking: MMR (Maximal Marginal Relevance), deduplication, metadata filtering
  - Vector ingestion pipeline (PostgreSQL → Milvus sync)

### Changed
- Settings: added Neo4j and Milvus configuration

## [0.5.0] - 2025-06-24

### Added
- Domain models: Document (文献), Person (人物), Herb (药材), Prescription (方剂)
- SQLAlchemy 2.0 async ORM models with full relationship mapping
- ForeignKey on Document.author_id → Person.id with ON DELETE SET NULL
- Pydantic schema layer: Base/Create/Brief/Response per entity + PaginationParams
- BaseRepository: generic async CRUD with pagination, search (contains), soft-delete, hard-delete
- Entity repositories: DocumentRepository, PersonRepository, HerbRepository, PrescriptionRepository
- Specialised query methods: get_by_dynasty, get_by_category, get_by_nature, search_query
- BaseService: generic service with validation hooks
- Entity services: DocumentService, PersonService, HerbService, PrescriptionService
- Alembic migration framework (env.py, script.py.mako, alembic.ini)
- Seed data: 3 persons, 3 documents, 5 herbs, 2 prescriptions
- Database testing utilities: in-memory SQLite fixtures (db_session, db_session_persistent)

### Changed
- Base model: UUID PK switched to String(36) for SQLite/PostgreSQL portability
- All model annotations use `Optional[X]` instead of `X | None` for SQLAlchemy 2.0 compat
- Repository layer no longer empty placeholder — full CRUD implementation
- Service layer no longer empty placeholder — validation + orchestration

### Fixed
- Document.language default now set via __init__ for non-DB contexts
- contains() used instead of ilike() for portable text search
- Search condition uses AND(is_deleted=False) rather than OR with is_deleted

## [0.4.0] - 2025-06-24

### Added
- i18n framework with vue-i18n (zh-CN & en locales, browser detection, localStorage persistence)
- Dark mode support (light/dark/auto themes via CSS custom properties)
- Layout system: DefaultLayout with AppNavbar, AppMain, AppFooter
- AppNavbar component: responsive navigation with mobile hamburger menu
- Locale switcher widget in navbar (中/EN toggle)
- Theme toggle widget in navbar (light → dark → auto cycle)
- Reusable StatusCard component with connected/disconnected states
- Reusable PlaceholderPage component for upcoming views
- Full Vue Router configuration: 6 routes (/, /search, /knowledge, /documents, /herbs, /about)
- Lazy-loaded route components via dynamic imports
- Design token system: CSS custom properties for light & dark themes
- About page with vision statement and tech stack grid
- SearchView, KnowledgeView, DocumentsView, HerbsView placeholder pages

### Changed
- HomeView refactored to use StatusCard components and i18n
- App.vue simplified — theme initialized via useTheme composable
- CSS reset and global styles use CSS custom properties
- Router updated: nested routes under DefaultLayout
- main.ts now registers i18n plugin

### Fixed
- TypeScript baseUrl in frontend tsconfig ensures @/* alias resolves
- Added missing tsconfig.json for @hfb/ui and @hfb/utils packages
- Vue type declarations included in tsconfig include paths

## [0.3.0] - 2025-06-24

### Added
- Backend: FastAPI application entry point with lifecycle management (`apps/backend/main.py`)
- Backend: Health, Readiness, Version, and Config API endpoints (`apps/backend/app/api/`)
- Backend: Application settings with Pydantic Settings (`apps/backend/app/core/config.py`)
- Backend: SQLAlchemy 2.0 async database engine and session management (`apps/backend/app/db/database.py`)
- Backend: Base database model with UUID PK, timestamps, and soft-delete (`apps/backend/app/db/base.py`)
- Backend: Structured logging configuration (`apps/backend/app/core/logging.py`)
- Backend: Infrastructure startup checks (`apps/backend/app/startup/`)
- Frontend: Vue 3 application scaffold (`apps/frontend/`)
- Frontend: Axios API client with typed health endpoints (`apps/frontend/src/api/client.ts`)
- Frontend: Pinia system store for connection health tracking (`apps/frontend/src/stores/system.ts`)
- Tests: Backend unit tests — 13 tests covering health endpoints, settings, base model
- Tests: Frontend unit tests — 3 tests covering systemStore with mocked API client
- Tests: Conftest with sys.path setup for backend test imports

### Fixed
- Vitest configuration: test files relocated to `apps/frontend/src/__tests__/`
- Vitest runs strictly from `apps/frontend/` directory with correct `@` aliases
- Backend tests: installed missing `asyncpg` dependency
- Root `package.json` test scripts delegate to `@hfb/frontend` via pnpm filter

## [0.1.0] - 2025-06-22

### Added
- Initial project documentation in `/docs/`
- Project governance and constitution
- Product roadmap v0
- Technical architecture blueprint
- Data standards and ontology specifications
- AI engineering standards (RAG, GraphRAG)
- Development standards
- UI design system guidelines
- Security acceptance specifications
- Sprint planning framework
- Prompt engineering templates
- System architecture diagrams
- Architecture Decision Records (ADR-0001 through ADR-0010)
- Decision tree documentation
- Machine-readable project metadata
