# MVP Implementation Plan — 皇甫谧数字人文平台

**Generated:** 2026-06-25
**Based on:** MVP_CODEBASE_AUDIT.md + HFB-PS-1709 + HFB-PS-1710 + HFB-ARC-0201
**Planning Framework:** 10 Phase incremental delivery

---

## Phase 1: 基础设施与项目骨架 ✅ IN PROGRESS

### 目标

确保 monorepo 可构建、可测试、可 lint、可运行；修复关键阻塞问题；建立开发基线。

### 修改文件

| File                                          | Change                                                                       |
| --------------------------------------------- | ---------------------------------------------------------------------------- |
| `apps/backend/app/core/config.py`             | Add `ELASTICSEARCH_HOST`, `ELASTICSEARCH_PORT`, `elasticsearch_url` property |
| `apps/frontend/src/layouts/DefaultLayout.vue` | Fix import paths for AppNavbar, AppMain, AppFooter                           |
| `eslint.config.mjs`                           | Fix Vue SFC parsing (ensure vue-eslint-parser is used)                       |
| `apps/backend/app/repositories/base.py`       | Fix `== False` → `is False` or `not ...` (E712)                              |
| `tests/unit/test_services.py`                 | Remove unused imports, fix fixture redefinition                              |
| Various files                                 | Auto-fix ruff lint issues                                                    |

### 新增文件

| File                               | Purpose                   |
| ---------------------------------- | ------------------------- |
| `apps/backend/app/api/__init__.py` | Explicit package marker   |
| `MVP_CODEBASE_AUDIT.md`            | Codebase status report    |
| `MVP_IMPLEMENTATION_PLAN.md`       | This file                 |
| `PHASE1_IMPLEMENTATION_REPORT.md`  | Phase 1 completion report |

### 验证命令

```bash
pnpm install          # ✅ Done — succeeds
pnpm lint             # ❌ 12 errors — MUST fix
pnpm typecheck        # ✅ Done — passes
pnpm test             # ✅ Done — 3 pass
pytest tests/unit     # ✅ Done — 51 pass
ruff check .          # ❌ 44 errors — MUST fix
python3 -m tools.hgt docs validate  # ✅ Done — passes
python3 -m tools.hgt docs report    # ✅ Done — passes
```

### 验收标准

- [ ] `pnpm lint` passes (0 errors)
- [ ] `ruff check apps/ tests/ tools/` passes (0 errors)
- [ ] `pnpm typecheck` passes (already ✅)
- [ ] `pnpm test` passes (already ✅)
- [ ] `pytest tests/unit` passes (already ✅)
- [ ] Docker Compose dev config validates
- [ ] HGT docs validate passes (already ✅)
- [ ] No critical blockers remain

### 不做什么

- 不新增任何领域模型
- 不新增任何 API 路由
- 不新增任何功能
- 不修改 docs/ 下的任何文件

---

## Phase 2: 用户与权限

### 目标

实现 RBAC 用户体系，JWT 认证，基础权限控制。所有后续模块依赖此 Phase。

### 数据模型

- **User** — id, username, email, hashed_password, display_name, affiliation, is_active, is_superuser
- **Role** — id, name, description
- **UserRole** — user_id, role_id (many-to-many)
- **Permission** — id, resource, action, description
- **RolePermission** — role_id, permission_id

### 修改文件

| File                                    | Change                                                |
| --------------------------------------- | ----------------------------------------------------- |
| `apps/backend/app/models/user.py`       | New User, Role, Permission models                     |
| `apps/backend/app/schemas/user.py`      | UserCreate, UserResponse, LoginRequest, TokenResponse |
| `apps/backend/app/repositories/user.py` | UserRepository                                        |
| `apps/backend/app/services/user.py`     | UserService (hash, verify, token generation)          |
| `apps/backend/app/api/v1/__init__.py`   | Register auth routes                                  |
| `apps/backend/app/core/config.py`       | Add JWT settings                                      |
| `apps/backend/main.py`                  | Add auth middleware                                   |

### 新增文件

