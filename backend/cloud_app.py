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
import openai
import boto3
from botocore.exceptions import ClientError
import pinecone
from sentence_transformers import SentenceTransformer
import io
import hashlib

app = FastAPI(title="Synapse Cloud Backend", version="1.0.0")

# CORS
cors_origins_env = os.environ.get("CORS_ORIGINS", "")
allow_origins = [o.strip() for o in cors_origins_env.split(",") if o.strip()] or [
    "http://localhost:3000",
    "https://your-railway-app.railway.app",  # Update with your Railway domain
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = os.environ.get("PINECONE_ENVIRONMENT")
PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME", "synapse-kb")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN", "").strip() or None

# Initialize cloud services
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

if PINECONE_API_KEY:
    pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )
else:
    s3_client = None

# Initialize sentence transformer for embeddings
embedding_model = SentenceTransformer('BAAI/bge-base-en-v1.5')

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
    return {
        "ok": True,
        "services": {
            "openai": bool(OPENAI_API_KEY),
            "pinecone": bool(PINECONE_API_KEY),
            "s3": bool(s3_client),
        }
    }

@app.get("/config")
def get_config() -> Dict[str, Any]:
    return {
        "auto_rag": os.environ.get("AUTO_RAG", "false").lower() == "true",
        "rag_top_k": int(os.environ.get("RAG_TOP_K", "4")),
        "rag_max_chars": int(os.environ.get("RAG_MAX_CHARS", "1800")),
        "llm_provider": "openai" if OPENAI_API_KEY else "none",
        "vector_db": "pinecone" if PINECONE_API_KEY else "none",
        "storage": "s3" if s3_client else "none"
    }

@app.post("/config")
def set_config(body: Dict[str, Any], request: Request) -> Dict[str, Any]:
    _require_auth(request)
    
    allowed_keys = {"AUTO_RAG", "RAG_TOP_K", "RAG_MAX_CHARS"}
    updates = {}
    
    for key, value in body.items():
        if key in allowed_keys:
            os.environ[key] = str(value)
            updates[key] = value
    
    return {"updated": updates}

@app.post("/rag/preview")
def rag_preview(body: Dict[str, Any] = Body(...)) -> Dict[str, Any]:
    q = (body.get("query") or "").strip()
    if not q:
        raise HTTPException(status_code=400, detail={"error": {"code": "INVALID_INPUT", "detail": "query is required"}})
    
    auto_rag = body.get("auto_rag")
    if auto_rag is None:
        auto_rag = os.environ.get("AUTO_RAG", "false").lower() == "true"
    
    if not auto_rag:
        return {"chunks": [], "query": q, "auto_rag": False}
    
    if not PINECONE_API_KEY:
        return {"chunks": [], "query": q, "auto_rag": True, "error": "Vector database not configured"}
    
    try:
        # Get query embedding
        query_embedding = embedding_model.encode(q).tolist()
        
        # Search Pinecone
        index = pinecone.Index(PINECONE_INDEX_NAME)
        results = index.query(
            vector=query_embedding,
            top_k=int(os.environ.get("RAG_TOP_K", "4")),
            include_metadata=True
        )
        
        chunks = []
        for match in results.matches:
            if match.metadata:
                chunks.append({
                    "content": match.metadata.get("content", ""),
                    "source": match.metadata.get("source", ""),
                    "score": match.score
                })
        
        return {"chunks": chunks, "query": q, "auto_rag": True}
    
    except Exception as e:
        return {"chunks": [], "query": q, "auto_rag": True, "error": str(e)}

@app.get("/kb/stats")
def kb_stats() -> Dict[str, Any]:
    if not PINECONE_API_KEY:
        return {"error": "Vector database not configured"}
    
    try:
        index = pinecone.Index(PINECONE_INDEX_NAME)
        stats = index.describe_index_stats()
        return {
            "total_vectors": stats.total_vector_count,
            "dimension": stats.dimension,
            "index_name": PINECONE_INDEX_NAME
        }
    except Exception as e:
        return {"error": str(e)}

