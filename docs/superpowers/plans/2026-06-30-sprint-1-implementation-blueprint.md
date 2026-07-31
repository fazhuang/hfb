---
title: Sprint 1 — Implementation Blueprint
document_id: HFB-ENG-SPRINT-01
version: 1.0.0
status: Implementation Ready
owner: Lead Implementation Planner
based_on: consolidation-mvp-core.md (2026-06-30)
effective_date: 2026-06-30
---

# Sprint 1 — Implementation Blueprint

> Codex-ready file-level implementation plan. Zero theory. Zero architecture. Only code.

---

## 1. File-by-File Task Map

### Task 1.1 — Institution Entity

```
FILE: apps/backend/app/models/institution.py
  Responsibility: Institution ORM model (高校/出版社/博物馆/图书馆/学会)
  Pattern: Copy Person model structure → trim to Institution fields
  Fields:
    name: Mapped[str] (required, max 300)
    type: Mapped[Optional[str]] (university/publisher/museum/library/academy)
    location: Mapped[Optional[str]] (max 300)
    description: Mapped[Optional[str]] (Text)
    established: Mapped[Optional[str]] (max 50)
    external_ref: Mapped[Optional[str]] (max 500)
  Inherits: BaseModel (id UUID, created_at, updated_at, deleted_at, is_deleted)
  Tablename: institutions
  Dependencies: None (self-contained model)
  Acceptance: model imports, __tablename__ == "institutions", has 4+ columns beyond BaseModel

FILE: apps/backend/app/schemas/entities.py — APPEND
  Append schemas (follow existing BookCreate/BookBrief pattern):
    class InstitutionCreate(BaseModel): name, type, location, description, established
    class InstitutionUpdate(BaseModel): all fields Optional
    class InstitutionBrief(BaseModel): id, name, type, created_at
    class InstitutionResponse(BaseModel): all fields + id, created_at, updated_at
  Dependencies: None
  Acceptance: Schema imports, InstitutionCreate.model_validate({...}) succeeds

FILE: apps/backend/app/api/v1/entities.py — APPEND
  After existing _make_crud calls, append:
    institution_service = InstitutionService()
    _make_crud("institution", InstitutionService, InstitutionCreate, InstitutionUpdate, InstitutionBrief, InstitutionResponse)
    _make_crud generates: GET/POST/PATCH/DELETE /api/v1/institutions
  Imports at top: add InstitutionService + 4 schemas
  Dependencies: InstitutionService, Institution schemas
  Acceptance: 4 CRUD endpoints registered, visible in OpenAPI /docs

FILE: apps/backend/app/services/entities.py — APPEND
  Append:
    class InstitutionService:
        def __init__(self): self.repo = InstitutionRepository()
        async def create(self, db, data: InstitutionCreate) -> InstitutionBrief: ...
        async def get(self, db, id: UUID) -> InstitutionResponse: ...
        async def list(self, db, page, size) -> PaginatedResult: ...
        async def update(self, db, id, data: InstitutionUpdate) -> InstitutionResponse: ...
        async def delete(self, db, id) -> None: ...
  Dependencies: InstitutionRepository, Institution model
  Acceptance: create() returns Brief, get() returns Response with DB-persisted data

FILE: apps/backend/app/repositories/entities.py — APPEND
  Append:
    class InstitutionRepository:
        def __init__(self, db: AsyncSession): ...
        async def create(self, **kwargs) -> Institution: ...
        async def get_by_id(self, id: UUID) -> Institution | None: ...
        async def search_query(self, q: str) -> tuple[list, int]: ...
        async def update(self, id, **kwargs) -> institution: ...
        async def delete(self, id) -> None: ...
  Pattern: COPY BookRepository, search by name ILIKE
  Dependencies: Institution model
  Acceptance: create() returns persisted model, search_query("大学") returns matches

FILE: apps/backend/app/models/__init__.py — EDIT
  Add: from app.models.institution import Institution
  Add "Institution" to __all__
  Dependencies: institution.py created
  Acceptance: from app.models import Institution works

FILE: tests/unit/test_entity_models.py — APPEND
  Append: class TestInstitutionModel with test_tablename, test_has_expected_columns
  Pattern: COPY TestBookModel → adapt assertions
  Acceptance: test passes with other entity tests

FILE: apps/backend/app/services/search_service.py — EDIT
  Add "institution" entry to ENTITY_CONFIG dict:
    "institution": {
        "model": Institution,
        "title_field": "name",
        "search_fields": ["name", "location", "description"],
        "route_prefix": "/institutions",
        "snippet_field": "description",
        "meta_fields": ["type", "established"],
    }
  Add import: from app.models.institution import Institution
  Dependencies: Institution model exists
  Acceptance: SearchService handles entity_type="institution"

FILE: apps/backend/app/db/migrations/versions/ — CREATE
  Migration: alembic revision --autogenerate -m "add_institution"
  Result: {hash}_add_institution.py (auto-generated)
  Acceptance: alembic upgrade head succeeds, table exists
```

