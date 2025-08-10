# Synapse

**Synapse** is a **100% private, local-first AI chat assistant** that runs entirely on your own hardware. Unlike cloud-based AI services, Synapse ensures your conversations, documents, and data never leave your local network.

## 🚀 What Makes Synapse Special?

- **🔒 Complete Privacy**: Everything runs locally - no data sent to external servers
- **🌐 No API Keys Required**: No need for OpenAI, Anthropic, or other cloud API keys
- **📚 Built-in Knowledge Base**: Upload your documents and chat with them using RAG (Retrieval-Augmented Generation)
- **💻 Local AI Models**: Connect to local LLM servers like llama.cpp for private AI conversations
- **🎯 Enterprise Ready**: Optional content filtering and policy enforcement
- **📱 Modern Web Interface**: Beautiful Streamlit UI with real-time streaming chat
- **🔧 Fully Customizable**: Modular architecture for easy modification and extension

## 🎯 Perfect For:

- **Businesses** handling sensitive documents and conversations
- **Researchers** working with confidential data
- **Privacy-conscious individuals** who want AI assistance without cloud dependencies
- **Organizations** requiring full control over their AI infrastructure
- **Offline environments** where internet access is limited or restricted

## Project layout

```text
Synapse/
  backend/
    app.py                 # FastAPI server (port 9000)
    chat_core/             # Core chat/RAG/guardian logic
      core.py
      rag.py
      guardian.py
      kb/
        index_kb.py        # Build FAISS index from documents
        retriever.py       # Hybrid/FAISS retriever
        build_titles.py    # Optional title vectors
    requirements.txt
    start_backend.sh
  frontend/
    app.py                 # Streamlit UI (port 8501)
    api/backend.py         # HTTP client for backend
    components/            # UI components
    requirements.txt
    start_frontend.sh
  scripts/
    start_llama.sh         # Run llama.cpp HTTP server (port 8080 by default)
    start_chat.sh          # CLI chat to the model (minimal)
    start_rag.sh           # CLI chat + RAG (advanced)
    restore_seed.sh        # Restore encrypted seed (simple)
    restore.sh             # Restore encrypted seed (advanced)
    watchdog.sh            # Sample watchdog for llama server
  guard_proxy.py           # Optional guard/redaction proxy for downstream LLMs
  chat_stream.py           # CLI chat program used by scripts
  workdir/                 # Runtime data (history, kb, logs)
  config.yml               # Seed configuration (for restore scripts)
  requirements.txt         # Extra libs (embedding/indexing)
  .env                     # Environment configuration (copy from env.example)
  env.example              # Example environment configuration
  README.md
```

## Requirements

- **Operating System**: macOS/Linux
- **Python**: 3.10+ 
- **Local AI Model**: Optional `llama.cpp` server for running open-source models locally
- **Internet**: Only required for initial setup (downloading Python packages and models)

## 💻 Hardware Requirements

### Minimum Requirements
- **RAM**: 8GB (16GB recommended for RAG operations)
- **Storage**: 10GB free space (more for large document collections)
- **CPU**: Multi-core processor (Intel i5/AMD Ryzen 5 or better)
- **GPU**: Optional but recommended for AI model inference

### Recommended for Production Use
- **RAM**: 16GB+ (32GB for large knowledge bases)
- **Storage**: 50GB+ SSD storage for documents and indexes
- **CPU**: Intel i7/AMD Ryzen 7 or better
- **GPU**: NVIDIA GPU with 8GB+ VRAM (for CUDA acceleration) or Apple Silicon (for Metal acceleration)

### For Large Language Models
- **RAM**: 32GB+ (for 7B+ parameter models)
- **GPU**: NVIDIA RTX 3080+ or equivalent for optimal performance
- **Storage**: 100GB+ for model files and indexes

## 🔐 Privacy & Security Features

- **Zero External Dependencies**: No cloud APIs, no external services, no data transmission
- **Local Data Storage**: All conversations, documents, and indexes stored on your hardware
- **Network Isolation**: Can run completely offline once set up
- **Optional Authentication**: Built-in token-based auth for multi-user environments
- **Content Filtering**: Optional guardian system for policy enforcement

## Installation

### Prerequisites

1. **Python 3.10+**: Ensure you have Python 3.10 or higher installed
   ```bash
   python3 --version
   ```

2. **Git**: Clone the repository
   ```bash
   git clone <your-repo-url>
   cd Synapse
   ```

3. **Environment Setup**: Copy and configure the environment file
   ```bash
   cp env.example .env
   # Edit .env to customize your configuration
   ```

### Virtual Environment Setup (.venv)

**Important**: Synapse uses a Python virtual environment (`.venv`) to isolate dependencies and avoid conflicts with your system Python installation.

