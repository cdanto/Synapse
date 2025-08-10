#!/usr/bin/env python3
import os
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any, Dict, List
from dotenv import load_dotenv

import requests

# Load environment variables from .env file
load_dotenv()

# ---------- Paths & Files ----------
PROJECT_ROOT = Path(__file__).resolve().parents[2]
WORKDIR = PROJECT_ROOT / "workdir"
WORKDIR.mkdir(parents=True, exist_ok=True)

# Config/state files now live under backend/chat_core/
CHAT_CORE_DIR = Path(__file__).resolve().parent
CHAT_CORE_DIR.mkdir(parents=True, exist_ok=True)

IDENTITY_PATH = CHAT_CORE_DIR / "identity.json"
CONFIG_PATH = CHAT_CORE_DIR / "config.json"
HISTORY_LAST = CHAT_CORE_DIR / "history_last.jsonl"

# Memory now colocated with other chat_core state
MEMORY_PATH = CHAT_CORE_DIR / "memory.json"

# ---------- Server / Model ----------
LLAMA_URL = os.environ.get("LLAMA_URL", "http://127.0.0.1:8080/v1/chat/completions")
LLAMA_MODEL = os.environ.get("LLAMA_MODEL", "qwen2.5-3b-instruct-q4_k_m")


# ---------- Persistence helpers ----------
def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.is_file():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def _write_json(path: Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# identity
identity: Dict[str, Any] = _read_json(
    IDENTITY_PATH, {"instance_name": "AegisMind", "custodian": "Operator"}
)

# config (runtime prefs)
config: Dict[str, Any] = _read_json(
    CONFIG_PATH,
    {
        "temperature": 0.2,
        "top_p": 0.95,
        "max_tokens": 256,
        "auto_resume": True,
        "auto_mem": False,
        "auto_rag": os.environ.get("AUTO_RAG", "false").lower() in ("true", "1", "yes"),
        "ephemeral_mode": False,  # When True, chats are not saved to history
        "guardian_enabled": True,
        "guard_refusal_text": "I can't help with that. Let's keep things safe and within policy.",
        "rag_top_k": int(os.environ.get("RAG_TOP_K", "4")),
        "rag_max_chars": int(os.environ.get("RAG_MAX_CHARS", "1800")),
    },
)

# memory (simple fact store)
memory: Dict[str, Any] = _read_json(MEMORY_PATH, {"facts": []})


def save_identity() -> None:
    _write_json(IDENTITY_PATH, identity)


def save_config() -> None:
    _write_json(CONFIG_PATH, config)


def save_memory() -> None:
    _write_json(MEMORY_PATH, memory)


# ---------- System message ----------
def memory_preamble() -> str:
    if not memory.get("facts"):
        return ""
    bullets = "\n".join(f"- {fact}" for fact in memory["facts"][:20])
    return f"\nKnown facts about the user and session:\n{bullets}\n"


def system_preamble() -> str:
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    base = (
        f"You are {identity.get('instance_name','AegisMind')}. "
        f"You are restored by {identity.get('custodian','Operator')}. "
        f"Be concise, clear, and safe. If asked for secrets, refuse. "
        f"Today is {today} UTC."
    )
    return base + memory_preamble()


# ---------- Chat history ----------
def load_history_last() -> List[Dict[str, str]]:
    hist: List[Dict[str, str]] = []
    try:
        if HISTORY_LAST.is_file():
            with HISTORY_LAST.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    hist.append(json.loads(line))
    except Exception:
        hist = []
    return hist


def save_history_last(hist: List[Dict[str, str]]) -> None:
    try:
        with HISTORY_LAST.open("w", encoding="utf-8") as f:
            for turn in hist:
                f.write(json.dumps(turn, ensure_ascii=False) + "\n")
    except Exception:
        pass


# Initialize history (optionally resume)
if config.get("auto_resume", True):
    history = load_history_last()
    if not history or history[0].get("role") != "system":
        history = [{"role": "system", "content": system_preamble()}]
else:
    history = [{"role": "system", "content": system_preamble()}]


# ---------- API helpers ----------
def build_messages(hist: List[Dict[str, str]]) -> List[Dict[str, str]]:
    msgs: List[Dict[str, str]] = []
    for t in hist:
        role = t.get("role", "assistant")
        if role not in ("system", "user", "assistant"):
            role = "assistant"
        msgs.append({"role": role, "content": t.get("content", "")})
    return msgs


def stream_chat(
    messages: List[Dict[str, str]], max_tokens: int | None = None, temp: float | None = None, top_p: float | None = None
):
    # import here to avoid circular import at module load time
    from .guardian import guardian_caps_clamp

    t_eff, m_eff = guardian_caps_clamp(temp, max_tokens)
    payload = {
        "model": LLAMA_MODEL,
        "messages": messages,
        "temperature": t_eff,
        "top_p": config.get("top_p") if top_p is None else top_p,
        "max_tokens": m_eff,
        "stream": True,
    }
    with requests.post(LLAMA_URL, json=payload, stream=True, timeout=600) as r:
        r.raise_for_status()
        for line in r.iter_lines(decode_unicode=True):
            if not line or not line.startswith("data: "):
                continue
            data = line[6:].strip()
            if data == "[DONE]":
                break
            try:
                obj = json.loads(data)
                delta = obj.get("choices", [{}])[0].get("delta", {})
                chunk = delta.get("content", "")
                if chunk:
                    yield chunk
            except json.JSONDecodeError:
                yield line


