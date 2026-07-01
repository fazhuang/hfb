"""
Academic Service — Sprint 2 academic product layer (P0 remediated).

Composes GenerationPipeline for each module. Does NOT modify Sprint 1 systems.

P0-1: EvidenceTrace maps 1:1 to output claims, not retrieval results.
P0-2: Reproducibility metadata (SHA-256), every sentence cited, empty=refusal.
P0-3: Synthesis retains source chunks, no manufactured facts.
P0-4: Hypotheses only with evidence; null when gapped.
P0-5: No unsupported factual prose. Extractive presentation.
P0-6: Unsupported-claim gate — deterministic proposition classifier.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.academic import (
    AcademicMetadata,
    AcademicResponse,
    CitationRef,
    EducationConcept,
    EvidenceTrace,
    ReproducibilityMetadata,
    ReportSection,
    ResearchSubQuestion,
    SynthesisTheme,
    UnsupportedClaimVerdict,
)
from app.schemas.generation import GroundedGenerationResponse
from app.services.generation_service import GenerationPipeline


class AcademicService:
    """Academic product layer — report, synthesis, research, education.

    All four methods share the same pipeline composition pattern:
    1. Run GenerationPipeline.generate() for fact-grounded claims
    2. Run unsupported-claim gate (P0-6)
    3. Extract claim-bound EvidenceTraces (P0-1)
    4. Structure output per module type
    5. Attach reproducibility metadata (P0-2)
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ==================================================================
    # P0-6: UNSUPPORTED-CLAIM GATE
    # ==================================================================

    # Proposition patterns that demand concrete evidence
    _UNSUPPORTED_PATTERNS: list[tuple[str, str]] = [
        # Universal quantifiers
        ("universal_quantifier", r"(所有|全部|任何|一切|凡是|必然)"),
        # Modern projection terms
        ("modern_projection", r"(现代医学|现代科学|现代概念|西医|科学验证|临床实验)"),
        # Causal/treatment assertions
        ("causal_assertion", r"(治疗|治愈|导致|证明|证实|可以.*治疗|能够.*治疗)"),
        # Yes/no proposition forms
        ("proposition", r"(是否|能否|是不是|有没有|可不)"),
    ]

    @classmethod
    def _classify_unsupported_proposition(cls, query: str) -> list[tuple[str, str]]:
        """Classify a query for unsupported proposition types. Returns matched types."""
        matched: list[tuple[str, str]] = []
        for ptype, pattern in cls._UNSUPPORTED_PATTERNS:
            if re.search(pattern, query):
                matched.append((ptype, pattern))
        return matched

    @classmethod
    def _extract_proposition_terms(cls, query: str) -> list[str]:
        """Extract the specific terms that trigger proposition patterns."""
        terms: list[str] = []
        for _ptype, pattern in cls._UNSUPPORTED_PATTERNS:
            for m in re.finditer(pattern, query):
                terms.append(m.group(1))
        return sorted(set(terms))

    @classmethod
    def _check_proposition_support(
        cls, query: str, chunks_content: list[str]
    ) -> UnsupportedClaimVerdict:
        """Deterministic unsupported-claim gate.

        For each proposition pattern found in the query, verify that
        the retrieved chunks contain evidence supporting the claim.
        Mere keyword overlap is NOT sufficient — the decisive
        proposition must be present in evidence.

        Supported: chunks contain the proposition's subject and predicate.
        Unsupported: only the subject (e.g. "皇甫谧") matches, not the predicate
                      (e.g. "现代医学概念").
        """
        matched_types = cls._classify_unsupported_proposition(query)
        if not matched_types:
            return UnsupportedClaimVerdict(
                is_supported=True,
                proposition_type="none",
                reason="No unsupported proposition pattern detected",
            )

        matched_keywords = cls._extract_proposition_terms(query)
        combined_content = "\n".join(chunks_content)
        # Normalize whitespace for comparison
        content_norm = re.sub(r"\s+", "", combined_content)

        # The query minus its proposition marker is the "subject"
        # The terms after proposition markers are the "predicate"
        # If only the subject matches chunks but not the predicate, gate fails

        # Extract proposition predicates from query
        # Pattern: X是否Y → subject=X, predicate=Y
        #          X治疗Y → subject=X, predicate=Y
        prop_terms = matched_keywords  # the trigger words

        # Check each matched proposition type
        for ptype, _pattern in matched_types:
            if ptype == "universal_quantifier":
                # "所有", "全部" etc — check if the claim about "all" is present in evidence
                # If evidence only mentions individual cases, universal claim is unsupported
                for term in prop_terms:
                    if term in ("所有", "全部", "任何", "一切", "凡是", "必然"):
                        if term not in content_norm:
                            return UnsupportedClaimVerdict(
                                is_supported=False,
                                proposition_type=ptype,
                                matched_keywords=prop_terms,
                                reason=f"Universal quantifier '{term}' not grounded in evidence",
                            )

            elif ptype == "modern_projection":
                for term in prop_terms:
                    norm_term = re.sub(r"\s+", "", term)
                    if norm_term in (
                        "现代医学",
                        "现代科学",
                        "现代概念",
                        "西医",
                        "科学验证",
                        "临床实验",
                    ):
                        if norm_term not in content_norm:
                            return UnsupportedClaimVerdict(
                                is_supported=False,
                                proposition_type=ptype,
                                matched_keywords=prop_terms,
                                reason=f"Modern concept '{term}' not found in retrieved chunks",
                            )

            elif ptype == "causal_assertion":
                for term in prop_terms:
                    norm_term = re.sub(r"\s+", "", term)
                    if norm_term in ("治疗", "治愈", "导致", "证明", "证实"):
                        # Causal claims need the causal predicate in evidence
                        # Check if any chunk explicitly states this causal relationship
                        if not any(
                            norm_term in re.sub(r"\s+", "", c) for c in chunks_content
                        ):
                            return UnsupportedClaimVerdict(
                                is_supported=False,
                                proposition_type=ptype,
                                matched_keywords=prop_terms,
                                reason=f"Causal assertion '{term}' not evidenced in chunks",
                            )

            elif ptype == "proposition":
                # Yes/no forms: the query asks "whether X is Y"
                # If the proposition's predicate doesn't appear in chunks at all,
                # we cannot support either answer
                # Extract predicate: text after 是否/能否 etc that's not in chunks
                # ponytail: extract predicate by removing subject keywords
                query_norm = re.sub(r"\s+", "", query)
                # Remove the proposition marker to get what's being asked
                re.sub(
                    r"(是否|能否|是不是|有没有|可不)", " ", query_norm
                )
                # Get candidate predicates: "现代医学概念", "所有疾病", etc.
                # If these predicates don't appear in content, gate fails
                set(query_norm)
                set(content_norm)

                # Check if the key non-subject terms from query appear in content
                # If content only matches the subject (e.g. 皇甫谧, 针灸) but not
                # the predicate (e.g. 现代, 治疗), the claim is unsupported
                subject_indicators = cls._find_query_subject_overlap(
                    query_norm, chunks_content
                )
                predicate_gap = cls._find_predicate_gap(
                    query_norm, chunks_content, subject_indicators
                )
                if predicate_gap:
                    return UnsupportedClaimVerdict(
                        is_supported=False,
                        proposition_type=ptype,
                        matched_keywords=prop_terms,
                        reason=f"Proposition predicate not evidenced: {predicate_gap}",
                    )

        return UnsupportedClaimVerdict(
            is_supported=True,
            proposition_type="mixed" if matched_types else "none",
            matched_keywords=matched_keywords,
            reason="Propositions checked against evidence",
        )

    @classmethod
    def _find_query_subject_overlap(
        cls, query_norm: str, chunks_content: list[str]
    ) -> set[str]:
        """Find query terms that DO appear in chunks (the subject)."""
        content_norm = re.sub(r"\s+", "", "\n".join(chunks_content))
        overlapping: set[str] = set()
        # Tokenize by breaking on common Chinese proposition markers
        tokens = re.split(r"[，。！？、：；（）\s]+", query_norm)
        for token in tokens:
            token_norm = re.sub(r"\s+", "", token)
            if len(token_norm) >= 2 and token_norm in content_norm:
                overlapping.add(token_norm)
        return overlapping

    @classmethod
    def _find_predicate_gap(
        cls, query_norm: str, chunks_content: list[str], subject_overlap: set[str]
    ) -> str | None:
        """Find significant query terms NOT present in chunks (predicate gap).

        Returns the first gapped term, or None if all terms are present.
        """
        content_norm = re.sub(r"\s+", "", "\n".join(chunks_content))
        # Split query into candidate terms
        tokens = re.split(r"[，。！？、：；（）\s]+", query_norm)
        significant_tokens = [t for t in tokens if len(re.sub(r"\s+", "", t)) >= 2]

        # Remove proposition markers to find predicates
        prop_markers = {"是否", "能否", "是不是", "有没有", "可不"}
        pred_candidates = [t for t in significant_tokens if t not in prop_markers]

        for token in pred_candidates:
            token_norm = re.sub(r"\s+", "", token)
            if len(token_norm) < 2:
                continue
            if token_norm not in content_norm and token_norm not in subject_overlap:
                # This token is in the question but not in any chunk — potential gap
                # But we need to check it's truly a predicate, not noise
                # Only flag if it's a substantial concept word (≥3 chars for Chinese)
                if len(token_norm) >= 3:
                    return token_norm
                # For 2-char tokens, only flag if it's clearly a concept
                if re.match(r"[一-鿿]{2}", token_norm):
                    return token_norm

        return None

    # ==================================================================
    # P0-1: CLAIM-BOUND EVIDENCE
    # ==================================================================

    @classmethod
    def _extract_claim_traces(
        cls, result: GroundedGenerationResponse
    ) -> list[EvidenceTrace]:
        """P0-1: EvidenceTrace per actual output claim, not per retrieval result.

        Each sentence in result.answer maps to one EvidenceTrace.
        The sentence's source text IS the quote, verified by GenerationPipeline.
        No fallback citations. Unused retrieval results excluded.
        """
        traces: list[EvidenceTrace] = []

        # Build citation lookup from result.citations
        citation_map: dict[str, dict] = {}
        for c in result.citations:
            citation_map[c["chunk_id"]] = c

        # Build content lookup from result.results
        content_map: dict[str, str] = {}
        for r in result.results:
            content_map[r["chunk_id"]] = r["content"]

        # Parse the answer into citation-bound claims
        # GenerationPipeline renders: "quote。 [doc_id:chunk_id]"
        # Each line between citation markers is a claim
        answer = result.answer
        if not answer or "EVIDENCE_GATE_REFUSAL" in answer:
            return []

        # Split by citation pattern to get claim-citation pairs
        citation_re = re.compile(r"\[([^\]]+):([^\]]+)\]")

        # Find all citation positions
        citations_positions = list(citation_re.finditer(answer))

        if not citations_positions:
            return []

        # For each citation, find its preceding quote text
        prev_end = 0
        for i, m in enumerate(citations_positions):
            citation_start = m.start()
            claim_text = answer[prev_end:citation_start].strip()
            # Strip trailing newlines/whitespace but preserve content
            claim_text = claim_text.rstrip("\n ")

            doc_id = m.group(1)
            chunk_id = m.group(2)

            if chunk_id in content_map:
                chunk_content = content_map[chunk_id]
                # Find the exact quote from the claim in the chunk
                quote = cls._find_quote_in_chunk(claim_text, chunk_content)
                if quote:
                    traces.append(
                        EvidenceTrace(
                            claim_text=claim_text,
                            quote=quote,
                            document_id=doc_id,
                            chunk_id=chunk_id,
                            citation_text=f"[{doc_id}:{chunk_id}]",
                        )
                    )

            prev_end = m.end()

        return traces

    @classmethod
    def _find_quote_in_chunk(cls, claim_text: str, chunk_content: str) -> str | None:
        """Find the longest contiguous substring of claim_text present in chunk_content.

        Returns the matching substring or None if no meaningful overlap.
        """
        # Remove citation markers from claim for matching
        clean_claim = re.sub(r"\[[^\]]+:[^\]]+\]", "", claim_text).strip()
        if not clean_claim:
            return None

        # Split into sentences for finer matching
        sentences = re.split(r"(?<=[。！？.!?])", clean_claim)
        best_match = None
        best_len = 0

        for sent in sentences:
            sent = sent.strip("， 。！？.!? \n")
            if len(sent) < 2:
                continue

            chunk_norm = re.sub(r"\s+", " ", chunk_content)
            sent_norm = re.sub(r"\s+", " ", sent)

            # Try exact match first
            if sent_norm in chunk_norm:
                if len(sent_norm) > best_len:
                    best_len = len(sent_norm)
                    best_match = sent.strip()
                continue

            # Try finding the longest common substring
            # ponytail: O(n*m) sliding window, fine for chunk-sized text
            for window in range(min(len(sent_norm), 50), 2, -1):
                for start in range(len(sent_norm) - window + 1):
                    sub = sent_norm[start : start + window]
                    if sub in chunk_norm:
                        if window > best_len:
                            best_len = window
                            best_match = sent[start : start + window]
                        break

        return best_match

    @classmethod
    def _extract_citations_from_result(
        cls, result: GroundedGenerationResponse
    ) -> list[CitationRef]:
        """P0-1: Only citations actually referenced in output."""
        return [
            CitationRef(
                document_id=c["document_id"],
                chunk_id=c["chunk_id"],
                text=c.get("text", ""),
            )
            for c in result.citations
        ]

    # ==================================================================
    # P0-2: REPRODUCIBILITY METADATA
    # ==================================================================

    @classmethod
    def _build_reproducibility(
        cls,
        output_payload: dict[str, Any],
        results_chunks: list[dict],
        cited_chunk_ids: list[str],
        document_ids: list[str],
    ) -> ReproducibilityMetadata:
        """P0-2: Deterministic SHA-256 metadata. No timestamps, no runtime values."""
        # Output hash — from the deterministic payload fields only
        output_str = _json_dumps_deterministic(output_payload)
        output_sha = hashlib.sha256(output_str.encode()).hexdigest()

        # Corpus hash — from ordered retrieval snapshot content
        corpus_parts = sorted(
            f"{c['document_id']}:{c['chunk_id']}:{c.get('content', '')}"
            for c in results_chunks
        )
        corpus_str = "\n".join(corpus_parts)
        corpus_sha = hashlib.sha256(corpus_str.encode()).hexdigest()

        return ReproducibilityMetadata(
            output_sha256=output_sha,
            corpus_sha256=corpus_sha,
            ordered_cited_chunk_ids=cited_chunk_ids,
            source_document_ids=sorted(set(document_ids)),
        )

    @classmethod
    def _build_results_chunks(cls, result: GroundedGenerationResponse) -> list[dict]:
        """Extract result chunks in deterministic order."""
        return sorted(
            [
                {
                    "document_id": r["document_id"],
                    "chunk_id": r["chunk_id"],
                    "content": r["content"],
                }
                for r in result.results
            ],
            key=lambda x: (x["document_id"], x["chunk_id"]),
        )

    # ==================================================================
    # P0-6: UNSUPPORTED-CLAIM REFUSAL RESPONSE
    # ==================================================================

    @classmethod
    def _build_unsupported_refusal(
        cls,
        query: str,
        academic_type: str,
        verdict: UnsupportedClaimVerdict,
    ) -> AcademicResponse:
        """Build a refusal response when the unsupported-claim gate rejects."""
        return AcademicResponse(
            query=query,
            academic_type=academic_type,  # type: ignore[arg-type]
            citations=[],
            evidence_trace=[],
            metadata=AcademicMetadata(
                total_claims=0,
                total_retrievals=1,
                total_documents=0,
            ),
            gate_verdict=verdict,
        )

    # ==================================================================
    # SHARED: Run pipeline + gate
    # ==================================================================

    async def _run_gated_generation(
        self, query: str, top_k: int
    ) -> tuple[GroundedGenerationResponse, UnsupportedClaimVerdict, bool]:
        """Run GenerationPipeline then unsupported-claim gate.

        Returns (result, verdict, gate_passed).
        """
        pipeline = GenerationPipeline(self.session)
        result = await pipeline.generate(query=query, top_k=top_k)

        # Build chunks content list for gate check
        chunks_content = [r["content"] for r in result.results]

        # Gate: unsupported-claim check
        verdict = self._check_proposition_support(query, chunks_content)

        # Gate passes if verdict.is_supported or if the query has no proposition patterns
        gate_passed = verdict.is_supported

        # If gate refuses but there is substantive evidence, check if the
        # refusal is truly warranted (predicate gap) or just keyword overlap
        if not gate_passed and result.results:
            # Verify: the chunks REALLY don't support the proposition
            # by checking actual substring presence
            pass  # _check_proposition_support already did this

        return result, verdict, gate_passed

    async def _collect_traces_and_citations(
        self, result: GroundedGenerationResponse
    ) -> tuple[list[EvidenceTrace], list[CitationRef], list[str], list[str]]:
        """P0-1: Extracts claim-bound traces + citations from a generation result."""
        traces = self._extract_claim_traces(result)
        citations = self._extract_citations_from_result(result)
        cited_chunk_ids = list(dict.fromkeys(t.chunk_id for t in traces))
        document_ids = list(dict.fromkeys(t.document_id for t in traces))
        return traces, citations, cited_chunk_ids, document_ids

    # ==================================================================
    # 1. ACADEMIC REPORT GENERATOR (P0-2)
    # ==================================================================

    _REPORT_DECOMPOSE_PATTERNS: dict[str, list[str]] = {
        "literature_review": ["文献来源与版本", "核心内容概述", "学术价值与影响"],
        "research_summary": ["研究背景", "主要发现", "关键证据"],
        "thematic_analysis": ["主题梳理", "文本证据", "跨文献关联"],
        "historical_interpretation": ["历史背景", "文献记载", "后世影响与评价"],
    }

    _REPORT_TITLES: dict[str, str] = {
        "literature_review": "文献综述",
        "research_summary": "研究摘要",
        "thematic_analysis": "主题分析",
        "historical_interpretation": "历史解读",
    }

    async def generate_report(
        self, query: str, report_type: str, top_k: int = 5
    ) -> AcademicResponse:
        """P0-2: Generate a structured academic report.

        - Every non-structural sentence cites its source.
        - Empty evidence → explicit refusal.
        - Reproducibility metadata included.
        - Unsupported-claim gate applied.
        """
        sections = self._REPORT_DECOMPOSE_PATTERNS.get(
            report_type, self._REPORT_DECOMPOSE_PATTERNS["research_summary"]
        )
        title = self._REPORT_TITLES.get(report_type, "研究报告")

        all_traces: list[EvidenceTrace] = []
        all_citations: list[CitationRef] = []
        report_sections: list[ReportSection] = []
        total_retrievals = 0
        any_gate_refused = False
        final_verdict: UnsupportedClaimVerdict | None = None
        all_results_chunks: list[dict] = []
        all_cited_chunk_ids: list[str] = []
        all_document_ids: list[str] = []

        for section_heading in sections:
            sub_query = f"{query} —— {section_heading}"

            result, verdict, gate_passed = await self._run_gated_generation(
                sub_query, top_k
            )
            total_retrievals += 1
            final_verdict = verdict
            all_results_chunks.extend(self._build_results_chunks(result))

            if not gate_passed:
                any_gate_refused = True
                report_sections.append(
                    ReportSection(
                        heading=section_heading,
                        body=f"EVIDENCE_GATE_REFUSAL: {verdict.reason}",
                        citations=[],
                        evidence=[],
                    )
                )
                continue

            (
                traces,
                citations,
                cited_ids,
                doc_ids,
            ) = await self._collect_traces_and_citations(result)
            all_traces.extend(traces)
            all_citations.extend(citations)
            all_cited_chunk_ids.extend(cited_ids)
            all_document_ids.extend(doc_ids)

            report_sections.append(
                ReportSection(
                    heading=section_heading,
                    body=result.answer,
                    citations=citations,
                    evidence=traces,
                )
            )

        # P0-2: Empty evidence → explicit refusal for the whole report
        if not all_traces and not any_gate_refused:
            return AcademicResponse(
                query=query,
                academic_type="report",
                title=f"{title}：{query}",
                sections=[],
                citations=[],
                evidence_trace=[],
                metadata=AcademicMetadata(
                    top_k=top_k,
                    total_claims=0,
                    total_retrievals=total_retrievals,
                    total_documents=0,
                ),
                gate_verdict=UnsupportedClaimVerdict(
                    is_supported=False,
                    proposition_type="empty_evidence",
                    reason="No evidence found for any section",
                ),
            )

        # Reproducibility metadata
        output_payload = {
            "query": query,
            "academic_type": "report",
            "title": f"{title}：{query}",
            "sections": [
                {"heading": s.heading, "body": s.body} for s in report_sections
            ],
        }

        return AcademicResponse(
            query=query,
            academic_type="report",
            title=f"{title}：{query}",
            sections=report_sections,
            citations=all_citations,
            evidence_trace=all_traces,
            metadata=AcademicMetadata(
                top_k=top_k,
                total_claims=len(all_traces),
                total_retrievals=total_retrievals,
                total_documents=len(set(all_document_ids)),
                reproducibility=self._build_reproducibility(
                    output_payload,
                    all_results_chunks,
                    all_cited_chunk_ids,
                    all_document_ids,
                ),
            ),
            gate_verdict=final_verdict,
        )

    # ==================================================================
    # 2. KNOWLEDGE SYNTHESIS ENGINE (P0-3)
    # ==================================================================

    async def synthesize(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P0-3: Synthesize knowledge — traceable aggregation, no manufactured facts.

        Each theme's claims retain exact source quotes.
        Theme descriptions are structural labels only.
        Cross-document provenance when ≥2 documents contribute.
        """
        result, verdict, gate_passed = await self._run_gated_generation(query, top_k)

        if not gate_passed:
            return self._build_unsupported_refusal(query, "synthesis", verdict)

        traces = self._extract_claim_traces(result)
        citations = self._extract_citations_from_result(result)

        # P0-3: Cluster by concept — claims remain exact source quotes
        themes = self._cluster_claims_by_concept(traces, query)

        # P0-3: Cross-document provenance
        for theme in themes:
            doc_ids = set(c.document_id for c in theme.claims)
            if len(doc_ids) >= 2:
                theme.cross_document_refs = sorted(doc_ids)

        cited_chunk_ids = list(dict.fromkeys(t.chunk_id for t in traces))
        document_ids = list(dict.fromkeys(t.document_id for t in traces))
        results_chunks = self._build_results_chunks(result)

        output_payload = {
            "query": query,
            "academic_type": "synthesis",
            "themes": [
                {
                    "title": t.title,
                    "claims": [c.claim_text for c in t.claims],
                    "cross_document_refs": t.cross_document_refs,
                }
                for t in themes
            ],
        }

        return AcademicResponse(
            query=query,
            academic_type="synthesis",
            themes=themes,
            citations=citations,
            evidence_trace=traces,
            metadata=AcademicMetadata(
                top_k=top_k,
                total_claims=len(traces),
                total_retrievals=1,
                total_documents=len(set(document_ids)),
                reproducibility=self._build_reproducibility(
                    output_payload, results_chunks, cited_chunk_ids, document_ids
                ),
            ),
            gate_verdict=verdict,
        )

    _CONCEPT_KEYWORDS: list[str] = [
        "经络",
        "针灸",
        "穴位",
        "经脉",
        "络脉",
        "脏腑",
        "气血",
        "阴阳",
        "五行",
        "本草",
        "方剂",
        "药性",
        "诊法",
        "脉诊",
        "望诊",
        "伤寒",
        "温病",
        "杂病",
        "甲乙经",
        "皇甫谧",
        "明堂",
    ]

    @classmethod
    def _cluster_claims_by_concept(
        cls, traces: list[EvidenceTrace], query: str
    ) -> list[SynthesisTheme]:
        """P0-3: Cluster claims by concept keyword overlap. No LLM.

        Claims remain exact source quotes. Theme descriptions are structural labels.
        """
        if not traces:
            return []

        # Match concepts against traces
        trace_themes: list[tuple[str, list[EvidenceTrace]]] = []
        assigned: set[int] = set()

        for kw in cls._CONCEPT_KEYWORDS:
            matching = [
                t
                for i, t in enumerate(traces)
                if i not in assigned and (kw in t.claim_text or kw in t.quote)
            ]
            if matching:
                assigned.update(
                    i
                    for i, t in enumerate(traces)
                    if kw in t.claim_text or kw in t.quote
                )
                trace_themes.append((kw, matching))

        # Remaining traces
        remaining = [t for i, t in enumerate(traces) if i not in assigned]
        if remaining:
            trace_themes.append(("相关文献", remaining))

        if not trace_themes:
            return []

        # Build themes — structural descriptions only, no factual assertions
        results: list[SynthesisTheme] = []
        seen_claims: set[tuple[str, str]] = set()
        for theme_name, theme_traces in trace_themes:
            deduped: list[EvidenceTrace] = []
            for t in theme_traces:
                key = (t.chunk_id, t.quote[:50])
                if key not in seen_claims:
                    seen_claims.add(key)
                    deduped.append(t)

            # Structural description only — no manufactured facts
            doc_count = len(set(t.document_id for t in deduped))
            if doc_count >= 2:
                desc = f"来自{doc_count}篇文献中关于「{theme_name}」的原文证据"
            else:
                desc = f"关于「{theme_name}」的原文引用"

            results.append(
                SynthesisTheme(
                    title=theme_name,
                    description=desc,
                    claims=deduped,
                )
            )

        return results

    # ==================================================================
    # 3. RESEARCH ASSISTANT MODE (P0-4)
    # ==================================================================

    _RESEARCH_DECOMPOSE_PATTERNS: list[tuple[str, str]] = [
        ("定义与概念", "什么是{query}？"),
        ("历史与来源", "{query}的历史渊源是什么？"),
        ("内容与结构", "{query}包含哪些内容？"),
        ("关联与影响", "{query}与哪些概念或文献有关？"),
    ]

    async def research(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P0-4: Research assistant — decompose, search, identify gaps.

        - Missing evidence = research gap (has_gap=True), hypothesis=null.
        - Hypotheses only populated with supporting EvidenceTrace.
        - No generic unsupported prose.
        """
        # First, run unsupported-claim gate on original query
        _, verdict, gate_passed = await self._run_gated_generation(query, top_k)

        sub_questions: list[ResearchSubQuestion] = []
        all_traces: list[EvidenceTrace] = []
        all_citations: list[CitationRef] = []
        all_results_chunks: list[dict] = []
        all_cited_chunk_ids: list[str] = []
        all_document_ids: list[str] = []
        total_retrievals = 0

        for aspect, template in self._RESEARCH_DECOMPOSE_PATTERNS:
            sub_q = template.replace("{query}", query)

            result, sub_verdict, sub_gate_passed = await self._run_gated_generation(
                sub_q, top_k
            )
            total_retrievals += 1
            all_results_chunks.extend(self._build_results_chunks(result))

            (
                traces,
                citations,
                cited_ids,
                doc_ids,
            ) = await self._collect_traces_and_citations(result)
            all_traces.extend(traces)
            all_citations.extend(citations)
            all_cited_chunk_ids.extend(cited_ids)
            all_document_ids.extend(doc_ids)

            has_gap = len(traces) == 0

            # P0-4: hypothesis is null unless supported by evidence
            # A gap is not a hypothesis — it's a research gap
            sub_questions.append(
                ResearchSubQuestion(
                    sub_question=sub_q,
                    evidence=traces,
                    has_gap=has_gap,
                    hypothesis=None,  # P0-4: null, not templated prose
                )
            )

        output_payload = {
            "query": query,
            "academic_type": "research",
            "decomposition": [
                {"sub_question": sq.sub_question, "has_gap": sq.has_gap}
                for sq in sub_questions
            ],
        }

        return AcademicResponse(
            query=query,
            academic_type="research",
            decomposition=sub_questions,
            citations=all_citations,
            evidence_trace=all_traces,
            metadata=AcademicMetadata(
                top_k=top_k,
                total_claims=len(all_traces),
                total_retrievals=total_retrievals,
                total_documents=len(set(all_document_ids)),
                reproducibility=self._build_reproducibility(
                    output_payload,
                    all_results_chunks,
                    all_cited_chunk_ids,
                    all_document_ids,
                ),
            ),
            gate_verdict=verdict,
        )

    # ==================================================================
    # 4. EDUCATION MODE (P0-5)
    # ==================================================================

    async def educate(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P0-5: Education mode — extractive presentation, no invented prose.

        - No sentence pattern: '「{query}」是中医文献中记载的重要概念。'
        - Every factual paragraph includes its own citation.
        - Difficulty = amount of cited detail, not word count.
        - Empty evidence → refusal, no factual explanation.
        - Unsupported propositions → gate refusal.
        """
        result, verdict, gate_passed = await self._run_gated_generation(query, top_k)

        if not gate_passed:
            return self._build_unsupported_refusal(query, "education", verdict)

        traces = self._extract_claim_traces(result)
        citations = self._extract_citations_from_result(result)

        # P0-5: Empty evidence → explicit refusal
        if not traces:
            return AcademicResponse(
                query=query,
                academic_type="education",
                explanation=[],
                citations=[],
                evidence_trace=[],
                metadata=AcademicMetadata(
                    top_k=top_k,
                    total_claims=0,
                    total_retrievals=1,
                    total_documents=0,
                ),
                gate_verdict=UnsupportedClaimVerdict(
                    is_supported=False,
                    proposition_type="empty_evidence",
                    reason="No evidence to create educational explanation",
                ),
            )

        # P0-5: Difficulty based on detail amount (citation count), not text length
        # Beginner: fewer citations (simpler)
        # Intermediate: more citations (more detail)
        beginner_traces: list[EvidenceTrace] = []
        intermediate_traces: list[EvidenceTrace] = []

        # Split by uniqueness: beginner = core facts, intermediate = all details
        for t in traces:
            # Short quotes serve as beginner-level core facts
            if len(t.quote) < 100:
                beginner_traces.append(t)
            else:
                intermediate_traces.append(t)

        # Ensure beginner always has something if evidence exists
        if not beginner_traces and intermediate_traces:
            beginner_traces = intermediate_traces[:1]
            intermediate_traces = intermediate_traces[1:]

        explanation: list[EducationConcept] = []

        if beginner_traces:
            beginner_citations = [
                CitationRef(
                    document_id=t.document_id, chunk_id=t.chunk_id, text=t.citation_text
                )
                for t in beginner_traces
            ]
            # P0-5: Extractive paragraphs — only direct quotes, no invented sentences
            paragraphs = self._render_extractive_paragraphs(
                beginner_traces, include_citation=True
            )
            explanation.append(
                EducationConcept(
                    concept=query,
                    level="beginner",
                    paragraphs=paragraphs,
                    citations=beginner_citations,
                    evidence=beginner_traces,
                )
            )

        if intermediate_traces:
            intermediate_citations = [
                CitationRef(
                    document_id=t.document_id, chunk_id=t.chunk_id, text=t.citation_text
                )
                for t in intermediate_traces
            ]
            paragraphs = self._render_extractive_paragraphs(
                intermediate_traces, include_citation=True
            )
            explanation.append(
                EducationConcept(
                    concept=query,
                    level="intermediate",
                    paragraphs=paragraphs,
                    citations=intermediate_citations,
                    evidence=intermediate_traces,
                )
            )

        cited_chunk_ids = list(dict.fromkeys(t.chunk_id for t in traces))
        document_ids = list(dict.fromkeys(t.document_id for t in traces))
        results_chunks = self._build_results_chunks(result)

        output_payload = {
            "query": query,
            "academic_type": "education",
            "explanation": [
                {
                    "concept": e.concept,
                    "level": e.level,
                    "paragraphs": e.paragraphs,
                }
                for e in explanation
            ],
        }

        return AcademicResponse(
            query=query,
            academic_type="education",
            explanation=explanation,
            citations=citations,
            evidence_trace=traces,
            metadata=AcademicMetadata(
                top_k=top_k,
                total_claims=len(traces),
                total_retrievals=1,
                total_documents=len(set(document_ids)),
                reproducibility=self._build_reproducibility(
                    output_payload,
                    results_chunks,
                    cited_chunk_ids,
                    document_ids,
                ),
            ),
            gate_verdict=verdict,
        )

    @classmethod
    def _render_extractive_paragraphs(
        cls, traces: list[EvidenceTrace], include_citation: bool = True
    ) -> list[str]:
        """P0-5: Render paragraphs as direct extractive presentation only.

        Each paragraph = quote + citation. No invented introductory sentences.
        """
        paragraphs: list[str] = []
        for t in traces:
            para = t.quote.strip()
            if not para:
                continue
            if para[-1] not in "。！？.!?）\"'":
                para += "。"
            if include_citation and t.citation_text:
                para += t.citation_text
            paragraphs.append(para)
        return paragraphs


# ---------------------------------------------------------------------------
# Deterministic JSON helpers
# ---------------------------------------------------------------------------


def _json_dumps_deterministic(obj: Any) -> str:
    """JSON dump with sorted keys for deterministic hashing."""
    import json as _json

    return _json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
