"""TCM Academic RAG — 学术检索增强生成.

Combines KG traversal + literature search to produce evidence chains
with citation paths for scholarly TCM research.
"""

from tcm_rag.models import (
    KGPath,
    TextHit,
    EvidenceChain,
    CitationPath,
    SearchResult,
)
from tcm_rag.pipeline import RAGPipeline

__all__ = [
    "KGPath",
    "TextHit",
    "EvidenceChain",
    "CitationPath",
    "SearchResult",
    "RAGPipeline",
]