1. **Create Virtual Environment**: Create a new virtual environment in the project directory
   ```bash
   python3 -m venv .venv
   ```

2. **Activate Virtual Environment**: Activate the virtual environment before installing dependencies or running the application
   
   **On macOS/Linux:**
   ```bash
   source .venv/bin/activate
   ```
   
   **On Windows:**
   ```bash
   .venv\Scripts\activate
   ```

3. **Verify Activation**: You should see `(.venv)` at the beginning of your command prompt
   ```bash
   (.venv) user@machine:~/Synapse$
   ```

4. **Deactivate When Done**: When you're finished working with Synapse, you can deactivate the virtual environment
   ```bash
   deactivate
   ```

**Note**: You'll need to activate the virtual environment each time you open a new terminal session to work with Synapse.

### Install Dependencies

**Make sure your virtual environment is activated** (you should see `(.venv)` in your prompt), then install dependencies:

1. **Backend Dependencies**: Core FastAPI server and chat functionality
   ```bash
   pip install -r backend/requirements.txt
   ```

2. **Frontend Dependencies**: Streamlit UI components
   ```bash
   pip install -r frontend/requirements.txt
   ```

3. **RAG & Indexing Dependencies**: Document processing and vector search
   ```bash
   pip install -r requirements.txt
   ```

### Optional: Install llama.cpp

For local LLM inference, you'll need llama.cpp:

```bash
# Clone and build llama.cpp
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make clean
make LLAMA_CUBLAS=1  # Enable CUDA if available
make LLAMA_METAL=1   # Enable Metal on macOS

# Download a model (example: Llama 2 7B)
wget https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf
```

## Quick start (local)

1. **Create and activate virtual environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r backend/requirements.txt
   pip install -r frontend/requirements.txt
   pip install -r requirements.txt    # extra libs for RAG/indexing
   ```

3. **Configure environment** (required for proper setup):
   ```bash
   cp env.example .env
   # Edit .env to customize your settings
   # This file contains your local configuration and is NOT committed to git
   ```

3. **Start an LLM server (llama.cpp)**. Adjust paths inside `scripts/start_llama.sh` or export env vars:
   ```bash
   bash scripts/start_llama.sh   # defaults to 127.0.0.1:8080
   ```

4. **Start the backend API**:
   ```bash
   bash backend/start_backend.sh   # serves on http://127.0.0.1:9000
   ```

5. **Start the frontend UI**:
   ```bash
   bash frontend/start_frontend.sh
   # open http://127.0.0.1:8501
   ```

**Important**: Keep your virtual environment activated while running Synapse. If you open a new terminal, remember to activate it again with `source .venv/bin/activate`.

If you set `AUTH_TOKEN` for the backend, the frontend must also send a bearer token. By default `AUTH_TOKEN` is unset (no auth required in local dev).

## 🔧 Environment Configuration

**⚠️ Important**: Synapse requires a `.env` file for configuration, but this file is **NOT committed to git** for security reasons.

### First-Time Setup

1. **Copy the environment template**:
   ```bash
   cp env.example .env
   ```

2. **Edit the `.env` file** with your preferred settings:
   ```bash
   # Use your preferred text editor
   nano .env
   # or
   code .env
   # or
   vim .env
   ```

3. **Restart services** after making changes:
   ```bash
   ./scripts/start_all.sh restart
   ```

### What's in the .env file?

The `.env` file contains your local configuration for:
- **RAG settings** (document search behavior)
- **LLM connection** (local AI model server)
- **Server ports** (backend and frontend)
- **Security tokens** (authentication)
- **AI model parameters** (context size, embeddings)

### Security Note

- ✅ **`.env` is ignored by git** - your local settings stay private
- ✅ **`env.example` is committed** - serves as a template for others
- ✅ **Never commit sensitive data** like API keys or tokens
- ✅ **Each developer** should have their own `.env` file

## Environment Variables

Synapse uses environment variables for configuration. You can set these in a `.env` file in the project root directory.

**📝 Note**: The `.env` file is excluded from git via `.gitignore` for security. Always use `env.example` as your starting template.

### Quick Setup

1. **Copy the example file**:
   ```bash
   cp env.example .env
   ```

2. **Edit `.env`** with your preferred settings
3. **Restart services** after making changes

### Configuration Categories

#### 🔍 **RAG Configuration**
Control how the AI searches and uses your knowledge base:

| Variable | Default | Description |
|----------|---------|-------------|
| `AUTO_RAG` | `false` | **Global RAG Control**: Enable/disable RAG for ALL messages |
| `RAG_TOP_K` | `4` | Number of document chunks to retrieve per query |
| `RAG_MAX_CHARS` | `1800` | Maximum characters to inject into AI context |
| `RAG_ALPHA` | `0.6` | Hybrid search balance (0=BM25 only, 1=vector only) |
| `RAG_VEC_K` | `64` | Vector search candidates before reranking |
| `RAG_BM25_K` | `64` | BM25 search candidates before reranking |
| `RAG_MMR_LAMBDA` | `0.6` | MMR diversity vs relevance balance |
| `RAG_MMR_POOL` | `24` | Pool size for MMR reranking |
| `RAG_USE_TITLES` | `1` | Enable title-based document retrieval |
| `RAG_TITLE_BOOST` | `0.25` | Weight multiplier for title similarity |
| `RAG_TITLE_K` | `64` | Maximum title vectors to consider |

#### 🤖 **LLM Configuration**
Connect to your local language model server:

| Variable | Default | Description |
|----------|---------|-------------|
| `LLAMA_URL` | `http://127.0.0.1:8080/v1/chat/completions` | URL of your llama.cpp server |
| `LLAMA_MODEL` | `qwen2.5-3b-instruct-q4_k_m` | Model identifier (for display only) |