### Task 1.2 — Place Entity

```
FILE: apps/backend/app/models/place.py
  Responsibility: Place ORM model (古地名+现代行政区+历史地点)
  Fields: name, type (city/county/mountain/region/heritage_site), latitude, longitude, dynasty, description
  Tablename: places
  Pattern: Same as Institution — copy, adapt fields
  Acceptance: model imports, __tablename__ == "places"

FILE: apps/backend/app/schemas/entities.py — APPEND
  PlaceCreate, PlaceUpdate, PlaceBrief, PlaceResponse
  Acceptance: Schema validates

FILE: apps/backend/app/api/v1/entities.py — APPEND
  _make_crud("place", PlaceService, ...)
  Acceptance: 4 CRUD endpoints registered

FILE: apps/backend/app/services/entities.py — APPEND
  PlaceService (same pattern as InstitutionService)
  Acceptance: create/get/list/update/delete all work

FILE: apps/backend/app/repositories/entities.py — APPEND
  PlaceRepository (search by name ILIKE, filter by type)
  Acceptance: create/search work

FILE: apps/backend/app/models/__init__.py — EDIT
  Add: from app.models.place import Place

FILE: tests/unit/test_entity_models.py — APPEND
  TestPlaceModel (test_tablename, test_has_expected_columns)

FILE: apps/backend/app/services/search_service.py — EDIT
  Add "place" entry to ENTITY_CONFIG

FILE: apps/backend/app/db/migrations/versions/ — CREATE
  alembic revision --autogenerate -m "add_place"
```

### Task 1.3 — Event Entity

```
FILE: apps/backend/app/models/event.py
  Fields: name, description, start_date, end_date, place_id (nullable FK), dynasty
  Tablename: events
  Acceptance: model imports with FK to places

FILE: apps/backend/app/schemas/entities.py — APPEND
  EventCreate, EventUpdate, EventBrief, EventResponse
  Acceptance: Schema validates

FILE: apps/backend/app/api/v1/entities.py — APPEND
  _make_crud("event", EventService, ...)
  Acceptance: 4 CRUD endpoints

FILE: apps/backend/app/services/entities.py — APPEND
  EventService
  Acceptance: create/get/list/update/delete

FILE: apps/backend/app/repositories/entities.py — APPEND
  EventRepository (search by name ILIKE)
  Acceptance: create/search

FILE: apps/backend/app/models/__init__.py — EDIT
  from app.models.event import Event

FILE: tests/unit/test_entity_models.py — APPEND
  TestEventModel

FILE: apps/backend/app/services/search_service.py — EDIT
  Add "event" to ENTITY_CONFIG

FILE: apps/backend/app/db/migrations/versions/ — CREATE
  alembic revision -m "add_event"
```

### Task 1.4 — Dynasty Entity

```
FILE: apps/backend/app/models/dynasty.py
  Fields: name, start_year (int, negative=BC), end_year (int), description, predecessor_id (self FK, nullable)
  Tablename: dynasties
  Acceptance: self-referential FK for predecessor

FILE: apps/backend/app/schemas/entities.py — APPEND
  DynastyCreate, DynastyUpdate, DynastyBrief, DynastyResponse
  Acceptance: Schema validates

FILE: apps/backend/app/api/v1/entities.py — APPEND
  _make_crud("dynasty", DynastyService, ...)
  Acceptance: 4 CRUD endpoints

FILE: apps/backend/app/services/entities.py — APPEND
  DynastyService
  Acceptance: create/get/list/update/delete

FILE: apps/backend/app/repositories/entities.py — APPEND
  DynastyRepository (search by name, order by start_year)
  Acceptance: create/search

FILE: apps/backend/app/models/__init__.py — EDIT
  from app.models.dynasty import Dynasty

FILE: tests/unit/test_entity_models.py — APPEND
  TestDynastyModel

FILE: apps/backend/app/services/search_service.py — EDIT
  Add "dynasty" to ENTITY_CONFIG

FILE: apps/backend/app/db/migrations/versions/ — CREATE
  alembic revision -m "add_dynasty"
```

### Task 1.5 — ES Integration in SearchService

