"""
Vercel API entry point for Synapse
This file serves as the main entry point for Vercel deployment
"""
import os
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, Query, Body, Request, Response, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, validator

# Create FastAPI app
app = FastAPI(title="Synapse API", version="1.0.0")

# CORS
cors_origins_env = os.environ.get("CORS_ORIGINS", "*")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] or ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Models
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

# Routes
@app.get("/")
def root():
    return {"message": "Synapse API is running on Vercel!", "status": "healthy"}

@app.get("/health")
def health() -> Dict[str, Any]:
    return {"ok": True, "deployment": "vercel"}

@app.get("/config")
def get_config() -> Dict[str, Any]:
    """Get current configuration"""
    return {
        "version": "1.0.0",
        "deployment": "vercel",
        "features": {
            "rag": False,
            "guardian": False,
            "local_llm": False,
            "file_upload": False
        },
        "limitations": [
            "No local file storage",
            "No persistent memory",
            "No local AI models",
            "30 second timeout limit"
        ]
    }

@app.post("/chat/stream")
async def chat_stream(body: StreamChatBody, request: Request) -> Response:
    """Streaming chat endpoint - simplified for Vercel"""
    
    # Validate input
    if not body.messages:
        raise HTTPException(status_code=400, detail="Messages are required")
    
    # Get the last user message
    last_message = body.messages[-1]
    if last_message.get("role") != "user":
        raise HTTPException(status_code=400, detail="Last message must be from user")
    
    user_content = last_message.get("content", "")
    
    # Simple response for Vercel deployment
    response_text = f"I'm Synapse running on Vercel! You said: {user_content}\n\nNote: This is a simplified deployment. For full functionality, consider self-hosting or using alternative platforms like Railway or DigitalOcean."
    
    def generate_response():
        words = response_text.split()
        for i, word in enumerate(words):
            chunk = {
                "id": f"vercel_{int(time.time() * 1000)}_{i}",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "synapse-vercel",
                "choices": [{
                    "index": 0,
                    "delta": {"content": word + " "},
                    "finish_reason": None
                }]
            }
            yield f"data: {json.dumps(chunk)}\n\n"
        
        # Final chunk
        final_chunk = {
            "id": f"vercel_{int(time.time() * 1000)}_final",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "synapse-vercel",
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/plain; charset=utf-8"
        }
    )

@app.post("/chat")
async def chat(body: StreamChatBody, request: Request) -> Dict[str, Any]:
    """Non-streaming chat endpoint - simplified for Vercel"""
    
    if not body.messages:
        raise HTTPException(status_code=400, detail="Messages are required")
    
    last_message = body.messages[-1]
    user_content = last_message.get("content", "")
    
    return {
        "id": f"vercel_{int(time.time() * 1000)}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "synapse-vercel",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": f"I'm Synapse running on Vercel! You said: {user_content}\n\nNote: This is a simplified deployment. For full functionality, consider self-hosting or using alternative platforms like Railway or DigitalOcean."
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": len(user_content.split()),
            "completion_tokens": 20,
            "total_tokens": len(user_content.split()) + 20
        }
    }

# Export for Vercel
handler = app