@app.post("/kb/upload")
async def kb_upload(request: Request, files: List[UploadFile] = File(...)) -> Dict[str, Any]:
    _require_auth(request)
    
    if not s3_client or not PINECONE_API_KEY:
        raise HTTPException(status_code=500, detail="Storage or vector database not configured")
    
    uploaded_files = []
    
    for file in files:
        try:
            # Read file content
            content = await file.read()
            content_text = content.decode('utf-8')
            
            # Generate file hash for unique ID
            file_hash = hashlib.md5(content).hexdigest()
            
            # Upload to S3
            s3_key = f"documents/{file_hash}_{file.filename}"
            s3_client.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=s3_key,
                Body=content,
                ContentType=file.content_type
            )
            
            # Create embeddings and store in Pinecone
            chunks = _create_chunks(content_text, 1000)  # 1000 char chunks
            
            index = pinecone.Index(PINECONE_INDEX_NAME)
            
            for i, chunk in enumerate(chunks):
                chunk_id = f"{file_hash}_{i}"
                chunk_embedding = embedding_model.encode(chunk).tolist()
                
                index.upsert(vectors=[{
                    "id": chunk_id,
                    "values": chunk_embedding,
                    "metadata": {
                        "content": chunk,
                        "source": file.filename,
                        "file_hash": file_hash,
                        "chunk_index": i
                    }
                }])
            
            uploaded_files.append({
                "filename": file.filename,
                "size": len(content),
                "chunks": len(chunks),
                "s3_key": s3_key
            })
            
        except Exception as e:
            uploaded_files.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return {"uploaded": uploaded_files}

def _create_chunks(text: str, chunk_size: int) -> List[str]:
    """Split text into chunks of specified size"""
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks

@app.post("/chat/stream")
async def chat_stream(body: StreamChatBody, request: Request) -> Response:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API not configured")
    
    messages = body.messages
    temperature = body.temperature or 0.7
    top_p = body.top_p or 1.0
    max_tokens = body.max_tokens or 1000
    auto_rag = body.auto_rag
    
    if auto_rag is None:
        auto_rag = os.environ.get("AUTO_RAG", "false").lower() == "true"
    
    # If RAG is enabled, enhance the last user message with context
    if auto_rag and messages and messages[-1]["role"] == "user":
        try:
            query = messages[-1]["content"]
            query_embedding = embedding_model.encode(query).tolist()
            
            if PINECONE_API_KEY:
                index = pinecone.Index(PINECONE_INDEX_NAME)
                results = index.query(
                    vector=query_embedding,
                    top_k=int(os.environ.get("RAG_TOP_K", "4")),
                    include_metadata=True
                )
                
                context_chunks = []
                for match in results.matches:
                    if match.metadata:
                        context_chunks.append(match.metadata.get("content", ""))
                
                if context_chunks:
                    context_text = "\n\n".join(context_chunks)
                    enhanced_message = f"Context:\n{context_text}\n\nUser question: {query}"
                    messages[-1]["content"] = enhanced_message
        except Exception as e:
            # Continue without RAG if there's an error
            pass
    
    def generate_response():
        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                stream=True
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield f"data: {json.dumps({'content': chunk.choices[0].delta.content})}\n\n"
            
            yield f"data: {json.dumps({'done': True})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_response(),
        media_type="text/plain",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
    )

@app.post("/chat")
async def chat(body: StreamChatBody, request: Request) -> Dict[str, Any]:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OpenAI API not configured")
    
    messages = body.messages
    temperature = body.temperature or 0.7
    top_p = body.top_p or 1.0
    max_tokens = body.max_tokens or 1000
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens
        )
        
        return {
            "response": response.choices[0].message.content,
            "usage": response.usage.dict() if response.usage else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "9000")))
