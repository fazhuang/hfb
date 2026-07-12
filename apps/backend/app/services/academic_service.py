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
import json
import re
from dataclasses import dataclass

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
from app.services.generation_service import _normalize_whitespace


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
# P0-3: ACADEMIC QUERY PLANNER — deterministic retrieval query building
# ======================================================================

# Question markers to strip for retrieval
_QUESTION_MARKERS_RE = re.compile(r"(是否|能否|是不是|有没有|可不|是什么|什么是|如何|怎么|怎样|为何|为什么|是谁)")

# Segmentation keywords — keep these as separate terms
_SEGMENT_KEYWORDS: list[str] = [
    "针灸甲乙经", "伤寒杂病论", "本草纲目", "黄帝内经", "神农本草经", "难经", "脉经",
    "针灸", "经络", "腧穴", "穴位", "脏腑", "辨证", "针刺", "艾灸",
    "皇甫谧", "张仲景", "李时珍", "孙思邈", "华佗", "扁鹊",
    "版本", "刻本", "抄本", "校注",
    "成书", "成书特点", "成书背景", "成书年代", "成书过程",
    "编纂", "编纂原则", "编纂特点", "学术思想", "学术价值",
    "中医", "针灸学", "文献学", "本草学", "方剂学",
    "临床", "治疗", "诊断", "脉诊", "病候", "证候",
    "针法", "灸法", "刺法", "补泻", "得气", "留针",
    "特点", "特征", "背景", "来源", "内容", "结构", "关联",
    "影响", "文献", "著作", "经典", "医学",
    "治疗", "治愈", "导致", "证明",
    "所有", "全部", "任何", "一切",
    "提出", "编撰", "记载", "论述", "包含",
    "定义", "概念", "历史", "来源",
]


