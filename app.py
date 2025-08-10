#!/usr/bin/env python3
import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from fastapi import FastAPI, Query, Body, Request, Response, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator

# We reuse existing logic from backend.chat_core
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.chat_core import core as cs
from backend.chat_core import rag as raglib
from backend.chat_core.guardian import guard_inbound, guard_outbound


app = FastAPI(title="my_friend backend", version="0.2.0")

# CORS
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] or [
    "http://127.0.0.1:8501",
    "http://localhost:8501",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "").strip() or None


def _require_auth(req: Request):
    if not AUTH_TOKEN:
        return
    auth = req.headers.get("authorization") or req.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer ") or auth.split(" ", 1)[1].strip() != AUTH_TOKEN:
        raise HTTPException(status_code=401, detail={"error": {"code": "UNAUTHORIZED", "detail": "Missing/invalid token"}})


class StreamChatBody(BaseModel):
    messages: List[Dict[str, Any]]  # Allow additional fields but validate role/content
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    auto_rag: Optional[bool] = None

    @validator('messages')
    def validate_messages(cls, v):
        """Validate that each message has required string fields."""
        for i, msg in enumerate(v):
            if not isinstance(msg, dict):
                raise ValueError(f"Message {i} must be a dictionary")
            if 'role' not in msg or not isinstance(msg['role'], str):
                raise ValueError(f"Message {i} must have a string 'role' field")
            if 'content' not in msg or not isinstance(msg['content'], str):
                raise ValueError(f"Message {i} must have a string 'content' field")
        return v


@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True}


@app.get("/rag/preview")
def rag_preview_get(q: str = Query(...), auto_rag: Optional[bool] = Query(None)) -> Dict[str, Any]:
    """GET endpoint for RAG preview - accepts query parameters."""
    return _rag_preview_logic(q, auto_rag)


@app.post("/rag/preview")
def rag_preview(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    """POST endpoint for RAG preview - accepts request body."""
    q = (body.get("query") or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_INPUT", "detail": "query is required"}})
    
    auto_rag = body.get("auto_rag")
    return _rag_preview_logic(q, auto_rag)


def _rag_preview_logic(q: str, auto_rag: Optional[bool] = None) -> Dict[str, Any]:
    """Shared logic for RAG preview functionality."""
    # Check if RAG is enabled - allow override via parameter
    use_rag = auto_rag if auto_rag is not None else cs.config.get("auto_rag", os.environ.get("AUTO_RAG", "false").lower() in ("true", "1", "yes"))
    if not use_rag:
        return {"chunks": [], "message": "RAG is currently disabled"}
    
    # Prefer advanced retriever if available
    chunks = []
    retr = raglib.get_retriever()
    if retr:
        try:
            hits = retr.search(q, top_k=int(cs.config.get("rag_top_k", 4)))
            for h in hits:
                chunks.append({
                    "title": (h.get("title") or Path(h.get("doc", "")).name),
                    "doc": h.get("doc", ""),
                    "snippet": (h.get("text", "")[:500]).strip(),
                })
        except Exception:
            chunks = []
    if not chunks:
        # fallback to lightweight KB only if RAG is enabled
        top = _top_chunks_local(q, top_k=int(cs.config.get("rag_top_k", 4)))
        chunks = [{"title": t["source"], "doc": t["source"], "snippet": t["text"][:500]} for t in top]
    return {"chunks": chunks}


def _top_chunks_local(query: str, top_k: int) -> List[Dict[str, str]]:
    # rank using raglib internals
    # only prime index if KB_INDEX is empty
    if not raglib.KB_INDEX:  # type: ignore
        raglib.build_context_block("prime")
    # reuse KB_INDEX via private access
    ranked = sorted(raglib.KB_INDEX, key=lambda ch: raglib._score_chunk(query, ch["text"]), reverse=True)  # type: ignore
    ranked = [r for r in ranked if raglib._score_chunk(query, r["text"]) > 0][:top_k]  # type: ignore
    return ranked


@app.get("/config")
def get_config() -> Dict[str, Any]:
    cfg = dict(cs.config)
    cfg.update({
        "emb_model": os.environ.get("EMB_MODEL", "BAAI/bge-small-en-v1.5"),
        "ctx_size": int(os.environ.get("CTX_SIZE", 32768)),
        "version": 1,
    })
    return cfg


@app.post("/config")
def set_config(body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    _require_auth(request)
    allowed_float = {"temperature", "top_p"}
    allowed_int = {"max_tokens", "rag_top_k", "rag_max_chars"}
    allowed_bool = {"auto_rag", "auto_resume", "auto_mem", "guardian_enabled", "ephemeral_mode"}

    for k, v in body.items():
        if k in allowed_float:
            try:
                cs.config[k] = float(v)
            except Exception:
                raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_INPUT", "detail": f"{k} must be float"}})
        elif k in allowed_int:
            try:
                cs.config[k] = int(v)
            except Exception:
                raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_INPUT", "detail": f"{k} must be integer"}})
        elif k in allowed_bool:
            cs.config[k] = bool(v) if isinstance(v, bool) else str(v).lower() in ("1", "true", "yes", "on")
        else:
            # ignore unknowns
            continue
    cs.save_config()
    return get_config()


@app.post("/kb/reload")
def kb_reload(request: Request) -> Dict[str, Any]:
    _require_auth(request)
    # Run indexer script located under backend/chat_core
    import subprocess
    script = (ROOT / "backend" / "chat_core" / "index_kb.py").resolve()
    if not script.is_file():
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "detail": str(script)}})
    try:
        subprocess.run([sys.executable, str(script)], check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "INDEX_FAILED", "detail": str(e)}})
    return kb_stats()


