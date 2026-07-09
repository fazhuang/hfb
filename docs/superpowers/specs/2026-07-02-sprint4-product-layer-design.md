# Sprint 4: Digital Humanities Research Platform — Session-Only Product Layer

**Date:** 2026-07-02
**Status:** Design approved + Architecture Review Patch applied — ready for implementation

---

## 1. Objective

Transform the HFB backend into a full Digital Humanities Research Platform. Sprint 4 adds the product layer on top of existing Sprints 1–3 services. No modification to ingestion, retrieval, citation, or knowledge graph core.

---

## 2. Architecture

```
V4 API Routes (thin routing layer, ~200 lines)
    ↓ compose
Existing Services (UNCHANGED)
    AcademicService, GraphService, ResearchWorkflowService, WorkspaceService, DashboardService
    ↓ read/write
Existing Models + 2 New Models
    QueryHistory, CitationCollection
```

**Decision: Sessions-only.** No Project entity for now — add when multi-session research grouping becomes a real need.

### 2.1 Service Boundary Enforcement Rule (STRICT)

V4 API layer MUST NOT access ORM or database models directly. ALL data access MUST go through existing services:
- AcademicService
- GraphService
- ResearchWorkflowService
- WorkspaceService
- DashboardService

No exception allowed. No inline SQLAlchemy queries in V4 route handlers. No direct model imports in V4 files.

**Violation detection:** any `select()`, `session.execute()`, `session.add()`, or model class import in `api/v4/` is a P0 blocker.

### 2.2 ResearchRun Abstraction (Logical Entity)

Workflow is decoupled from session via a logical execution unit — NOT a database entity.

```
ResearchRun (logical, in-memory / workflow_state JSON)
├── run_id          (UUID, generated at workflow start)
├── session_id      (FK binding)
├── query_history_binding  (list of query_ids from this run)
├── step_execution_trace   (list of {step_name, status, started_at, completed_at, trace_ids[]})
└── output_artifacts       (list of {artifact_type, artifact_id, created_at})
```

Rule: `Session ≠ Execution`. One session can contain multiple ResearchRuns. Each run is a self-contained execution with its own traceability chain. Stored in `ResearchSession.workflow_state` JSON — no new table.

---

## 3. New Models

### 3.1 QueryHistory

File: `apps/backend/app/models/workspace.py` (same file as ResearchSession)

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (BaseModel) | Primary key |
| session_id | FK → research_sessions.id | Owning session |
| query_text | Text | Original query string |
| query_type | String(50) | report / synthesis / research / education / graph / search |
| result_summary | Text (JSON) | Hit count, citation count, source doc count |
| citation_count | Integer | Number of citations returned |
| created_at, updated_at | DateTime | Timestamps (BaseModel) |

### 3.2 CitationCollection

File: `apps/backend/app/models/workspace.py` (same file as ResearchSession)

| Field | Type | Description |
|-------|------|-------------|
| id | UUID (BaseModel) | Primary key |
| session_id | FK → research_sessions.id | Owning session |
| trace_json | Text (JSON) | Full EvidenceTrace, immutable |
| citation_text | Text | Formatted citation string |
| source_document | String(500) | Source document name |
| tags | String(500), nullable | User tags |
| notes | Text, nullable | User annotations |
| created_at, updated_at | DateTime | Timestamps (BaseModel) |

### 3.3 Repositories

No dedicated repository classes needed. Use `BaseRepository` directly or inline SQLAlchemy queries.

---

## 4. V4 API Endpoints

### POST /api/v4/research/session

Create/initialize a research session. Delegates to WorkspaceService + DashboardService (no direct ORM access).

```
Request:  { title?: str, query?: str }
Response: { session_id, title, dashboard_overview, query_id? }
Traceability: query_id in response
```

### POST /api/v4/research/query

Execute a research query within a session. Delegates to AcademicService or GraphService.

```
Request:  { session_id, query: str, mode: report|synthesis|research|education|graph }
Response: AcademicResponse + { query_id, traceability: { query_id, trace_ids[], citation_count, source_documents[] } }
Side-effect: writes QueryHistory row via WorkspaceService (NOT direct DB)
```

### POST /api/v4/research/workflow

Execute a structured 5-step research workflow. Each step is a self-contained ResearchRun (logical entity) stored in `ResearchSession.workflow_state`.

