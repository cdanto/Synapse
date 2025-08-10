#!/usr/bin/env bash
# start_llama.sh — launch llama.cpp HTTP server on macOS (Metal)
# Works well for Apple M4 Pro (20-core GPU), Qwen2.5 7B q4_k_m

set -euo pipefail

# ---- paths (edit if needed) ----
BIN="${BIN:-$HOME/llama.cpp/build/bin/llama-server}"
MODEL_DIR="${MODEL_DIR:-$HOME/models/qwen2.5-3b}"
MODEL_FILE="${LLAMA_MODEL_FILE:-}"   # optional: point directly to a .gguf

# ---- server settings ----
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-8080}"

CTX_SIZE="${CTX_SIZE:-8192}"         # further reduced for speed
N_GPU_LAYERS="${N_GPU_LAYERS:-99}"   # push as many layers to GPU as possible
THREADS="${THREADS:-$(sysctl -n hw.ncpu)}"   # auto: CPU threads

NO_WARMUP="${NO_WARMUP:-1}"          # skip initial warmup if 1

# ---- pick a model file if not specified ----
if [[ -z "$MODEL_FILE" ]]; then
  CANDIDATE=$(ls -1 "$MODEL_DIR"/*.gguf 2>/dev/null | grep -i 'q4_k_m' | head -n 1 || true)
  if [[ -z "$CANDIDATE" ]]; then
    CANDIDATE=$(ls -1 "$MODEL_DIR"/*.gguf 2>/dev/null | head -n 1 || true)
  fi
  if [[ -z "$CANDIDATE" ]]; then
    echo "ERROR: No .gguf found in $MODEL_DIR" >&2
    exit 1
  fi
  MODEL_FILE="$CANDIDATE"
fi

# ---- sanity checks ----
if [[ ! -x "$BIN" ]]; then
  echo "ERROR: llama-server not found or not executable at: $BIN" >&2
  echo "Build it with:  (in llama.cpp)  make -j && make -j server" >&2
  exit 1
fi
if [[ ! -f "$MODEL_FILE" ]]; then
  echo "ERROR: model file not found: $MODEL_FILE" >&2
  exit 1
fi

echo "== llama.cpp server =="
echo "BIN        : $BIN"
echo "MODEL_FILE : $MODEL_FILE"
echo "HOST:PORT  : $HOST:$PORT"
echo "CTX_SIZE   : $CTX_SIZE"
echo "N_GPU_LAYERS: $N_GPU_LAYERS"
echo "THREADS    : $THREADS"
echo

CMD=(
  "$BIN"
  --model "$MODEL_FILE"
  --host "$HOST" --port "$PORT"
  --ctx-size "$CTX_SIZE"
  --n-gpu-layers "$N_GPU_LAYERS"
  --threads "$THREADS"
  --n-predict 512
  --batch-size 1024
  --ubatch-size 256
  --mlock
  --cont-batching
  --parallel 1
)

if [[ "$NO_WARMUP" == "1" ]]; then
  CMD+=( --no-warmup )
fi

if [[ "${1:-}" == "daemon" ]]; then
  LOG_DIR="${LOG_DIR:-$HOME/llama_logs}"
  mkdir -p "$LOG_DIR"
  TS=$(date +"%Y%m%d-%H%M%S")
  LOG_FILE="$LOG_DIR/server_$TS.log"
  echo "Starting in background… logs -> $LOG_FILE"
  nohup "${CMD[@]}" >"$LOG_FILE" 2>&1 &
  echo $! > "$LOG_DIR/server.pid"
  echo "PID $(cat "$LOG_DIR/server.pid")"
else
  echo "Starting in foreground… (Ctrl+C to stop)"
  exec "${CMD[@]}"
fi


