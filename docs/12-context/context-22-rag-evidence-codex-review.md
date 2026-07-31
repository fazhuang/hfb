# Context 22 RAG Evidence Binding Codex Re-Review

Date: 2026-07-10

Verdict: WORKTREE PASS

Release note: 当前结论基于 dirty worktree。未执行 clean HEAD / clean export 发布验收，因此不能替代提交后发布门禁。

## Scope

本轮重新验收 RAG 证据绑定：

- 是否只使用合规全文。
- 是否每个回答都有 citation。
- 是否无证据不生成结论。
- 是否过滤商业数据库全文。
- 是否保留页码和段落。
- 是否测试覆盖幻觉防控。

## Current Result

| Gate                      | Verdict                    | Evidence                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| ------------------------- | -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 是否只使用合规全文        | PASS                       | `RetrievalService(strict_compliance=True)` 与 `EvidenceRAGService` 共享 `_compliance_clauses`：`rag_enabled=True`、版权状态在 allowlist、`authorization_basis` 或 `license_type` 非空、`withdrawn_at IS NULL`。同时外层查询仍过滤 `Document.is_deleted=False` 与 `DocumentChunk.is_deleted=False`。见 `apps/backend/app/services/retrieval.py:34-63`、`apps/backend/app/services/retrieval.py:129-153`、`apps/backend/app/services/evidence_rag_service.py:125-138`。 |
| 是否每个回答都有 citation | PASS for RAG/generate path | `EvidenceRAGResponse` 非拒答强制 `citations/evidence` 非空；`GenerationPipeline` 非拒答 citations/results 均携带 citation。                                                                                                                                                                                                                                                                                                                                           |
| 是否无证据不生成结论      | PASS                       | 商业受限、禁用版权、缺授权依据、撤回态污染均拒答；运行探针中撤回态返回 `EVIDENCE_GATE_REFUSAL` 且 results/citations 为空。                                                                                                                                                                                                                                                                                                                                            |
| 是否过滤商业数据库全文    | PASS                       | `commercial_restricted` 不在 allowlist；此前商业库污染态探针已关闭，合并测试持续覆盖该状态。                                                                                                                                                                                                                                                                                                                                                                          |
| 是否保留页码和段落        | PASS                       | `EvidenceRAGService` citation 保留 `p.` / `par.`；`GenerationPipeline` citations/results 保留 `page_number`、`paragraph_index`、`source_url`、`copyright_status`。                                                                                                                                                                                                                                                                                                    |
| 是否测试覆盖幻觉防控      | PASS for current gate      | 测试覆盖无证据拒答、商业/禁用状态、缺授权依据、license_type-only、撤回态污染、API generate 层拒答、正常合规文档成功与 provenance。                                                                                                                                                                                                                                                                                                                                    |

## Commands Run

```text
.venv/bin/python -m pytest tests/unit/test_rag_generation_compliance.py -q
26 passed in 5.59s
```

```text
.venv/bin/python -m pytest tests/unit/test_rag_evidence_binding.py tests/unit/test_rag_no_unsupported_claims.py tests/unit/test_rag_copyright_filter.py tests/unit/test_fulltext_compliance.py tests/unit/test_day4_generation.py tests/unit/test_rag_generation_compliance.py -q
143 passed, 1 deselected in 20.06s
```

## Runtime Probes

Withdrawn polluted state is now blocked:

```text
copyright_status = public_domain
authorization_basis = "public domain"
rag_enabled = True
withdrawn_at = non-null
is_deleted = False
chunk.is_deleted = False
query = WITHDRAWN_POLLUTION_SENTINEL

Observed:
rag_refusal= True
rag_evidence_count= 0
rag_citations_count= 0
gen_answer= EVIDENCE_GATE_REFUSAL: 验证失败: EMPTY_RETRIEVAL
gen_results= []
gen_citations= []
gen_error_code= EMPTY_RETRIEVAL
```

Clean compliant document still succeeds and preserves provenance:

```text
copyright_status = public_domain
authorization_basis = "public domain"
rag_enabled = True
withdrawn_at = None
query = CLEAN_COMPLIANT_SENTINEL

Observed:
rag_refusal= False
rag_evidence_count= 1
rag evidence includes source_url=https://example.org/clean, page_number=8, paragraph_index=4
gen_refusal= False
gen citations/results include source_url, copyright_status, page_number=8, paragraph_index=4
```

## Accepted Worktree Surface

The current worktree satisfies Context 22 RAG evidence binding for the scoped RAG/generate paths:

- Evidence source must be non-deleted, non-withdrawn, `rag_enabled`, copyright-allowed, and authorization-backed.
- Restricted or polluted evidence states fail closed.
- Non-refusal responses preserve citation and provenance.

Final gate: WORKTREE PASS.
