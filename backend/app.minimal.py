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

app = FastAPI(title="Synapse Backend (Minimal)", version="0.3.0")

# CORS
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] or [
    "http://127.0.0.1:8501",
    "http://localhost:8501",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
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
    messages: List[Dict[str, Any]]
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    auto_rag: Optional[bool] = None

    @validator('messages')
    def validate_messages(cls, v):
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

@app.get("/config")
def get_config() -> Dict[str, Any]:
    """Get configuration - minimal version without heavy dependencies"""
    return {
        "version": 2,
        "auto_rag": False,
        "rag_top_k": 4,
        "rag_max_chars": 1800,
        "max_tokens": 2048,
        "temperature": 0.7,
        "top_p": 0.95,
        "guardian_enabled": False,
        "note": "Minimal backend - RAG and heavy ML features disabled for Railway deployment"
    }

@app.post("/config")
def set_config(body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Set configuration - minimal version"""
    _require_auth(request)
    # In minimal mode, just return success
    return {"status": "success", "message": "Config updated (minimal mode)"}

@app.post("/rag/toggle")
def toggle_rag(request: Request) -> Dict[str, Any]:
    """Toggle RAG - disabled in minimal mode"""
    _require_auth(request)
    return {"status": "disabled", "message": "RAG is disabled in minimal mode"}

@app.post("/rag/set")
def set_rag_state(body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Set RAG state - disabled in minimal mode"""
    _require_auth(request)
    return {"status": "disabled", "message": "RAG is disabled in minimal mode"}

@app.post("/guardian/toggle")
def toggle_guardian(request: Request) -> Dict[str, Any]:
    """Toggle guardian - disabled in minimal mode"""
    _require_auth(request)
    return {"status": "disabled", "message": "Guardian is disabled in minimal mode"}

@app.post("/guardian/set")
def set_guardian_state(body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    """Set guardian state - disabled in minimal mode"""
    _require_auth(request)
    return {"status": "disabled", "message": "Guardian is disabled in minimal mode"}

@app.post("/kb/clear")
def clear_knowledge_base(request: Request) -> Dict[str, Any]:
    """Clear knowledge base - disabled in minimal mode"""
    _require_auth(request)
    return {"status": "disabled", "message": "Knowledge base is disabled in minimal mode"}

@app.post("/chat/clear")
def clear_chat_history(request: Request) -> Dict[str, Any]:
    """Clear chat history - minimal version"""
    _require_auth(request)
    return {"status": "success", "message": "Chat history cleared"}

@app.post("/kb/reload")
def kb_reload(request: Request) -> Dict[str, Any]:
    """Reload knowledge base - disabled in minimal mode"""
    _require_auth(request)
    return {"status": "disabled", "message": "Knowledge base is disabled in minimal mode"}

@app.get("/kb/stats")
def kb_stats(request: Request) -> Dict[str, Any]:
    """Get knowledge base stats - minimal version"""
    return {
        "index_path": "disabled",
        "chunks": 0,
        "emb_model": "disabled",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "total_files": 0,
        "note": "Knowledge base disabled in minimal mode"
    }

@app.post("/kb/upload")
async def kb_upload(request: Request, files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    """Upload files to knowledge base - disabled in minimal mode"""
    _require_auth(request)
    return {"status": "disabled", "message": "File upload is disabled in minimal mode"}

@app.get("/kb/files")
def kb_files(request: Request) -> Dict[str, Any]:
    """Get knowledge base files - minimal version"""
    return {
        "files": [],
        "note": "Knowledge base disabled in minimal mode"
    }

@app.post("/kb/delete")
def kb_delete(body: Dict[str, Any], request: Request = None) -> Dict[str, Any]:
    """Delete file from knowledge base - disabled in minimal mode"""
    if request:
        _require_auth(request)
    return {"status": "disabled", "message": "File deletion is disabled in minimal mode"}

@app.post("/chat/stream")
async def chat_stream(body: StreamChatBody, request: Request) -> Response:
    """Stream chat response - minimal version using external API"""
    _require_auth(request)
    
    # In minimal mode, we'll just echo back a simple response
    # In production, you'd connect to an external LLM API
    
    def iterator():
        response_data = {
            "type": "message",
            "content": "Hello! This is Synapse running in minimal mode. RAG and heavy ML features are disabled for Railway deployment. You can still chat, but responses will be basic.",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        yield f"data: {json.dumps(response_data)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        iterator(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/chat")
async def chat(body: StreamChatBody, request: Request) -> Dict[str, Any]:
    """Regular chat endpoint - minimal version"""
    _require_auth(request)
    
    # Simple echo response for minimal mode
    return {
        "response": "Hello! This is Synapse running in minimal mode. RAG and heavy ML features are disabled for Railway deployment.",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": "minimal"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
