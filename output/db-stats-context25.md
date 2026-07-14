# HFB Database Statistics — Context 25 Audit

**Database:** `hfb` on `localhost:5432`, user `hfb`
**Snapshot date:** 2026-07-13
**Total tables in public schema:** 42

---

## Row Counts for All 42 Tables

| # | Table Name | Row Count | Data Type | Notes |
|---|-----------|-----------|-----------|-------|
| 1 | academic_entities | 0 | empty | TCM entity table, created but unused |
| 2 | academic_relations | 0 | empty | TCM relation table, created but unused |
| 3 | alembic_version | 1 | seed | Single migration tracking row |
| 4 | books | 2 | seed | 针灸甲乙经, 黄帝内经 — classical book metadata |
| 5 | chapters | 1 | seed | 序 chapter for 针灸甲乙经 |
| 6 | citation_collections | 0 | empty | Unused grouping table |
| 7 | citations | 5 | real | Linked to evidences, part of the citation chain |
| 8 | classical_versions | 0 | empty | Unused; versions table is the active one |
| 9 | commentaries | 0 | empty | Unused |
| 10 | document_chunks | 14 | real + test | Chunks from real ingestion + test probes; 5 soft-deleted |
| 11 | documents | 17 | seed + test | 3 seed (classical texts) + 14 test/probe docs; 5 soft-deleted |
| 12 | entity_relations | 5 | real | Real graph edges (person-book, book-book, book-passage) |
| 13 | evidences | 6 | real + test | 1 test + 5 real from research workflow |
| 14 | fulltext_ingestion_audit | 23 | real | Full audit trail of all ingestion actions (ingest/withdraw) |
| 15 | images | 0 | empty | Unused |
| 16 | institutions | 0 | empty | Unused |
| 17 | papers | 20 | real | Real academic papers from 5 ingestion sources (OpenAlex, Crossref, CORE, PubMed, Internet Archive) |
| 18 | passage_mappings | 0 | empty | Unused |
| 19 | passages | 8 | real | 8 passages from 针灸甲乙经 序 chapter |
| 20 | permissions | 144 | seed | RBAC permission definitions |
| 21 | persons | 3 | seed | 皇甫谧, 张仲景, 李时珍 |
| 22 | query_histories | 65 | real | Research workflow traces with citation provenance |
| 23 | relation_confidences | 0 | empty | Unused |
| 24 | relation_evidences | 0 | empty | Unused |
| 25 | research_notes | 1 | test | Single test note from Context25 workflow |
| 26 | research_sessions | 35 | real + test | Mix of test sessions and real research workflows |
| 27 | role_permission | 423 | seed | RBAC role-permission mappings |
| 28 | roles | 7 | seed | 7 RBAC roles defined |
| 29 | sentences | 0 | empty | Unused |
| 30 | source_policies | 5 | seed | 5 ingestion sources configured (openalex, crossref, core, pubmed, internet_archive) |
| 31 | source_refs | 1 | real | 1 bibliographic source ref linking a passage to ctext.org |
| 32 | tcm_entities | 0 | empty | Unused |
| 33 | text_sentences | 0 | empty | Unused |
| 34 | text_tokens | 0 | empty | Unused |
| 35 | textual_variants | 0 | empty | Unused |
| 36 | tokens | 0 | empty | Unused |
| 37 | user_role | 8 | seed | 8 user-role assignments |
| 38 | users | 8 | seed + test | 1 admin + 7 test/researcher users |
| 39 | variants | 0 | empty | Unused |
| 40 | version_diffs | 0 | empty | Unused |
| 41 | version_relations | 0 | empty | Unused |
| 42 | versions | 1 | seed | Single version: 明代刻本 of 针灸甲乙经 |

---

## Required Tables Mapping