```
FILE: apps/backend/app/services/search_service.py — EDIT (ADD ~60 lines)
  Current: ILIKE only across ENTITY_CONFIG models
  Target: ILIKE baseline + ES query path when Elasticsearch is available

  Implementation:
    1. Add _es_client property (lazy init AsyncElasticsearch from config)
    2. Add _es_search(query, entity_types, page, size) method:
       - Build multi-index ES query (match on search_fields, filter by entity_type)
       - Return [SearchResultItem] + total count
    3. Modify search() method:
       - Try ES first → if exception → fallback to ILIKE
       - If ES disabled (config.ELASTICSEARCH_ENABLED=False) → ILIKE only
    4. ES results already include highlight snippets; ILIKE results use snippet_field truncation

  Config additions (config.py):
    ELASTICSEARCH_ENABLED: bool = True  # Feature flag
    ELASTICSEARCH_INDEX_PREFIX: str = "hfb"

  ES Index strategy (manual, not migration):
    - Index per entity type: hfb_persons, hfb_books, hfb_passages, etc.
    - Reindex endpoint already exists: POST /api/v1/search/reindex
    - Reindex logic already stubbed: search_service.py:407

  Dependencies: Elasticsearch service running (docker compose)
  Risk: ES unavailable → graceful fallback to ILIKE (existing behavior)
  Acceptance: Search returns ES results when ES is up, ILIKE when ES is down

FILE: apps/backend/app/core/config.py — EDIT
  Add: ELASTICSEARCH_ENABLED: bool = True
  Add: ELASTICSEARCH_INDEX_PREFIX: str = "hfb"
  Dependencies: None
  Acceptance: settings.ELASTICSEARCH_ENABLED is True

FILE: tests/unit/test_search.py — APPEND
  TestESSearchFallback:
    - ES disabled → uses ILIKE
    - ES enabled but unreachable → falls back to ILIKE
    - Note: requires ES mock or monkeypatch
  Acceptance: 2 new tests pass
```

### Task 1.6 — Status Lifecycle State Machine

```
FILE: apps/backend/app/core/status_machine.py — CREATE
  Responsibility: Single-file state machine for Entity lifecycle
  No framework, no dependency. Pure Python.

  Implementation:
    VALID_TRANSITIONS = {
        "draft":       {"review"},
        "review":      {"published", "draft"},  # draft = rejection
        "published":   {"archived"},
        "archived":    {"deprecated"},
        "deprecated":  set(),  # terminal
    }

    def can_transition(current: str, target: str) -> bool:
        return target in VALID_TRANSITIONS.get(current, set())

    def validate_transition(current: str, target: str) -> None:
        if not can_transition(current, target):
            raise InvalidStatusTransitionError(
                f"Cannot transition from '{current}' to '{target}'"
            )

  Dependencies: None (pure function, no DB, no framework)
  Acceptance: can_transition("draft","review")=True, can_transition("draft","published")=False

FILE: apps/backend/app/core/exceptions.py — CREATE
  Responsibility: Single-file custom exceptions

  class EntityNotFoundError(Exception): pass
  class InvalidStatusTransitionError(Exception): pass
  class ConflictError(Exception): pass  # optimistic lock

  Dependencies: None
  Acceptance: raise EntityNotFoundError("foo") works

FILE: apps/backend/app/services/entities.py — EDIT (ADD 5 lines per service)
  In each Service.update() method, BEFORE calling repo.update():
    from app.core.status_machine import validate_transition
    from app.core.exceptions import InvalidStatusTransitionError

    if "status" in update_data:
        current = await self.repo.get_by_id(id)
        if current is None:
            raise EntityNotFoundError(f"{entity_name} {id} not found")
        validate_transition(current.status, update_data["status"])

  Pattern: Add to BookService, VersionService, PassageService, PaperService, ImageService, PersonService
           AND InstitutionService, PlaceService, EventService, DynastyService
  Dependencies: status_machine.py, exceptions.py
  Risk: Existing tests may need status field set. Review test fixtures.
  Acceptance: PATCH status=published on draft entity → 409 error

FILE: apps/backend/app/core/error_handlers.py — CREATE
  Responsibility: Register on FastAPI app to convert exceptions → unified envelope

  @app.exception_handler(EntityNotFoundError)
  async def entity_not_found_handler(request, exc):
      return JSONResponse(status_code=404, content={
          "success": False, "timestamp": utcnow_iso(),
          "data": None, "message": str(exc)
      })

  @app.exception_handler(InvalidStatusTransitionError)
  async def invalid_transition_handler(request, exc):
      return JSONResponse(status_code=409, content={...})

  Dependencies: exceptions.py
  Acceptance: Raising EntityNotFoundError in a route returns 404

FILE: apps/backend/main.py — EDIT (ADD 2 lines)
  from app.core.exceptions import EntityNotFoundError, InvalidStatusTransitionError
  from app.core.error_handlers import register_error_handlers
  register_error_handlers(app)  # or inline the exception_handler decorators

  Dependencies: error_handlers.py
  Acceptance: Exception raised in test → 404/409 in test assertion
```

