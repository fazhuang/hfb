"""
AI and Workspace API routes.

Per HFB-PS-1705 AI Research Workspace Product Specification.

Endpoints:
  POST /api/v1/ai/chat       — Streaming AI chat with evidence-gated RAG
  POST /api/v1/ai/summarize  — Summarize text
  POST /api/v1/ai/translate  — Translate classical Chinese
  POST /api/v1/ai/compare    — AI-assisted version comparison
  CRUD /api/v1/workspace/sessions — Research session management
  CRUD /api/v1/workspace/notes    — Research notes
"""
from __future__ import annotations

import json
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_session
from app.middleware.auth import get_current_user, require_permission
from app.schemas.ai_response import (
    StructuredResponseBuilder,
)
from app.services.ai_service import AIService
from app.services.rag_service import RAGService
from app.services.workspace_service import WorkspaceService
from app.utils.response import api_response

# --- Routers ---

ai_router = APIRouter(prefix="/ai", tags=["AI"])
workspace_router = APIRouter(prefix="/workspace", tags=["Workspace"])

guard_ai_read = require_permission("ai", "read")
guard_workspace_read = require_permission("workspace", "read")
guard_workspace_write = require_permission("workspace", "create")


# ============================================================
# Request models
# ============================================================


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    use_rag: bool = True
    entity_types: list[str] | None = None


class SummarizeRequest(BaseModel):
    text: str = Field(..., min_length=1)
    max_words: int = 200


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_lang: str = "现代汉语"


class CompareRequest(BaseModel):
    source_text: str = Field(..., min_length=1)
    target_text: str = Field(..., min_length=1)
    source_label: str = "源版本"
    target_label: str = "目标版本"


class SessionCreateRequest(BaseModel):
    title: str = "未命名研究"


class SessionUpdateRequest(BaseModel):
    title: str | None = None
    active_entities: list[str] | None = None
    context_notes: str | None = None


class NoteCreateRequest(BaseModel):
    content: str = Field(..., min_length=1)
    entity_type: str | None = None
    entity_id: str | None = None
    tags: str | None = None


class NoteUpdateRequest(BaseModel):
    content: str | None = None
    tags: str | None = None


# ============================================================
# AI Chat (streaming)
# ============================================================


@ai_router.post("/chat", dependencies=[Depends(guard_ai_read)])
async def ai_chat(
    body: ChatRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    current_user: str = Depends(get_current_user),
) -> StreamingResponse:
    """Streaming AI chat with evidence-gated RAG context retrieval.

    The response is a Server-Sent Events (SSE) stream.  Each chunk is a JSON
    object with `content` (the answer fragment).  The final event before
    `done` contains `structured` — the full StructuredAIResponse envelope
    with answer + evidence[] + citations[] + graph_context[].

    When no evidence is found (RAG returns empty context), the assistant
    refuses to answer: the stream contains a refusal message and the
    structured envelope has empty evidence/citations/graph_context.
    """
    ai_svc = AIService()

    # --- 1. Retrieve evidence via RAG ---
    rag_svc = RAGService(session)
    rag_chunks: list[dict[str, Any]] = []
    context = ""
    if body.use_rag:
        rag_chunks = await rag_svc.retrieve(body.message, top_k=5)
        context = await rag_svc.assemble_context(body.message, top_k=5)

    # --- 2. Build messages with chat history ---
    messages: list[dict[str, str]] = [{"role": "user", "content": body.message}]
    if body.session_id:
        ws_svc = WorkspaceService(session)
        history = await ws_svc.get_chat_history(body.session_id)
        for h in history[-6:]:
            messages.insert(0, {"role": h["role"], "content": h["content"]})

    # Save user message
    if body.session_id:
        ws_svc = WorkspaceService(session)
        await ws_svc.append_chat_message(body.session_id, "user", body.message)

    # --- 3. Stream answer + emit structured envelope on completion ---
    async def generate():
        full_answer = ""
        builder = StructuredResponseBuilder()

        # Evidence gate: if RAG returned nothing, refuse immediately
        if not rag_chunks:
            refusal = builder.refuse(body.message)
            yield f"data: {json.dumps({'content': refusal.answer, 'structured': refusal.model_dump(mode='json')})}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
            if body.session_id:
                await ws_svc.append_chat_message(body.session_id, "assistant", refusal.answer)
            return

        # Stream LLM response
        async for chunk in ai_svc.chat_stream(messages, context=context):
            full_answer += chunk
            yield f"data: {json.dumps({'content': chunk})}\n\n"

        # Build structured envelope from RAG chunks + answer
        structured = builder.build(full_answer, rag_chunks)
        yield f"data: {json.dumps({'structured': structured.model_dump(mode='json')})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

        if body.session_id:
            await ws_svc.append_chat_message(body.session_id, "assistant", full_answer)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


# ============================================================
# Summarize
# ============================================================


@ai_router.post("/summarize", response_model=dict, dependencies=[Depends(guard_ai_read)])
async def summarize(body: SummarizeRequest) -> dict:
    ai_svc = AIService()
    result = await ai_svc.summarize(body.text, body.max_words)
    return api_response(data={"summary": result})


# ============================================================
# Translate
# ============================================================


@ai_router.post("/translate", response_model=dict, dependencies=[Depends(guard_ai_read)])
async def translate(body: TranslateRequest) -> dict:
    ai_svc = AIService()
    result = await ai_svc.translate(body.text, body.target_lang)
    return api_response(data={"translation": result})


# ============================================================
# AI Compare
# ============================================================