```
Request:  { session_id, topic: str, workflow_type: str }
  → creates ResearchRun { run_id, session_id, ... }
Steps: 1) Topic selection  2) Literature retrieval  3) Evidence synthesis  4) Report generation  5) Citation export
  → each step writes to ResearchRun.step_execution_trace
Response: { run_id, steps: [{name, status, result, trace_ids[]}], traceability: { run_id, step→trace_ids{} } }
Side-effect: updates session.workflow_state with ResearchRun, writes QueryHistory per step
Invariant: Session ≠ Execution. One session can hold multiple ResearchRuns.
```

### POST /api/v4/visualization/graph

Generate structured visualization data — strict schema only.

```
Request:  { concept_labels[], graph_type: concept|citation|timeline|document }
Response: VisualizationGraph { nodes: VisualizationNode[], edges: VisualizationEdge[] }
           + { traceability: { source_entities[], edge_evidence[] } }
Schema:  extra="forbid" on all node/edge types. Every edge carries evidence_ids[].
```

### POST /api/v4/education/learn

Education mode with grounded explanations.

```
Request:  { session_id, topic: str, level: beginner|intermediate|advanced }
Response: AcademicResponse (education mode) + { query_id, traceability }
Side-effect: writes QueryHistory row
```

**Safety constraint (STRICT):** Education outputs MUST ONLY be:
- Simplifications of existing retrieved evidence
- Paraphrases of retrieved chunks
- NEVER introduce new factual content not present in the corpus

Rule: **"No inference beyond corpus evidence allowed."** Every education claim must be traceable to a retrieved passage. The `educate()` method in `AcademicService` already enforces this via claim-binding — V4 must not bypass it.

---

## 5. Traceability Design

### 5.1 Internal Full-Fidelity Trace

Each `trace_id` MUST internally carry:

| Field | Type | Description |
|-------|------|-------------|
| trace_id | UUID | Stable identifier |
| document_id | UUID | Source document |
| chunk_id | UUID | Retrieved chunk |
| passage_id | UUID | Source passage |
| retrieval_score | float | Relevance score |
| retrieval_method | string | dense / sparse / hybrid |
| timestamp | datetime | Internal only, NOT API-exposed |

### 5.2 API-Visible Traceability

Every V4 response includes a `traceability` block — stable IDs only, no internal fields leaked:

```json
{
  "query_id": "uuid",
  "trace_ids": ["uuid", ...],
  "citation_count": 5,
  "source_documents": ["《甲乙经》·宋校本", ...]
}
```

**Rule:** Internal full-fidelity trace is for debugging and reproducibility. API returns only stable IDs. No `retrieval_score`, `retrieval_method`, or `timestamp` ever exposed.

**Trace chain:** query → QueryHistory → AcademicResponse → EvidenceTrace[] → passage → version → book → document

Existing `EvidenceTrace` already carries `passage_id`, `document_id`, `citation_text`. Internal trace fields stored in `QueryHistory.result_summary` JSON — not in the API response envelope.

---

### 5.3 Visualization Schema Standardization

REPLACED loose `nodes[]`, `edges[]` WITH strict typed schemas:

```python
class VisualizationNode(BaseModel):
    """Strict visualization node — no free-form fields."""
    model_config = ConfigDict(extra="forbid")
    id: str
    type: Literal["concept", "document", "entity"]
    label: str
    metadata: dict[str, str]  # type-specific key-value, no nesting
    trace_ids: list[str]       # backlinks to EvidenceTrace

class VisualizationEdge(BaseModel):
    """Strict visualization edge — every edge carries evidence."""
    model_config = ConfigDict(extra="forbid")
    source: str
    target: str
    type: Literal["citation", "hierarchy", "co_occurrence", "similarity", "timeline"]
    weight: float
    evidence_ids: list[str]    # backlinks to EvidenceTrace

class VisualizationGraph(BaseModel):
    """Full graph output — no untyped structures."""
    model_config = ConfigDict(extra="forbid")
    nodes: list[VisualizationNode]
    edges: list[VisualizationEdge]
```

**Rules:**
- No free-form graph structures
- No untyped fields
- Every edge must carry `evidence_ids[]` — no edge without provenance
- Every node must carry `trace_ids[]`
- No rendering logic — data only

---

## 6. Test Requirements (21 tests)

| Category | Count | What |
|----------|-------|------|
| Research session | 5 | create session, create with query, list sessions, QueryHistory write via WorkspaceService, CitationCollection CRUD |
| Workflow execution | 5 | full 5-step flow, ResearchRun decoupling (2 runs in same session), step traceability, export markdown, error on invalid step |
| Visualization data | 4 | concept graph with strict nodes, citation network with evidence_ids on edges, timeline data, schema extra="forbid" enforcement |
| Education mode | 4 | beginner/intermediate/advanced level output, citation binding per concept, "no inference beyond corpus" guard, QueryHistory recording |
| Traceability validation | 3 | response includes traceability block, every trace_id resolves to passage, full chain to document with internal fields not leaked |