### Task 1.7 — EntityNotFoundError + Handler

```
(This task is absorbed into Task 1.6 — the exceptions.py + error_handlers.py
 files created there serve the same purpose. No separate files needed.)

  Verification checklist:
    ✓ EntityNotFoundError raises → HTTP 404
    ✓ InvalidStatusTransitionError raises → HTTP 409
    ✓ Error response uses unified envelope {success: false, timestamp, data: null, message}
```

### Task 1.8 — X-Request-ID Middleware

```
FILE: apps/backend/app/middleware/request_id.py — CREATE
  Responsibility: Inject X-Request-ID into every response

  Implementation (~25 lines):
    from starlette.middleware.base import BaseHTTPMiddleware
    from uuid import uuid4

    class RequestIDMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request_id = request.headers.get("X-Request-ID", str(uuid4()))
            request.state.request_id = request_id
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response

  Dependencies: None (stdlib uuid)
  Acceptance: Any GET response includes X-Request-ID header

FILE: apps/backend/main.py — EDIT (ADD 2 lines)
  from app.middleware.request_id import RequestIDMiddleware
  app.add_middleware(RequestIDMiddleware)
  Place AFTER CORS middleware, BEFORE auth middleware.

  Dependencies: request_id.py
  Acceptance: health endpoint returns X-Request-ID header

FILE: tests/unit/test_health.py — APPEND
  def test_request_id_header():
      from main import app
      transport = ASGITransport(app=app)
      async with AsyncClient(...) as client:
          response = await client.get("/health")
          assert "X-Request-ID" in response.headers
          assert len(response.headers["X-Request-ID"]) == 36  # UUID format
  Acceptance: 1 new test passes
```

---

## 2. Backend Implementation Order

```
Phase A — Foundation (Day 1 — sequential, no parallelism)
  A1. status_machine.py                     ← pure function, zero deps
  A2. exceptions.py                          ← pure Python, zero deps
  A3. error_handlers.py                      ← depends on A2
  A4. main.py (register handlers)            ← depends on A3
  A5. request_id.py                          ← independent of A1-A4
  A6. main.py (register middleware)          ← depends on A5
  A7. RUN TESTS — verify 220 pass           ← gate

Phase B — Entity Batch 1 (Day 1-2 — parallel after A7)
  B1. models/institution.py                  ← independent
  B2. schemas/entities.py (append)           ← independent of B1 (schemas first)
  B3. repositories/entities.py (append)      ← depends on B1
  B4. services/entities.py (append)          ← depends on B3
  B5. api/v1/entities.py (append route)      ← depends on B4
  B6. models/__init__.py (add import)        ← depends on B1
  B7. search_service.py (add ENTITY_CONFIG)  ← depends on B1
  B8. migration (alembic autogenerate)       ← depends on B1
  B9. tests/unit/test_entity_models.py       ← depends on B1
  B10. RUN TESTS — verify green             ← gate

Phase C — Entity Batch 2 (Day 2-3 — parallel, same pattern)
  C1. models/place.py                        ← independent
  C2. schemas append + repo + service + api + init + search + migration + test
  C3. models/event.py                        ← independent (needs Place FK)
  C4. schemas append + repo + service + api + init + search + migration + test
  C5. models/dynasty.py                      ← independent
  C6. schemas append + repo + service + api + init + search + migration + test
  C7. RUN TESTS — verify green              ← gate

Phase D — ES Integration (Day 3-4 — sequential, depends on Phase C complete)
  D1. config.py (add ES feature flags)       ← independent
  D2. search_service.py (add ES query path)  ← depends on D1
  D3. tests/unit/test_search.py (add ES fallback test) ← depends on D2
  D4. RUN TESTS with ES enabled flag        ← gate
  D5. RUN TESTS with ES disabled flag       ← gate (verify fallback)
  D6. Manual test: POST /api/v1/search/reindex → verify ES index populated

Phase E — Status Lifecycle Integration (Day 4-5 — sequential)
  E1. services/entities.py (add validate_transition to each Service.update)
  E2. services/entities.py (add EntityNotFoundError raise in each Service.get/update)
  E3. RUN TESTS — fix any broken fixtures   ← gate (may take time)
  E4. Write 3 new tests: draft→review OK, draft→published REJECTED, nonexistent→404

Phase F — Integration & Polish (Day 5-6)
  F1. Full test suite run (expect 250+ tests)
  F2. ruff check + mypy pass
  F3. alembic upgrade head clean
  F4. docker compose up → GET /ready returns 200
  F5. POST /api/v1/institutions → returns 201
  F6. GET /api/v1/search?q=针灸&entity_type=passage → returns ES results
  F7. Manually verify X-Request-ID in all responses
```

