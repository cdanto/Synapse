#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")"/.. && pwd)"
if [[ -f "$ROOT/.venv/bin/activate" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
fi

# LLM server endpoint + model label (match llama-server model)
export LLAMA_URL="${LLAMA_URL:-http://127.0.0.1:8080/v1/chat/completions}"
export LLAMA_MODEL="${LLAMA_MODEL:-qwen2.5-3b-instruct-q4_k_m}"

# Embedding model (must match when you built the index)
export EMB_MODEL="${EMB_MODEL:-BAAI/bge-base-en-v1.5}"

# Retriever knobs
export RAG_ALPHA="${RAG_ALPHA:-0.6}"
export RAG_VEC_K="${RAG_VEC_K:-64}"
export RAG_BM25_K="${RAG_BM25_K:-64}"
export RAG_MMR_LAMBDA="${RAG_MMR_LAMBDA:-0.3}"
export RAG_MMR_POOL="${RAG_MMR_POOL:-24}"
# Optional cross-encoder reranker:
# export RAG_RERANKER="cross-encoder/ms-marco-MiniLM-L-6-v2"
# export RAG_RERANK_FROM=40

# Rebuild index (fast if docs unchanged)
python3 "$ROOT/backend/chat_core/index_kb.py"

# Start chat (your chat_stream.py is in root)
python3 "$ROOT/chat_stream.py"