| File                                        | Purpose                                    |
| ------------------------------------------- | ------------------------------------------ |
| `apps/backend/app/models/user.py`           | User/Role/Permission SQLAlchemy models     |
| `apps/backend/app/schemas/user.py`          | Auth Pydantic schemas                      |
| `apps/backend/app/repositories/user.py`     | User data access                           |
| `apps/backend/app/services/auth_service.py` | JWT, password hashing, token management    |
| `apps/backend/app/api/v1/auth.py`           | POST /auth/login, /auth/register, /auth/me |
| `apps/backend/app/api/v1/users.py`          | CRUD /users (admin)                        |
| `apps/backend/app/middleware/auth.py`       | JWT dependency + RBAC guard                |
| `apps/frontend/src/stores/auth.ts`          | Auth Pinia store                           |
| `apps/frontend/src/views/LoginView.vue`     | Login page                                 |
| `apps/frontend/src/router/guards.ts`        | Auth navigation guards                     |
| `tests/unit/test_auth.py`                   | Auth unit tests                            |
| `tests/unit/test_user_models.py`            | User model tests                           |
| `tests/unit/test_permissions.py`            | Permission logic tests                     |

### API

- `POST /api/v1/auth/login` — Login, returns JWT
- `POST /api/v1/auth/register` — Register (MVP: admin-only or open with verification)
- `GET /api/v1/auth/me` — Current user info
- `POST /api/v1/auth/refresh` — Refresh token
- `GET /api/v1/users` — List users (admin)
- `POST /api/v1/users` — Create user (admin)
- `GET /api/v1/users/{id}` — Get user
- `PUT /api/v1/users/{id}` — Update user
- `DELETE /api/v1/users/{id}` — Soft-delete user

### 测试

- Password hashing/verification
- JWT encode/decode
- RBAC guard logic
- Login flow integration
- Invalid credentials handling

### 验收标准

- [ ] User can register and login
- [ ] JWT token issued and verified
- [ ] Protected routes reject unauthenticated requests
- [ ] RBAC guards enforce permission checks
- [ ] All auth tests pass
- [ ] Frontend login page functional

### 不做什么

- 不做 SSO/OAuth（Post-MVP）
- 不做 API Token 管理（Phase 9）
- 不做复杂的组织/团队权限

---

## Phase 3: 核心领域对象

### 目标

完成所有 MVP 领域模型：Book, Version, Chapter, Passage, Paper, Image。Wire CRUD API。扩展 Document 为 Book 相关。

### 数据模型

- **Book** (书籍) — title, author_id, dynasty, year, category, abstract
- **Version** (版本) — book_id, version_name, era, repository, shelf_mark, editor, description
- **Chapter** (章节) — book_id, version_id?, title, order, parent_id (自引用)
- **Passage** (段落) — chapter_id, version_id, content_text, order, translation, notes
- **Paper** (论文) — title, authors, journal, year, doi, abstract, keywords, full_text_url
- **Image** (影像) — related_entity_type, related_entity_id, url, caption, source, license

### 修改文件

| File                                  | Change                                                                  |
| ------------------------------------- | ----------------------------------------------------------------------- |
| `apps/backend/app/models/`            | Add Book, Version, Chapter, Passage, Paper, Image models                |
| `apps/backend/app/models/document.py` | Refactor: Document → generic base for Book/Paper, or add subtype fields |
| `apps/backend/app/schemas/`           | Add schemas for all new entities                                        |
| `apps/backend/app/repositories/`      | Add repositories                                                        |
| `apps/backend/app/services/`          | Add services                                                            |
| `apps/backend/app/api/v1/`            | Add CRUD route modules for each entity                                  |

### API (per entity: GET list, GET by id, POST create, PUT update, DELETE soft-delete)

- `/api/v1/books`
- `/api/v1/versions`
- `/api/v1/chapters`
- `/api/v1/passages`
- `/api/v1/papers`
- `/api/v1/images`
- `/api/v1/persons` (wire existing model)
- `/api/v1/documents` (wire existing model)

### 测试

- Model validation for each entity
- Repository CRUD for each entity
- Schema validation edge cases
- API integration tests for each resource

### 验收标准

- [ ] All 8 domain entities have full CRUD API
- [ ] All models follow BaseModel conventions
- [ ] Relationships correctly modeled (FKs, cascade)
- [ ] API responses use unified envelope
- [ ] All tests pass (unit + integration)
- [ ] OpenAPI docs auto-generated

### 不做什么

- 不做 Herb/Prescription/Disease 等医学本体（Post-MVP）
- 不做 IIIF integration（Post-MVP）
- 不做批量导入（Phase 9）

---

## Phase 4: Version Center

### 目标

实现版本比较、版本树、版本差异可视化（per HFB-PS-1701）。这是平台核心差异化能力。

### 数据模型

- Extend **Version** model
- **VersionRelation** — source_version_id, target_version_id, relation_type (derived_from, revised_from, copied_from)