def _rebuild_kb() -> Dict[str, Any]:
    import subprocess
    script = (ROOT / "backend" / "chat_core" / "index_kb.py").resolve()
    if not script.is_file():
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "detail": str(script)}})
    try:
        subprocess.run([sys.executable, str(script)], check=True)
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail={"error": {"code": "INDEX_FAILED", "detail": str(e)}})
    return kb_stats()

@app.get("/kb/stats")
def kb_stats() -> Dict[str, Any]:
    kb = ROOT / "backend" / "chat_core" / "kb"
    docs_dir = (ROOT / "workdir" / "docs").resolve()
    meta = kb / "meta.json"
    chunks = 0
    updated_at = None
    if meta.is_file():
        try:
            data = json.loads(meta.read_text("utf-8"))
            chunks = len(data)
            updated_at = datetime.fromtimestamp(meta.stat().st_mtime, tz=timezone.utc).isoformat()
        except Exception:
            chunks = 0
    # Count docs
    total_files = 0
    try:
        if docs_dir.is_dir():
            total_files = sum(1 for p in docs_dir.rglob("*") if p.is_file())
    except Exception:
        total_files = 0
    return {
        "index_path": str(kb / "faiss.index"),
        "chunks": chunks,
        "emb_model": os.environ.get("EMB_MODEL", "BAAI/bge-small-en-v1.5"),
        "updated_at": updated_at,
        "total_files": total_files,
    }


