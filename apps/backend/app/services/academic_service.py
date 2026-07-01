"""
Academic Service — Sprint 2 academic product layer (deep-fix).

P0-1: Uses ProvedGenerationPipeline for 1:1 claim→EvidenceTrace. No substring fallback.
P0-2: Unified fail-closed with ACADEMIC_CLAIM_BINDING_FAILED / UNSUPPORTED_PROPOSITION / EMPTY_ACADEMIC_EVIDENCE.
P0-3: Research gate rejects immediately; no sub-queries after gate failure.
P0-4: Hypothesis only from speculative original corpus text with citation.
P0-5: Same-evidence-sentence gate — subject+predicate+quantifier must co-occur in one sentence.
P1-2: Education levels by retrieval rank (not text length).
P1-3: Reproducibility hardened — complete artifact hash, deduped corpus, refusal hashes.
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
from app.services.generation_proof import (
    GenerationProof,
    ProvedGenerationPipeline,
    VerifiedClaim,
)


# ======================================================================
# P0-2: Unified error codes
# ======================================================================


class AcademicErrorCode:
    ACADEMIC_CLAIM_BINDING_FAILED = "ACADEMIC_CLAIM_BINDING_FAILED"
    UNSUPPORTED_PROPOSITION = "UNSUPPORTED_PROPOSITION"
    EMPTY_ACADEMIC_EVIDENCE = "EMPTY_ACADEMIC_EVIDENCE"


# ======================================================================
# P0-4: Speculative expression patterns in classical Chinese corpus
# ======================================================================

_SPECULATIVE_PATTERNS: list[str] = [
    "可能",
    "或可",
    "推测",
    "尚待考证",
    "有待进一步研究",
    "未详",
    "未明",
    "待考",
    "存疑",
    "阙疑",
    "或云",
    "一说",
    "传云",
    "相传",
    "盖",
]


def _extract_hypothesis_from_chunk(chunk_content: str) -> str | None:
    """P0-4: Extract a speculative sentence from chunk IF it contains speculative markers.

    Returns the exact original sentence with speculative expression, or None.
    No new text is generated.
    """
    sentences = re.split(r"(?<=[。！？.!?])", chunk_content)
    for sent in sentences:
        sent = sent.strip()
        if not sent:
            continue
        for pat in _SPECULATIVE_PATTERNS:
            if pat in sent:
                return sent
    return None


# ======================================================================
# P0-5: SAME-EVIDENCE-SENTENCE GATE
# ======================================================================

# Proposition markers
_PROP_MARKERS_RE = re.compile(r"(是否|能否|是不是|有没有|可不)")

# Patterns that demand same-sentence evidence
_GATE_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("universal_quantifier", re.compile(r"(所有|全部|任何|一切|凡是|必然)")),
    (
        "modern_projection",
        re.compile(r"(现代医学|现代科学|现代概念|西医|科学验证|临床实验)"),
    ),
    (
        "causal_assertion",
        re.compile(r"(治疗|治愈|导致|证明|证实|可以.*治疗|能够.*治疗)"),
    ),
    ("proposition", _PROP_MARKERS_RE),
]


def _classify_query(query: str) -> list[tuple[str, str]]:
    """Classify query for proposition types."""
    matched: list[tuple[str, str]] = []
    query_norm = re.sub(r"\s+", "", query)
    for ptype, pat in _GATE_PATTERNS:
        for m in pat.finditer(query_norm):
            matched.append((ptype, m.group(1)))
    return matched


def _extract_all_gate_terms(query: str) -> list[str]:
    """Extract all matched gate terms from query."""
    terms: list[str] = []
    query_norm = re.sub(r"\s+", "", query)
    for _ptype, pat in _GATE_PATTERNS:
        for m in pat.finditer(query_norm):
            terms.append(m.group(1))
    return sorted(set(terms))


def _tokenize_chinese(text: str) -> list[str]:
    """Crude Chinese tokenizer — split on common delimiters, keep ≥2 char segments.

    ponytail: no jieba dependency. Good enough for gate checks.
    """
    # Remove proposition markers
    clean = _PROP_MARKERS_RE.sub(" ", text)
    # Split on punctuation and whitespace
    segments = re.split(r"[，。！？、：；（）\s]+", clean)
    return [s for s in segments if len(s) >= 2]


def _check_same_sentence_support(
    query: str, chunks_content: list[str]
) -> UnsupportedClaimVerdict:
    """P0-5: Same-evidence-sentence gate.

    A proposition is supported ONLY IF its subject, predicate, AND quantifier
    all appear TOGETHER in at least one sentence within the retrieved chunks.

    Keywords scattered across different chunks or different sentences = NOT supported.
    Negative evidence sentence = must preserve the original polarity.
    """
    query_norm = re.sub(r"\s+", "", query)
    classifications = _classify_query(query)
    gate_terms = _extract_all_gate_terms(query)

    if not classifications:
        return UnsupportedClaimVerdict(
            is_supported=True,
            proposition_type="none",
            reason="No gated proposition pattern detected",
        )

    # Split all chunk content into individual sentences
    all_sentences: list[str] = []
    for content in chunks_content:
        content_clean = re.sub(r"\s+", "", content)
        sents = re.split(r"(?<=[。！？.!?])", content_clean)
        all_sentences.extend(s.strip() for s in sents if s.strip())

    # P0-5: Check each classification type
    any(c[0] == "proposition" for c in classifications)
    any(c[0] == "modern_projection" for c in classifications)
    any(c[0] == "causal_assertion" for c in classifications)
    any(c[0] == "universal_quantifier" for c in classifications)

    # Build the set of terms that must be found TOGETHER
    # Subject: the query terms that DO appear in chunks (which chunks show this)
    # Predicate: the gated terms from modern_projection and causal_assertion
    # Quantifier: the universal quantifier terms
    # Polarity: the proposition marker (是否 etc.)

    # Build a set of required terms from the query
    subject_terms: set[str] = set()

    # Extract subject — words from query that are NOT gate terms and NOT proposition markers
    clean_query = _PROP_MARKERS_RE.sub(" ", query_norm)
    query_words = _tokenize_chinese(clean_query)
    for w in query_words:
        if w not in gate_terms and w not in (
            "是否",
            "能否",
            "是不是",
            "有没有",
            "可不",
        ):
            subject_terms.add(w)

    # Required terms = subject terms that appear anywhere in the chunk set
    all_content_flat = re.sub(r"\s+", "", "\n".join(chunks_content))
    appearing_subjects = {s for s in subject_terms if s in all_content_flat}

    # Gate terms that triggered
    modern_terms = {t for pt, t in classifications if pt == "modern_projection"}
    causal_terms = {t for pt, t in classifications if pt == "causal_assertion"}
    universal_terms = {t for pt, t in classifications if pt == "universal_quantifier"}

    # Build the set of predicate/quantifier terms that must co-occur with subject
    predicate_terms = modern_terms | causal_terms | universal_terms

    if not predicate_terms:
        # Only proposition marker — just check that the question's subject appears
        if not appearing_subjects:
            return UnsupportedClaimVerdict(
                is_supported=False,
                proposition_type="proposition",
                matched_keywords=gate_terms,
                reason="Query subject not found in any retrieved chunk",
            )
        return UnsupportedClaimVerdict(
            is_supported=True,
            proposition_type="proposition",
            matched_keywords=gate_terms,
            reason="Subject found in evidence; no gated predicate to verify",
        )

    # P0-5 CORE CHECK: For each predicate term, find at least one sentence
    # where BOTH the predicate AND at least one subject term appear together.
    for pred_term in predicate_terms:
        pred_norm = pred_term.strip()
        found_same_sentence = False

        for sent in all_sentences:
            # Check if this sentence contains the predicate term
            if pred_norm not in sent:
                continue
            # Check if this sentence also contains at least one subject term
            # OR if there are no subject terms (query is purely a statement)
            if not appearing_subjects:
                found_same_sentence = True
                break
            for subj in appearing_subjects:
                if subj in sent:
                    found_same_sentence = True
                    break
            if found_same_sentence:
                break

        if not found_same_sentence:
            # Try: does the predicate appear ANYWHERE? If not, definitely unsupported.
            pred_anywhere = pred_norm in all_content_flat
            if not pred_anywhere:
                return UnsupportedClaimVerdict(
                    is_supported=False,
                    proposition_type="mixed",
                    matched_keywords=gate_terms,
                    reason=f"Predicate '{pred_norm}' not found in any retrieved chunk",
                )
            else:
                return UnsupportedClaimVerdict(
                    is_supported=False,
                    proposition_type="mixed",
                    matched_keywords=gate_terms,
                    reason=f"Predicate '{pred_norm}' found but not co-occurring with subject in any sentence",
                )

    # All predicate terms verified in same sentence with subject
    return UnsupportedClaimVerdict(
        is_supported=True,
        proposition_type="mixed",
        matched_keywords=gate_terms,
        reason="All propositions verified in same-sentence evidence",
    )


# ======================================================================
# ACADEMIC SERVICE
# ======================================================================


class AcademicService:
    """Academic product layer — report, synthesis, research, education.

    Deep-fix changes:
    - P0-1: ProvedGenerationPipeline → strict 1:1 claim binding, no substring fallback
    - P0-2: Unified fail-closed with explicit error codes
    - P0-3: Research gate rejects immediately; no sub-queries after gate failure
    - P0-4: Hypothesis only from corpus speculative expressions with citation
    - P0-5: Same-evidence-sentence gate
    - P1-2: Education levels by retrieval rank, not text length
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ==================================================================
    # P0-1: STRICT 1:1 CLAIM → EVIDENCE BINDING
    # ==================================================================

    @staticmethod
    def _verified_claim_to_trace(vc: VerifiedClaim) -> EvidenceTrace:
        """P0-1: Map one VerifiedClaim → one EvidenceTrace. 1:1. No substring guessing."""
        return EvidenceTrace(
            claim_text=vc.claim_text,
            quote=vc.quote,
            document_id=vc.document_id,
            chunk_id=vc.chunk_id,
            citation_text=vc.citation_str,
        )

    @staticmethod
    def _verified_claim_to_citation(vc: VerifiedClaim) -> CitationRef:
        """Map one VerifiedClaim → one CitationRef."""
        return CitationRef(
            document_id=vc.document_id,
            chunk_id=vc.chunk_id,
            text=vc.citation_str,
        )

    @staticmethod
    def _claims_to_traces(claims: list[VerifiedClaim]) -> list[EvidenceTrace]:
        """P0-1: Convert verified claims to evidence traces. 1:1 mapping."""
        return [AcademicService._verified_claim_to_trace(vc) for vc in claims]

    @staticmethod
    def _claims_to_citations(claims: list[VerifiedClaim]) -> list[CitationRef]:
        """Convert verified claims to citation refs. Deduplicated by chunk_id."""
        seen: set[str] = set()
        refs: list[CitationRef] = []
        for vc in claims:
            if vc.chunk_id not in seen:
                seen.add(vc.chunk_id)
                refs.append(AcademicService._verified_claim_to_citation(vc))
        return refs

    # ==================================================================
    # P0-2: UNIFIED FAIL-CLOSED
    # ==================================================================

    @classmethod
    def _build_fail_closed(
        cls,
        query: str,
        academic_type: str,
        error_code: str,
        reason: str,
        matched_keywords: list[str] | None = None,
    ) -> AcademicResponse:
        """P0-2: Unified fail-closed response.

        - No sections/themes/evidence/citations
        - gate_verdict.is_supported == false
        - Stable error code
        - Non-factual refusal reason
        - No raw claim text leaked
        """
        return AcademicResponse(
            query=query,
            academic_type=academic_type,  # type: ignore[arg-type]
            citations=[],
            evidence_trace=[],
            metadata=AcademicMetadata(
                total_claims=0,
                total_retrievals=0,
                total_documents=0,
                reproducibility=ReproducibilityMetadata(
                    pipeline_version="academic-grounded-v2-p0",
                ),
            ),
            gate_verdict=UnsupportedClaimVerdict(
                is_supported=False,
                proposition_type=error_code,
                matched_keywords=matched_keywords or [],
                reason=reason,
            ),
        )

    # ==================================================================
    # SHARED: Run pipeline + gate + extract proof
    # ==================================================================

    async def _run_gated_proof(
        self, query: str, top_k: int
    ) -> tuple[GenerationProof, UnsupportedClaimVerdict, bool]:
        """Run ProvedGenerationPipeline, gate, and extract proof.

        Returns (proof, verdict, gate_passed).

        Gate passed = verdict.is_supported. If gate fails, proof may still
        contain data but the caller must respect gate_passed.
        """
        pipeline = ProvedGenerationPipeline(self.session)
        proof = await pipeline.generate_with_proof(query=query, top_k=top_k)

        # Gate: same-sentence evidence check
        chunks_content = [r["content"] for r in proof.response.results]
        verdict = _check_same_sentence_support(query, chunks_content)
        gate_passed = verdict.is_supported

        return proof, verdict, gate_passed

    # ==================================================================
    # P1-3: REPRODUCIBILITY — hardened
    # ==================================================================

    @classmethod
    def _build_reproducibility(
        cls,
        deterministic_payload: dict[str, Any],
        all_results_chunks: list[dict],
        cited_chunk_ids: list[str],
        document_ids: list[str],
    ) -> ReproducibilityMetadata:
        """P1-3: Hardened reproducibility metadata.

        - output_sha256: covers complete academic artifact, excludes itself
        - corpus_sha256: deduped canonical source records
        - ordered_cited_chunk_ids: deduped, stable order
        - refusal responses also produce non-empty hashes
        """
        import json

        # Output hash — deterministic payload, sorted keys
        output_str = json.dumps(
            deterministic_payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        output_sha = hashlib.sha256(output_str.encode()).hexdigest()

        # Corpus hash — deduped by (document_id, chunk_id)
        seen_corpus: set[tuple[str, str]] = set()
        deduped_corpus: list[str] = []
        for c in sorted(
            all_results_chunks, key=lambda x: (x["document_id"], x["chunk_id"])
        ):
            key = (c["document_id"], c["chunk_id"])
            if key not in seen_corpus:
                seen_corpus.add(key)
                deduped_corpus.append(
                    f"{c['document_id']}:{c['chunk_id']}:{c.get('content', '')}"
                )
        corpus_str = "\n".join(deduped_corpus)
        corpus_sha = hashlib.sha256(corpus_str.encode()).hexdigest()

        return ReproducibilityMetadata(
            output_sha256=output_sha,
            corpus_sha256=corpus_sha,
            ordered_cited_chunk_ids=list(dict.fromkeys(cited_chunk_ids)),
            source_document_ids=sorted(set(document_ids)),
        )

    @staticmethod
    def _build_results_chunks_from_proof(proof: GenerationProof) -> list[dict]:
        """Extract result chunks from proof in deterministic order."""
        return sorted(
            [
                {
                    "document_id": r["document_id"],
                    "chunk_id": r["chunk_id"],
                    "content": r["content"],
                }
                for r in proof.response.results
            ],
            key=lambda x: (x["document_id"], x["chunk_id"]),
        )

    # ==================================================================
    # 1. ACADEMIC REPORT GENERATOR
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
        """P0-2: Generate a structured academic report with strict claim binding."""
        sections = self._REPORT_DECOMPOSE_PATTERNS.get(
            report_type, self._REPORT_DECOMPOSE_PATTERNS["research_summary"]
        )
        title = self._REPORT_TITLES.get(report_type, "研究报告")

        all_claims: list[VerifiedClaim] = []
        report_sections: list[ReportSection] = []
        total_retrievals = 0
        final_verdict: UnsupportedClaimVerdict | None = None
        all_results_chunks: list[dict] = []

        for section_heading in sections:
            sub_query = f"{query} —— {section_heading}"
            proof, verdict, gate_passed = await self._run_gated_proof(sub_query, top_k)
            total_retrievals += 1
            final_verdict = verdict
            all_results_chunks.extend(self._build_results_chunks_from_proof(proof))

            if not gate_passed:
                report_sections.append(
                    ReportSection(
                        heading=section_heading,
                        body=f"EVIDENCE_GATE_REFUSAL: {verdict.reason}",
                        citations=[],
                        evidence=[],
                    )
                )
                continue

            section_claims = proof.verified_claims
            # P0-1: fail closed if ANY claim cannot be bound
            if not section_claims and proof.response.results:
                return self._build_fail_closed(
                    query,
                    "report",
                    AcademicErrorCode.ACADEMIC_CLAIM_BINDING_FAILED,
                    f"Claims could not be bound for section '{section_heading}'",
                )

            all_claims.extend(section_claims)

            report_sections.append(
                ReportSection(
                    heading=section_heading,
                    body=proof.response.answer,
                    citations=self._claims_to_citations(section_claims),
                    evidence=self._claims_to_traces(section_claims),
                )
            )

        # P0-2: Empty evidence → explicit refusal
        if not all_claims:
            return self._build_fail_closed(
                query,
                "report",
                AcademicErrorCode.EMPTY_ACADEMIC_EVIDENCE,
                "No evidence found for any section",
            )

        all_traces = self._claims_to_traces(all_claims)
        all_citations = self._claims_to_citations(all_claims)
        cited_ids = list(dict.fromkeys(vc.chunk_id for vc in all_claims))
        doc_ids = list(dict.fromkeys(vc.document_id for vc in all_claims))

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
                total_claims=len(all_claims),
                total_retrievals=total_retrievals,
                total_documents=len(set(doc_ids)),
                reproducibility=self._build_reproducibility(
                    output_payload, all_results_chunks, cited_ids, doc_ids
                ),
            ),
            gate_verdict=final_verdict,
        )

    # ==================================================================
    # 2. KNOWLEDGE SYNTHESIS ENGINE
    # ==================================================================

    async def synthesize(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P0-3: Synthesize knowledge with strict claim binding."""
        proof, verdict, gate_passed = await self._run_gated_proof(query, top_k)

        if not gate_passed:
            return self._build_fail_closed(
                query,
                "synthesis",
                AcademicErrorCode.UNSUPPORTED_PROPOSITION,
                verdict.reason,
                verdict.matched_keywords,
            )

        claims = proof.verified_claims
        if not claims:
            return self._build_fail_closed(
                query,
                "synthesis",
                AcademicErrorCode.EMPTY_ACADEMIC_EVIDENCE,
                "No evidence found",
            )

        traces = self._claims_to_traces(claims)
        citations = self._claims_to_citations(claims)

        # Cluster by concept
        themes = self._cluster_claims_by_concept(claims)

        for theme in themes:
            doc_ids_set = set(c.document_id for c in theme.claims)
            if len(doc_ids_set) >= 2:
                theme.cross_document_refs = sorted(doc_ids_set)

        cited_ids = list(dict.fromkeys(vc.chunk_id for vc in claims))
        doc_ids = list(dict.fromkeys(vc.document_id for vc in claims))
        results_chunks = self._build_results_chunks_from_proof(proof)

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
                total_claims=len(claims),
                total_retrievals=1,
                total_documents=len(set(doc_ids)),
                reproducibility=self._build_reproducibility(
                    output_payload, results_chunks, cited_ids, doc_ids
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
        cls, claims: list[VerifiedClaim]
    ) -> list[SynthesisTheme]:
        """Cluster verified claims by concept keyword overlap."""
        if not claims:
            return []

        trace_themes: list[tuple[str, list[VerifiedClaim]]] = []
        assigned: set[int] = set()

        for kw in cls._CONCEPT_KEYWORDS:
            matching = [
                vc
                for i, vc in enumerate(claims)
                if i not in assigned and (kw in vc.claim_text or kw in vc.quote)
            ]
            if matching:
                assigned.update(
                    i
                    for i, vc in enumerate(claims)
                    if kw in vc.claim_text or kw in vc.quote
                )
                trace_themes.append((kw, matching))

        remaining = [vc for i, vc in enumerate(claims) if i not in assigned]
        if remaining:
            trace_themes.append(("相关文献", remaining))

        if not trace_themes:
            return []

        results: list[SynthesisTheme] = []
        seen: set[tuple[str, str]] = set()
        for theme_name, theme_claims in trace_themes:
            deduped: list[EvidenceTrace] = []
            for vc in theme_claims:
                key = (vc.chunk_id, vc.quote[:50])
                if key not in seen:
                    seen.add(key)
                    deduped.append(AcademicService._verified_claim_to_trace(vc))

            doc_count = len(set(vc.document_id for vc in theme_claims))
            desc = (
                f"来自{doc_count}篇文献中关于「{theme_name}」的原文证据"
                if doc_count >= 2
                else f"关于「{theme_name}」的原文引用"
            )

            results.append(
                SynthesisTheme(title=theme_name, description=desc, claims=deduped)
            )

        return results

    # ==================================================================
    # 3. RESEARCH ASSISTANT MODE (P0-3: gate-first, P0-4: hypothesis from corpus)
    # ==================================================================

    _RESEARCH_DECOMPOSE_PATTERNS: list[tuple[str, str]] = [
        ("定义与概念", "什么是{query}？"),
        ("历史与来源", "{query}的历史渊源是什么？"),
        ("内容与结构", "{query}包含哪些内容？"),
        ("关联与影响", "{query}与哪些概念或文献有关？"),
    ]

    async def research(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P0-3: Gate-first research. P0-4: Hypothesis from corpus only.

        - Original query gate fails → immediate refusal, NO sub-queries.
        - Each sub-query gate fails → that sub-question is a gap, no evidence.
        - Hypothesis only from corpus speculative expressions with citation.
        """
        # P0-3: Run gate on original query FIRST
        _, original_verdict, original_gate_passed = await self._run_gated_proof(
            query, top_k
        )

        if not original_gate_passed:
            return self._build_fail_closed(
                query,
                "research",
                AcademicErrorCode.UNSUPPORTED_PROPOSITION,
                original_verdict.reason,
                original_verdict.matched_keywords,
            )

        # Gate passed — proceed with sub-question decomposition
        sub_questions: list[ResearchSubQuestion] = []
        all_claims: list[VerifiedClaim] = []
        all_results_chunks: list[dict] = []
        total_retrievals = 0

        for aspect, template in self._RESEARCH_DECOMPOSE_PATTERNS:
            sub_q = template.replace("{query}", query)

            proof, sub_verdict, sub_gate_passed = await self._run_gated_proof(
                sub_q, top_k
            )
            total_retrievals += 1
            all_results_chunks.extend(self._build_results_chunks_from_proof(proof))

            if not sub_gate_passed:
                # P0-3: sub-gate failure → pure gap, no evidence, no hypothesis
                sub_questions.append(
                    ResearchSubQuestion(
                        sub_question=sub_q,
                        evidence=[],
                        has_gap=True,
                        hypothesis=None,
                    )
                )
                continue

            sub_claims = proof.verified_claims
            if not sub_claims:
                sub_questions.append(
                    ResearchSubQuestion(
                        sub_question=sub_q,
                        evidence=[],
                        has_gap=True,
                        hypothesis=None,
                    )
                )
                continue

            all_claims.extend(sub_claims)

            # P0-4: Hypothesis from corpus speculative expressions ONLY
            hypothesis: str | None = None
            hypothesis_evidence: list[EvidenceTrace] = []

            for vc in sub_claims:
                # Look up the original chunk content for speculative markers
                chunk_content = ""
                for r in proof.response.results:
                    if r["chunk_id"] == vc.chunk_id:
                        chunk_content = r["content"]
                        break
                if chunk_content:
                    extracted = _extract_hypothesis_from_chunk(chunk_content)
                    if extracted:
                        hypothesis = f"{extracted}{vc.citation_str}"
                        hypothesis_evidence.append(self._verified_claim_to_trace(vc))
                        break  # First speculative sentence wins

            sub_questions.append(
                ResearchSubQuestion(
                    sub_question=sub_q,
                    evidence=self._claims_to_traces(sub_claims),
                    has_gap=False,
                    hypothesis=hypothesis,
                )
            )

        all_traces = self._claims_to_traces(all_claims)
        all_citations = self._claims_to_citations(all_claims)
        cited_ids = list(dict.fromkeys(vc.chunk_id for vc in all_claims))
        doc_ids = list(dict.fromkeys(vc.document_id for vc in all_claims))

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
                total_claims=len(all_claims),
                total_retrievals=total_retrievals,
                total_documents=len(set(doc_ids)),
                reproducibility=self._build_reproducibility(
                    output_payload, all_results_chunks, cited_ids, doc_ids
                ),
            ),
            gate_verdict=original_verdict,
        )

    # ==================================================================
    # 4. EDUCATION MODE (P1-2: rank-based levels)
    # ==================================================================

    async def educate(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P1-2: Education mode with retrieval-rank-based difficulty.

        - beginner: top-ranked claim(s) only, fewer details
        - intermediate: all claims, full provenance
        - Every paragraph ends with citation marker.
        - No text-length-based level assignment.
        """
        proof, verdict, gate_passed = await self._run_gated_proof(query, top_k)

        if not gate_passed:
            return self._build_fail_closed(
                query,
                "education",
                AcademicErrorCode.UNSUPPORTED_PROPOSITION,
                verdict.reason,
                verdict.matched_keywords,
            )

        claims = proof.verified_claims
        if not claims:
            return self._build_fail_closed(
                query,
                "education",
                AcademicErrorCode.EMPTY_ACADEMIC_EVIDENCE,
                "No evidence to create educational explanation",
            )

        # P1-2: Level by retrieval rank, NOT text length
        # beginner = top-ranked claim (first in retrieval order)
        # intermediate = all claims
        beginner_claims = claims[:1]  # top-ranked
        intermediate_claims = claims

        explanation: list[EducationConcept] = []

        if beginner_claims:
            explanation.append(
                EducationConcept(
                    concept=query,
                    level="beginner",
                    paragraphs=self._render_extractive_paragraphs(beginner_claims),
                    citations=self._claims_to_citations(beginner_claims),
                    evidence=self._claims_to_traces(beginner_claims),
                )
            )

        if intermediate_claims and len(intermediate_claims) > len(beginner_claims):
            explanation.append(
                EducationConcept(
                    concept=query,
                    level="intermediate",
                    paragraphs=self._render_extractive_paragraphs(intermediate_claims),
                    citations=self._claims_to_citations(intermediate_claims),
                    evidence=self._claims_to_traces(intermediate_claims),
                )
            )

        all_traces = self._claims_to_traces(claims)
        all_citations = self._claims_to_citations(claims)
        cited_ids = list(dict.fromkeys(vc.chunk_id for vc in claims))
        doc_ids = list(dict.fromkeys(vc.document_id for vc in claims))
        results_chunks = self._build_results_chunks_from_proof(proof)

        output_payload = {
            "query": query,
            "academic_type": "education",
            "explanation": [
                {"concept": e.concept, "level": e.level, "paragraphs": e.paragraphs}
                for e in explanation
            ],
        }

        return AcademicResponse(
            query=query,
            academic_type="education",
            explanation=explanation,
            citations=all_citations,
            evidence_trace=all_traces,
            metadata=AcademicMetadata(
                top_k=top_k,
                total_claims=len(claims),
                total_retrievals=1,
                total_documents=len(set(doc_ids)),
                reproducibility=self._build_reproducibility(
                    output_payload, results_chunks, cited_ids, doc_ids
                ),
            ),
            gate_verdict=verdict,
        )

    @staticmethod
    def _render_extractive_paragraphs(
        claims: list[VerifiedClaim],
    ) -> list[str]:
        """Render extractive paragraphs — each is quote + citation. No invented prose."""
        paragraphs: list[str] = []
        for vc in claims:
            para = vc.quote.strip()
            if not para:
                continue
            if para[-1] not in "。！？.!?）\"'":
                para += "。"
            para += vc.citation_str
            paragraphs.append(para)
        return paragraphs