### 6.1 Traceability Test Spec

Each trace_id MUST internally carry: document_id, chunk_id, passage_id, retrieval_score, retrieval_method, timestamp. API response MUST NOT expose retrieval_score, retrieval_method, or timestamp. Tests verify both internal completeness AND API surface cleanliness.

---

## 7. Constraints

### 7.1 Core Constraints (from Sprint 1–3)
- DO NOT modify: ingestion, retrieval, citation system, knowledge graph core
- DO NOT modify: API v1/v2/v3 contracts
- All outputs must remain citation-bound and fully traceable

### 7.2 Hardened Constraints (Architecture Review Patch)

| # | Rule | Priority |
|---|------|----------|
| C1 | V4 API MUST NOT access ORM or database models directly — all data access through existing services | P0 |
| C2 | Session ≠ Execution — ResearchRun is a logical entity, not a DB row; one session can hold multiple runs | P0 |
| C3 | Traceability is internal full-fidelity (document_id, chunk_id, passage_id, retrieval_score, retrieval_method, timestamp); API returns only stable IDs | P0 |
| C4 | Visualization outputs MUST use strict typed schemas (VisualizationNode, VisualizationEdge) with extra="forbid" — no free-form graphs | P0 |
| C5 | Education outputs MUST ONLY simplify/paraphrase retrieved evidence — no inference beyond corpus | P0 |
| C6 | V4 API MUST NOT bypass v1–v3 logic — all outputs pass through citation system | P1 |
| C7 | All graph outputs MUST remain corpus-bound — every edge carries evidence_ids[] | P1 |
| C8 | No new Service classes — compose existing ones only | P0 |

### 7.3 Violation Detection

- Any `select()`, `session.execute()`, `session.add()`, or model class import in `api/v4/` = P0 blocker
- Any V4 response missing `traceability` block = P0 blocker
- Any VisualizationEdge without `evidence_ids[]` = P1 blocker
- Any education claim not traceable to a passage = P0 blocker

---

## 8. Files to Create/Modify

| File | Action | Content |
|------|--------|---------|
| `models/workspace.py` | Edit | Add QueryHistory, CitationCollection |
| `models/__init__.py` | Edit | Export new models |
| `api/v4/__init__.py` | Create | V4 router |
| `api/v4/research.py` | Create | session, query, workflow endpoints (no ORM access) |
| `api/v4/visualization.py` | Create | graph endpoint with strict schema |
| `api/v4/education.py` | Create | learn endpoint with corpus-bound safety |
| `api/__init__.py` | Edit | Register V4 router |
| `schemas/v4.py` | Create | V4 request/response schemas + VisualizationNode/Edge/Graph |
| `db/migrations/` | Create | Alembic migration for QueryHistory + CitationCollection tables |
| `tests/unit/test_sprint4_v4.py` | Create | All 21 tests |

---

## 9. Risk Reduction Summary

| Risk | Before Patch | After Patch |
|------|-------------|-------------|
| Service boundary violation | V4 could directly import models / run raw SQL | C1: all data access through existing services; violation = P0 blocker |
| Workflow/session coupling | Workflow tied to session state, one-run-per-session | C2: ResearchRun logical entity decouples execution from session; multi-run support |
| Traceability gaps | trace_ids only, no internal fidelity | C3: internal full-fidelity (6 fields); API surface returns stable IDs only |
| Visualization schema drift | loose nodes[]/edges[] — any shape accepted | C4: strict typed schemas with extra="forbid", evidence_ids on every edge |
| Education factual drift | No explicit guard against hallucinated content | C5: "No inference beyond corpus evidence" rule, every claim traceable to passage |
| API bypass risk | V4 could skip v1–v3 to call services directly | C6: all outputs must pass through citation system |
| Graph provenance gap | Edges could exist without evidence backlinks | C7: every edge carries evidence_ids[]; corpus-bound |

---

## 10. Backward Compatibility Confirmation

- V1 API: UNCHANGED (11 route files)
- V2 API: UNCHANGED (1 route file)
- Existing services: UNCHANGED (zero modification)
- Existing models: UNCHANGED (2 new models added, no existing columns touched)
- Existing tests: UNCHANGED (new test file only)
- Database: ADDITIVE only — 2 new tables, no schema migrations on existing tables