---

## 3. API Endpoints Specification

### 3.1 Existing (unchanged) — 14 route groups

| Route Group    | Base Path                | Existing                                                                              |
| -------------- | ------------------------ | ------------------------------------------------------------------------------------- |
| Auth           | `/api/v1/auth`           | ✅ POST login, register, GET me                                                       |
| Entities       | `/api/v1/{resource}`     | ✅ CRUD for 8 types (book, version, chapter, passage, paper, image, person, document) |
| AI             | `/api/v1/ai`             | ✅ POST chat, summarize, translate, compare                                           |
| Search         | `/api/v1/search`         | ✅ GET search, suggest, POST reindex                                                  |
| Graph          | `/api/v1/graph`          | ✅ GET neighbors, paths, subgraph                                                     |
| Version Center | `/api/v1/version-center` | ✅ Version comparison                                                                 |
| Workspace      | `/api/v1/workspace`      | ✅ CRUD sessions, notes                                                               |
| Research       | `/api/v1/research`       | ✅ Research workflow                                                                  |
| Dashboard      | `/api/v1/dashboard`      | ✅ Dashboard stats                                                                    |
| Users          | `/api/v1/users`          | ✅ User management                                                                    |
| Health         | `/health`                | ✅ GET 200                                                                            |
| Ready          | `/ready`                 | ✅ GET 200 or 503                                                                     |
| Version        | `/version`               | ✅ GET version info                                                                   |
| Config         | `/config`                | ✅ GET public config                                                                  |

### 3.2 New (Sprint 1 additions) — 4 entity types

```
POST   /api/v1/institutions         ← InstitutionCreate → InstitutionBrief
GET    /api/v1/institutions         ← ?page=1&size=20 → PaginatedResult[InstitutionBrief]
GET    /api/v1/institutions/{id}    ← → InstitutionResponse
PATCH  /api/v1/institutions/{id}    ← InstitutionUpdate → InstitutionResponse
DELETE /api/v1/institutions/{id}    ← → 204

POST   /api/v1/places               ← PlaceCreate → PlaceBrief
GET    /api/v1/places               ← ?page=1&size=20 → PaginatedResult[PlaceBrief]
GET    /api/v1/places/{id}          ← → PlaceResponse
PATCH  /api/v1/places/{id}          ← PlaceUpdate → PlaceResponse
DELETE /api/v1/places/{id}          ← → 204

POST   /api/v1/events               ← EventCreate → EventBrief
GET    /api/v1/events               ← ?page=1&size=20 → PaginatedResult[EventBrief]
GET    /api/v1/events/{id}          ← → EventResponse
PATCH  /api/v1/events/{id}          ← EventUpdate → EventResponse
DELETE /api/v1/events/{id}          ← → 204

POST   /api/v1/dynasties            ← DynastyCreate → DynastyBrief
GET    /api/v1/dynasties            ← ?page=1&size=20 → PaginatedResult[DynastyBrief]
GET    /api/v1/dynasties/{id}       ← → DynastyResponse
PATCH  /api/v1/dynasties/{id}       ← DynastyUpdate → DynastyResponse
DELETE /api/v1/dynasties/{id}       ← → 204
```

### 3.3 Request/Response Schema Template

All follow the existing pattern from `_make_crud` factory in `api/v1/entities.py`:

```json
// Create (POST)
{
  "name": "复旦大学",
  "type": "university",
  "location": "上海市"
}

// Response — Brief (POST, GET list)
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "复旦大学",
  "type": "university",
  "created_at": "2026-06-30T12:00:00Z"
}

// Response — Full (GET single)
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "复旦大学",
  "type": "university",
  "location": "上海市",
  "description": null,
  "established": "1905",
  "created_at": "2026-06-30T12:00:00Z",
  "updated_at": "2026-06-30T12:00:00Z"
}

// Update (PATCH) — all fields optional
{
  "description": "教育部直属重点大学"
}

// Unified envelope (all responses)
{
  "success": true,
  "timestamp": "2026-06-30T12:00:00.000Z",
  "data": { ... },
  "message": "OK"
}

// Error envelope (new — from error_handlers.py)
{
  "success": false,
  "timestamp": "2026-06-30T12:00:00.000Z",
  "data": null,
  "message": "Entity 'institution' with id '550e8400-...' not found"
}
```

### 3.4 Validation Rules

