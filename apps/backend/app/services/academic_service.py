"""
Academic Service — Sprint 2 academic product layer.

Composes GenerationPipeline for each module. Does NOT modify Sprint 1 systems.
All facts come from GenerationPipeline; this service only orchestrates and structures.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.academic import (
    AcademicMetadata,
    AcademicResponse,
    CitationRef,
    EducationConcept,
    EvidenceTrace,
    ReportSection,
    ResearchSubQuestion,
    SynthesisTheme,
)
from app.schemas.generation import GroundedGenerationResponse
from app.services.generation_service import GenerationPipeline


class AcademicService:
    """Academic product layer — report, synthesis, research, education.

    All four methods share the same pipeline composition pattern:
    1. Run GenerationPipeline.generate() for fact-grounded claims
    2. Extract EvidenceTrace from results
    3. Structure output per module type
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------------
    # Helpers — shared across all modules
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_evidence_traces(
        result: GroundedGenerationResponse,
    ) -> list[EvidenceTrace]:
        """Extract evidence traces from a generation result's results+citations."""
        traces: list[EvidenceTrace] = []
        citation_map: dict[str, str] = {}
        for c in result.citations:
            citation_map[c["chunk_id"]] = c.get("text", "")

        for r in result.results:
            chunk_id = r["chunk_id"]
            # Extract claim text from answer — each line is "quote[citation]"
            # We use the content as claim_text since it's the original source
            traces.append(
                EvidenceTrace(
                    claim_text=r["content"][:300],  # excerpt for traceability
                    document_id=r["document_id"],
                    chunk_id=chunk_id,
                    quote=r["content"][:300],
                    citation_text=citation_map.get(
                        chunk_id, f"[{r['document_id']}:{chunk_id}]"
                    ),
                )
            )
        return traces

    @staticmethod
    def _extract_citations(result: GroundedGenerationResponse) -> list[CitationRef]:
        """Extract citation refs from a generation result."""
        return [
            CitationRef(
                document_id=c["document_id"],
                chunk_id=c["chunk_id"],
                text=c.get("text", ""),
            )
            for c in result.citations
        ]

    @staticmethod
    def _unique_documents(traces: list[EvidenceTrace]) -> int:
        """Count unique documents across traces."""
        return len(set(t.document_id for t in traces))

    # ------------------------------------------------------------------
    # 1. Academic Report Generator
    # ------------------------------------------------------------------

    # Sub-theme decomposition patterns for 皇甫谧 domain
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
        """Generate a structured academic report.

        Decomposes query into sub-themes, runs GenerationPipeline per theme,
        assembles sections.
        """
        sections = self._REPORT_DECOMPOSE_PATTERNS.get(
            report_type, self._REPORT_DECOMPOSE_PATTERNS["research_summary"]
        )
        title = self._REPORT_TITLES.get(report_type, "研究报告")

        all_traces: list[EvidenceTrace] = []
        all_citations: list[CitationRef] = []
        report_sections: list[ReportSection] = []
        total_retrievals = 0

        for section_heading in sections:
            # Build a targeted sub-query for this section
            sub_query = f"{query} —— {section_heading}"

            pipeline = GenerationPipeline(self.session)
            result = await pipeline.generate(query=sub_query, top_k=top_k)
            total_retrievals += 1

            traces = self._extract_evidence_traces(result)
            citations = self._extract_citations(result)

            all_traces.extend(traces)
            all_citations.extend(citations)

            report_sections.append(
                ReportSection(
                    heading=section_heading,
                    body=result.answer,
                    citations=citations,
                    evidence=traces,
                )
            )

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
                total_documents=self._unique_documents(all_traces),
            ),
        )

    # ------------------------------------------------------------------
    # 2. Knowledge Synthesis Engine
    # ------------------------------------------------------------------

    async def synthesize(self, query: str, top_k: int = 5) -> AcademicResponse:
        """Synthesize knowledge across multiple chunks/documents.

        Runs generation, clusters claims by concept keywords, marks cross-doc refs.
        """
        pipeline = GenerationPipeline(self.session)
        result = await pipeline.generate(query=query, top_k=top_k)

        traces = self._extract_evidence_traces(result)
        citations = self._extract_citations(result)

        # Concept clustering — deterministic by keyword overlap, no LLM
        themes = self._cluster_by_concept(traces, query)

        # Mark cross-document refs
        for theme in themes:
            doc_ids = set(c.document_id for c in theme.claims)
            if len(doc_ids) > 1:
                theme.cross_document_refs = sorted(doc_ids)

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
                total_documents=self._unique_documents(traces),
            ),
        )

    # TCM concept keywords for clustering
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
    def _cluster_by_concept(
        cls, traces: list[EvidenceTrace], query: str
    ) -> list[SynthesisTheme]:
        """Cluster evidence traces by concept keyword overlap. No LLM."""
        if not traces:
            return []

        # Extract query keywords
        query_chars = set(query)

        # Build keyword scores per trace
        trace_themes: list[tuple[str, list[EvidenceTrace]]] = []
        assigned: set[int] = set()

        for kw in cls._CONCEPT_KEYWORDS:
            if kw not in query and not any(c in query_chars for c in kw):
                continue
            matching = [
                t
                for i, t in enumerate(traces)
                if i not in assigned and kw in t.claim_text
            ]
            if matching:
                assigned.update(i for i, t in enumerate(traces) if kw in t.claim_text)
                trace_themes.append((kw, matching))

        # Remaining traces go to a general theme
        remaining = [t for i, t in enumerate(traces) if i not in assigned]
        if remaining:
            trace_themes.append(("相关文献", remaining))

        if not trace_themes:
            trace_themes.append(("检索结果", list(traces)))

        # Build themes
        results: list[SynthesisTheme] = []
        # ponytail: O(n²) scan for dedup, fine for top_k ≤ 20
        seen_claims: set[tuple[str, str]] = set()
        for theme_name, theme_traces in trace_themes:
            deduped: list[EvidenceTrace] = []
            for t in theme_traces:
                key = (t.chunk_id, t.quote[:50])
                if key not in seen_claims:
                    seen_claims.add(key)
                    deduped.append(t)

            results.append(
                SynthesisTheme(
                    title=theme_name,
                    description=f"与「{theme_name}」相关的文献证据",
                    claims=deduped,
                )
            )

        return results

    # ------------------------------------------------------------------
    # 3. Research Assistant Mode
    # ------------------------------------------------------------------

    # Research question decomposition patterns
    _RESEARCH_DECOMPOSE_PATTERNS: list[tuple[str, str]] = [
        ("定义与概念", "什么是{query}？"),
        ("历史与来源", "{query}的历史渊源是什么？"),
        ("内容与结构", "{query}包含哪些内容？"),
        ("关联与影响", "{query}与哪些概念或文献有关？"),
    ]

    async def research(self, query: str, top_k: int = 5) -> AcademicResponse:
        """Research assistant — decompose, search, identify gaps.

        Decomposes query into sub-questions, runs GenerationPipeline per question,
        marks gaps where no evidence found.
        """
        sub_questions: list[ResearchSubQuestion] = []
        all_traces: list[EvidenceTrace] = []
        all_citations: list[CitationRef] = []
        total_retrievals = 0

        for aspect, template in self._RESEARCH_DECOMPOSE_PATTERNS:
            sub_q = template.replace("{query}", query)

            pipeline = GenerationPipeline(self.session)
            result = await pipeline.generate(query=sub_q, top_k=top_k)
            total_retrievals += 1

            traces = self._extract_evidence_traces(result)
            citations = self._extract_citations(result)

            all_traces.extend(traces)
            all_citations.extend(citations)

            has_gap = len(traces) == 0
            hypothesis = None
            if has_gap:
                hypothesis = f"「{aspect}」暂无文献证据支持，可进一步探索。"

            sub_questions.append(
                ResearchSubQuestion(
                    sub_question=sub_q,
                    evidence=traces,
                    has_gap=has_gap,
                    hypothesis=hypothesis,
                )
            )

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
                total_documents=self._unique_documents(all_traces),
            ),
        )

    # ------------------------------------------------------------------
    # 4. Education Mode
    # ------------------------------------------------------------------

    async def educate(self, query: str, top_k: int = 5) -> AcademicResponse:
        """Education mode — explain concepts with difficulty layering.

        Runs generation once, layers claims by complexity, builds teaching output.
        """
        pipeline = GenerationPipeline(self.session)
        result = await pipeline.generate(query=query, top_k=top_k)

        traces = self._extract_evidence_traces(result)
        citations = self._extract_citations(result)

        # Layer by difficulty: beginner (shorter, fewer citations) vs intermediate
        beginner_traces: list[EvidenceTrace] = []
        intermediate_traces: list[EvidenceTrace] = []

        for t in traces:
            if len(t.claim_text) < 200 and len(t.claim_text) > 0:
                beginner_traces.append(t)
            else:
                intermediate_traces.append(t)

        # If no beginner traces, promote some from intermediate
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
            # Build simplified paragraphs from beginner traces
            paragraphs = self._render_education_paragraphs(
                query, beginner_traces, simplified=True
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
            paragraphs = self._render_education_paragraphs(
                query, intermediate_traces, simplified=False
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
                total_documents=self._unique_documents(traces),
            ),
        )

    @staticmethod
    def _render_education_paragraphs(
        concept: str, traces: list[EvidenceTrace], simplified: bool = False
    ) -> list[str]:
        """Render education paragraphs from evidence traces. No free LLM text."""
        if not traces:
            return [f"关于「{concept}」，当前暂无足够的文献资料可供解释。"]

        paragraphs: list[str] = []
        if simplified:
            paragraphs.append(f"「{concept}」是中医文献中记载的重要概念。")
        else:
            paragraphs.append(f"关于「{concept}」，相关文献提供了以下记载：")

        for t in traces:
            # ponytail: deterministic rendering, no LLM
            para = f"{t.quote}"
            if t.citation_text:
                para += f"（出处：{t.citation_text}）"
            paragraphs.append(para)

        return paragraphs
