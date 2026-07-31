# Roadmap — 皇甫谧数字人文平台

## Overview

本路线图覆盖 **Sprint 0 至 Sprint 16**，总工期预计 4-6 个月。

```
Sprint 0    → Foundation & Governance ✅
Sprint 1-4  → Core Infrastructure
Sprint 5-8  → Search & AI
Sprint 9-12 → Features & Quality
Sprint 13-16→ Production Readiness
```

---

## Sprint 0 — Foundation ✅

### Sprint 0.1 — Project Governance ✅

- Project Charter & Constitution
- Documentation structure
- ADR process established
- AI engineering standards
- Product roadmap v0

### Sprint 0.2 — Repository Foundation ✅

- Monorepo scaffolding
- GitHub community files
- Git standards & pre-commit
- Python & Node development standards
- Docker configurations
- CI/CD pipelines
- VS Code workspace
- Makefile

---

## Sprint 1 — Backend Core Infrastructure

**Goal**: FastAPI project scaffolding with database connections

- [ ] FastAPI application skeleton
- [ ] Pydantic models & settings
- [ ] PostgreSQL connection & Alembic migrations
- [ ] Health check endpoints
- [ ] Structured logging
- [ ] Error handling middleware
- [ ] CORS configuration
- [ ] Unit test infrastructure

---

## Sprint 2 — Frontend Scaffolding

**Goal**: Vue 3 project setup with component architecture

- [x] Vite + Vue 3 + TypeScript setup
- [x] Vue Router configuration
- [x] Pinia state management
- [x] Component directory structure
- [x] Layout system
- [x] API client configuration
- [x] i18n framework
- [x] Dark mode support

---

## Sprint 3 — Database & Data Layer

**Goal**: Full database schema and data access layer

- [x] PostgreSQL schema design
- [x] Alembic migration framework
- [x] SQLAlchemy 2.0 async models
- [x] Repository pattern implementation
- [x] Data validation pipeline
- [x] Seed data & fixtures
- [x] Database testing utilities

---

## Sprint 4 — Knowledge Graph Engine ✅

**Goal**: Application-layer graph traversals on PostgreSQL (Neo4j deferred)

- [x] EntityRelation model (cross-entity relationships)
- [x] GraphService (BFS path finding, neighborhood, subgraph)
- [x] FK-derived edges (Book→Person, Version→Book, Passage→Version)
- [x] Graph API (7 endpoints)
- [x] GraphExplorerView + GraphCanvas.vue (vis-network)
- [x] Seed graph relations (8 curated scholar relationships)

---

## Sprint 5 — Vector Search & RAG ✅

**Goal**: Unified search with ILIKE and RAG pipeline

- [x] SearchService (ILIKE cross-entity, scoring, snippets)
- [x] Autocomplete (prefix match)
- [x] Search API (3 endpoints)
- [x] SearchView with faceted filters, pagination
- [x] RAG service (context retrieval + assembly)
- [x] AI Gateway (streaming chat, summarize, translate, compare)

---

## Sprint 6 — API Layer ✅

**Goal**: Full REST API with OpenAPI documentation

- [x] CRUD endpoints for all 8 entity types
- [x] Graph API, Search API, AI API, Dashboard API
- [x] Workspace API (sessions + notes)
- [x] Pagination & filtering
- [x] API versioning (v1)
- [x] RBAC on all endpoints (73 total, audited)
- [x] OpenAPI auto-documentation via FastAPI

---

## Sprint 7 — UI Components

**Goal**: Design system and component library

- [ ] Component library setup (packages/ui)
- [ ] Design system tokens (colors, typography, spacing)
- [ ] Core components (Button, Input, Card, Table, Modal, etc.)
- [ ] Form components with validation
- [ ] Data visualization components
- [ ] Accessibility (WCAG 2.1 AA)

---

## Sprint 8 — Full-Text Search

**Goal**: Elasticsearch integration for document search

- [ ] Elasticsearch index design
- [ ] Document ingestion pipeline
- [ ] Chinese text analysis (jieba/IK)
- [ ] Advanced search queries
- [ ] Faceted search
- [ ] Search result highlighting
- [ ] Search analytics

---

## Sprint 9 — AI Pipeline

**Goal**: End-to-end AI processing pipeline

- [ ] LLM integration layer
- [ ] GraphRAG implementation
- [ ] Entity extraction pipeline
- [ ] Relation extraction pipeline
- [ ] Text classification
- [ ] Named entity recognition (TCM-specific)
- [ ] AI pipeline orchestration

---

## Sprint 10 — User Authentication

**Goal**: Authentication and authorization

- [ ] JWT-based authentication
- [ ] Role-based access control (RBAC)
- [ ] OAuth2 / Social login
- [ ] Session management
- [ ] Password policies
- [ ] Audit logging
- [ ] API key management

---

## Sprint 11 — Admin Dashboard

**Goal**: Administrative interface

- [ ] Admin layout
- [ ] User management
- [ ] System monitoring dashboard
- [ ] Data import/export
- [ ] Configuration management
- [ ] Job queue monitoring

---

## Sprint 12 — Testing & QA

**Goal**: Comprehensive test coverage

- [ ] Unit test suite (80%+ coverage)
- [ ] Integration test suite
- [ ] E2E test suite (Playwright)
- [ ] Performance testing (k6)
- [ ] Security testing (OWASP ZAP)
- [ ] Accessibility testing
- [ ] Visual regression testing

---

## Sprint 13 — Deployment & DevOps

**Goal**: Production deployment infrastructure

- [ ] Kubernetes manifests
- [ ] Helm charts
- [ ] Terraform infrastructure
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Centralized logging (ELK/Loki)
- [ ] Backup & disaster recovery
- [ ] Auto-scaling configuration

---

## Sprint 14 — Documentation & Localization

**Goal**: Complete documentation and i18n

- [ ] API documentation (OpenAPI)
- [ ] User manual (中文 + English)
- [ ] Developer guide
- [ ] Administrator guide
- [ ] i18n implementation (zh-CN, en)
- [ ] Translation pipeline
- [ ] Documentation website

---

## Sprint 15 — Security Audit & Hardening

**Goal**: Security review and hardening

- [ ] Third-party security audit
- [ ] Dependency vulnerability scan
- [ ] SAST/DAST integration
- [ ] Penetration testing
- [ ] Hardening checklist
- [ ] Compliance review
- [ ] Incident response plan

---

## Sprint 16 — Production Launch

**Goal**: Production go-live

- [ ] Production environment setup
- [ ] Load testing & capacity planning
- [ ] Go-live checklist
- [ ] Rollback plan
- [ ] Monitoring & alerting finalization
- [ ] Launch announcement
- [ ] Post-launch support plan

---

> **注意**：本路线图为规划文档，具体Sprint内容可能根据实际情况调整。所有变更需通过ADR流程记录。