@ai_router.post("/compare", response_model=dict, dependencies=[Depends(guard_ai_read)])
async def ai_compare(body: CompareRequest) -> dict:
    ai_svc = AIService()
    result = await ai_svc.ai_compare(body.source_text, body.target_text, body.source_label, body.target_label)
    return api_response(data={"comparison": result})


# ============================================================
# Workspace — Sessions
# ============================================================


@workspace_router.get("/sessions", response_model=dict, dependencies=[Depends(guard_workspace_read)])
async def list_sessions(
    current_user: str = Depends(get_current_user),
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> dict:
    svc = WorkspaceService(session)
    items = await svc.list_sessions(current_user)
    return api_response(data=[_session_dict(s) for s in items])


@workspace_router.post("/sessions", response_model=dict, dependencies=[Depends(guard_workspace_write)])
async def create_session(
    body: SessionCreateRequest,
    current_user: str = Depends(get_current_user),
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> dict:
    svc = WorkspaceService(session)
    obj = await svc.create_session(current_user, body.title)
    return api_response(data=_session_dict(obj), message="Created")


@workspace_router.get("/sessions/{session_id}", response_model=dict, dependencies=[Depends(guard_workspace_read)])
async def get_session_route(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
    current_user: str = Depends(get_current_user),
) -> dict:
    svc = WorkspaceService(session)
    obj = await svc.get_session(session_id)
    if obj is None or obj.user_id != current_user:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    return api_response(data=_session_dict(obj))


@workspace_router.patch("/sessions/{session_id}", response_model=dict, dependencies=[Depends(guard_workspace_write)])
async def update_session_route(
    session_id: UUID,
    body: SessionUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
    current_user: str = Depends(get_current_user),
) -> dict:
    svc = WorkspaceService(session)
    obj = await svc.get_session(session_id)
    if obj is None or obj.user_id != current_user:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    obj = await svc.update_session(
        session_id,
        title=body.title,
        active_entities=body.active_entities,
        context_notes=body.context_notes,
    )
    return api_response(data=_session_dict(obj), message="Updated")


@workspace_router.delete("/sessions/{session_id}", response_model=dict, dependencies=[Depends(guard_workspace_write)])
async def delete_session_route(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
    current_user: str = Depends(get_current_user),
) -> dict:
    svc = WorkspaceService(session)
    obj = await svc.get_session(session_id)
    if obj is None or obj.user_id != current_user:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    await svc.delete_session(session_id)
    return api_response(data=None, message="Deleted")


# ============================================================
# Workspace — Notes
# ============================================================


@workspace_router.get("/sessions/{session_id}/notes", response_model=dict, dependencies=[Depends(guard_workspace_read)])
async def list_notes(
    session_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
    current_user: str = Depends(get_current_user),
) -> dict:
    svc = WorkspaceService(session)
    s = await svc.get_session(session_id)
    if s is None or s.user_id != current_user:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    items = await svc.list_notes(session_id)
    return api_response(data=[_note_dict(n) for n in items])


@workspace_router.post("/sessions/{session_id}/notes", response_model=dict, dependencies=[Depends(guard_workspace_write)])
async def create_note(
    session_id: UUID,
    body: NoteCreateRequest,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
    current_user: str = Depends(get_current_user),
) -> dict:
    svc = WorkspaceService(session)
    s = await svc.get_session(session_id)
    if s is None or s.user_id != current_user:
        from fastapi import HTTPException
        raise HTTPException(404, "Session not found")
    note = await svc.create_note(session_id, body.content, body.entity_type, body.entity_id, body.tags)
    return api_response(data=_note_dict(note), message="Created")


@workspace_router.patch("/notes/{note_id}", response_model=dict, dependencies=[Depends(guard_workspace_write)])
async def update_note_route(
    note_id: UUID,
    body: NoteUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
    current_user: str = Depends(get_current_user),
) -> dict:
    svc = WorkspaceService(session)
    # Verify note belongs to user via its session ownership
    note = await svc.get_note_with_session(note_id)
    if note is None or note[1].user_id != current_user:
        from fastapi import HTTPException
        raise HTTPException(404, "Note not found")
    note = await svc.update_note(note_id, content=body.content, tags=body.tags)
    return api_response(data=_note_dict(note), message="Updated")


@workspace_router.delete("/notes/{note_id}", response_model=dict, dependencies=[Depends(guard_workspace_write)])
async def delete_note_route(
    note_id: UUID,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
    current_user: str = Depends(get_current_user),
) -> dict:
    svc = WorkspaceService(session)
    note = await svc.get_note_with_session(note_id)
    if note is None or note[1].user_id != current_user:
        from fastapi import HTTPException
        raise HTTPException(404, "Note not found")
    await svc.delete_note(note_id)
    return api_response(data=None, message="Deleted")


# ============================================================
# Helpers
# ============================================================


def _session_dict(s: Any) -> dict:
    active = None
    if s.active_entities:
        try:
            active = json.loads(s.active_entities)
        except (json.JSONDecodeError, TypeError):
            active = None

    return {
        "id": s.id,
        "title": s.title,
        "active_entities": active,
        "context_notes": s.context_notes,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _note_dict(n: Any) -> dict:
    return {
        "id": n.id,
        "session_id": n.session_id,
        "entity_type": n.entity_type,
        "entity_id": n.entity_id,
        "content": n.content,
        "tags": n.tags,
        "created_at": n.created_at.isoformat() if n.created_at else None,
        "updated_at": n.updated_at.isoformat() if n.updated_at else None,
    }