### 功能

- Version comparison (text diff)
- Version lineage tree visualization
- Version metadata (repository, shelf mark, editor, date)
- Passage-level version diff
- Export version comparison

### 修改文件

| File                                                   | Change                               |
| ------------------------------------------------------ | ------------------------------------ |
| `apps/backend/app/models/version.py`                   | Add VersionRelation, extend fields   |
| `apps/backend/app/services/version_service.py`         | Diff algorithms, lineage computation |
| `apps/backend/app/api/v1/versions.py`                  | Add compare, lineage, diff endpoints |
| `apps/frontend/src/views/VersionCenterView.vue`        | Version center page                  |
| `apps/frontend/src/components/version/VersionTree.vue` | Tree visualization                   |
| `apps/frontend/src/components/version/VersionDiff.vue` | Diff viewer                          |

### API

- `GET /api/v1/versions/{id}/lineage` — Version tree
- `GET /api/v1/versions/compare?id1=...&id2=...` — Full comparison
- `GET /api/v1/versions/{id}/passages/{pid}/diff?against=...` — Passage diff

### 验收标准

- [ ] Two versions can be compared side-by-side
- [ ] Version lineage tree renders correctly
- [ ] Passage-level diffs are accurate
- [ ] Metadata display complete

### 不做什么

- 不做 AI 辅助校勘（Post-MVP）
- 不做外部版本导入（Phase 9）

---

## Phase 5: Passage / Book / Person 基础能力

### 目标

完成 Passage Center, Book Center, Person Center 的前端页面和高级后端能力。

### 功能

- Passage reading with annotations
- Passage cross-reference
- Book catalog browsing
- Person profile pages
- Person-to-Book relationship graph (preliminary)
- Search within book/passage

### 前端页面

- `PassageReaderView.vue` — Passage reading with annotation tools
- `BookDetailView.vue` — Book metadata + chapters + versions
- `BookListView.vue` — Book catalog with filters
- `PersonDetailView.vue` — Person profile + works + relationships
- `PersonListView.vue` — Person directory with dynasty/time filters

### 验收标准

- [ ] Passage reader supports annotation
- [ ] Book catalog filters by dynasty, category
- [ ] Person profiles show works and relationships
- [ ] Cross-references navigable

---

## Phase 6: Knowledge Graph

### 目标

实现基础知识图谱：实体关系建模、图谱可视化、路径查询（per HFB-PS-1707, 0809）。

### 技术决策

Per HFB-ARC-0201 Chapter 5: Neo4j 是 Post-MVP 技术。**MVP 阶段使用 PostgreSQL + 应用层图算法** 实现轻量图谱。Neo4j 接口预留但不开通。

### 功能

- Entity relationship CRUD via API
- Graph visualization (force-directed layout)
- Path finding between entities
- Neighborhood exploration
- Person-Version-Book-Passage nexus graph

### 修改文件

| File                                                 | Change                              |
| ---------------------------------------------------- | ----------------------------------- |
| `apps/backend/app/models/graph.py`                   | Edge model for relationship storage |
| `apps/backend/app/services/graph_service.py`         | Graph traversal, path finding       |
| `apps/backend/app/api/v1/graph.py`                   | Graph API endpoints                 |
| `apps/frontend/src/components/graph/GraphCanvas.vue` | D3.js / vis.js force graph          |
| `apps/frontend/src/views/GraphExplorerView.vue`      | Graph exploration page              |

### API

- `GET /api/v1/graph/neighbors/{entity_type}/{id}` — Neighborhood
- `GET /api/v1/graph/path?source=...&target=...` — Path finding
- `GET /api/v1/graph/entity/{entity_type}/{id}` — Entity subgraph
- `GET /api/v1/graph/entities?types=...&limit=...` — Search nodes

### 验收标准

- [ ] Entities and relationships stored in PostgreSQL
- [ ] Graph visualization renders with D3.js or similar
- [ ] Path finding between entities works
- [ ] Neighborhood query returns correct results
- [ ] Graph Neo4j interface reserved (service abstraction)

### 不做什么

- 不做 Neo4j 部署（Post-MVP）
- 不做 GraphRAG（Post-MVP）
- 不做图谱编辑（read-only in MVP）
- 不做复杂本体推理

---

## Phase 7: Unified Search

### 目标

实现统一检索：关键词 + 全文 + 语义向量检索（PostgreSQL pgvector）（per HFB-PS-1706）。

### 技术决策