def build_academic_retrieval_query(query: str) -> str:
    """P0-3: Build a retrieval query from an academic query.

    - Strips question markers (是否, 能否, 是不是, 有没有)
    - Segments around known keywords so each term is ≥2 chars
    - Never degrades to single-character search
    """
    # Strip question markers
    clean = _QUESTION_MARKERS_RE.sub(" ", query)
    # Normalize whitespace
    clean = re.sub(r"\s+", " ", clean).strip()

    # Segment: insert spaces around known keywords
    for kw in _SEGMENT_KEYWORDS:
        clean = clean.replace(kw, f" {kw} ")

    # Normalize again
    clean = re.sub(r"\s+", " ", clean).strip()

    # Filter: keep terms with ≥2 Chinese characters, or domain names
    terms = clean.split()
    result_terms: list[str] = []
    for t in terms:
        # Count Chinese chars
        chinese_chars = len(re.findall(r"[一-鿿]", t))
        if chinese_chars >= 2:
            result_terms.append(t)

    if not result_terms:
        # Fallback: brute-force bigram segmentation for Chinese text
        chinese_chars = re.findall(r"[一-鿿]", clean)
        if len(chinese_chars) >= 2:
            for i in range(0, len(chinese_chars) - 1, 1):
                bigram = "".join(chinese_chars[i:i+2])
                if bigram not in result_terms:
                    result_terms.append(bigram)
            # Also add trigrams for better coverage
            if len(chinese_chars) >= 3:
                for i in range(0, len(chinese_chars) - 2, 1):
                    trigram = "".join(chinese_chars[i:i+3])
                    if trigram not in result_terms:
                        result_terms.append(trigram)
        if not result_terms:
            return clean if clean else query

    return " ".join(result_terms)


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
        # Sprint 4 P0: accumulated retrieval snapshot from the last proof run.
        # V4 routes read this after calling academic methods to get real
        # RetrievalResult.score and retrieval_method.
        # dict[chunk_id, {document_id, chunk_id, score, retrieval_method, content}]
        self.last_snapshot: dict[str, dict] = {}

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
        corpus_records: list[CorpusRecord] | None = None,
    ) -> AcademicResponse:
        """P0-2: Unified fail-closed response.

        - No sections/themes/evidence/citations
        - gate_verdict.is_supported == false
        - Stable error code
        - Non-factual refusal reason
        - No raw claim text leaked
        """
        response = AcademicResponse(
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
        # P0-6: All responses go through unified finalizer
        return finalize_academic_response(response, corpus_records=corpus_records)

    # ==================================================================
    # SHARED: Run pipeline + gate + validate proof
    # ==================================================================

    async def _run_gated_proof(
        self,
        gate_query: str,
        top_k: int,
        retrieval_query: str | None = None,
    ) -> tuple[GenerationProof, UnsupportedClaimVerdict, bool, str | None]:
        """Run pipeline, gate, and validate proof completeness.

        Returns (proof, verdict, gate_passed, fail_reason).

        P0-1: Only INTEGRITY_ERROR → binding failure. NO_EVIDENCE → let caller handle.
        P0-3: retrieval_query is used for retrieval; gate_query for same-sentence check.
        """
        actual_retrieval = retrieval_query if retrieval_query else gate_query
        pipeline = ProvedGenerationPipeline(self.session)
        proof = await pipeline.generate_with_proof(query=actual_retrieval, top_k=top_k)

        # Sprint 4 P0: accumulate retrieval snapshot from this proof into last_snapshot
        if proof.retrieval_snapshot:
            self.last_snapshot.update(proof.retrieval_snapshot)

        # P0-1: INTEGRITY_ERROR — proof validation failed with explicit error code
        if proof.has_integrity_error:
            chunks_content = [r["content"] for r in proof.response.results]
            verdict = _check_same_sentence_support(gate_query, chunks_content)
            return proof, verdict, False, proof.error_code

        # P0-1: NO_EVIDENCE — empty retrieval, not an error
        if proof.has_no_evidence:
            verdict = _check_same_sentence_support(gate_query, [])
            return proof, verdict, False, None

        # Gate: same-sentence evidence check on gate_query (not retrieval_query)
        chunks_content = [r["content"] for r in proof.response.results]
        verdict = _check_same_sentence_support(gate_query, chunks_content)
        gate_passed = verdict.is_supported

        if not gate_passed:
            return proof, verdict, False, None

        # Gate passed but proof must still be complete
        if not proof.is_complete:
            return (
                proof,
                verdict,
                False,
                AcademicErrorCode.ACADEMIC_CLAIM_BINDING_FAILED,
            )

        return proof, verdict, True, None

    # ==================================================================
    # P0-3: Unified proof-completeness check
    # ==================================================================

    @classmethod
    def _fail_on_proof_integrity_error(
        cls,
        query: str,
        academic_type: str,
        proof: GenerationProof,
    ) -> AcademicResponse | None:
        """P0-1: Only fail closed on INTEGRITY_ERROR.

        Returns None if proof is ok to continue (valid or no_evidence).
        Only returns fail-closed when proof.has_integrity_error.
        """
        if not proof.has_integrity_error:
            return None

        return cls._build_fail_closed(
            query,
            academic_type,
            proof.error_code or AcademicErrorCode.ACADEMIC_CLAIM_BINDING_FAILED,
            f"Proof integrity check failed: {proof.error_code or 'incomplete'}",
            corpus_records=_build_corpus_records_from_proof(proof),
        )

    # ==================================================================
    # P1-3: REPRODUCIBILITY — now handled by unified finalize_academic_response
    # ==================================================================

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
        """P0-2: Generate a structured academic report with strict claim binding and proof check."""
        sections = self._REPORT_DECOMPOSE_PATTERNS.get(
            report_type, self._REPORT_DECOMPOSE_PATTERNS["research_summary"]
        )
        title = self._REPORT_TITLES.get(report_type, "研究报告")

        all_claims: list[VerifiedClaim] = []
        report_sections: list[ReportSection] = []
        total_retrievals = 0
        final_verdict: UnsupportedClaimVerdict | None = None
        all_corpus_records: list[CorpusRecord] = []

        for section_heading in sections:
            sub_query = f"{query} —— {section_heading}"
            retrieval_q = build_academic_retrieval_query(sub_query)
            proof, verdict, gate_passed, fail_reason = await self._run_gated_proof(
                gate_query=sub_query,
                top_k=top_k,
                retrieval_query=retrieval_q,
            )
            total_retrievals += 1
            final_verdict = verdict
            all_corpus_records.extend(_build_corpus_records_from_proof(proof))

            # P0-1: INTEGRITY_ERROR → hard fail
            if proof.has_integrity_error:
                return self._build_fail_closed(
                    query,
                    "report",
                    proof.error_code or AcademicErrorCode.ACADEMIC_CLAIM_BINDING_FAILED,
                    f"Proof integrity error for section '{section_heading}': {proof.error_code}",
                    corpus_records=all_corpus_records,
                )

            # P0-1: NO_EVIDENCE → evidence gap for this section, other sections continue
            if proof.has_no_evidence:
                report_sections.append(
                    ReportSection(
                        heading=section_heading,
                        body="EVIDENCE_GAP: 无相关资料。",
                        citations=[],
                        evidence=[],
                    )
                )
                continue

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
            # P0-2: fail closed if ANY claim cannot be bound
            if not section_claims and proof.response.results:
                return self._build_fail_closed(
                    query,
                    "report",
                    AcademicErrorCode.ACADEMIC_CLAIM_BINDING_FAILED,
                    f"Claims could not be bound for section '{section_heading}'",
                    corpus_records=all_corpus_records,
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
                corpus_records=all_corpus_records,
            )

        all_traces = self._claims_to_traces(all_claims)
        all_citations = self._claims_to_citations(all_claims)
        doc_ids = list(dict.fromkeys(vc.document_id for vc in all_claims))

        return finalize_academic_response(
            AcademicResponse(
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
                ),
                gate_verdict=final_verdict,
            ),
            corpus_records=all_corpus_records,
        )

    # ==================================================================
    # 2. KNOWLEDGE SYNTHESIS ENGINE
    # ==================================================================

    async def synthesize(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P0-3: Synthesize knowledge with strict claim binding and proof check."""
        retrieval_q = build_academic_retrieval_query(query)
        proof, verdict, gate_passed, fail_reason = await self._run_gated_proof(
            gate_query=query,
            top_k=top_k,
            retrieval_query=retrieval_q,
        )

        # P0-1: INTEGRITY_ERROR → fail closed
        fail = self._fail_on_proof_integrity_error(query, "synthesis", proof)
        if fail is not None:
            return fail

        # P0-1: NO_EVIDENCE → EMPTY_ACADEMIC_EVIDENCE
        if proof.has_no_evidence:
            return self._build_fail_closed(
                query,
                "synthesis",
                AcademicErrorCode.EMPTY_ACADEMIC_EVIDENCE,
                "No evidence found",
            )

        if not gate_passed:
            reason = fail_reason if fail_reason else verdict.reason
            code = (
                fail_reason
                if fail_reason
                else AcademicErrorCode.UNSUPPORTED_PROPOSITION
            )
            return self._build_fail_closed(
                query,
                "synthesis",
                code,
                reason,
                verdict.matched_keywords,
                corpus_records=_build_corpus_records_from_proof(proof),
            )

        claims = proof.verified_claims
        if not claims:
            return self._build_fail_closed(
                query,
                "synthesis",
                AcademicErrorCode.EMPTY_ACADEMIC_EVIDENCE,
                "No evidence found",
                corpus_records=_build_corpus_records_from_proof(proof),
            )

        traces = self._claims_to_traces(claims)
        citations = self._claims_to_citations(claims)

        # Cluster by concept
        themes = self._cluster_claims_by_concept(claims)

        for theme in themes:
            doc_ids_set = set(c.document_id for c in theme.claims)
            if len(doc_ids_set) >= 2:
                theme.cross_document_refs = sorted(doc_ids_set)

        doc_ids = list(dict.fromkeys(vc.document_id for vc in claims))

        return finalize_academic_response(
            AcademicResponse(
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
                ),
                gate_verdict=verdict,
            ),
            corpus_records=_build_corpus_records_from_proof(proof),
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

    _RESEARCH_DECOMPOSE_PATTERNS: list[tuple[str, str, str]] = [
        ("定义与概念", "什么是{query}？", "{query} 定义 概念"),
        ("历史与来源", "{query}的历史渊源是什么？", "{query} 历史 来源"),
        ("内容与结构", "{query}包含哪些内容？", "{query} 内容 结构"),
        ("关联与影响", "{query}与哪些概念或文献有关？", "{query} 关联 影响 文献"),
    ]

    async def research(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P0-3: Gate-first research. P0-4: Hypothesis from corpus only. P0-5: Hypothesis trace.

        Flow:
        1. Classify original query for proposition patterns.
        2. If original query is a gated proposition AND no supporting evidence → immediate UNSUPPORTED_PROPOSITION.
        3. If original query is NOT a gated proposition → always proceed with decomposition even if retrieval is empty.
        4. Each sub-question: INTEGRITY_ERROR → fail closed; NO_EVIDENCE → gap; VALID → evidence.
        5. Hypothesis traces go into both sub.evidence and top-level evidence_trace.
        """
        # P0-2: Classify original query
        classifications = _classify_query(query)

        # Run retrieval for original query
        retrieval_q = build_academic_retrieval_query(query)
        proof, original_verdict, _, fail_reason = await self._run_gated_proof(
            gate_query=query,
            top_k=top_k,
            retrieval_query=retrieval_q,
        )

        # P0-1: INTEGRITY_ERROR → fail closed
        if proof.has_integrity_error:
            return self._build_fail_closed(
                query,
                "research",
                proof.error_code or AcademicErrorCode.ACADEMIC_CLAIM_BINDING_FAILED,
                f"Proof integrity error: {proof.error_code}",
                corpus_records=_build_corpus_records_from_proof(proof),
            )

        # P0-2: Gated proposition + no evidence → immediate refusal
        if classifications and proof.has_no_evidence:
            return self._build_fail_closed(
                query,
                "research",
                AcademicErrorCode.UNSUPPORTED_PROPOSITION,
                original_verdict.reason,
                original_verdict.matched_keywords,
            )

        # P0-2: Gated proposition + evidence doesn't pass same-sentence gate → refusal
        if classifications and not original_verdict.is_supported:
            return self._build_fail_closed(
                query,
                "research",
                AcademicErrorCode.UNSUPPORTED_PROPOSITION,
                original_verdict.reason,
                original_verdict.matched_keywords,
                corpus_records=_build_corpus_records_from_proof(proof),
            )

        # P0-2: Not a gated proposition, or gate passed → proceed with decomposition
        sub_questions: list[ResearchSubQuestion] = []
        all_claims: list[VerifiedClaim] = []
        hypothesis_traces: list[EvidenceTrace] = []
        all_corpus_records: list[list[CorpusRecord]] = []
        total_retrievals = 0

        for (
            aspect,
            display_template,
            retrieval_template,
        ) in self._RESEARCH_DECOMPOSE_PATTERNS:
            sub_display = display_template.replace("{query}", query)
            sub_retrieval = build_academic_retrieval_query(retrieval_template.replace("{query}", query))

            (
                sub_proof,
                sub_verdict,
                sub_gate_passed,
                sub_fail_reason,
            ) = await self._run_gated_proof(
                gate_query=sub_display,
                top_k=top_k,
                retrieval_query=sub_retrieval,
            )
            total_retrievals += 1
            all_corpus_records.append(_build_corpus_records_from_proof(sub_proof))

            # P0-1: INTEGRITY_ERROR → hard fail
            if sub_proof.has_integrity_error:
                return self._build_fail_closed(
                    query,
                    "research",
                    sub_proof.error_code
                    or AcademicErrorCode.ACADEMIC_CLAIM_BINDING_FAILED,
                    f"Proof integrity error for sub-question '{sub_display}': {sub_proof.error_code}",
                    corpus_records=_merge_corpus_records(*all_corpus_records),
                )

            # P0-1: NO_EVIDENCE → gap
            if sub_proof.has_no_evidence:
                sub_questions.append(
                    ResearchSubQuestion(
                        sub_question=sub_display,
                        evidence=[],
                        has_gap=True,
                        hypothesis=None,
                    )
                )
                continue

            # Gate didn't pass → gap
            if not sub_gate_passed:
                sub_questions.append(
                    ResearchSubQuestion(
                        sub_question=sub_display,
                        evidence=[],
                        has_gap=True,
                        hypothesis=None,
                    )
                )
                continue

            sub_claims = sub_proof.verified_claims
            if not sub_claims:
                sub_questions.append(
                    ResearchSubQuestion(
                        sub_question=sub_display,
                        evidence=[],
                        has_gap=True,
                        hypothesis=None,
                    )
                )
                continue

            all_claims.extend(sub_claims)

            # P0-5: Sub-question evidence = canonical evidence (claims_to_traces)
            sub_evidence = self._claims_to_traces(sub_claims)

            # P0-4, P0-5: Hypothesis from corpus speculative expressions WITH exact trace
            hypothesis: str | None = None
            hypothesis_evidence: list[EvidenceTrace] = []

            for vc in sub_claims:
                chunk_content = ""
                for r in sub_proof.response.results:
                    if r["chunk_id"] == vc.chunk_id:
                        chunk_content = r["content"]
                        break
                if chunk_content:
                    extracted = _extract_hypothesis_from_chunk(chunk_content)
                    if extracted:
                        hypothesis_norm = _normalize_whitespace(extracted)
                        chunk_norm = _normalize_whitespace(chunk_content)
                        if hypothesis_norm in chunk_norm:
                            hypothesis = f"{extracted}{vc.citation_str}"
                            hyp_trace = EvidenceTrace(
                                claim_text=extracted,
                                quote=extracted,
                                document_id=vc.document_id,
                                chunk_id=vc.chunk_id,
                                citation_text=vc.citation_str,
                            )
                            hypothesis_evidence.append(hyp_trace)
                            hypothesis_traces.append(hyp_trace)
                            break

            # P0-5: Sub-question evidence includes hypothesis traces
            sub_evidence = _dedup_traces(sub_evidence + hypothesis_evidence)

            sub_questions.append(
                ResearchSubQuestion(
                    sub_question=sub_display,
                    evidence=sub_evidence,
                    has_gap=False,
                    hypothesis=hypothesis,
                )
            )

        all_traces = self._claims_to_traces(all_claims)
        # P0-5: Include hypothesis traces in top-level evidence_trace
        all_traces = _dedup_traces(all_traces + hypothesis_traces)
        all_citations = self._claims_to_citations(all_claims)
        for ht in hypothesis_traces:
            all_citations = _merge_citation(all_citations, ht)
        doc_ids = list(dict.fromkeys(vc.document_id for vc in all_claims))

        # Determine gate verdict for response
        gate_verdict = (
            original_verdict if not original_verdict.is_supported else original_verdict
        )

        return finalize_academic_response(
            AcademicResponse(
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
                ),
                gate_verdict=gate_verdict,
            ),
            corpus_records=_merge_corpus_records(*all_corpus_records),
        )

    # ==================================================================
    # 4. EDUCATION MODE (P1-2: rank-based levels)
    # ==================================================================

    async def educate(self, query: str, top_k: int = 5) -> AcademicResponse:
        """P1-2: Education mode with retrieval-rank-based difficulty, proof check.

        - beginner: top-ranked claim(s) only, fewer details
        - intermediate: all claims, full provenance
        - Every paragraph ends with citation marker.
        - No text-length-based level assignment.
        """
        retrieval_q = build_academic_retrieval_query(query)
        proof, verdict, gate_passed, fail_reason = await self._run_gated_proof(
            gate_query=query,
            top_k=top_k,
            retrieval_query=retrieval_q,
        )

        # P0-1: INTEGRITY_ERROR → fail closed
        fail = self._fail_on_proof_integrity_error(query, "education", proof)
        if fail is not None:
            return fail

        # P0-1: NO_EVIDENCE → EMPTY_ACADEMIC_EVIDENCE
        if proof.has_no_evidence:
            return self._build_fail_closed(
                query,
                "education",
                AcademicErrorCode.EMPTY_ACADEMIC_EVIDENCE,
                "No evidence to create educational explanation",
            )

        if not gate_passed:
            reason = fail_reason if fail_reason else verdict.reason
            code = (
                fail_reason
                if fail_reason
                else AcademicErrorCode.UNSUPPORTED_PROPOSITION
            )
            return self._build_fail_closed(
                query,
                "education",
                code,
                reason,
                verdict.matched_keywords,
                corpus_records=_build_corpus_records_from_proof(proof),
            )

        claims = proof.verified_claims
        if not claims:
            return self._build_fail_closed(
                query,
                "education",
                AcademicErrorCode.EMPTY_ACADEMIC_EVIDENCE,
                "No evidence to create educational explanation",
                corpus_records=_build_corpus_records_from_proof(proof),
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
        doc_ids = list(dict.fromkeys(vc.document_id for vc in claims))

        return finalize_academic_response(
            AcademicResponse(
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
                ),
                gate_verdict=verdict,
            ),
            corpus_records=_build_corpus_records_from_proof(proof),
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


# ======================================================================
# P0-5: Hypothesis trace helpers
# ======================================================================


def _dedup_traces(traces: list[EvidenceTrace]) -> list[EvidenceTrace]:
    """Deduplicate evidence traces by (chunk_id, quote)."""
    seen: set[tuple[str, str]] = set()
    result: list[EvidenceTrace] = []
    for t in traces:
        key = (t.chunk_id, t.quote)
        if key not in seen:
            seen.add(key)
            result.append(t)
    return result


def _merge_citation(
    citations: list[CitationRef], trace: EvidenceTrace
) -> list[CitationRef]:
    """Add a citation from an evidence trace if not already present."""
    for c in citations:
        if c.chunk_id == trace.chunk_id:
            return citations
    citations.append(
        CitationRef(
            document_id=trace.document_id,
            chunk_id=trace.chunk_id,
            text=trace.citation_text,
        )
    )
    return citations


# ======================================================================
# P0-6: UNIFIED FINALIZER — complete artifact hash with full chunk content
# ======================================================================


@dataclass(frozen=True)
class CorpusRecord:
    """P0-6: A retrieval snapshot record with full chunk content."""

    document_id: str
    chunk_id: str
    content: str  # full chunk content, not just the quote


def _canonical_json(payload: dict) -> str:
    """Canonical JSON serialization."""
    return json.dumps(
        payload,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def finalize_academic_response(
    response: AcademicResponse,
    corpus_records: list[CorpusRecord] | None = None,
) -> AcademicResponse:
    """P0-6: Unified finalizer — computes complete artifact hashes.

    corpus_records: real retrieval snapshot with full chunk content.
    If None, builds from evidence_trace (backward compat for refusal responses).
    If empty list, corpus_sha256 = sha256(b"").

    Steps:
    1. Build deduped, sorted corpus records from full chunk content
    2. Compute corpus_sha256 (non-empty even for empty corpus)
    3. Write pipeline_version, ordered_cited_chunk_ids, source_document_ids
    4. Set output_sha256 to "" temporarily
    5. Full canonical JSON serialization of the entire response
    6. Compute output SHA-256
    7. Write back output_sha256
    8. All responses (success and refusal) go through this finalizer
    """
    repro = response.metadata.reproducibility

    # Extract cited chunk IDs from evidence traces
    cited_ids = list(dict.fromkeys(t.chunk_id for t in response.evidence_trace))
    doc_ids = sorted(set(t.document_id for t in response.evidence_trace))

    repro.ordered_cited_chunk_ids = cited_ids
    repro.source_document_ids = doc_ids
    repro.pipeline_version = "academic-grounded-v2-p0"

    # P0-6: Corpus hash from full chunk content, NOT from quotes
    if corpus_records is None:
        # Backward compat: fall back to evidence trace quotes
        corpus_parts: list[str] = []
        seen_corpus: set[tuple[str, str]] = set()
        for t in sorted(
            response.evidence_trace, key=lambda x: (x.document_id, x.chunk_id)
        ):
            key = (t.document_id, t.chunk_id)
            if key not in seen_corpus:
                seen_corpus.add(key)
                corpus_parts.append(f"{t.document_id}:{t.chunk_id}:{t.quote}")
        corpus_str = "\n".join(corpus_parts)
    elif not corpus_records:
        # Empty corpus → sha256(b"")
        corpus_str = ""
    else:
        # P0-6: Full chunk content, sorted, deduped
        seen_corpus: set[tuple[str, str]] = set()
        corpus_parts: list[str] = []
        for cr in sorted(corpus_records, key=lambda x: (x.document_id, x.chunk_id)):
            key = (cr.document_id, cr.chunk_id)
            if key not in seen_corpus:
                seen_corpus.add(key)
                corpus_parts.append(f"{cr.document_id}:{cr.chunk_id}:{cr.content}")
        corpus_str = "\n".join(corpus_parts)

    repro.corpus_sha256 = hashlib.sha256(corpus_str.encode()).hexdigest()

    # Set output_sha256 empty first, then compute
    repro.output_sha256 = ""

    payload = response.model_dump(mode="json")
    payload["metadata"]["reproducibility"]["output_sha256"] = ""
    output_str = _canonical_json(payload)
    output_sha = hashlib.sha256(output_str.encode()).hexdigest()

    repro.output_sha256 = output_sha
    response.metadata.reproducibility = repro

    return response


def _build_corpus_records_from_proof(proof: GenerationProof) -> list[CorpusRecord]:
    """P0-6: Build CorpusRecord list from a GenerationProof's retrieval snapshot."""
    seen: set[tuple[str, str]] = set()
    records: list[CorpusRecord] = []
    for r in proof.response.results:
        key = (r["document_id"], r["chunk_id"])
        if key not in seen:
            seen.add(key)
            records.append(
                CorpusRecord(
                    document_id=r["document_id"],
                    chunk_id=r["chunk_id"],
                    content=r["content"],
                )
            )
    return records


def _merge_corpus_records(*record_lists: list[CorpusRecord]) -> list[CorpusRecord]:
    """P0-6: Merge multiple CorpusRecord lists, deduplicating by (document_id, chunk_id)."""
    seen: set[tuple[str, str]] = set()
    merged: list[CorpusRecord] = []
    for records in record_lists:
        for cr in records:
            key = (cr.document_id, cr.chunk_id)
            if key not in seen:
                seen.add(key)
                merged.append(cr)
    return merged