| Field             | Rule                                             | Enforced By                                  |
| ----------------- | ------------------------------------------------ | -------------------------------------------- |
| name              | required, 1–300 chars                            | Pydantic Field(min_length=1, max_length=300) |
| id (path)         | valid UUID                                       | FastAPI UUID type                            |
| page (query)      | int ≥ 1, default 1                               | Query(default=1, ge=1)                       |
| size (query)      | int 1–100, default 20                            | Query(default=20, ge=1, le=100)              |
| status            | enum: draft/review/published/archived/deprecated | status_machine.py                            |
| status transition | draft→published rejected                         | Service layer validate_transition()          |

---

## 4. Database Minimal Schema

### 4.1 Existing Tables (unchanged)

```
users, roles, permissions, user_roles           ← Auth
books, versions, chapters, passages             ← Versioning
persons                                          ← Personnel
papers, images, documents                        ← Research
entity_relations, version_relations              ← Graph
passage_mappings, version_diffs                  ← Version comparison
research_sessions, research_notes                ← Workspace
```

### 4.2 New Tables (Sprint 1)

```sql
-- All new tables inherit BaseModel: id UUID PK, created_at, updated_at,
-- deleted_at, is_deleted. Pattern from app/db/base.py.

CREATE TABLE institutions (
    id UUID PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    type VARCHAR(50),          -- university/publisher/museum/library/academy
    location VARCHAR(300),
    description TEXT,
    established VARCHAR(50),
    external_ref VARCHAR(500),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    is_deleted BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE places (
    id UUID PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    type VARCHAR(50),          -- city/county/mountain/region/heritage_site
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    dynasty VARCHAR(100),
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    is_deleted BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE events (
    id UUID PRIMARY KEY,
    name VARCHAR(300) NOT NULL,
    description TEXT,
    start_date VARCHAR(50),
    end_date VARCHAR(50),
    place_id UUID REFERENCES places(id) ON DELETE SET NULL,
    dynasty VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    is_deleted BOOLEAN NOT NULL DEFAULT false
);

CREATE TABLE dynasties (
    id UUID PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    start_year INTEGER,
    end_year INTEGER,
    description TEXT,
    predecessor_id UUID REFERENCES dynasties(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at TIMESTAMPTZ,
    is_deleted BOOLEAN NOT NULL DEFAULT false
);
```

### 4.3 Indexes (added by migration)

```sql
CREATE INDEX idx_institutions_name ON institutions (name);
CREATE INDEX idx_institutions_type ON institutions (type);
CREATE INDEX idx_places_name ON places (name);
CREATE INDEX idx_places_type ON places (type);
CREATE INDEX idx_events_name ON events (name);
CREATE INDEX idx_events_place_id ON events (place_id);
CREATE INDEX idx_dynasties_name ON dynasties (name);
CREATE INDEX idx_dynasties_predecessor ON dynasties (predecessor_id);
```

### 4.4 What We Do NOT Create (Sprint 1)

```
✗ metadata table        → Sprint 2
✗ evidence table        → Sprint 2
✗ relation_evidence     → Sprint 2
✗ citation table        → Sprint 2
✗ business_audit_log    → Sprint 2
✗ review_queue          → Sprint 2
✗ graph_events          → Post-MVP
✗ acupoint/meridian/... → Post-MVP
```

---

## 5. RAG Minimal Pipeline (MVP ONLY)

### 5.1 Current State (what we already have)

```
User Question
     │
     ▼
RAGService.retrieve(message, top_k=5)
     │
     ├→ SearchService.search(message, entity_types=[...])
     │      │
     │      └→ PostgreSQL ILIKE across ENTITY_CONFIG search_fields
     │
     ▼
RAGService.assemble_context(message, top_k=5)
     │
     ├→ Combine SearchResultItem[] → format as context blocks
     ├→ Each block tagged with [entity_type, title, excerpt, citation_label]
     │
     ▼
AIService.chat_stream(messages, context=context)
     │
     ├→ httpx → LLM Provider (OpenAI/Anthropic)
     ├→ System prompt: evidence-gated (from EVIDENCE_GATED_SYSTEM_PROMPT)
     │
     ▼
StructuredResponseBuilder.build(answer_text, rag_chunks)
     │
     ├→ EvidenceItem[] from chunks
     ├→ Citation[] from chunks
     ├→ GraphContext[] from evidence entities
     │
     ▼
StructuredAIResponse {answer, evidence, citations, graph_context}
```

### 5.2 Sprint 1 Addition — ES in retrieval path