Per HFB-ARC-0201 Chapter 5: Elasticsearch 是 MVP 技术 (ADR-0005)。Milvus 是 Post-MVP 技术 (ADR-0007)。**MVP 使用 ES 全文检索 + pgvector 向量检索**。

### 功能

- Full-text search across all entities
- Semantic search (pgvector embedding)
- Faceted filtering (entity type, dynasty, category)
- Search results with snippets
- Cross-entity search (find passages related to a person)

### 修改文件

| File                                                    | Change                                  |
| ------------------------------------------------------- | --------------------------------------- |
| `apps/backend/app/services/search_service.py`           | Unified search orchestrator             |
| `apps/backend/app/services/embedding_service.py`        | Text embedding generation               |
| `apps/backend/app/api/v1/search.py`                     | Search API                              |
| `apps/backend/app/tasks/indexing.py`                    | ES indexing tasks                       |
| `apps/frontend/src/views/SearchView.vue`                | Replace placeholder with full search UI |
| `apps/frontend/src/components/search/SearchResults.vue` | Results display                         |

### API

- `GET /api/v1/search?q=...&type=...&filters=...` — Unified search
- `GET /api/v1/search/suggest?q=...` — Autocomplete
- `POST /api/v1/search/index` — Trigger reindex (admin)

### 验收标准

- [ ] Full-text search returns relevant results ≤2s
- [ ] Semantic search returns conceptually related results
- [ ] Faceted filtering works for type/dynasty/category
- [ ] Search works across all entity types

### 不做什么

- 不做 Milvus 部署（Post-MVP）
- 不做 AI 增强检索（Phase 8）

---

## Phase 8: AI Research Workspace

### 目标

实现 AI 科研工作台核心能力（per HFB-PS-1705）。这是 MVP 最核心的产品功能。

### 功能

- AI Assistant (右侧面板，常驻)
- 学术问答（基于知识库 RAG）
- Passage 检索
- 版本对比辅助
- 自动引文 / 自动摘要
- 学术翻译
- Research Canvas (中心阅读区)
- Knowledge Navigator (左侧导航)
- Evidence Panel (右侧证据面板)
- Research Session (自动保存)
- Notes System (研究笔记)

### 技术实现

- RAG pipeline: pgvector + ES hybrid retrieval
- Context assembly: current Version + Passage + Graph + Note + Citation
- LLM integration: unified AI Gateway pattern
- Streaming response
- Citation auto-attachment
- AI output marked as "AI Generated"

### 修改文件

| File                                                        | Change                           |
| ----------------------------------------------------------- | -------------------------------- |
| `apps/backend/app/services/ai_service.py`                   | AI gateway (LLM, embedding, RAG) |
| `apps/backend/app/services/rag_service.py`                  | RAG pipeline                     |
| `apps/backend/app/services/workspace_service.py`            | Research session management      |
| `apps/backend/app/api/v1/ai.py`                             | AI endpoints                     |
| `apps/backend/app/api/v1/workspace.py`                      | Workspace management             |
| `apps/frontend/src/views/WorkspaceView.vue`                 | Four-panel workspace layout      |
| `apps/frontend/src/components/workspace/AIAssistant.vue`    | AI chat panel                    |
| `apps/frontend/src/components/workspace/KnowledgeNav.vue`   | Left navigation                  |
| `apps/frontend/src/components/workspace/ResearchCanvas.vue` | Center reading area              |
| `apps/frontend/src/components/workspace/EvidencePanel.vue`  | Right evidence panel             |
| `apps/frontend/src/components/workspace/NotesEditor.vue`    | Markdown notes                   |

### API

- `POST /api/v1/ai/chat` — Streaming AI chat
- `POST /api/v1/ai/summarize` — Summarize passage
- `POST /api/v1/ai/translate` — Academic translation
- `POST /api/v1/ai/compare` — AI-assisted version comparison
- `GET/POST /api/v1/workspace/sessions` — Research sessions
- `GET/POST /api/v1/workspace/notes` — Research notes

### 验收标准

- [ ] AI Assistant provides answers with citations
- [ ] Answers reference real Passage/Version/Person data
- [ ] Streaming response works
- [ ] Four-panel layout functional
- [ ] Research session auto-saves
- [ ] Notes support Markdown with citation insertion
- [ ] AI output marked "AI Generated"

### 不做什么

- 不做多 Agent 协同（Post-MVP）
- 不做 AI 自主科研（Post-MVP）
- 不做 AI 自动论文生成（Post-MVP）
- 不做外部知识库接入（Post-MVP）