#### ⚙️ **Backend Configuration**
Control the FastAPI server behavior:

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `9000` | Backend API server port |
| `HOST` | `127.0.0.1` | Backend server bind address |
| `CORS_ORIGINS` | `http://localhost:8501,http://127.0.0.1:8501` | Allowed frontend origins |
| `AUTH_TOKEN` | *(empty)* | Bearer token for API authentication |

#### 🎨 **Frontend Configuration**
Control the Streamlit UI:

| Variable | Default | Description |
|----------|---------|-------------|
| `BACKEND_URL` | `http://127.0.0.1:9000` | Backend API endpoint |

#### 🧠 **AI Model Configuration**
Advanced AI model settings:

| Variable | Default | Description |
|----------|---------|-------------|
| `EMB_MODEL` | `BAAI/bge-base-en-v1.5` | Embedding model for document vectors |
| `CTX_SIZE` | `32768` | Maximum context size for LLM |

#### 🛡️ **Guardian Configuration**
Content filtering and policy enforcement:

| Variable | Default | Description |
|----------|---------|-------------|
| `GUARDIAN_ENABLED` | `true` | Enable content filtering |
| `GUARD_PORT` | `8081` | Guardian proxy server port |

### Environment File Example

```bash
# Synapse Environment Configuration

# RAG Configuration
AUTO_RAG=false                    # Start with RAG disabled
RAG_TOP_K=4                      # Retrieve 4 chunks per query
RAG_MAX_CHARS=1800              # Max 1800 chars in AI context

# LLM Configuration  
LLAMA_URL=http://127.0.0.1:8080/v1/chat/completions
LLAMA_MODEL=qwen2.5-3b-instruct-q4_k_m

# Backend Configuration
PORT=9000                        # Backend API port
HOST=127.0.0.1                  # Bind to localhost only
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501

# Frontend Configuration
BACKEND_URL=http://127.0.0.1:9000

# AI Model Configuration
EMB_MODEL=BAAI/bge-base-en-v1.5  # Document embedding model
CTX_SIZE=32768                   # LLM context size hint
```

### Dynamic Configuration

Some settings can be changed at runtime through the UI:

- **RAG Toggle**: Use the Global RAG Control in the main chat area
- **Model Parameters**: Adjust temperature, top_p, max_tokens in the sidebar
- **RAG Settings**: Modify top_k and max_chars in the sidebar

**Note**: Changes made through the UI are persisted to the `.env` file and take effect immediately.

### Security Considerations

- **Local Development**: Leave `AUTH_TOKEN` empty for local use
- **Production**: Set `AUTH_TOKEN` to a strong, random value
- **Network Access**: Use `HOST=127.0.0.1` for local-only access
- **CORS**: Restrict `CORS_ORIGINS` to trusted frontend URLs only

## Knowledge Base (RAG)

- Upload docs from the Streamlit sidebar. Supported: txt, md, pdf, docx, rtf.
- The backend stores files under `workdir/docs/` and builds a FAISS index under `workdir/kb/`.

API endpoints (backend):

- `GET /config` → runtime config
- `POST /config` → update whitelisted keys (requires `AUTH_TOKEN` if set)
- `POST /rag/preview` {"query": "..."} → preview top chunks
- `GET /kb/stats` → index path, chunks, emb model, updated_at
- `POST /kb/upload` (multipart files) → save docs (requires `AUTH_TOKEN` if set)
- `POST /kb/reload` → rebuild FAISS index (requires `AUTH_TOKEN` if set)
- `POST /chat/stream` → Server-Sent Events stream for chat

Example: upload + index via curl