```
SearchService.search() — MODIFIED
     │
     ├→ IF settings.ELASTICSEARCH_ENABLED:
     │      try: ES multi-index query → results with highlights
     │      except: fallback → ILIKE
     │   ELSE: ILIKE (existing behavior)
     │
     ▼
Same RAGService path as above — context assembly unchanged
```

### 5.3 What we do NOT add (Post-MVP)

```
✗ Vector embedding (pgvector) → Post-MVP
✗ Semantic similarity search → Post-MVP
✗ BGE-M3 or any Embedding model → Post-MVP
✗ Cross-encoder Reranker (BGE-Reranker-v2) → Post-MVP
✗ BM25 fusion with ES → Post-MVP
✗ Claim-Evidence cross-check → Post-MVP
✗ Confidence scoring with multi-factor → Post-MVP
✗ Hallucination detection → Post-MVP (current gate: no evidence = refuse)
✗ Abstention gate → Post-MVP
✗ Citation RAG → Post-MVP
✗ GraphRAG → Post-MVP
```

**MVP RAG = ILIKE + ES keyword + LLM + StructuredResponseBuilder. That's it.**

---

## 6. Execution Timeline (Day-based)

### Day 1 — Foundation + Institution

```
Morning (4h):
  09:00  Create models/institution.py (30 min)
  09:30  Append schemas/entities.py — InstitutionCreate/Update/Brief/Response (30 min)
  10:00  Create repositories/entities.py — InstitutionRepository (30 min)
  10:30  Create services/entities.py — InstitutionService (30 min)
  11:00  Append api/v1/entities.py — register Institution CRUD routes (30 min)
  11:30  Edit models/__init__.py — add Institution import (5 min)
  11:35  Add Institution to search_service.py ENTITY_CONFIG (15 min)
  11:50  Generate migration: alembic revision --autogenerate -m "add_institution"

Afternoon (4h):
  13:00  Apply migration: alembic upgrade head. Verify table exists.
  13:15  Write TestInstitutionModel (30 min)
  13:45  Manual test: POST /api/v1/institutions via /docs — verify 201
  14:00  Create core/status_machine.py (30 min)
  14:30  Create core/exceptions.py (15 min)
  14:45  Create core/error_handlers.py (45 min)
  15:30  Edit main.py — register error handlers (15 min)
  15:45  Create middleware/request_id.py (30 min)
  16:15  Edit main.py — register RequestIDMiddleware (10 min)
  16:25  Write test_request_id_header (20 min)
  16:45  RUN FULL TEST SUITE → verify 220+ pass
  17:30  Fix any failures. Gate: all tests green.
```

### Day 2 — Place + Event + Dynasty

```
Morning (4h):
  09:00  Create models/place.py → schemas → repo → service → api → init → search → migration → test
  11:00  Create models/event.py → schemas → repo → service → api → init → search → migration → test

Afternoon (4h):
  13:00  Create models/dynasty.py → schemas → repo → service → api → init → search → migration → test
  15:00  RUN FULL TEST SUITE → verify 240+ pass
  16:00  Fix any failures
  17:00  Gate: all tests green, all 4 new entities have CRUD endpoints
```

### Day 3 — ES Integration

```
Morning (4h):
  09:00  Edit config.py — add ELASTICSEARCH_ENABLED + INDEX_PREFIX
  09:15  Edit search_service.py — add _es_client, _es_search method (2h)
  11:15  Edit search_service.py — modify search() for ES primary / ILIKE fallback (45 min)

Afternoon (4h):
  13:00  Write TestESSearchFallback (1h)
  14:00  Test with ES enabled flag → green
  14:30  Test with ES disabled flag → green (ILIKE fallback works)
  15:00  Manual test: POST /api/v1/search/reindex → ES indices populated
  15:30  Manual test: GET /api/v1/search?q=针灸 → ES results with highlights
  16:30  Fix any integration issues
  17:00  Gate: ES search works when available, ILIKE fallback works when not
```

### Day 4 — Status Lifecycle Integration

```
Morning (4h):
  09:00  Edit services/entities.py — add validate_transition to BookService.update (30 min)
  09:30  Repeat for VersionService, PassageService, PaperService, ImageService, PersonService (1h)
  10:30  Repeat for InstitutionService, PlaceService, EventService, DynastyService (30 min)
  11:00  Add EntityNotFoundError raise to all Service.get/update methods (30 min)
  11:30  RUN TESTS → assess breakage

Afternoon (4h):
  13:00  Fix test fixtures: add status fields where missing (may be substantial)
  15:00  Write 3 new tests: draft→review OK, draft→published REJECTED, nonexistent→404
  16:00  RUN FULL TEST SUITE → verify 250+ pass
  17:00  Gate: all tests green, lifecycle transitions enforced
```

