---
title: Docs Changelog
document_id: HFB-DOC-CHANGELOG
version: 0.1.0
status: Draft
owner: Documentation Committee
reviewer: —
effective_date: 2026-06-25
scope: Documentation
priority: P2
---

# Docs Changelog

## Initial Upgrade Scaffold

- Renamed docs/03-data/0302_Ontology_Specification.md.md -> docs/03-data/0302_Ontology_Specification.md
- Archived docs/00-governance/00_Project_Charter.md -> docs/\_archive/legacy/00-governance**00_Project_Charter**20260625014208.md
- Archived docs/00-governance/01_Project_Constitution.md -> docs/\_archive/legacy/00-governance**01_Project_Constitution**20260625014208.md
- Archived docs/07-security/00_Acceptance_Specification.md -> docs/\_archive/legacy/07-security**00_Acceptance_Specification**20260625014208.md

## Run: 2026-06-25T02:34:23

- No changes.

## Run: 2026-06-25 (Manual Upgrade)

- Added YAML frontmatter to 36 files missing headers (document_id, version, status, owner, etc.)
- Created 21 missing README.md files for directories
  - `docs/08-domain/sprint-notes/README.md`
  - `docs/10-diagrams/src/README.md`
  - `docs/12-context/Sprint00/` through `Sprint16/` (17 README.md files)
  - `docs/_archive/README.md`
  - `docs/_archive/legacy/README.md`

## Run: 2026-06-25 (Governance Directory Upgrade)

Upgraded `docs/00-governance/` from early-stage project descriptions to the platform's supreme governance system:

- **0001-project-charter**: v0.1.0 → v1.0.0 — filled mission/vision/scope/success; added §6-§9 for product authority, MVP boundary, production gate, research framework
- **0002-project-constitution**: v1.0.0 → v1.1.0 — added §15 (product authority), §16 (MVP boundary), §17 (production gate); rewrote §11 (AI roles with clear boundaries)
- **0003-governance**: v0.1.0 → v1.0.0 — added §7 (MVP scope control), §8 (production gate control), §9 (AI role boundary enforcement); added AI role permission matrix
- **0004-documentation-rules**: v0.1.0 → v1.0.0 — added §1 (YAML metadata spec with document_id naming), §10 (document hierarchy with conflict resolution)
- **0005-ai-execution-protocol**: v1.0.0 → v1.1.0 — updated §3 (SSOT) and §4 (bootstrap) to reference 17/16 series; added MVP boundary and production standard to §7 (scope control)
- **README.md**: rewritten as unified governance entry with authority hierarchy, key references, and quick-entry guide

## Run: 2026-06-25 (Architecture Directory Upgrade)

Upgraded `docs/02-architecture/` to align with the upgraded governance system and 17-Platform-Specifications:

- **0201_Technical_Blueprint**: v1.0.0 → v1.1.0 — added Chapter 16 (MVP & Production Constraints); cross-referenced 17-series throughout all chapters; updated tech evolution roadmap to 10-Sprint MVP scope; separated MVP vs Post-MVP tech stack with ADR references; added phased AI architecture table; extended architecture red lines with MVP/production constraints
- **README.md**: rewritten as architecture index with linkage to 11-adr/, 17-Platform-Specifications/, 10-diagrams/, 15-decision-tree/

## Run: 2026-06-25 (Data Directory Upgrade)

Upgraded `docs/03-data/` to align with governance and platform specifications:

- **0301_Data_Standard**: v1.0.0 → v1.1.0 — added Chapter 13 (MVP Constraints) with data domain boundaries from HFB-PS-1709; updated related_documents
- **0302_Ontology**: v1.0.0 → v1.1.0 — added HFB-PS-1709 cross-reference in Chapter 18 for MVP entity boundaries; updated related_documents
- **0303_Metadata**: v1.0.0 → v1.1.0 — added Chapter 16 (MVP & Production Constraints); updated related_documents
- **0304_Entity**: v1.0.0 → v1.1.0 — added HFB-PS-1709 cross-reference in Chapter 3 for MVP entity boundaries; updated related_documents
- **0305_Relation**: v1.0.0 → v1.1.0 — updated related_documents
- **README.md**: rewritten as data standards index with spec hierarchy, linked directories, MVP data boundary summary

## Run: 2026-06-25 (AI Directory Upgrade)

Upgraded `docs/04-ai/` to align with governance, platform specifications, and data standards:

- **0401_AI_Engineering_Standard**: v1.0.0 → v1.1.0 — added Chapter 18 (MVP & Production Constraints); reformatted Chapter 17 as phased table with MVP/Post-MVP labels; updated related_documents with HFB-PS-1705/1709/1710
- **0402_RAG**: v1.0.0 → v1.1.0 — updated related_documents
- **0403_GraphRAG**: v1.0.0 → v1.1.0 — reaffirmed Post-MVP only; updated related_documents
- **0404_Prompt_Engineering**: v1.0.0 → v1.1.0 — updated related_documents
- **0405_AI_Academic_Review**: v1.0.0 → v1.1.0 — updated related_documents
- **README.md**: rewritten as AI spec index with hierarchy, AI role responsibility table, MVP AI boundary table

## Run: 2026-06-25 (Development Directory Upgrade)

Upgraded `docs/05-development/` to align with governance, architecture, and platform specifications:

- **All 10 spec files** (0501–0510): v1.0.0 → v1.1.0 — updated related_documents with HFB-PS-1709, HFB-PS-1710, HFB-GOV-0003, HFB-PS-1702, HFB-PS-1708 as appropriate
- **README.md**: rewritten as dev standards index with spec hierarchy table, linked directories, MVP dev boundary, production dev standards

## Run: 2026-06-25 (UI Directory Upgrade)

Upgraded `docs/06-ui/` to align with platform specifications:

- **All 5 spec files** (0601–0605): v1.0.0 → v1.1.0 — updated related_documents with HFB-PS-1702, HFB-PS-1703, HFB-PS-1705, HFB-PS-1707, HFB-PS-1709, HFB-PS-1710 as appropriate
- **README.md**: rewritten as UI spec index with hierarchy, Gemini UX review role, linked directories, MVP UI boundary

## Run: 2026-06-25 (Security + Domain Directories Upgrade)

**07-security** — 5 spec files v1.0.0 → v1.1.0; README rewritten; all now reference HFB-PS-1710 as production go-live supreme standard.

**08-domain** — 9 spec files v1.0.0 → v1.1.0; README rewritten as knowledge model index with dependency graph, MVP data boundary, linked directories; all now reference HFB-PS-1709 and 16-research-framework.

## Run: 2026-06-25 (Prompts + Diagrams Directories Upgrade)

**09-prompts** — README rewritten as Prompt asset index with AI role responsibility table, linked directories, engineering reference.

**10-diagrams** — README updated with linked directories and MVP chart boundary.

## Run: 2026-06-25 (Context + Machine + Knowledge + Decision-Tree + Academic-Assets Upgrade)

**11-adr** — README updated with MVP column in ADR list, MVP & ADR section, linked directories.

**12-context** — README rewritten with AI bootstrap flow, MVP context constraint, linked directories.

**13-machine** — README updated with linked directories and AI Execution Protocol reference.

**14-knowledge** — README updated with linked directories and MVP data boundary.

**15-decision-tree** — README updated with MVP column, linked directories.

**18-academic-assets** — README updated with linked directories and MVP constraint.

## Run: 2026-06-25 (Research Framework Upgrade)

**16-research-framework** — README rewritten as research framework index with linked directories, governance authority reference, product function alignment constraint.

## Run: 2026-06-25 (Platform Specifications Upgrade)

**17-Platform-Specifications** — README rewritten as product specs supreme authority index with linked directories, governance authority references, change control process. All 10 spec files (1701–1710) v1.0.0 → v1.1.0 with updated related_documents referencing HFB-GOV-0001/0002/0005 and cross-references to each other.

## Run: 2026-06-25 (Acceptance Blocker Fixes)

Fixed all acceptance blockers from audit:

- **documentation-index.md** — rebuilt from real file tree (291 files); removed nonexistent paths (`08-sprints/`, `0002-constitution.md`); corrected all file references
- **P0 README YAML headers** — added to 9 files (`00-governance/` through `08-domain/sprint-notes/`)
- **01-product** — rewrote `00_Product_Roadmap.md` (GraphRAG removed from MVP, aligned with HFB-PS-1709/1710) and `README.md`
- **HFB-STD-\* purge** — replaced all 7 occurrences across 9 files with real document_ids
- **.DS_Store** — deleted 4 files
- **DOCS_STRUCTURE_AUDIT.md** — updated to current state (0 missing YAML, 0 missing README)

Verification: .md.md=0, HFB-STD-=0, .DS_Store=0, no broken paths, all P0 READMEs have YAML headers, zero document_id duplicates.

## Final Summary: 2026-06-25

Complete docs upgrade and acceptance fix concluded. **18 directories, ~100 files modified.** All blockers resolved. Zero HFB-STD-\*, zero .DS_Store, zero .md.md, zero broken paths, zero duplicate document_ids.