---

## Phase 9: Dashboard

### 目标

实现 Dashboard 首页和管理后台（per MVP Ch.8）。

### 功能

- System overview dashboard
- Recent activity timeline
- Entity statistics
- User management (admin)
- System health display
- Data management (admin): import, export, reindex
- Log viewer (admin)

### 前端页面

- `DashboardView.vue` — Main dashboard
- `AdminUsersView.vue` — User management
- `AdminDataView.vue` — Data management
- `AdminLogsView.vue` — System logs

### 验收标准

- [ ] Dashboard shows system health and stats
- [ ] Admin pages for user/data/log management
- [ ] Only accessible by admin role

---

## Phase 10: Testing & Production Readiness

### 目标

达到 HFB-PS-1710 上线准入标准。

### 必须完成

- Integration tests for all API flows
- E2E tests for critical user journeys
- API tests for all endpoints
- Permission tests (RBAC enforcement)
- AI tests (response quality, citation accuracy)
- Graph tests (traversal correctness)
- Search tests (relevance, performance)
- Security audit (OWASP, prompt injection, XSS, CSRF)
- Performance testing (load test key endpoints)
- Documentation (deployment, API, database, admin guide)
- Docker production config validation
- CI/CD pipeline verification

### 验收标准 (per HFB-PS-1710)

- [ ] All MVP features complete
- [ ] Test coverage ≥90% backend, ≥80% frontend
- [ ] All tests passing (unit, integration, E2E, API, permission, AI, graph, search)
- [ ] Security checks pass
- [ ] Performance targets met (home ≤2s, API ≤500ms, search ≤2s)
- [ ] RBAC fully enforced
- [ ] All data has source + citation
- [ ] AI outputs have evidence markers
- [ ] No Demo code
- [ ] Documentation complete

### 不做什么

- 不做 Phase 10 应该完成的事情之外的任何事

---

## Phase Dependency Graph

```
Phase 1 (Infrastructure) ──► Phase 2 (User/RBAC) ──► Phase 3 (Domain Models)
                                                          │
                                                          ▼
                                         Phase 4 (Version Center)
                                         Phase 5 (Passage/Book/Person)
                                                          │
                                                          ▼
                                         Phase 6 (Knowledge Graph)
                                         Phase 7 (Unified Search)
                                                          │
                                                          ▼
                                         Phase 8 (AI Research Workspace)
                                                          │
                                                          ▼
                                         Phase 9 (Dashboard)
                                                          │
                                                          ▼
                                         Phase 10 (Testing & Readiness)
```

Phases 4-7 can partially overlap once Phase 3 completes. Phase 8 depends on 6+7 (needs Graph + Search). Phase 9 can start after Phase 2.

---

## Risk Register

| Risk                                    | Likelihood | Impact | Mitigation                                        |
| --------------------------------------- | ---------- | ------ | ------------------------------------------------- |
| ES connectivity issues in Docker        | Medium     | Medium | Verify with Docker Compose dev config early       |
| pgvector extension not available in CI  | Low        | High   | Use pgvector/pgvector:pg16 image                  |
| AI API costs / rate limits              | Medium     | Medium | Cache frequent queries; use cost-effective models |
| Data quality for seed data              | Low        | High   | Academic review of all seed data                  |
| Frontend complexity of Workspace layout | Medium     | Medium | Iterate on four-panel layout; use CSS Grid        |
| Scope creep into Post-MVP features      | High       | High   | Strict adherence to MVP boundary per 1709         |

---

## Total Estimated Deliverables

| Phase     | New Models | New API Endpoints | New Frontend Pages | Test Files |
| --------- | ---------- | ----------------- | ------------------ | ---------- |
| Phase 1   | 0          | 0                 | 0                  | 0          |
| Phase 2   | 4          | 9                 | 2                  | 3          |
| Phase 3   | 6          | ~48               | 0                  | 6          |
| Phase 4   | 1          | 3                 | 2                  | 2          |
| Phase 5   | 0          | ~12               | 5                  | 3          |
| Phase 6   | 1          | 4                 | 2                  | 2          |
| Phase 7   | 0          | 3                 | 1                  | 2          |
| Phase 8   | 0          | ~10               | 5                  | 4          |
| Phase 9   | 0          | 0                 | 4                  | 1          |
| Phase 10  | 0          | 0                 | 0                  | 10+        |
| **Total** | **12**     | **~89**           | **21**             | **33+**    |
