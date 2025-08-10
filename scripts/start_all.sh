#!/usr/bin/env bash
set -euo pipefail

# Orchestrate Synapse services in this order:
# 1) backend  2) llama  3) rag (CLI)  4) frontend

ROOT="$(cd "$(dirname "$0")"/.. && pwd)"
LOG_DIR="$ROOT/workdir/logs"
PID_DIR="$ROOT/workdir/pids"
mkdir -p "$LOG_DIR" "$PID_DIR"

export PYTHONIOENCODING="utf-8"
export LANG="en_US.UTF-8"
export LC_ALL="en_US.UTF-8"

die() { echo "ERROR: $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

ensure_venv() {
  if [[ ! -d "$ROOT/.venv" ]]; then
    have python3 || die "python3 not found"
    echo "Creating virtualenv at $ROOT/.venv ..."
    python3 -m venv "$ROOT/.venv"
  fi
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  python3 -m pip install --upgrade pip >/dev/null
}

install_reqs() {
  # shellcheck disable=SC1091
  source "$ROOT/.venv/bin/activate"
  echo "Installing Python dependencies (no cache)..."
  [[ -f "$ROOT/backend/requirements.txt" ]] && python3 -m pip install --no-cache-dir -r "$ROOT/backend/requirements.txt"
  [[ -f "$ROOT/frontend/requirements.txt" ]] && python3 -m pip install --no-cache-dir -r "$ROOT/frontend/requirements.txt"
  [[ -f "$ROOT/requirements.txt" ]] && python3 -m pip install --no-cache-dir -r "$ROOT/requirements.txt"
}

start_backend() {
  echo "Starting backend... (logs -> $LOG_DIR/backend.log)"
  nohup "$ROOT/scripts/start_backend.sh" >"$LOG_DIR/backend.log" 2>&1 &
  echo $! > "$PID_DIR/backend.pid"
}

start_llama() {
  echo "Starting llama server..."
  "$ROOT/scripts/start_llama.sh" daemon || die "failed to start llama"
  # Try to adopt PID written by llama launcher
  if [[ -f "$HOME/llama_logs/server.pid" ]]; then
    cp "$HOME/llama_logs/server.pid" "$PID_DIR/llama.pid"
  else
    # Fallback discovery
    pid=$(pgrep -f "llama-server.*--port[= ]8080" | head -n1 || true)
    [[ -n "${pid:-}" ]] && echo "$pid" > "$PID_DIR/llama.pid" || true
  fi
}

start_rag() {
  echo "Starting RAG CLI... (logs -> $LOG_DIR/rag.log)"
  nohup "$ROOT/scripts/start_rag.sh" >"$LOG_DIR/rag.log" 2>&1 &
  echo $! > "$PID_DIR/rag.pid"
}

start_frontend() {
  echo "Starting frontend... (logs -> $LOG_DIR/frontend.log)"
  nohup "$ROOT/scripts/start_frontend.sh" >"$LOG_DIR/frontend.log" 2>&1 &
  echo $! > "$PID_DIR/frontend.pid"
}

show_status() {
  for svc in backend llama rag frontend; do
    pid_file="$PID_DIR/$svc.pid"
    if [[ -f "$pid_file" ]] && pid=$(cat "$pid_file" 2>/dev/null); then
      if kill -0 "$pid" >/dev/null 2>&1; then
        echo "$svc: running (pid $pid)"
        continue
      fi
    fi
    echo "$svc: stopped"
  done
}

stop_one() {
  local name="$1"; shift
  local file="$1"; shift
  if [[ -f "$file" ]]; then
    local pid; pid="$(cat "$file" 2>/dev/null || true)"
    if [[ -n "$pid" ]]; then
      kill "$pid" 2>/dev/null || true
      for i in {1..20}; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
      done
      kill -9 "$pid" 2>/dev/null || true
    fi
    rm -f "$file"
  fi
}

stop_all() {
  stop_one frontend "$PID_DIR/frontend.pid"
  stop_one rag      "$PID_DIR/rag.pid"
  stop_one backend  "$PID_DIR/backend.pid"
  stop_one llama    "$PID_DIR/llama.pid"
  # also try external llama pid file if present
  [[ -f "$HOME/llama_logs/server.pid" ]] && stop_one llama "$HOME/llama_logs/server.pid" || true
}

cmd="${1:-start}"; shift || true
reinstall="0"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --reinstall) reinstall="1"; shift ;;
    *) break ;;
  esac
done

case "$cmd" in
  start)
    ensure_venv
    [[ "$reinstall" == "1" ]] && install_reqs
    start_backend
    sleep 1
    start_llama
    sleep 1
    start_rag
    sleep 1
    start_frontend
    show_status
    ;;
  stop)
    stop_all
    show_status
    ;;
  restart)
    stop_all
    ensure_venv
    [[ "$reinstall" == "1" ]] && install_reqs
    start_backend
    sleep 1
    start_llama
    sleep 1
    start_rag
    sleep 1
    start_frontend
    show_status
    ;;
  status)
    show_status
    ;;
  *)
    cat <<USAGE
Usage: $0 [start|stop|restart|status] [--reinstall]
  start         Start backend, llama, rag, frontend (in this order)
  stop          Stop all services
  restart       Stop then start all services
  status        Show simple service status
  --reinstall   Reinstall Python dependencies with --no-cache-dir (applies to start/restart)
USAGE
    exit 1
    ;;
esac