```bash
curl -X POST -F "files=@/path/to/file.pdf" http://127.0.0.1:9000/kb/upload
curl -X POST http://127.0.0.1:9000/kb/reload
```

## Optional guard proxy

`guard_proxy.py` can sit in front of a downstream LLM to redact outputs and enforce simple policies.

```bash
python3 guard_proxy.py  # listens on 127.0.0.1:8081
# set the backend to point to this proxy instead of llama.cpp if desired
```

## CLI chat (advanced)

- Minimal chat to the model: `bash scripts/start_chat.sh`
- RAG-enhanced CLI chat: `bash scripts/start_rag.sh`

Note: the backend already provides a streaming chat endpoint and the Streamlit UI is the primary interface.

## Seed restore (encrypted bundle)

This repository includes restore scripts for an encrypted seed archive referenced by `config.yml`.

Options:

- Simple: `bash scripts/restore_seed.sh`
- Advanced (integrity output and cleanup prompt): `bash scripts/restore.sh [ENC_FILE] [OUT_TAR] [EXTRACT_DIR]`

You will be prompted for AES key and IV (both hex). The decrypted TAR is extracted under the target directory (default `workdir`). Handle keys and plaintext artifacts with care.

## 📁 Project Structure & Git

### What's Excluded from Git

Synapse uses `.gitignore` to exclude sensitive and temporary files:

- **`.env`** - Your local environment configuration (copy from `env.example`)
- **`workdir/logs/`** - Application logs and runtime data
- **`workdir/pids/`** - Process ID files
- **`chat_core/kb/`** - Knowledge base indexes and metadata
- **`chat_core/history_*.jsonl`** - Chat conversation history
- **`*.log`** - Any log files
- **`.venv/`** - Python virtual environment
- **`__pycache__/`** - Python bytecode cache

### What's Included in Git

- **`env.example`** - Environment configuration template
- **Source code** - All Python, HTML, CSS, and configuration files
- **Scripts** - Startup and utility scripts
- **Documentation** - README, requirements, and examples

## Troubleshooting

### Common Issues

- Frontend cannot reach backend: ensure backend is on `http://127.0.0.1:9000` and `CORS_ORIGINS` allows `http://localhost:8501`.
- Backend 401 errors: unset `AUTH_TOKEN` for local dev, or modify the frontend to pass a bearer token to `BackendClient`.
- RAG preview shows no chunks: add docs under `workdir/docs/` and hit `POST /kb/reload`, or upload from the UI.
- Llama server connection failures: verify `LLAMA_URL` and that llama.cpp is serving on the expected port.

### Environment Configuration Issues

- **RAG not working**: Check `AUTO_RAG=true` in your `.env` file
- **Wrong ports**: Verify `PORT=9000` (backend) and `BACKEND_URL=http://127.0.0.1:9000` (frontend)
- **CORS errors**: Ensure `CORS_ORIGINS` includes your frontend URL
- **Authentication errors**: Set `AUTH_TOKEN` or leave it empty for local development
- **Model not responding**: Verify `LLAMA_URL` points to your running llama.cpp server

### Configuration Debugging

1. **Check current environment**:
   ```bash
   # Backend config endpoint
   curl http://127.0.0.1:9000/config
   
   # Frontend environment
   echo $BACKEND_URL
   ```

2. **Verify .env file**:
   ```bash
   cat .env | grep -v "^#" | grep -v "^$"
   ```

3. **Restart services** after `.env` changes:
   ```bash
   ./scripts/start_all.sh restart
   ```

## Docker (optional, no Dockerfile provided)

You can run services in ephemeral containers using the official Python image. If llama.cpp runs on the host, set `LLAMA_URL=http://host.docker.internal:8080/v1/chat/completions` inside containers.

Backend:

```bash
docker run --rm -it \
  -p 9000:9000 \
  -e CORS_ORIGINS=http://localhost:8501 \
  -e LLAMA_URL=http://host.docker.internal:8080/v1/chat/completions \
  -w /app -v "$PWD":/app python:3.11-slim bash -lc \
  "pip install --no-cache-dir -r backend/requirements.txt && \
    python -m pip install --no-cache-dir -r requirements.txt && \
    uvicorn backend.app:app --host 0.0.0.0 --port 9000 --no-server-header"
```

Frontend:

```bash
docker run --rm -it \
  -p 8501:8501 \
  -e BACKEND_URL=http://host.docker.internal:9000 \
  -w /app -v "$PWD":/app python:3.11-slim bash -lc \
  "pip install --no-cache-dir -r frontend/requirements.txt && \
    python -m streamlit run frontend/app.py --server.port 8501"
```

To rebuild images without cache, add `--no-cache` when you introduce Dockerfiles. For the ephemeral runs above, `pip install --no-cache-dir` avoids using pip's cache.