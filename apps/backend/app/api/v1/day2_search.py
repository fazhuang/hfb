"""
Day 2 Search API — document chunk retrieval with citation binding.

Endpoints:
  POST /api/v1/search         — Search document chunks (primary endpoint)
  POST /api/v1/search/chunks  — Search document chunks (compatibility alias)
  POST /api/v1/search/ingest  — Ingest a plain-text document
"""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.schemas.chunk_search import (
    SearchRequest,
    SearchResponse,
    SearchResult,
    Metadata,
    IngestTextRequest,
)
from app.services.ingestion import IngestionService, IngestionError
from app.services.retrieval import RetrievalService
from app.utils.response import api_response

router = APIRouter(prefix="/search", tags=["Search"])

# ponytail: auth deferred to post-Day-2 hardening.
# Search/ingest use no required permission to allow integration
# testing; user-level auth is applied through the frontend gateway
# and will be wired via require_permission("search", "read") later.



@router.post("", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> SearchResponse:
    """Search document chunks by keyword.

    Each result includes a citation in the format [doc_id:chunk_id]
    that can be traced back to the source document and chunk.

    Response contract (frozen):
      query:    echo of the search query
      results:  [{chunk_id, document_id, content, score, citation}]
      metadata: {top_k, model: "retrieval-only"}

    No LLM-generated answers. No AI service calls. Fully deterministic.
    """
    svc = RetrievalService(session)
    result = await svc.search(
        query=body.query,
        top_k=body.top_k,
        document_id=body.document_id,
        year=body.year,
        author_id=body.author_id,
    )

    return SearchResponse(
        query=body.query,
        results=[
            SearchResult(
                chunk_id=r.chunk_id,
                document_id=r.document_id,
                content=r.content,
                score=r.score,
                citation=r.citation,
            )
            for r in result.results
        ],
        metadata=Metadata(
            top_k=body.top_k,
            model="retrieval-only",
        ),
    )


@router.post("/chunks", response_model=dict)
async def search_chunks(
    body: SearchRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Search document chunks (compatibility alias for POST /api/v1/search/chunks)."""
    svc = RetrievalService(session)
    result = await svc.search(
        query=body.query,
        top_k=body.top_k,
        document_id=body.document_id,
        year=body.year,
        author_id=body.author_id,
    )
    return api_response(
        data={
            "query": result.query,
            "total": result.total,
            "max_score": result.max_score,
            "results": [
                {
                    "chunk_id": r.chunk_id,
                    "document_id": r.document_id,
                    "document_title": r.document_title,
                    "chunk_index": r.chunk_index,
                    "content": r.content,
                    "citation": r.citation,
                    "score": r.score,
                    "metadata": r.metadata,
                }
                for r in result.results
            ],
        }
    )


@router.post("/ingest", response_model=dict)
async def ingest_text(
    body: IngestTextRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    """Ingest a plain-text document, chunk it, and store it for retrieval.

    Context 21: copyright_status and authorization fields are passed to
    IngestionService.ingest_text() which enforces the compliance gate before
    any full-text is stored or chunked.
    """
    try:
        metadata: dict = {}
        if body.dynasty:
            metadata["dynasty"] = body.dynasty
        if body.category:
            metadata["category"] = body.category

        # Context 21: compliance fields
        metadata["copyright_status"] = body.copyright_status
        if body.license_type:
            metadata["license_type"] = body.license_type
        if body.authorization_basis:
            metadata["authorization_basis"] = body.authorization_basis
        if body.source_url:
            metadata["source_url"] = body.source_url
        if body.source_name:
            metadata["source_name"] = body.source_name
        if body.metadata_only:
            metadata["copyright_status"] = "metadata_only"
        if body.forbidden_fulltext:
            metadata["forbidden_fulltext"] = True

        svc = IngestionService(session)
        result = await svc.ingest_text(
            title=body.title,
            text=body.text,
            metadata=metadata if metadata else None,
            max_chunk_chars=body.max_chunk_chars,
        )
        return api_response(
            data={
                "document_id": result.document_id,
                "title": result.title,
                "chunk_count": result.chunk_count,
                "total_chars": result.total_chars,
                "checksum": result.checksum,
            }
        )
    except IngestionError as e:
        return api_response(success=False, message=str(e), data=None)