| Required Table | Actual Table(s) | Row Count | Data Type | Notes |
|---------------|-----------------|-----------|-----------|-------|
| documents | documents | 17 | seed + test | 3 classical seed docs + 14 ingestion/test probes |
| literature_records | papers (+ books) | 20 (+2) | real (+seed) | `papers` = academic ingestion from 5 sources; `books` = classical book metadata |
| versions / classical_text_versions | versions (classical_versions exists but empty) | 1 (0) | seed (empty) | Only 1 version seeded (明代刻本) |
| full_text_documents | documents (+ document_chunks) | 17 (+14) | seed + test (+real+test) | Documents store full text; chunks are the RAG-ready splits |
| evidences | evidences | 6 | real + test | 1 test + 5 from real research workflow |
| citations | citations | 5 | real | All link to evidences via `evidence_id` |
| source_refs | source_refs | 1 | real | Links passage to ctext.org URL |
| persons | persons | 3 | seed | Classical TCM authors |
| places | — | — | does not exist | No places/institutions table with data; `institutions` = 0 rows |
| events | — | — | does not exist | No events table in the schema |
| research | research_sessions (+ research_notes) | 35 (+1) | real + test (+test) | Sessions track user research workflows |
| ingestion_jobs | fulltext_ingestion_audit | 23 | real | Full audit trail: 12 fulltext_ingest + 11 withdraw actions |
| chunks | document_chunks | 14 | real + test | 5 of 14 are soft-deleted |
| embeddings | — | — | stored externally | No embedding table/column in PostgreSQL; Milvus is configured as the vector store |
| vectors | — | — | stored externally | pgvector extension available (Docker image: `pgvector/pgvector:pg16`) but no vector columns/tables created yet |

---

## Citation Chain Verification

### Schema
```
citations.evidence_id → evidences.id
evidences.source_passage_id → passages.id
passages.version_id → versions.id
versions.book_id → books.id
```

### Chain Integrity Check (5 of 5 citations verified)
```
citation_id                          → evidence_id                        → passage_id                          → version_id                          → version_name
e58bcbf8-... (target: document)      → dc321f04-...                        → 1112a4bb-...                        → 9b48b722-...                        → 明代刻本
34a9480b-... (target: document)      → 45d52522-...                        → 995e8d98-...                        → 9b48b722-...                        → 明代刻本
fcde7c0c-... (target: document)      → 72a74dc2-...                        → b7a0bca6-...                        → 9b48b722-...                        → 明代刻本
f5658cf0-... (target: document)      → d33c410c-...                        → e8d72894-...                        → 9b48b722-...                        → 明代刻本
9d648b51-... (target: document)      → b106e4fb-...                        → 0b7398ae-...                        → 9b48b722-...                        → 明代刻本
```

All 5 citations chain cleanly through evidence → passage → version. All point to the single seeded version (明代刻本 of 针灸甲乙经). The citation `target_type` is `document` for all 5, meaning they cite documents directly rather than passages.

### Extended Chain (entity_relations → citations)

The full provenance pipeline is:
1. `entity_relations` (5 rows) — graph edges with evidence fields (`evidence_document_id`, `evidence_chunk_id`, `evidence_passage_id`, `evidence_version_id`, `evidence_quote`)
2. `evidences` (6 rows) — deduplicated evidence records linked to `source_passage_id`
3. `citations` (5 rows) — links to evidences via `evidence_id`
4. `passages` (8 rows) — content text with `version_id` FK
5. `versions` (1 row) — version metadata with `book_id` FK

---

## Key Observations

1. **Real data exists** in: papers (20), fulltext_ingestion_audit (23), document_chunks (14), passages (8), citations (5), evidences (6), entity_relations (5), research_sessions (35), query_histories (65), source_refs (1).

2. **Seed data exists** in: persons (3), books (2), documents (3 of 17), versions (1), chapters (1), source_policies (5), users (8), roles/permissions.

3. **Test probes present**: Several documents/chunks with "探针", "Codex", "Context25" markers, created during acceptance testing. 5 documents and 5 chunks are soft-deleted.

4. **Empty/unused tables**: 18 of 42 tables have 0 rows (academic_entities, academic_relations, citation_collections, classical_versions, commentaries, images, institutions, passage_mappings, relation_confidences, relation_evidences, sentences, tcm_entities, text_sentences, text_tokens, textual_variants, tokens, version_diffs, version_relations).

5. **No PostgreSQL vectors**: pgvector is available (pgvector/pgvector:pg16 Docker image) but no vector columns or indexes exist. Embeddings are configured to use Milvus externally (host: localhost:19530).

6. **No places or events tables**: These domain entities don't exist in the current schema.

7. **Active ingestion sources**: 5 configured (openalex, crossref, core, pubmed, internet_archive), all enabled.

8. **Soft-delete pattern**: Most tables use `deleted_at` + `is_deleted` columns for logical deletion.