@app.post("/kb/upload")
async def kb_upload(request: Request, files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    _require_auth(request)
    docs_dir = (ROOT / "workdir" / "docs").resolve()
    docs_dir.mkdir(parents=True, exist_ok=True)
    saved: List[str] = []
    for f in files:
        try:
            dest = docs_dir / Path(f.filename).name
            content = await f.read()
            dest.write_bytes(content)
            saved.append(dest.name)
        except Exception as e:
            raise HTTPException(status_code=500, detail={"error": {"code": "UPLOAD_FAILED", "detail": str(e)}})
    stats = _rebuild_kb()
    return {"saved": saved, "docs_dir": str(docs_dir), "kb": stats}


@app.get("/kb/files")
def kb_files(request: Request) -> Dict[str, Any]:
    _require_auth(request)
    docs_dir = (ROOT / "workdir" / "docs").resolve()
    items: List[Dict[str, Any]] = []
    if docs_dir.is_dir():
        for p in sorted(docs_dir.iterdir(), key=lambda x: x.name.lower()):
            if not p.is_file():
                continue
            try:
                st = p.stat()
                items.append({
                    "name": p.name,
                    "size": st.st_size,
                    "mtime": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
                })
            except Exception:
                continue
    return {"files": items}


@app.post("/kb/delete")
def kb_delete(body: Dict[str, Any] = Body(...), request: Request = None) -> Dict[str, Any]:
    _require_auth(request)
    docs_dir = (ROOT / "workdir" / "docs").resolve()
    names: List[str] = list(body.get("files") or [])
    deleted: List[str] = []
    missing: List[str] = []
    failed: List[Dict[str, str]] = []
    for name in names:
        # Prevent path traversal; restrict to base name only
        safe_name = Path(name).name
        target = (docs_dir / safe_name).resolve()
        try:
            if not str(target).startswith(str(docs_dir)):
                failed.append({"name": safe_name, "error": "invalid path"})
                continue
            if not target.exists():
                missing.append(safe_name)
                continue
            if target.is_file():
                target.unlink()
                deleted.append(safe_name)
        except Exception as e:
            failed.append({"name": safe_name, "error": str(e)})
    kb: Dict[str, Any] = {}
    if deleted:
        kb = _rebuild_kb()
    return {"deleted": deleted, "missing": missing, "failed": failed, "kb": kb}


def _sse_header(chunk: Dict[str, Any]) -> str:
    return f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"


@app.post("/chat/stream")
async def chat_stream(body: StreamChatBody, request: Request) -> Response:
    # Optional auth for streaming as well
    _require_auth(request)

    # Build messages; if auto_rag, prepend transient system context
    user_text = ""
    for m in body.messages:
        if m.get("role") == "user":
            user_text = m.get("content", "")
    # Guard inbound first to get safe text
    ok_in, safe_user, _ = guard_inbound(user_text)
    if not ok_in:
        safe_user = cs.config.get("guard_refusal_text", "I can't help with that.")
    
    # Check if RAG mode has changed and clear history if needed
    use_rag = cs.config.get("auto_rag", os.environ.get("AUTO_RAG", "false").lower() in ("true", "1", "yes")) if body.auto_rag is None else bool(body.auto_rag)
    previous_rag_state = getattr(cs, '_previous_rag_state', None)
    
    # If RAG was enabled before but is now disabled, clear the history
    if previous_rag_state is True and not use_rag:
        cs.history = [cs.history[0]] if cs.history else []  # Keep only system message
        cs.save_history_last(cs.history)
        # st.info("Chat history cleared - RAG mode disabled") # This line was commented out in the original file
    
    # Update the stored RAG state
    cs._previous_rag_state = use_rag
    
    # Create a transient history including the current user message
    history_for_call = cs.history + [{"role": "user", "content": safe_user}]

    turn_context = ""
    sources_payload: List[Dict[str, str]] = []
    
    # Only use RAG if explicitly enabled
    if use_rag:
        turn_context = raglib.build_context_block(safe_user or "")
        # also build sources list for trailer
        retr = raglib.get_retriever()
        if retr:
            try:
                hits = retr.search(safe_user or "", top_k=int(cs.config.get("rag_top_k", 4)))
                for h in hits:
                    # Enhanced source information with relevance scoring
                    doc_name = h.get("doc", "")
                    title = h.get("title") or Path(doc_name).name
                    text = h.get("text", "")
                    
                    # Get comprehensive scoring information
                    relevance_score = h.get("score_total", 0.0)
                    confidence = "High" if relevance_score > 0.7 else "Medium" if relevance_score > 0.4 else "Low"
                    
                    # Extract better context - get sentences around key terms
                    snippet = text[:800].strip()  # Longer snippet
                    if len(text) > 800:
                        snippet += "..."
                    
                    # Add metadata
                    sources_payload.append({
                        "title": title,
                        "doc": doc_name,
                        "snippet": snippet,
                        "relevance_score": round(relevance_score, 3),
                        "confidence": confidence,
                        "chunk_id": h.get("id", ""),
                        "page": h.get("page", ""),
                        "section": h.get("section", ""),
                        "word_count": len(text.split()),
                        "vector_score": round(h.get("score_vec_norm", 0.0), 3),
                        "bm25_score": round(h.get("score_bm25_norm", 0.0), 3),
                        "title_boost": round(h.get("score_title", 0.0), 3)
                    })
            except Exception:
                sources_payload = []
        if not sources_payload:
            # Only fallback to local KB if RAG is enabled
            top = _top_chunks_local(safe_user or "", top_k=int(cs.config.get("rag_top_k", 4)))
            sources_payload = [{"title": t["source"], "doc": t["source"], "snippet": t["text"][:500]} for t in top]
    else:
        # When RAG is disabled, ensure no RAG context is used
        turn_context = ""
        sources_payload = []

    if turn_context:
        messages = cs.build_messages([history_for_call[0]] + [{"role": "system", "content": turn_context}] + history_for_call[1:])
    else:
        messages = cs.build_messages(history_for_call)

    # persist current user turn (unless in ephemeral mode)
    if not cs.config.get("ephemeral_mode", False):
        cs.history.append({"role": "user", "content": safe_user})
        cs.save_history_last(cs.history)

    # When RAG is disabled, add explicit instruction to not reference knowledge base
    if not turn_context and not use_rag:
        no_rag_instruction = "IMPORTANT: Do not reference or mention any knowledge base documents, uploaded files, or external sources. Respond based only on your general knowledge and the conversation history."
        messages = cs.build_messages([history_for_call[0]] + [{"role": "system", "content": no_rag_instruction}] + history_for_call[1:])

    def iterator():
        try:
            # already applied inbound guard above
            # stream and redact each chunk
            for tok in cs.stream_chat(messages, max_tokens=body.max_tokens, temp=body.temperature, top_p=body.top_p):
                safe_tok = guard_outbound(tok)
                if not safe_tok:
                    continue
                yield _sse_header({"delta": safe_tok, "done": False})
                # No sleep for maximum performance
        except Exception as e:
            yield _sse_header({"error": str(e), "done": True})
            return
        # at end, persist assistant message and send sources
        # We do not reconstruct full text here; clients typically do
        yield _sse_header({"done": True, "sources": sources_payload})

    return StreamingResponse(iterator(), media_type="text/event-stream")


@app.post("/chat")
async def chat(body: StreamChatBody, request: Request) -> Dict[str, Any]:
    """Non-streaming chat endpoint as fallback for /chat/stream"""
    _require_auth(request)
    
    # Build messages; if auto_rag, prepend transient system context
    user_text = ""
    for m in body.messages:
        if m.get("role") == "user":
            user_text = m.get("content", "")
    
    # Guard inbound first to get safe text
    ok_in, safe_user, _ = guard_inbound(user_text)
    if not ok_in:
        safe_user = cs.config.get("guard_refusal_text", "I can't help with that.")
    
    # Check if RAG mode has changed and clear history if needed
    use_rag = cs.config.get("auto_rag", os.environ.get("AUTO_RAG", "false").lower() in ("true", "1", "yes")) if body.auto_rag is None else bool(body.auto_rag)
    previous_rag_state = getattr(cs, '_previous_rag_state', None)
    
    # If RAG was enabled before but is now disabled, clear the history
    if previous_rag_state is True and not use_rag:
        cs.history = [cs.history[0]] if cs.history else []  # Keep only system message
        cs.save_history_last(cs.history)
    
    # Update the stored RAG state
    cs._previous_rag_state = use_rag
    
    # Create a transient history including the current user message
    history_for_call = cs.history + [{"role": "user", "content": safe_user}]

    turn_context = ""
    sources_payload: List[Dict[str, str]] = []
    
    # Only use RAG if explicitly enabled
    if use_rag:
        turn_context = raglib.build_context_block(safe_user or "")
        # also build sources list for trailer
        retr = raglib.get_retriever()
        if retr:
            try:
                hits = retr.search(safe_user or "", top_k=int(cs.config.get("rag_top_k", 4)))
                for h in hits:
                    # Enhanced source information with relevance scoring
                    doc_name = h.get("doc", "")
                    title = h.get("title") or Path(doc_name).name
                    text = h.get("text", "")
                    
                    # Get comprehensive scoring information
                    relevance_score = h.get("score_total", 0.0)
                    confidence = "High" if relevance_score > 0.7 else "Medium" if relevance_score > 0.4 else "Low"
                    
                    # Extract better context - get sentences around key terms
                    snippet = text[:800].strip()  # Longer snippet
                    if len(text) > 800:
                        snippet += "..."
                    
                    # Add metadata
                    sources_payload.append({
                        "title": title,
                        "doc": doc_name,
                        "snippet": snippet,
                        "relevance_score": round(relevance_score, 3),
                        "confidence": confidence,
                        "chunk_id": h.get("id", ""),
                        "page": h.get("page", ""),
                        "section": h.get("section", ""),
                        "word_count": len(text.split()),
                        "vector_score": round(h.get("score_vec_norm", 0.0), 3),
                        "bm25_score": round(h.get("score_bm25_norm", 0.0), 3),
                        "title_boost": round(h.get("score_title", 0.0), 3)
                    })
            except Exception:
                sources_payload = []
        if not sources_payload:
            # Only fallback to local KB if RAG is enabled
            top = _top_chunks_local(safe_user or "", top_k=int(cs.config.get("rag_top_k", 4)))
            sources_payload = [{"title": t["source"], "doc": t["source"], "snippet": t["text"][:500]} for t in top]
    else:
        # When RAG is disabled, ensure no RAG context is used
        turn_context = ""
        sources_payload = []

    if turn_context:
        messages = cs.build_messages([history_for_call[0]] + [{"role": "system", "content": turn_context}] + history_for_call[1:])
    else:
        messages = cs.build_messages(history_for_call)

    # persist current user turn (unless in ephemeral mode)
    if not cs.config.get("ephemeral_mode", False):
        cs.history.append({"role": "user", "content": safe_user})
        cs.save_history_last(cs.history)

    # When RAG is disabled, add explicit instruction to not reference knowledge base
    if not turn_context and not use_rag:
        no_rag_instruction = "IMPORTANT: Do not reference or mention any knowledge base documents, uploaded files, or external sources. Respond based only on your general knowledge and the conversation history."
        messages = cs.build_messages([history_for_call[0]] + [{"role": "system", "content": no_rag_instruction}] + history_for_call[1:])

    try:
        # Collect the full response
        full_response = ""
        for tok in cs.stream_chat(messages, max_tokens=body.max_tokens, temp=body.temperature, top_p=body.top_p):
            safe_tok = guard_outbound(tok)
            if safe_tok:
                full_response += safe_tok
        
        return {
            "reply": full_response,
            "sources": sources_payload,
            "done": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 8000)), reload=False)