### Day 5 — Integration + Polish

```
Morning (4h):
  09:00  ruff check → fix all lint errors
  10:00  mypy apps/backend → fix all type errors
  11:00  alembic downgrade -1 → upgrade head → verify clean migration cycle

Afternoon (4h):
  13:00  docker compose up (all 6 services) → GET /ready returns 200
  13:30  Smoke test: POST /api/v1/institutions → 201
  13:45  Smoke test: GET /api/v1/search?q=针灸&entity_type=passage → results
  14:00  Smoke test: PATCH /api/v1/books/{id} status=published (from draft) → 409
  14:15  Smoke test: GET /api/v1/books/00000000-0000-0000-0000-000000000000 → 404
  14:30  Verify X-Request-ID in all smoke test responses
  15:00  Clean up, document any known issues
  16:00  Final gate: 250+ tests, lint clean, type clean, compose healthy
```

---

## 7. New Files Created (Sprint 1)

| File                                     | Lines (est.) | Purpose                |
| ---------------------------------------- | ------------ | ---------------------- |
| `models/institution.py`                  | ~35          | Institution model      |
| `models/place.py`                        | ~35          | Place model            |
| `models/event.py`                        | ~40          | Event model            |
| `models/dynasty.py`                      | ~40          | Dynasty model          |
| `core/status_machine.py`                 | ~30          | State machine          |
| `core/exceptions.py`                     | ~15          | Custom exceptions      |
| `core/error_handlers.py`                 | ~35          | Exception→HTTP mapping |
| `middleware/request_id.py`               | ~25          | X-Request-ID           |
| `db/migrations/versions/{4 hashes}_*.py` | ~200 (auto)  | 4 migrations           |

## 8. Files Modified (Sprint 1)

| File                               | Lines added (est.) | Change                             |
| ---------------------------------- | ------------------ | ---------------------------------- |
| `schemas/entities.py`              | ~80                | 16 schemas (4 entities × 4)        |
| `repositories/entities.py`         | ~120               | 4 repositories                     |
| `services/entities.py`             | ~160               | 4 services + lifecycle integration |
| `api/v1/entities.py`               | ~25                | 4 route registrations              |
| `models/__init__.py`               | ~10                | 4 imports                          |
| `services/search_service.py`       | ~80                | ENTITY_CONFIG + ES query path      |
| `core/config.py`                   | ~5                 | ES feature flags                   |
| `main.py`                          | ~10                | Error handlers + middleware        |
| `tests/unit/test_entity_models.py` | ~80                | 4 test classes                     |
| `tests/unit/test_search.py`        | ~40                | ES fallback tests                  |
| `tests/unit/test_health.py`        | ~15                | Request ID test                    |

**Total: ~1,000 new lines, ~600 modified lines, 0 deleted lines.**

---

## 7. Post-MVP Explicitly Excluded List

| Feature                                                  | When     | Trigger                    |
| -------------------------------------------------------- | -------- | -------------------------- |
| Neo4j deployment                                         | Phase 2  | ADR-0004 Active            |
| GraphRAG                                                 | Phase 2  | Neo4j deployed             |
| pgvector / Text RAG                                      | Phase 2  | Embedding model selected   |
| Citation RAG                                             | Phase 2  | PG vector search live      |
| Milvus                                                   | Phase 3  | >100K vectors              |
| Evidence / Citation tables                               | Sprint 2 | Sprint 1 complete          |
| ReviewService / Expert Workbench                         | Sprint 2 | Evidence tables exist      |
| Metadata table                                           | Sprint 2 | ReviewService exists       |
| BusinessAuditLog                                         | Sprint 2 | ReviewService exists       |
| Acupoint/Meridian/Disease/Symptom/Herb/Formula/Treatment | Phase 2  | HFB-DAT-0304 approval      |
| OCR pipeline                                             | Phase 2  | Corpus acquired            |
| NER pipeline                                             | Phase 2  | Model fine-tuned           |
| Relation extraction                                      | Phase 2  | NER operational            |
| Literature review assistant                              | Phase 2  | RAG + GraphRAG live        |
| Evidence chain assistant                                 | Phase 2  | GraphRAG live              |
| Version comparison assistant                             | Phase 2  | Multi-version data         |
| Topic suggestion assistant                               | Phase 2  | >500 papers                |
| Teaching assistant                                       | Phase 3  | Learning center built      |
| Academic audit assistant                                 | Phase 3  | All assistants live        |
| Structured logging (structlog)                           | Never    | Not needed                 |
| Port/Adapter interfaces (ABC)                            | Never    | Existing layering adequate |
| Request audit middleware                                 | Sprint 3 | Ops requirement            |
